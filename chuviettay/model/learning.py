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
from chuviettay.model.text_utils import (
    PUNCT_CHARS,
    classify_token,
    is_symbol_label,
    sample_signature,
)

__all__ = [
    "LearnResult",
    "PUNCT_CHARS",
    "classify_token",
    "is_symbol_label",
    "learn_from_files",
    "sample_signature",
]

_log = logging.getLogger(__name__)


@dataclass
class LearnResult:
    n_added: int
    file_notes: list[str] = field(default_factory=list)   # ghi chú hiệu chỉnh cỡ tay (nếu file nào có lệch)




def learn_from_files(bank: Bank, paths: list[str]) -> LearnResult:
    """Đọc từng file trong `paths`, học mọi ô đã viết tay vào kho mẫu `bank`. Nếu ô đầu
    tiên (0,0,0) của một file là ô "đo cỡ tay" (file có thẻ hw2c), tự tính hệ số cỡ tay
    cho riêng file đó trước khi thêm mẫu, để các từ mới học khớp cỡ với chữ đã học
    trước đây. Rebuild + lưu kho mẫu MỘT LẦN ở cuối (sau khi đã học hết mọi file)."""
    import hashlib
    added = 0
    file_notes: list[str] = []
    learned_files = bank.d.setdefault("learned_files", {})

    for path in paths:
        try:
            with open(path, "rb") as f:
                f_hash = hashlib.sha256(f.read()).hexdigest()
        except OSError:
            f_hash = ""

        if f_hash and f_hash in learned_files:
            _log.info("File %s đã được học trước đó, bỏ qua để tránh nhân đôi mẫu (L11).", path)
            continue

        raw, has_calib = xopp.parse_learn_file(path)

        # ô đầu tiên (trang 0, hàng 0, cột 0) là ô "đo cỡ tay" khi file có thẻ hw2c:
        # một từ đã biết sẵn, không đánh dấu gì trên chữ, chỉ nhận ra qua vị trí này.
        scale = 1.0
        cal = raw.get((0, 0, 0))
        if has_calib and cal:
            got = cal.right - cal.left
            scale = compute_scale(bank.words.get(cal.label), got)

        file_added = 0
        for r in raw.values():
            rel = [[round((v - (r.left if i % 2 == 0 else r.base)) * scale, 2)
                    for i, v in enumerate(s)] for s in r.strokes]
            width = round((r.right - r.left) * scale, 2)
            cat = classify_token(r.label, bank)
            if cat == "symbols":
                bank.add_symbol_sample(r.label, rel, width)
            else:
                bank.add_sample(r.label, rel, width, dedup=False)
            added += 1
            file_added += 1

        if f_hash and file_added > 0:
            learned_files[f_hash] = os.path.basename(path)

        if abs(scale - 1.0) > 0.05:
            ratio = 1 / scale if scale < 1 else scale
            file_notes.append(
                "  %s: bạn viết %s bình thường khoảng %.1f lần, đã tự chỉnh các từ mới về đúng cỡ."
                % (os.path.basename(path), "to hơn" if scale < 1 else "nhỏ hơn", ratio))
        _log.info("Học từ %s: %d ô, hệ số cỡ tay %.3f", path, len(raw), scale)

    bank.rebuild()
    bank.save()
    return LearnResult(n_added=added, file_notes=file_notes)
