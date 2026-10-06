"""BrowserBridge -- Facade duy nhất kết nối Web Worker (Pyodide) và AppController.

Ranh giới kiến trúc:
  - CHỈ gọi qua chuviettay.controller.app_controller.AppController.
  - KHÔNG BAO GIỜ import chuviettay.model, chuviettay.view, chuviettay.cli, tkinter.
  - Toàn bộ kết quả trả về là JSON-serializable (chuyển đổi tuple/set sang list).
  - Bắt mọi ngoại lệ và đóng gói theo chuẩn {ok: False, error: str, error_type: str}.
"""
from __future__ import annotations

import base64
import dataclasses
import os
import re
import tempfile
from typing import Any

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.controller.teach_geometry import (
    BASE_PX,
    CANVAS_H,
    CANVAS_W,
    MIN_POINT_DIST,
    ZOOM,
    strokes_to_bank_units,
)
from chuviettay.document.ir import Document, PageBreak
from chuviettay.importer.markdown_importer import MarkdownImporter

# Regex nhận diện thẻ ngắt trang
PAGEBREAK_RE = re.compile(r"<!--\s*pagebreak\s*-->|\\pagebreak", re.IGNORECASE)


def _err_res(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": str(exc),
        "error_type": type(exc).__name__,
    }


def _clean_json(obj: Any) -> Any:
    """Chuyển đổi triệt để tuple và set sang list để đảm bảo JSON serialization an toàn."""
    if isinstance(obj, (list, tuple, set)):
        return [_clean_json(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _clean_json(v) for k, v in obj.items()}
    if dataclasses.is_dataclass(obj):
        return _clean_json(dataclasses.asdict(obj))
    return obj


class BrowserBridge:
    """Cầu nối giữa môi trường trình duyệt Web và hệ thống Chữ Viết Tay."""

    def __init__(self, bank_path: str | None = None):
        self.bank_path: str = bank_path or "/tmp/active_bank.json.gz"
        self._ctl: AppController = AppController(
            bank_path=self.bank_path,
            timer_factory=lambda *a, **k: None,  # Môi trường Web Worker không tạo thread Timer
        )

    def init(self) -> dict[str, Any]:
        """Khởi tạo kho mẫu tại bank_path nếu chưa có."""
        try:
            self._ctl.load_bank(self.bank_path, create_if_missing=True)
            return {"ok": True}
        except Exception as e:
            return _err_res(e)

    @property
    def session_scale(self) -> float:
        """Hệ số cỡ tay hiện tại của phiên."""
        return float(self._ctl.session_scale)

    @session_scale.setter
    def session_scale(self, val: float) -> None:
        self._ctl.session_scale = float(val)

    def get_canvas_spec(self, label: str = "") -> dict[str, Any]:
        """Cung cấp các thông số hình học chuẩn của canvas dạy từ."""
        try:
            if self._ctl.bank is not None:
                xh = float(self._ctl.x_height or 7.94)
            else:
                xh = 7.94
            xh_px = round(xh * ZOOM, 2)
            return {
                "ok": True,
                "width": CANVAS_W,
                "height": CANVAS_H,
                "base_px": BASE_PX,
                "zoom": ZOOM,
                "min_point_dist": MIN_POINT_DIST,
                "xh": xh,
                "guidelines": {
                    "baseline": float(BASE_PX),
                    "xh_line": round(BASE_PX - xh_px, 2),
                    "hw3_lines": {
                        "top": round(BASE_PX - 2.0 * xh_px, 2),
                        "mean": round(BASE_PX - xh_px, 2),
                        "base": float(BASE_PX),
                        "bottom": round(BASE_PX + 0.5 * xh_px, 2),
                    },
                },
                "hw3_guides": {
                    "baseline": BASE_PX,
                },
            }
        except Exception as e:
            return _err_res(e)

    def get_write_defaults(self) -> dict[str, Any]:
        """Trả về toàn bộ các giá trị mặc định của WriteOptions."""
        try:
            opts = WriteOptions()
            return {"ok": True, "data": _clean_json(opts)}
        except Exception as e:
            return _err_res(e)

    def load_bank(self, gz_bytes: bytes, create_if_missing: bool = False) -> dict[str, Any]:
        """Ghi nạp file kho mẫu gzip bytes vào MEMFS và nạp vào Controller."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.bank_path)), exist_ok=True)
            with open(self.bank_path, "wb") as f:
                f.write(gz_bytes)
            self._ctl.load_bank(self.bank_path, create_if_missing=create_if_missing)
            stats = self.get_stats()
            return {"ok": True, "stats": stats.get("data", {})}
        except Exception as e:
            return _err_res(e)

    def export_bank(self) -> bytes:
        """Ép lưu các thay đổi và trả về nội dung nhị phân (.json.gz)."""
        self._ctl.flush_save()
        if os.path.exists(self.bank_path):
            with open(self.bank_path, "rb") as f:
                return f.read()
        return b""

    def get_stats(self) -> dict[str, Any]:
        """Thống kê chi tiết số từ, mẫu, ký tự, dấu thanh trong kho."""
        try:
            stats = self._ctl.get_stats()
            return {"ok": True, "data": _clean_json(stats)}
        except Exception as e:
            return _err_res(e)

    def write_text(
        self,
        text: str,
        options: dict[str, Any] | None = None,
        fmt: str = "txt",
    ) -> dict[str, Any]:
        """Dàn trang và kết xuất văn bản thành file .xopp.
        Hỗ trợ ngắt trang `<!-- pagebreak -->` / `\\pagebreak` khi fmt='md'."""
        try:
            opts_dict = options or {}
            # Lọc các trường hợp lệ của WriteOptions
            valid_fields = {f.name for f in dataclasses.fields(WriteOptions)}
            filtered_opts = {k: v for k, v in opts_dict.items() if k in valid_fields}
            write_opts = WriteOptions(**filtered_opts)

            with tempfile.NamedTemporaryFile(suffix=".xopp", delete=False) as tmp:
                out_path = tmp.name

            missing_token_boxes: list[dict[str, Any]] = []

            def _token_cb(box: Any) -> None:
                if box.missing:
                    missing_token_boxes.append(dataclasses.asdict(box))

            try:
                warnings_list: list[str] = []
                # Xử lý ngắt trang nếu là định dạng markdown hoặc có chứa cú pháp ngắt trang
                if fmt == "md" or PAGEBREAK_RE.search(text):
                    chunks = PAGEBREAK_RE.split(text)
                    all_blocks = []
                    md_importer = MarkdownImporter()
                    for idx, chunk in enumerate(chunks):
                        clean_chunk = chunk.strip()
                        if clean_chunk:
                            res = md_importer.import_text(clean_chunk)
                            all_blocks.extend(res.document.blocks)
                            warnings_list.extend(res.warnings)
                        if idx < len(chunks) - 1:
                            all_blocks.append(PageBreak())
                    doc = Document(blocks=all_blocks)
                    result = self._ctl.write_document(doc, write_opts, out_path, token_layout_callback=_token_cb)
                else:
                    result = self._ctl.write_text(text, write_opts, out_path, token_layout_callback=_token_cb)

                with open(out_path, "rb") as f:
                    xopp_bytes = f.read()

                missing_sorted = [list(item) for item in result.missing_sorted()]

                res_data = {
                    "ok": True,
                    "xopp_base64": base64.b64encode(xopp_bytes).decode("ascii"),
                    "n_pages": result.n_pages,
                    "n_lines": result.n_lines,
                    "n_strokes": result.n_strokes,
                    "n_tokens": result.n_tokens,
                    "n_missing_tokens": result.n_missing_tokens,
                    "missing_sorted": missing_sorted,
                    "missing_token_boxes": missing_token_boxes,
                    "warnings": warnings_list,
                }
                return res_data
            finally:
                if os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except OSError:
                        pass
        except Exception as e:
            return _err_res(e)

    def teach_sample(
        self,
        label: str,
        strokes: list[list[float]] | None = None,
        width: float | None = None,
        category: str = "letters",
        calibrating: bool = False,
        pixel_strokes: list[list[tuple[float, float]]] | None = None,
        deferred_save: bool = True,
    ) -> dict[str, Any]:
        """Lưu một mẫu ký tự đã vẽ trực tiếp."""
        try:
            if pixel_strokes:
                norm_px = [[(float(pt[0]), float(pt[1])) for pt in st] for st in pixel_strokes]
                rel_strokes, w = strokes_to_bank_units(norm_px, self._ctl.session_scale)
                recompute_fn = lambda new_scale: strokes_to_bank_units(norm_px, new_scale)
            else:
                rel_strokes = [list(st) for st in (strokes or [])]
                w = float(width if width is not None else 0.0)
                recompute_fn = None

            outcome = self._ctl.teach_char(
                label,
                rel_strokes,
                w,
                calibrating=calibrating,
                recompute=recompute_fn,
                deferred_save=deferred_save,
            )

            res = {
                "ok": True,
                "label": outcome.label,
                "session_scale": outcome.session_scale,
                "recalibrated": outcome.recalibrated,
                "outcome": _clean_json(outcome),
            }
            return res
        except Exception as e:
            return _err_res(e)

    def pick_calibration_char(self) -> dict[str, Any]:
        """Chọn ký tự mốc ổn định để đo cỡ tay."""
        try:
            ch = self._ctl.pick_calibration_char()
            return {"ok": True, "char": ch, "word": ch}
        except Exception as e:
            return _err_res(e)

    def pick_calibration_word(self) -> dict[str, Any]:
        """Chọn từ/ký tự mốc ổn định để đo cỡ tay (deprecated alias)."""
        return self.pick_calibration_char()

    def import_grid(self, xopp_bytes: bytes, dedup: bool = True) -> dict[str, Any]:
        """Nạp file .xopp lưới ô tập viết và cập nhật kho ký tự mẫu."""
        try:
            res = self._ctl.import_grid(xopp_bytes, dedup=dedup)
            return {
                "ok": True,
                "data": _clean_json(res),
            }
        except Exception as e:
            return _err_res(e)

    def teach_char(
        self,
        label: str,
        strokes: list[list[float]] | None = None,
        width: float | None = None,
        calibrating: bool = False,
        pixel_strokes: list[list[tuple[float, float]]] | None = None,
        deferred_save: bool = True,
    ) -> dict[str, Any]:
        """Lưu một mẫu ký tự vào kho tương ứng (chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh)."""
        try:
            if pixel_strokes:
                norm_px = [[(float(pt[0]), float(pt[1])) for pt in st] for st in pixel_strokes]
                rel_strokes, w = strokes_to_bank_units(norm_px, self._ctl.session_scale)
                recompute_fn = lambda new_scale: strokes_to_bank_units(norm_px, new_scale)
            else:
                rel_strokes = [list(st) for st in (strokes or [])]
                w = float(width if width is not None else 0.0)
                recompute_fn = None

            outcome = self._ctl.teach_char(
                label,
                rel_strokes,
                w,
                calibrating=calibrating,
                recompute=recompute_fn,
                deferred_save=deferred_save,
            )
            return {
                "ok": True,
                "label": outcome.label,
                "session_scale": outcome.session_scale,
                "recalibrated": outcome.recalibrated,
                "outcome": _clean_json(outcome),
            }
        except Exception as e:
            return _err_res(e)

    def get_char_catalog(self, group_id: str = "co_ban") -> dict[str, Any]:
        """Lấy danh mục ký tự mẫu theo nhóm."""
        try:
            group = self._ctl.get_char_catalog(group_id)
            return {
                "ok": True,
                "data": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "chars": list(group.chars),
                },
            }
        except Exception as e:
            return _err_res(e)

    def list_char_catalogs(self) -> dict[str, Any]:
        """Trả về danh sách tóm tắt tất cả các nhóm catalog ký tự có sẵn."""
        try:
            groups = self._ctl.list_char_catalogs()
            res_data = [
                {"id": g.id, "name": g.name, "description": g.description, "count": len(g.chars)}
                for g in groups
            ]
            return {"ok": True, "data": res_data}
        except Exception as e:
            return _err_res(e)

    def export_char_grid(self, group_id: str = "co_ban", target_xh: float = 7.94) -> dict[str, Any]:
        """Sinh file lưới ô chuẩn hw3 cho nhóm ký tự để tải về."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".xopp", delete=False) as tmp:
                out_path = tmp.name
            try:
                self._ctl.export_letter_grid(out_path, target_xh=target_xh, group_id=group_id)
                with open(out_path, "rb") as f:
                    xopp_bytes = f.read()
                return {
                    "ok": True,
                    "xopp_base64": base64.b64encode(xopp_bytes).decode("ascii"),
                }
            finally:
                if os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except OSError:
                        pass
        except Exception as e:
            return _err_res(e)

    def get_missing_queue(
        self,
        kind: str = "co_ban",
        limit: int = 50,
        exclude: list[str] | None = None,
    ) -> dict[str, Any]:
        """Lấy danh sách các ký tự còn thiếu trong hàng đợi dạy chữ."""
        try:
            ex = set(exclude or [])
            if kind in ("co_ban", "toan_hy_lap", "mo_rong", "day_du"):
                tokens = self._ctl.get_missing_chars(group_id=kind, exclude=ex)
            elif kind == "essentials":
                tokens = self._ctl.missing_minimal_essentials(exclude=ex)
            else:
                tokens = self._ctl.missing_seed_words(limit, exclude=ex)
            return {"ok": True, "tokens": tokens}
        except Exception as e:
            return _err_res(e)

    def get_missing_chars(
        self,
        group_id: str = "co_ban",
        exclude: list[str] | None = None,
    ) -> dict[str, Any]:
        """Lấy danh sách các ký tự còn thiếu theo nhóm catalog."""
        try:
            ex = set(exclude or [])
            tokens = self._ctl.get_missing_chars(group_id=group_id, exclude=ex)
            return {"ok": True, "tokens": tokens}
        except Exception as e:
            return _err_res(e)

    def list_category_items(self, category: str = "letters") -> dict[str, Any]:
        """Liệt kê danh sách [nhãn, số mẫu] của một danh mục cụ thể."""
        try:
            bank = self._ctl._require_bank()
            cat_map = {
                "words": bank.words,
                "letters": getattr(bank, "letters", {}),
                "digits": bank.digits,
                "punct": bank.punct,
                "symbols": getattr(bank, "symbols", {}),
                "marks": bank.marks,
            }
            target = cat_map.get(category, {})
            items = sorted([k, len(v)] for k, v in target.items())
            return {"ok": True, "data": items}
        except Exception as e:
            return _err_res(e)

    def list_words(self) -> dict[str, Any]:
        """Liệt kê danh sách các từ và số mẫu."""
        try:
            words = self._ctl.list_words()
            return {"ok": True, "data": [[w, c] for (w, c) in words]}
        except Exception as e:
            return _err_res(e)

    def list_letters(self) -> dict[str, Any]:
        """Liệt kê danh sách các chữ cái và số mẫu."""
        try:
            letters = self._ctl.list_letters()
            return {"ok": True, "data": [[ch, c] for (ch, c) in letters]}
        except Exception as e:
            return _err_res(e)

    def list_label_samples(self, label: str, category: str = "words") -> dict[str, Any]:
        """Lấy danh sách các mẫu của một nhãn cụ thể."""
        try:
            samples = self._ctl.list_label_samples(label, category=category)
            return {"ok": True, "data": _clean_json(samples)}
        except Exception as e:
            return _err_res(e)

    def drop_label(self, label: str, category: str = "words") -> dict[str, Any]:
        """Xoá toàn bộ mẫu của một nhãn."""
        try:
            if category in ("letters", "digits", "punct", "symbols", "marks"):
                res = self._ctl.drop_char(label)
            else:
                res = self._ctl.drop_words([label], category=category)
            return {"ok": True, "data": _clean_json(res)}
        except Exception as e:
            return _err_res(e)

    def drop_chars(self, chars: list[str]) -> dict[str, Any]:
        """Xoá hàng loạt danh sách các ký tự khỏi kho mẫu."""
        try:
            res = self._ctl.drop_chars(chars)
            return {
                "ok": True,
                "data": _clean_json(res),
                "total_removed_chars": res.total_removed_chars,
                "total_removed_samples": res.total_removed_samples,
            }
        except Exception as e:
            return _err_res(e)

    def flush_save(self) -> dict[str, Any]:
        """Ép lưu các thay đổi đang hoãn xuống đĩa."""
        try:
            self._ctl.flush_save()
            return {"ok": True}
        except Exception as e:
            return _err_res(e)

    def export_check(self) -> dict[str, Any]:
        """Xuất file .xopp kiểm tra toàn bộ mẫu chữ đã học dạng lưới ô (lệnh check)."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".xopp", delete=False) as tmp:
                out_path = tmp.name
            try:
                result = self._ctl.export_check(out_path)
                with open(out_path, "rb") as f:
                    xopp_bytes = f.read()
                return {
                    "ok": True,
                    "xopp_base64": base64.b64encode(xopp_bytes).decode("ascii"),
                    "n_words": result.n_words,
                }
            finally:
                if os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except OSError:
                        pass
        except Exception as e:
            return _err_res(e)

    def get_latex_symbols(self) -> dict[str, Any]:
        """Trả về danh sách ký hiệu LaTeX gom nhóm theo loại để hiển thị trên web."""
        try:
            from chuviettay.math.symbols import LATEX_SYMBOL_MAP

            categories = {
                "Hy Lạp thường": [r"\alpha", r"\beta", r"\gamma", r"\delta", r"\epsilon", r"\theta", r"\lambda", r"\mu", r"\pi", r"\rho", r"\sigma", r"\tau", r"\phi", r"\omega"],
                "Hy Lạp hoa": [r"\Gamma", r"\Delta", r"\Theta", r"\Lambda", r"\Pi", r"\Sigma", r"\Phi", r"\Psi", r"\Omega"],
                "Toán tử & Phép tính": [r"\pm", r"\mp", r"\times", r"\div", r"\cdot", r"\sum", r"\prod", r"\int", r"\oint", r"\oplus", r"\otimes"],
                "Quan hệ & So sánh": [r"\le", r"\ge", r"\ne", r"\approx", r"\equiv", r"\sim", r"\in", r"\notin", r"\subset", r"\supset", r"\subseteq", r"\supseteq"],
                "Mũi tên": [r"\to", r"\leftarrow", r"\leftrightarrow", r"\Rightarrow", r"\Leftarrow", r"\Leftrightarrow", r"\mapsto"],
                "Logic & Tập hợp": [r"\infty", r"\forall", r"\exists", r"\emptyset", r"\nabla", r"\partial", r"\angle"],
            }
            res_symbols = {}
            for cat, macros in categories.items():
                res_symbols[cat] = [
                    {"latex": m, "display": LATEX_SYMBOL_MAP.get(m, m)}
                    for m in macros
                ]
            return {"ok": True, "symbols": res_symbols}
        except Exception as e:
            return _err_res(e)

    def import_docx(self, docx_bytes: bytes) -> dict[str, Any]:
        """Nạp tệp .docx và trích xuất nội dung văn bản / markdown."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(docx_bytes)
                docx_path = tmp.name
            try:
                res = self._ctl.import_document(docx_path, fmt="docx")
                lines = []
                for b in res.document.blocks:
                    if hasattr(b, "inlines"):
                        line_parts = []
                        for inl in b.inlines:
                            if hasattr(inl, "text") and inl.text:
                                line_parts.append(inl.text)
                            elif hasattr(inl, "latex") and inl.latex:
                                line_parts.append(f"${inl.latex}$")
                            elif hasattr(inl, "symbol") and inl.symbol:
                                line_parts.append(inl.symbol)
                        lines.append(" ".join(line_parts))
                return {
                    "ok": True,
                    "markdown_text": "\n\n".join(lines),
                    "warnings": res.warnings,
                    "unsupported": res.unsupported,
                }
            finally:
                if os.path.exists(docx_path):
                    try:
                        os.remove(docx_path)
                    except OSError:
                        pass
        except Exception as e:
            return _err_res(e)
