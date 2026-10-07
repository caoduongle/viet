import random
import pytest
from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer
from chuviettay.model.text_utils import bbox, min_stroke_clearance


def make_test_bank(tmp_path):
    bank_path = str(tmp_path / "test_punct_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.xh = 10.0
    bank.pen = {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"}

    # Thêm chữ cái 'đ', 'ổ', 'i', 'y', 'a'
    bank.add_letter_sample("đ", [[0.0, -8.0, 4.0, -8.0], [2.0, 0.0, 2.0, -10.0]], width=5.0)
    bank.add_letter_sample("ổ", [[0.0, -4.0, 4.0, -4.0]], width=5.0)
    bank.add_letter_sample("i", [[0.0, 0.0, 0.0, -5.0], [0.0, -7.0, 0.5, -7.0]], width=3.0)
    bank.add_letter_sample("y", [[0.0, -5.0, 2.0, 0.0, 4.0, -5.0], [4.0, -5.0, 1.0, 5.0]], width=5.0)
    bank.add_letter_sample("a", [[0.0, -3.0, 3.0, -3.0]], width=4.0)

    # Thêm chữ số với min_x = 0
    bank.digits["0"] = [{"s": [[0.0, 0.0, 3.0, 0.0, 3.0, -8.0, 0.0, -8.0, 0.0, 0.0]], "w": 4.0}]
    bank.digits["1"] = [{"s": [[0.0, -2.0, 2.0, -8.0, 2.0, 0.0]], "w": 3.0}]
    bank.digits["2"] = [{"s": [[0.0, -6.0, 4.0, -6.0, 0.0, 0.0, 4.0, 0.0]], "w": 5.0}]
    bank.digits["4"] = [{"s": [[3.0, 0.0, 3.0, -8.0, 0.0, -2.0, 4.0, -2.0]], "w": 5.0}]
    bank.digits["5"] = [{"s": [[0.0, -8.0, 4.0, -8.0, 0.0, -4.0, 4.0, -2.0]], "w": 5.0}]
    bank.digits["8"] = [{"s": [[2.0, -8.0, 0.0, -4.0, 4.0, 0.0]], "w": 5.0}]

    # Thêm dấu câu với min_x bị lệch (mô phỏng kho mẫu thực tế)
    # colon ':' có min_x = 4.5
    bank.punct[":"] = [{"s": [[4.5, -7.0, 4.5, -6.0], [4.5, -2.0, 4.5, -1.0]]}]
    # comma ',' có min_x = 3.0
    bank.punct[","] = [{"s": [[3.0, -1.0, 3.5, 0.0, 2.5, 2.0]]}]
    # period '.' có min_x = 5.0
    bank.punct["."] = [{"s": [[5.0, -1.0, 5.5, -1.0]]}]
    # open paren '(' có min_x = 6.0
    bank.punct["("] = [{"s": [[6.0, -9.0, 5.0, -4.0, 6.0, 1.0]], "w": 3.0}]
    # close paren ')' có min_x = 4.0
    bank.punct[")"] = [{"s": [[4.0, -9.0, 5.0, -4.0, 4.0, 1.0]], "w": 3.0}]

    # dgaps chứa giá trị lớn (mô phỏng kho mẫu thực tế bị out of range)
    bank.d["dgaps"] = [8.5, 11.2, 7.5, 6.8]

    return bank


def test_trail_punctuation_clearance_and_zero_collision(tmp_path):
    bank = make_test_bank(tmp_path)
    wr = Writer(bank, random.Random(42))

    # Ghép token 'y:'
    strokes, w, miss = wr.token("y:")
    assert not miss, f"Missing characters: {miss}"
    assert len(strokes) >= 3, "Phải có cả nét của 'y' và nét của ':'"

    # Nét của 'y' (2 nét đầu) và nét của ':' (2 nét sau)
    y_strokes = strokes[:2]
    colon_strokes = strokes[2:]

    # Tọa độ x lớn nhất của 'y'
    y_max_x = max(pt for st in y_strokes for pt in st[0::2])
    # Tọa độ x nhỏ nhất của ':'
    colon_min_x = min(pt for st in colon_strokes for pt in st[0::2])

    # 1. Zero collision: colon không được đè lên 'y'
    assert colon_min_x > y_max_x, f"Dấu ':' bị đè lên chữ 'y': colon_min_x={colon_min_x} <= y_max_x={y_max_x}"

    # 2. Clearance: khoảng cách hở quang học phải >= 0.15 * xh
    clearance = colon_min_x - y_max_x
    assert clearance >= 0.15 * bank.xh, f"Khoảng đệm quá nhỏ: clearance={clearance} < {0.15 * bank.xh}"


def test_single_punctuation_token_normalized_origin(tmp_path):
    bank = make_test_bank(tmp_path)
    wr = Writer(bank, random.Random(42))

    # Token chỉ có duy nhất ':'
    strokes, w, miss = wr.token(":")
    assert not miss
    # min_x của nét phải được chuẩn hóa bắt đầu từ ~0 (hoặc side_bearing nhỏ), không bị thụt lề 4.5
    min_x = min(pt for st in strokes for pt in st[0::2])
    assert min_x < 1.0, f"Dấu ':' đứng một mình bị trôi lề x quá lớn: min_x={min_x}"
    assert w > 0


def test_digit_spacing_bounded_by_xh(tmp_path):
    bank = make_test_bank(tmp_path)
    wr = Writer(bank, random.Random(42))

    # Ghép chuỗi số '18'
    strokes, w, miss = wr.token("18")
    assert not miss
    # Nét số 1 và số 8
    d1_stroke = strokes[0]
    d8_stroke = strokes[1]
    d1_max_x = max(d1_stroke[0::2])
    d8_min_x = min(d8_stroke[0::2])

    gap = d8_min_x - d1_max_x
    # Với digit '1' có w=3.0 và d1_max_x=2.0 (tức có 1.0 margin phải), gap thực tế giữa nét = margin (1.0) + dgap (2.2) = 3.2
    # Khoảng cách giữa nét không vượt quá 0.35 * xh và dgap không bị bung theo các outlier cũ 8.5/11.2
    assert gap <= 0.35 * bank.xh, f"Khoảng cách 2 chữ số quá xa: gap={gap} > {0.35 * bank.xh}"
    assert gap >= 0.05 * bank.xh, f"Khoảng cách 2 chữ số quá dính: gap={gap} < {0.05 * bank.xh}"


def test_decimal_number_punctuation_spacing(tmp_path):
    bank = make_test_bank(tmp_path)
    wr = Writer(bank, random.Random(42))

    # Ghép số thập phân '0,12'
    strokes, w, miss = wr.token("0,12")
    assert not miss
    # Đảm bảo toàn bộ các nét được sắp xếp tăng dần theo x
    xs = [min(st[0::2]) for st in strokes]
    assert xs == sorted(xs), f"Thứ tự nét số thập phân bị lộn xộn: {xs}"


def test_lead_punctuation_clearance(tmp_path):
    bank = make_test_bank(tmp_path)
    wr = Writer(bank, random.Random(42))

    # Ghép token '(a'
    strokes, w, miss = wr.token("(a")
    assert not miss
    paren_st = strokes[0]
    a_st = strokes[1]
    paren_max_x = max(paren_st[0::2])
    a_min_x = min(a_st[0::2])

    assert a_min_x > paren_max_x, "Chữ 'a' bị đè lên dấu '('"
    assert (a_min_x - paren_max_x) >= 0.10 * bank.xh, "Khoảng cách sau dấu '(' quá nhỏ"
