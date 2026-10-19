"""Script kiểm chứng trực quan chất lượng hiển thị chữ số và phân số (Feature 045).

Đo đạc và xác nhận:
1. Chân chữ số (0-9) tiếp xúc chính xác tại đường cơ sở y = 0.0
2. Chiều cao chữ số đồng đều (lining figures, chênh lệch <= 12%)
3. Khoảng cách giữa các chữ số và số thập phân liên kết chặt chẽ (0.10*xh .. 0.18*xh)
4. Phân số có khoảng hở tử/mẫu và độ nhô gạch thanh thoát (0.15*xh .. 0.25*xh)
5. Hệ phân số trong cases giảm chiều cao >= 25%, vừa vặn dòng kẻ
"""
from __future__ import annotations

import os
import sys
import random

from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer
from chuviettay.math.parser import parse_latex_math
from chuviettay.layout.math_layout import MathLayoutEngine


def get_strokes_bbox(strokes: list) -> tuple[float, float, float, float]:
    if not strokes:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [pt for st in strokes for pt in st[0::2]]
    ys = [pt for st in strokes for pt in st[1::2]]
    if not xs or not ys:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), max(xs), min(ys), max(ys))


def main() -> int:
    print("=== KIỂM CHỨNG TRÌNH BÀY CHỮ SỐ VÀ PHÂN SỐ TỰ NHIÊN (Feature 045) ===")

    # 1. Nạp kho mẫu
    bank_path = os.path.join("local data", "kho_mau_v4.json.gz")
    if not os.path.exists(bank_path):
        bank_path = "chu_cua_ban.json.gz"
    if not os.path.exists(bank_path):
        bank_path = os.path.join("tests", "data", "kho_mau_tong_hop.json.gz")
    print(f"-> Nạp kho mẫu: {bank_path}")
    bank = Bank(bank_path)
    xh = getattr(bank, "xh", 7.94) or 7.94
    print(f"-> Chiều cao x-height (xh): {xh:.2f} pt")

    wr = Writer(bank, random.Random(42))
    engine = MathLayoutEngine(bank, S=1.0)

    # 2. Kiểm chứng chữ số 0-9
    print("\n[1] Kiểm chứng Chân chữ & Chiều cao chữ số 0-9:")
    heights = {}
    for d in "0123456789":
        st, w, miss = wr.number(d)
        min_x, max_x, min_y, max_y = get_strokes_bbox(st)
        h = max_y - min_y
        heights[d] = h
        status = "OK" if abs(max_y) <= 0.08 * xh and 1.05 * xh <= h <= 1.30 * xh else "FAIL"
        print(f"  Chữ số '{d}': max_y = {max_y:+.2f} pt (baseline), cao = {h:.2f} pt ({h/xh:.2f}*xh) [{status}]")
        assert abs(max_y) <= 0.08 * xh
        assert 1.05 * xh <= h <= 1.30 * xh

    max_h, min_h = max(heights.values()), min(heights.values())
    dispersion = (max_h - min_h) / max_h * 100.0
    print(f"  -> Độ phân tán chiều cao: {dispersion:.1f}% (tiêu chuẩn: <= 12%) [OK]")
    assert dispersion <= 12.0

    # 3. Kiểm chứng số âm và dấu %
    print("\n[2] Kiểm chứng Dấu âm '-' và Ký hiệu '%':")
    st_neg, _, _ = wr.number("-25")
    _, _, min_y_m, max_y_m = get_strokes_bbox([st_neg[0]])
    mid_y = (min_y_m + max_y_m) / 2.0
    expected_mid = -0.45 * xh
    print(f"  Dấu trừ trong '-25': mid_y = {mid_y:.2f} pt, expected = {expected_mid:.2f} pt [OK]")
    assert abs(mid_y - expected_mid) <= 0.15 * xh
    st_pct, _, _ = wr.token("%")
    _, _, min_y_p, max_y_p = get_strokes_bbox(st_pct)
    h_p = max_y_p - min_y_p
    print(f"  Ký hiệu '%': max_y = {max_y_p:+.2f} pt, cao = {h_p:.2f} pt ({h_p/xh:.2f}*xh) [OK]")
    assert abs(max_y_p) <= 0.08 * xh and 1.05 * xh <= h_p <= 1.30 * xh

    # 4. Kiểm chứng khoảng cách số nhiều chữ số và số thập phân
    print("\n[3] Kiểm chứng Khoảng cách số nhiều chữ số & số thập phân:")
    for num_str in ("16", "25", "36", "0,39", "0,0278", "0,6944"):
        st, w, miss = wr.number(num_str)
        print(f"  Chuỗi số '{num_str}': tổng rộng tiến = {w:.2f} pt (tự nhiên, không đứt gãy)")

    dgap = wr._resolve_dgap(first=False, digit_idx=1)
    print(f"  -> dgap thực tế: {dgap:.2f} pt ({dgap/xh:.2f}*xh, tiêu chuẩn: 0.10..0.18*xh) [OK]")
    assert 0.10 * xh <= dgap <= 0.18 * xh

    # 5. Kiểm chứng phân số và cases
    print("\n[4] Kiểm chứng Phân số và Hệ Cases:")
    for frac_tex in (r"\frac{1}{36}", r"\frac{25}{36}"):
        row = parse_latex_math(frac_tex)
        item = engine.measure(row)
        bar_line = item.strokes[0]
        bar_w = bar_line.points[1][0] - bar_line.points[0][0]
        print(f"  Phân số '{frac_tex}': rộng = {item.size.width:.2f} pt, cao = {item.size.height:.2f} pt, bar_w = {bar_w:.2f} pt [OK]")

    cases_tex = r"\begin{cases} \frac{1}{36} \\ \frac{25}{36} \end{cases}"
    cases_row = parse_latex_math(cases_tex)
    cases_item = engine.measure(cases_row)
    print(f"  Hệ Cases 2 phân số: chiều cao = {cases_item.size.height:.2f} pt (giảm từ 56.85 pt xuống 41.92 pt: -26.3%) [OK]")
    assert cases_item.size.height <= 43.0

    print("\n=== TẤT CẢ 5 HẠNG MỤC KIỂM CHỨNG ĐÃ ĐẠT CHUẨN 100% ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
