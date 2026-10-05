"""FidelityLayoutEngine: Đặt nét vẽ viết tay vào đúng bounding box không gian mà không reflow."""
from __future__ import annotations

import logging
import os
import random
from typing import TYPE_CHECKING

from chuviettay.fidelity.fixed_model import FixedDocument
from chuviettay.model import xopp
from chuviettay.model.composer import WriteOptions, WriteResult
from chuviettay.model.text_utils import normalize_text, place
from chuviettay.model.writer import Writer

if TYPE_CHECKING:
    from chuviettay.model.bank import Bank

_log = logging.getLogger(__name__)


class FidelityLayoutEngine:
    """Công cụ dàn nét chữ viết tay khớp theo tọa độ cố định của tài liệu."""

    def __init__(self, bank: Bank, opts: WriteOptions) -> None:
        self.bank = bank
        self.opts = opts
        self.rnd = random.Random(opts.seed)
        self.wr = Writer(bank, self.rnd, opts.jitter, not opts.strict_case, opts.space, assemble_letters=opts.assemble_letters)

    def render(self, document: FixedDocument, out_path: str) -> WriteResult:
        """Kết xuất FixedDocument thành tệp .xopp đa trang liên kết PDF nền."""
        self.opts.validate()

        # Xác định tên tệp PDF nền (ưu tiên đường dẫn relative để đảm bảo tính di động)
        bg_pdf = document.background_pdf_path
        if bg_pdf:
            bg_filename = os.path.basename(bg_pdf)
        else:
            bg_filename = os.path.splitext(os.path.basename(out_path))[0] + "_background.pdf"

        parts = [xopp.HEAD]
        total_strokes = 0
        total_tokens = 0
        missing_tokens = 0
        total_lines = 0

        # Lấy khoảng cách từ các mẫu khoảng trống
        gaps = [g for g in self.bank.d.get("wgaps", []) if 6.0 <= g <= 20.0] or [11.0]
        base_scale = self.opts.scale
        bank_xh = getattr(self.bank, "xh", 16.0)

        for page in document.pages:
            p_w = page.width
            p_h = page.height
            p_idx = page.page_index

            bg_xml = xopp.pdf_background_xml(bg_filename, p_idx, domain="relative")
            parts.append(xopp.page_open_xml(p_w, p_h, background=bg_xml))

            page_strokes: list[str] = []

            for tb in page.text_boxes:
                raw_text = tb.text.strip()
                if not raw_text:
                    continue

                total_lines += 1
                norm_text = normalize_text(raw_text)
                words = norm_text.split()
                if not words:
                    continue

                # Tính tỷ lệ thu phóng theo font size ban đầu so với x-height kho mẫu (R5)
                target_font_size = tb.font_size or 12.0
                font_scale_ratio = target_font_size / (bank_xh if bank_xh > 0 else 7.0)
                eff_scale = base_scale * font_scale_ratio

                # Tính baseline y (thường nằm ở khoảng 75% chiều cao của dòng)
                baseline_y = tb.y + (tb.height * 0.75)
                cur_x = tb.x
                max_w = tb.width

                # Bước 1: Thử lấy token để ước tính tổng bề rộng dòng
                token_data = []
                total_w = 0.0
                for idx, w_tok in enumerate(words):
                    st, w, miss = self.wr.token(w_tok)
                    total_tokens += 1
                    if miss:
                        missing_tokens += 1
                        for m in miss:
                            self.wr.missing[m] = self.wr.missing.get(m, 0) + 1

                    w_scaled = w * eff_scale
                    gap_scaled = (
                        (self.rnd.choice(gaps) * eff_scale * self.opts.space)
                        if idx > 0 else 0.0
                    )
                    token_data.append((w_tok, st, w, gap_scaled))
                    total_w += gap_scaled + w_scaled

                # Bước 2: Tự động co tỷ lệ nếu dòng bị dài hơn chiều rộng bounding box
                scale_adj = 1.0
                if max_w > 20.0 and total_w > max_w:
                    scale_adj = max_w / total_w

                final_scale = eff_scale * scale_adj

                # Bước 3: Đặt nét vẽ vào tọa độ (hỗ trợ left, center, right alignment)
                cur_x = tb.x
                if tb.align == "center":
                    cur_x = tb.x + max(0.0, (tb.width - (total_w * scale_adj)) / 2.0)
                elif tb.align == "right":
                    cur_x = tb.x + max(0.0, tb.width - (total_w * scale_adj))

                pen_dict = getattr(self.bank, "pen", None) or {"tool": "pen", "color": "#000000ff", "width": "1.41"}
                if not isinstance(pen_dict, dict):
                    pen_dict = {"tool": "pen", "color": "#000000ff", "width": str(pen_dict)}

                for w_tok, st, w, gap in token_data:
                    cur_x += gap * scale_adj
                    if st:
                        placed = place(st, cur_x, baseline_y, final_scale, 0.0)
                        wscale = (
                            self.opts.wscale * (1 + self.rnd.gauss(0, 0.02 * self.opts.jitter))
                            if self.opts.jitter > 0
                            else self.opts.wscale
                        )
                        for pts in placed:
                            total_strokes += 1
                            page_strokes.append(
                                xopp.stroke_xml(pts, pen_dict, self.opts.color, wscale)
                            )
                    cur_x += w * final_scale

            parts.extend(page_strokes)
            parts.append(xopp.PAGE_CLOSE)

        parts.append("</xournal>")

        # Lưu file .xopp
        xopp.save_xopp(out_path, parts)

        missing_grid_path = None
        # R5: Tự động tạo file lưới ô từ còn thiếu nếu được yêu cầu
        if missing_tokens > 0 and self.opts.missing_grid:
            raw_grid_path = os.path.splitext(out_path)[0] + "_thieu.xopp"
            grid_path = xopp.resolve_missing_grid_path(raw_grid_path)
            miss_keys = sorted(self.wr.missing)
            samples = {k: self.bank.words[k][0]["s"] for k in miss_keys if k in self.bank.words}
            xopp.make_grid(
                grid_path,
                miss_keys,
                self.bank,
                f"Các từ thiếu mẫu khi viết {os.path.basename(out_path)}",
                samples,
                calib=False,
                grid_version="hw3",
            )
            missing_grid_path = grid_path
            _log.info("Đã tạo file lưới ô từ còn thiếu: %s (%d từ)", grid_path, len(miss_keys))

        total_images = sum(len(p.image_boxes) for p in document.pages)
        total_tables = sum(len(p.table_geometries) for p in document.pages)

        from chuviettay.model.text_utils import missing_letters_ranked
        missing_lets = (
            missing_letters_ranked(
                list(self.wr.missing.keys()),
                getattr(self.bank, "letters", {}),
                getattr(self.bank, "marks", {}),
                strict_case=self.opts.strict_case,
                bank_digits=getattr(self.bank, "digits", {}),
                bank_punct=getattr(self.bank, "punct", {}),
                bank_symbols=getattr(self.bank, "symbols", {}),
                bank_words=getattr(self.bank, "words", {}),
            )
            if self.wr.missing
            else []
        )

        return WriteResult(
            out_path=out_path,
            n_lines=total_lines,
            n_strokes=total_strokes,
            n_tokens=total_tokens,
            n_missing_tokens=missing_tokens,
            missing=dict(self.wr.missing),
            missing_symbols=dict(getattr(self.wr, "missing_symbols", {})),
            n_pages=len(document.pages),
            n_images=total_images,
            n_tables=total_tables,
            missing_grid_path=missing_grid_path,
            missing_letters=missing_lets,
            assembled_words=list(self.wr.assembled),
        )
