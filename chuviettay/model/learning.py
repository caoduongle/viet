"""
learning -- học mẫu chữ mới từ (các) file .xopp người dùng đã viết tay vào lưới ô.

Tương ứng lệnh `learn` trong bản gốc (hw_note.py: cmd_learn). Khác bản gốc ở chỗ dùng
lại xopp.parse_learn_file() để đọc file (thay vì lặp lại vòng lặp parse XML ngay trong
hàm này) và calibration.compute_scale() để tính hệ số cỡ tay (thay vì công thức viết
tay riêng) -- xem docstring của 2 module đó để biết vì sao gộp lại.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from chuviettay.model import xopp
from chuviettay.model.bank import Bank
from chuviettay.model.calibration import compute_scale

_log = logging.getLogger(__name__)


@dataclass
class LearnResult:
    n_added: int
    file_notes: list[str] = field(default_factory=list)   # ghi chú hiệu chỉnh cỡ tay (nếu file nào có lệch)


def is_symbol_label(label: str, bank: Bank | None = None) -> bool:
    """Xác định xem nhãn ô học có phải là ký hiệu toán học / glyph đặc biệt hay không."""
    if label.startswith("\\"):
        return True
    if bank is not None and hasattr(bank, "symbols") and label in bank.symbols:
        return True
    if len(label) == 1:
        import unicodedata
        cat = unicodedata.category(label)
        if cat in ("Sm", "So", "Sk"):
            return True
        code = ord(label)
        if (0x0370 <= code <= 0x03FF) or (0x2190 <= code <= 0x22FF):
            return True
    return False


def learn_from_files(bank: Bank, paths: list[str]) -> LearnResult:
    """Đọc từng file trong `paths`, học mọi ô đã viết tay vào kho mẫu `bank`. Nếu ô đầu
    tiên (0,0,0) của một file là ô "đo cỡ tay" (file có thẻ hw2c), tự tính hệ số cỡ tay
    cho riêng file đó trước khi thêm mẫu, để các từ mới học khớp cỡ với chữ đã học
    trước đây. Rebuild + lưu kho mẫu MỘT LẦN ở cuối (sau khi đã học hết mọi file)."""
    added = 0
    file_notes: list[str] = []
    for path in paths:
        raw, has_calib = xopp.parse_learn_file(path)

        # ô đầu tiên (trang 0, hàng 0, cột 0) là ô "đo cỡ tay" khi file có thẻ hw2c:
        # một từ đã biết sẵn, không đánh dấu gì trên chữ, chỉ nhận ra qua vị trí này.
        scale = 1.0
        cal = raw.get((0, 0, 0))
        if has_calib and cal:
            got = cal.right - cal.left
            scale = compute_scale(bank.words.get(cal.label), got)

        for r in raw.values():
            rel = [[round((v - (r.left if i % 2 == 0 else r.base)) * scale, 2)
                    for i, v in enumerate(s)] for s in r.strokes]
            width = round((r.right - r.left) * scale, 2)
            if is_symbol_label(r.label, bank):
                bank.add_symbol_sample(r.label, rel, width)
            else:
                bank.add_sample(r.label, rel, width)
            added += 1

        if abs(scale - 1.0) > 0.05:
            ratio = 1 / scale if scale < 1 else scale
            file_notes.append(
                "  %s: bạn viết %s bình thường khoảng %.1f lần, đã tự chỉnh các từ mới về đúng cỡ."
                % (os.path.basename(path), "to hơn" if scale < 1 else "nhỏ hơn", ratio))
        _log.info("Học từ %s: %d ô, hệ số cỡ tay %.3f", path, len(raw), scale)

    bank.rebuild()
    bank.save()
    return LearnResult(n_added=added, file_notes=file_notes)
