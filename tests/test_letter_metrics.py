"""Kiểm thử tính toán chỉ số hình học chữ cái (metrics, side bearings, contours, normalization)."""
import pytest

from chuviettay.model.text_utils import (
    classify_char_category,
    classify_left_contour,
    classify_right_contour,
    compute_side_bearings,
    contour_pair_gap,
    normalize_letter_sample,
)


def test_classify_char_category():
    # Nhóm chữ thường x-height
    assert classify_char_category("a") == "x_height"
    assert classify_char_category("o") == "x_height"
    assert classify_char_category("m") == "x_height"
    assert classify_char_category("ă") == "x_height"
    assert classify_char_category("ê") == "x_height"
    assert classify_char_category("à") == "x_height"
    assert classify_char_category("ớ") == "x_height"

    # Nhóm thân vươn cao (ascender)
    assert classify_char_category("b") == "ascender"
    assert classify_char_category("d") == "ascender"
    assert classify_char_category("đ") == "ascender"
    assert classify_char_category("h") == "ascender"
    assert classify_char_category("k") == "ascender"
    assert classify_char_category("l") == "ascender"
    assert classify_char_category("t") == "ascender"

    # Nhóm đuôi xuống (descender)
    assert classify_char_category("g") == "descender"
    assert classify_char_category("p") == "descender"
    assert classify_char_category("q") == "descender"
    assert classify_char_category("y") == "descender"
    assert classify_char_category("ỳ") == "descender"

    # Nhóm chữ hoa
    assert classify_char_category("A") == "uppercase"
    assert classify_char_category("B") == "uppercase"
    assert classify_char_category("Đ") == "uppercase"

    # Nhóm số, dấu câu, ký hiệu
    assert classify_char_category("5") == "digit"
    assert classify_char_category(",") == "punct"
    assert classify_char_category("+") == "symbol"


def test_classify_contours():
    # Tròn cong (CURVED)
    assert classify_left_contour("o") == "CURVED"
    assert classify_right_contour("o") == "CURVED"
    assert classify_left_contour("c") == "CURVED"
    assert classify_right_contour("c") == "OPEN"

    # Thẳng đứng (STRAIGHT)
    assert classify_left_contour("l") == "STRAIGHT"
    assert classify_right_contour("l") == "STRAIGHT"
    assert classify_left_contour("n") == "STRAIGHT"
    assert classify_right_contour("n") == "STRAIGHT"

    # Hở / chéo (OPEN)
    assert classify_left_contour("v") == "OPEN"
    assert classify_right_contour("v") == "OPEN"
    assert classify_left_contour("r") == "STRAIGHT"
    assert classify_right_contour("r") == "OPEN"


def test_contour_pair_gap():
    # Cong gặp Cong: khoảng cách tự nhiên hẹp nhất vì 2 đường cong tạo negative space
    gap_cc = contour_pair_gap("CURVED", "CURVED", xh=8.0)
    # Thẳng gặp Thẳng: cần khoảng cách chuẩn lớn hơn để tránh dính
    gap_ss = contour_pair_gap("STRAIGHT", "STRAIGHT", xh=8.0)
    # Hở gặp Thẳng hoặc Cong
    gap_os = contour_pair_gap("OPEN", "STRAIGHT", xh=8.0)

    assert gap_cc < gap_ss
    assert gap_cc > 0
    assert gap_ss > 0
    assert gap_os > 0


def test_compute_side_bearings():
    # Một nét chữ 'o' có w=4.0, xh=8.0
    strokes = [[0.0, -4.0, 4.0, -4.0, 4.0, 0.0, 0.0, 0.0]]
    lsb, rsb, adv = compute_side_bearings("o", strokes, w=4.0, xh=8.0)
    assert lsb > 0
    assert rsb > 0
    assert adv >= 4.0 + lsb + rsb - 0.01


def test_normalize_letter_sample():
    # Chữ 'a' trong kho thô cao 3.85pt, baseline tại 0, xh thô = 3.85
    # Cần scale lên xh mục tiêu = 7.94pt
    strokes = [[0.0, -3.85, 2.0, -3.85, 4.0, 0.0, 0.0, 0.0]]
    norm_sample = normalize_letter_sample(
        char="a",
        strokes=strokes,
        raw_w=4.0,
        raw_xh=3.85,
        target_xh=7.94,
    )

    assert "s" in norm_sample
    assert "w" in norm_sample
    assert "lsb" in norm_sample
    assert "rsb" in norm_sample
    assert "adv" in norm_sample
    assert norm_sample["cat"] == "x_height"

    # Chiều cao sau chuẩn hoá phải khớp target_xh (~7.94)
    norm_st = norm_sample["s"]
    ys = [norm_st[k][i + 1] for k in range(len(norm_st)) for i in range(0, len(norm_st[k]) - 1, 2)]
    h = max(ys) - min(ys)
    assert pytest.approx(h, rel=0.05) == 7.94
    # Baseline chân chữ phải ở y = 0
    assert pytest.approx(max(ys), abs=0.05) == 0.0


def test_missing_letters_ranked_with_digits_symbols():
    from chuviettay.model.text_utils import missing_letters_ranked

    bank_letters = {"a": [{"s": [], "w": 5.0}], "b": [{"s": [], "w": 5.0}]}
    bank_marks = {}
    bank_digits = {"5": [{"s": [], "w": 4.0}], "0": [{"s": [], "w": 4.0}]}
    bank_punct = {"_": [{"s": [], "w": 3.0}], "(": [{"s": [], "w": 3.0}]}
    bank_symbols = {">=": [{"s": [], "w": 6.0}]}

    # Từ có số và ký hiệu: "5000", "a_b", ">=", "45mm"
    missing = ["5000", "a_b", "45mm"]
    ranked = missing_letters_ranked(
        missing,
        bank_letters=bank_letters,
        bank_marks=bank_marks,
        bank_digits=bank_digits,
        bank_punct=bank_punct,
        bank_symbols=bank_symbols,
    )
    needed = [item[0] for item in ranked]
    # '5000' có '5' và '0' -> không thiếu gì
    # 'a_b' có 'a', '_', 'b' -> không thiếu gì
    # '45mm' có '5', thiếu '4', 'm'
    assert "4" in needed
    assert "m" in needed
    assert "5" not in needed
    assert "_" not in needed

