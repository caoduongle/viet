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
import uuid

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
from chuviettay.document.ir import Document, Heading, LineBreak, ListBlock, MathBlock, PageBreak, Table, TableCell
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
        self.bank_revision: int = 1
        self.worker_epoch: str = str(uuid.uuid4())
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

    def get_page_catalog(self) -> dict[str, Any]:
        """Cung cấp danh mục khổ giấy, mẫu nền và tone màu chuẩn."""
        try:
            cat = self._ctl.get_page_catalog()
            return {"ok": True, "catalog": _clean_json(cat)}
        except Exception as e:
            return _err_res(e)

    def load_bank(self, gz_bytes: bytes, create_if_missing: bool = False) -> dict[str, Any]:
        """Ghi nạp file kho mẫu gzip bytes vào MEMFS và nạp vào Controller."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.bank_path)), exist_ok=True)
            with open(self.bank_path, "wb") as f:
                f.write(gz_bytes)
            self._ctl.load_bank(self.bank_path, create_if_missing=create_if_missing)
            self.bank_revision += 1
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

    def get_bank_snapshot(self, profile_id: str = "default") -> dict[str, Any]:
        """Cung cấp toàn bộ dữ liệu snapshot của kho mẫu trong một lượt gọi duy nhất."""
        try:
            stats_res = self.get_stats()
            if not stats_res.get("ok"):
                return stats_res
            stats = stats_res.get("data", {})

            letters_res = self.list_letters()
            if not letters_res.get("ok"):
                return letters_res
            symbols_res = self.list_category_items("symbols")
            if not symbols_res.get("ok"):
                return symbols_res
            marks_res = self.list_category_items("marks")
            if not marks_res.get("ok"):
                return marks_res

            data = {
                "revision": self.bank_revision,
                "worker_epoch": self.worker_epoch,
                "profile_id": str(profile_id),
                "stats": stats,
                "letters": letters_res.get("data", []),
                "digits": stats.get("digit_counts", {}),
                "punct": stats.get("punct_counts", {}),
                "symbols": symbols_res.get("data", []),
                "marks": marks_res.get("data", []),
            }
            return {
                "ok": True,
                "data": _clean_json(data),
            }
        except Exception as exc:
            return _err_res(exc)

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
            ignored_options = sorted([k for k in opts_dict.keys() if k not in valid_fields])
            write_opts = WriteOptions(**filtered_opts)

            with tempfile.NamedTemporaryFile(suffix=".xopp", delete=False) as tmp:
                out_path = tmp.name

            missing_token_boxes: list[dict[str, Any]] = []

            def _token_cb(box: Any) -> None:
                if box.missing:
                    missing_token_boxes.append(dataclasses.asdict(box))

            try:
                warnings_list: list[str] = []
                unsupported_list: list[str] = []
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
                            unsupported_list.extend(res.unsupported)
                        if idx < len(chunks) - 1:
                            all_blocks.append(PageBreak())
                    doc = Document(blocks=all_blocks)
                    result = self._ctl.write_document(doc, write_opts, out_path, token_layout_callback=_token_cb)
                else:
                    result = self._ctl.write_text(text, write_opts, out_path, token_layout_callback=_token_cb)

                if getattr(result, "warnings", None):
                    warnings_list.extend(result.warnings)
                if getattr(result, "unsupported", None):
                    unsupported_list.extend(result.unsupported)

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
                    "unsupported": unsupported_list,
                    "seed_used": getattr(result, "seed_used", None),
                    "ignored_options": ignored_options,
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

    def clear_document_history(self) -> dict[str, Any]:
        """Đặt lại tài liệu và hạt giống đã căn chỉnh của lượt trước trong AppController."""
        try:
            self._ctl.clear_document_history()
            return {"ok": True}
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
            self.bank_revision += 1

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
            self.bank_revision += 1
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
            self.bank_revision += 1
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
            self.bank_revision += 1
            return {"ok": True, "data": _clean_json(res)}
        except Exception as e:
            return _err_res(e)

    def drop_chars(self, chars: list[str]) -> dict[str, Any]:
        """Xoá hàng loạt danh sách các ký tự khỏi kho mẫu."""
        try:
            res = self._ctl.drop_chars(chars)
            self.bank_revision += 1
            return {
                "ok": True,
                "data": _clean_json(res),
                "total_removed_chars": res.total_removed_chars,
                "total_removed_samples": res.total_removed_samples,
            }
        except Exception as e:
            return _err_res(e)

    def drop_label_samples(
        self,
        label: str,
        indices: list[int],
        category: str = "words",
    ) -> dict[str, Any]:
        """Xoá các biến thể mẫu nét cụ thể của một nhãn."""
        try:
            res = self._ctl.drop_label_samples(label, indices, category=category)
            self.bank_revision += 1
            return {"ok": True, "data": _clean_json(res)}
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
                return self._document_to_markdown_dict(res.document, res.warnings, res.unsupported)
            finally:
                if os.path.exists(docx_path):
                    try:
                        os.remove(docx_path)
                    except OSError:
                        pass
        except Exception as e:
            return _err_res(e)

    def _document_to_markdown_dict(
        self,
        doc: Document,
        warnings: list[str] | None = None,
        unsupported: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tuần tự hóa Document IR thành Markdown dạng text, bảo toàn số cột logic bằng 2D occupancy grid."""
        lines: list[str] = []
        warnings_out = list(warnings or [])
        unsupported_out = list(unsupported or [])

        def _escape_md(text: str) -> str:
            """Escape các ký tự điều khiển Markdown để bảo toàn nguyên vẹn khi re-import."""
            if not text:
                return ""
            # Escape gạch chéo ngược đầu tiên, sau đó các ký tự đặc biệt
            s = text.replace("\\", "\\\\")
            for ch in ("*", "_", "~", "#", "$", "|"):
                s = s.replace(ch, "\\" + ch)
            return s

        def _serialize_inlines(inlines: list[Any], line_break_sep: str = "\n", escape_pipe_in_math: bool = False) -> str:
            parts: list[str] = []
            for inl in inlines:
                if hasattr(inl, "text") and inl.text:
                    t = inl.text
                    if line_break_sep != "\n":
                        t = t.replace("\r\n", line_break_sep).replace("\n", line_break_sep)
                    parts.append(_escape_md(t))
                elif hasattr(inl, "latex") and inl.latex:
                    ltx = inl.latex.replace("|", r"\|") if escape_pipe_in_math else inl.latex
                    parts.append(f"${ltx}$")
                elif hasattr(inl, "symbol") and inl.symbol:
                    parts.append(_escape_md(inl.symbol))
                elif isinstance(inl, LineBreak):
                    parts.append(line_break_sep)
            return "".join(parts)

        def _extract_cell_markdown(cell: TableCell) -> str:
            block_strs: list[str] = []
            for blk in cell.blocks:
                if isinstance(blk, MathBlock) and blk.latex:
                    escaped_latex = blk.latex.replace("|", r"\|")
                    block_strs.append(f"${escaped_latex}$")
                elif hasattr(blk, "inlines"):
                    s = _serialize_inlines(blk.inlines, line_break_sep=" ", escape_pipe_in_math=True).strip()
                    if s:
                        block_strs.append(s)
            txt = " ".join(block_strs).strip()
            return txt if txt else " "

        def _serialize_list_block(lb: ListBlock, depth: int = 0) -> str:
            list_lines: list[str] = []
            pad = "  " * depth
            for idx, item_blocks in enumerate(lb.items):
                marker = f"{lb.start + idx}. " if lb.ordered else "- "
                first_sub = True
                for sub in item_blocks:
                    if isinstance(sub, ListBlock):
                        sub_str = _serialize_list_block(sub, depth + 1)
                        if sub_str:
                            list_lines.append(sub_str)
                    elif isinstance(sub, MathBlock) and sub.latex:
                        prefix = (pad + marker) if first_sub else (pad + "  ")
                        first_sub = False
                        list_lines.append(f"{prefix}$${sub.latex.strip()}$$")
                    elif hasattr(sub, "inlines"):
                        prefix = (pad + marker) if first_sub else (pad + "  ")
                        first_sub = False
                        s = _serialize_inlines(sub.inlines, line_break_sep=" ")
                        list_lines.append(f"{prefix}{s}")
            return "\n".join(list_lines)

        for b in doc.blocks:
            if isinstance(b, MathBlock):
                if b.latex:
                    lines.append(f"$${b.latex.strip()}$$")
            elif isinstance(b, PageBreak):
                lines.append(r"\pagebreak")
            elif isinstance(b, ListBlock):
                lb_str = _serialize_list_block(b)
                if lb_str:
                    lines.append(lb_str)
            elif hasattr(b, "inlines"):
                if isinstance(b, Heading):
                    lvl = max(1, min(6, getattr(b, "level", 1)))
                    prefix = "#" * lvl + " "
                    content_str = _serialize_inlines(b.inlines, line_break_sep=" ")
                    lines.append(prefix + content_str)
                else:
                    content_str = _serialize_inlines(b.inlines, line_break_sep="\n")
                    lines.append(content_str)
            elif isinstance(b, Table) and b.rows:
                has_merges = any(
                    c.rowspan > 1 or c.colspan > 1
                    for r in b.rows for c in r.cells
                )
                if has_merges:
                    warnings_out.append(
                        "Bảng chứa ô gộp (hàng/cột): cấu trúc được giản lược sang dạng bảng Markdown."
                    )

                # 2D Occupancy Grid: phục hồi toạ độ cột và tổng số cột logic
                occupied: set[tuple[int, int]] = set()
                placements: list[tuple[int, int, int, int, TableCell]] = []
                max_c = 0
                for r_idx, row in enumerate(b.rows):
                    c_cursor = 0
                    for cell in row.cells:
                        while (r_idx, c_cursor) in occupied:
                            c_cursor += 1
                        cs = max(1, getattr(cell, "colspan", 1))
                        rs = max(1, getattr(cell, "rowspan", 1))
                        placements.append((r_idx, c_cursor, rs, cs, cell))
                        for dr in range(rs):
                            for dc in range(cs):
                                occupied.add((r_idx + dr, c_cursor + dc))
                        c_cursor += cs
                        max_c = max(max_c, c_cursor)

                num_cols = max(max_c, 1)
                num_rows = len(b.rows)

                # Tạo lưới 2D chứa nội dung cell đã trích xuất và ô đệm " "
                grid: list[list[str]] = [[" " for _ in range(num_cols)] for _ in range(num_rows)]
                for r, c, rs, cs, cell in placements:
                    grid[r][c] = _extract_cell_markdown(cell)

                # Căn lề các cột
                col_alignments = b.col_alignments or []
                align_markers = []
                for c_idx in range(num_cols):
                    align = col_alignments[c_idx].lower() if c_idx < len(col_alignments) else "left"
                    if align == "center":
                        align_markers.append(":---:")
                    elif align == "right":
                        align_markers.append("---:")
                    else:
                        align_markers.append(":---")

                table_lines = [
                    "| " + " | ".join(grid[0]) + " |",
                    "| " + " | ".join(align_markers) + " |",
                ]

                for r_idx in range(1, num_rows):
                    table_lines.append("| " + " | ".join(grid[r_idx]) + " |")

                lines.append("\n".join(table_lines))

        return {
            "ok": True,
            "markdown_text": "\n\n".join(lines),
            "warnings": warnings_out,
            "unsupported": unsupported_out,
        }
