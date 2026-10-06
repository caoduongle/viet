"""
Hiệu chỉnh cỡ tay (calibration).

Bản gốc có CÙNG một công thức hiệu chỉnh cỡ tay xuất hiện ở HAI nơi khác nhau:
- hw_note.py: cmd_learn() -- khi học từ file .xopp đã viết tay (dùng ô "đo cỡ tay" đầu tiên)
- hw_gui.py: TeachTab.save_word() -- khi hiệu chỉnh trực tiếp trong app (nút "Hiệu chỉnh cỡ tay")

Hai nơi này đã bị lệch nhau một lần trong quá khứ là chuyện hoàn toàn có thể xảy ra
(sửa công thức ở chỗ này mà quên sửa chỗ kia). Gộp về MỘT hàm duy nhất ở đây để về sau
chỉ cần sửa/kiểm thử một chỗ.

Công thức giữ NGUYÊN từ bản gốc: scale = clamp(cỡ_chữ_đã_biết / cỡ_vừa_đo, 0.3, 3.0).
"""
from __future__ import annotations

import statistics
from typing import Any

from chuviettay.model.text_utils import clamp

# biên hiệu chỉnh cho phép: to nhất gấp ~3.3 lần, nhỏ nhất còn ~1/3 -- giữ nguyên bản gốc
DEFAULT_SCALE_BOUNDS: tuple[float, float] = (0.3, 3.0)

# dưới ngưỡng này (đơn vị kho mẫu) coi như đo chưa đáng tin, không hiệu chỉnh
MIN_MEASURABLE_WIDTH = 0.5


def compute_scale(
    ref_instances: list[dict] | None,
    measured_width: float,
    bounds: tuple[float, float] = DEFAULT_SCALE_BOUNDS,
) -> float:
    """Tính hệ số cỡ tay dựa trên MỘT từ đã biết trước (ref_instances: các mẫu đã có
    sẵn trong kho cho từ đó) so với độ rộng vừa đo được khi người dùng viết lại đúng
    từ đó (measured_width, ĐƠN VỊ THÔ -- chưa nhân hệ số cũ nào).

    Trả về 1.0 (không hiệu chỉnh) nếu chưa có mẫu tham chiếu, hoặc phép đo quá nhỏ để
    tin cậy (measured_width <= 0.5).
    """
    if not ref_instances or measured_width <= MIN_MEASURABLE_WIDTH:
        return 1.0
    ref_width = statistics.median(inst["w"] for inst in ref_instances)
    lo, hi = bounds
    return clamp(ref_width / measured_width, lo, hi)


PREFERRED_CALIB_CHARS = ("o", "a", "e", "n", "u", "c", "m")


def _calc_cv(insts: list[dict]) -> float:
    ws = [inst.get("w", 0.0) for inst in insts]
    if len(ws) < 2:
        return 0.0
    mean_w = statistics.mean(ws)
    if mean_w <= 0:
        return 0.0
    return statistics.stdev(ws) / mean_w


def pick_calib_char(bank: Any) -> str | None:
    """Chọn một ký tự trong kho đã có mẫu để đo cỡ tay (ưu tiên các chữ cái chuẩn x-height
    có độ rộng và hình dáng ổn định: 'o', 'a', 'e', 'n', 'u', 'c', 'm').
    """
    letters = getattr(bank, "letters", {})
    if not letters:
        return None

    # 1. Preferred characters with >= 3 samples
    pref_cands = [ch for ch in PREFERRED_CALIB_CHARS if ch in letters and len(letters[ch]) >= 3]
    if pref_cands:
        return min(pref_cands, key=lambda ch: (_calc_cv(letters[ch]), -len(letters[ch])))

    # 2. Other lowercase characters with >= 3 samples
    other_cands = [
        ch for ch, insts in letters.items()
        if len(ch) == 1 and ch.isalpha() and ch.islower() and len(insts) >= 3
    ]
    if other_cands:
        return min(other_cands, key=lambda ch: (_calc_cv(letters[ch]), -len(letters[ch])))

    # 3. Any letter with most samples
    valid = [(ch, insts) for ch, insts in letters.items() if insts]
    if not valid:
        return None
    return max(valid, key=lambda item: len(item[1]))[0]
