"""Công cụ di trú và chuẩn hóa kho mẫu chữ viết tay (Schema v3/v4).

Chuyển các ký tự đơn lẻ từ `words` sang `letters`, chuẩn hóa x-height đồng dạng,
tính toán khoảng đệm lsb/rsb, và bóc tách dấu thanh rời vào `marks`.
Không bao giờ ghi đè trực tiếp lên file gốc.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
from pathlib import Path
from typing import Any

from chuviettay.config import NANG, TONES
from chuviettay.model.bank_schema import validate_bank_dict
from chuviettay.model.file_lock import FileLock
from chuviettay.model.text_utils import (
    Stroke,
    bbox,
    near_extreme,
    normalize_letter_sample,
    shift,
    tone_info,
    vowel_x,
)


def extract_tone_from_sample(
    label: str,
    strokes: list[Stroke],
    raw_w: float,
) -> tuple[int, dict[str, Any], list[Stroke]] | None:
    """Tách nét dấu thanh ra khỏi mẫu chữ cái có dấu dựa trên nhãn ô đã biết.

    Args:
        label: Nhãn ký tự (ví dụ: 'á', 'à', 'ạ').
        strokes: Danh sách các nét vẽ của mẫu.
        raw_w: Độ rộng hộp chữ của mẫu.

    Returns:
        (chỉ_số_nét_dấu_ti, bản_ghi_dấu_thanh_mark, danh_sách_nét_thân_body)
        hoặc None nếu không tách được.
    """
    T, vi, hats, letters = tone_info(label)
    if not T or vi < 0 or len(strokes) < 2:
        return None

    bbs = [bbox(s) for s in strokes]

    if T == NANG:
        # Dấu nặng: nét thấp nhất (toạ độ y cực đại)
        ti = max(range(len(strokes)), key=lambda k: bbs[k][3])
        # Kiểm tra tính hợp lệ: nét dấu nặng phải nằm thấp hơn đỉnh thân chữ
        other_max_y = max(bbs[k][3] for k in range(len(strokes)) if k != ti)
        if bbs[ti][3] < other_max_y - 1.0:
            return None
    else:
        # Dấu thanh trên (sắc, huyền, hỏi, ngã): nét cao nhất (toạ độ y âm nhất)
        ti = min(range(len(strokes)), key=lambda k: bbs[k][1])
        # Kiểm tra tính hợp lệ: nét dấu phải nằm cao hơn hoặc ngang bằng đỉnh thân chữ
        other_min_y = min(bbs[k][1] for k in range(len(strokes)) if k != ti)
        if bbs[ti][1] > other_min_y + 1.0:
            return None

    mark_stroke = strokes[ti]
    body_strokes = [s for k, s in enumerate(strokes) if k != ti]
    if not body_strokes:
        return None

    xs = mark_stroke[0::2]
    ys = mark_stroke[1::2]
    if not xs or not ys:
        return None

    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    xv = vowel_x(letters, vi, raw_w)
    base_ref_y = max(0.0, near_extreme(body_strokes, cx, max)) if T == NANG else near_extreme(body_strokes, cx, min)
    dy = cy - base_ref_y

    mark = {
        "T": T,
        "s": [shift(mark_stroke, -cx, -cy)],
        "dx": round(cx - xv, 2),
        "dy": round(dy, 2),
        "_src": label,
    }
    return ti, mark, body_strokes


def migrate_bank_dict_letters(
    bank_dict: dict[str, Any],
    target_xh: float = 7.94,
) -> dict[str, Any]:
    """Di trú từ điển kho mẫu: chuyển ký tự đơn sang 'letters' và chuẩn hóa hình học.

    Args:
        bank_dict: Dữ liệu kho mẫu ban đầu (không bị thay đổi).
        target_xh: x-height mục tiêu để chuẩn hóa (mặc định 7.94 pt đo từ note).

    Returns:
        Từ điển kho mẫu mới đã được nâng cấp và chuẩn hóa.
    """
    out = copy.deepcopy(bank_dict)

    raw_xh = float(out.get("xh", 3.85))
    if raw_xh <= 0:
        raw_xh = 3.85

    scale = target_xh / raw_xh

    words = out.get("words", {})
    letters = out.setdefault("letters", {})
    marks = out.setdefault("marks", {t: [] for t in TONES})
    for t in TONES:
        if t not in marks:
            marks[t] = []

    single_keys = [k for k in list(words.keys()) if len(k) == 1]
    migrated_count = 0
    extracted_marks_count = 0
    failed_marks: list[str] = []

    for k in single_keys:
        samples = words.pop(k)
        norm_samples: list[dict[str, Any]] = []

        for inst in samples:
            raw_s = inst.get("s", [])
            raw_w = float(inst.get("w", raw_xh))

            # Chuẩn hoá kích thước và neo baseline cho mẫu chữ
            norm_inst = normalize_letter_sample(k, raw_s, raw_w, raw_xh, target_xh=target_xh)

            # Thử bóc tách dấu thanh nếu là nguyên âm có dấu
            tone_res = extract_tone_from_sample(k, raw_s, raw_w)
            if tone_res is not None:
                ti, mark, _ = tone_res
                norm_inst["ti"] = ti
                norm_inst["T"] = mark["T"]
                norm_inst["vi"] = 0

                # Chuẩn hóa nét dấu thanh theo tỉ lệ scale
                mark_scaled_s = [[round(coord * scale, 2) for coord in s] for s in mark["s"]]
                scaled_mark = {
                    "T": mark["T"],
                    "s": mark_scaled_s,
                    "dx": round(mark["dx"] * scale, 2),
                    "dy": round(mark["dy"] * scale, 2),
                    "_src": k,
                }
                marks[mark["T"]].append(scaled_mark)
                extracted_marks_count += 1
            else:
                T, vi, _, _ = tone_info(k)
                if T:
                    failed_marks.append(k)

            norm_samples.append(norm_inst)

        letters[k] = norm_samples
        migrated_count += 1

    out["xh"] = round(target_xh, 2)

    return out


def migrate_bank_file(
    in_path: str | Path,
    out_path: str | Path,
    target_xh: float = 7.94,
) -> tuple[int, int, list[str]]:
    """Di trú file kho mẫu từ in_path sang out_path một cách nguyên tử (atomic)."""
    in_p = Path(in_path)
    out_p = Path(out_path)

    if not in_p.exists():
        raise FileNotFoundError(f"Không tìm thấy file nguồn: {in_p}")

    with gzip.open(in_p, "rt", encoding="utf-8") as gf:
        d = json.load(gf)

    migrated_d = migrate_bank_dict_letters(d, target_xh=target_xh)
    validate_bank_dict(migrated_d, context=str(out_p), allow_legacy=True)

    out_p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_p.with_suffix(out_p.suffix + ".tmp")

    lock_file = str(out_p) + ".lock"
    with FileLock(lock_file):
        with gzip.open(tmp_path, "wt", encoding="utf-8", compresslevel=6) as out_f:
            json.dump(migrated_d, out_f, ensure_ascii=False)
        if tmp_path.exists():
            tmp_path.replace(out_p)

    migrated_chars = len(migrated_d.get("letters", {}))
    total_marks = sum(len(m_list) for m_list in migrated_d.get("marks", {}).values())
    failed = [k for k, insts in migrated_d.get("letters", {}).items() if tone_info(k)[0] and insts[0].get("ti", -1) < 0]

    return migrated_chars, total_marks, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Di trú kho ký tự từ words sang letters với chuẩn hóa x-height.")
    parser.add_argument("--in", dest="in_path", required=True, help="Đường dẫn file kho nguồn (.json.gz)")
    parser.add_argument("--out", dest="out_path", required=True, help="Đường dẫn file kho đích (.json.gz)")
    parser.add_argument("--target-xh", type=float, default=7.94, help="x-height mục tiêu chuẩn hóa (mặc định 7.94)")

    args = parser.parse_args()
    chars, marks_count, failed = migrate_bank_file(args.in_path, args.out_path, target_xh=args.target_xh)

    print("=== KẾT QUẢ DI TRÚ KHO KÝ TỰ ===")
    print(f"- Đã chuyển {chars} ký tự đơn sang mục 'letters' (chuẩn hoá x-height = {args.target_xh} pt).")
    print(f"- Đã bóc tách thành công {marks_count} mẫu dấu thanh rời vào mục 'marks'.")
    if failed:
        print(f"- Các chữ có dấu không bóc tách được ({len(failed)}): {', '.join(failed)}")
    else:
        print("- 100% các chữ cái có dấu đều được bóc tách nét thành công!")
    print(f"- File mới đã lưu tại: {args.out_path}")


if __name__ == "__main__":
    main()
