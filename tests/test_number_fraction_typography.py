"""Test suite chuyên biệt cho tính năng chuẩn hóa chữ số và phân số tự nhiên (Feature 045)."""
from __future__ import annotations

import os
import random
import pytest

from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer
from chuviettay.math.parser import parse_latex_math
from chuviettay.layout.math_layout import MathLayoutEngine


def get_strokes_bbox(strokes: list) -> tuple[float, float, float, float]:
    """Tính bounding box (min_x, max_x, min_y, max_y) cho danh sách nét vẽ."""
    if not strokes:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [pt for st in strokes for pt in st[0::2]]
    ys = [pt for st in strokes for pt in st[1::2]]
    if not xs or not ys:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), max(xs), min(ys), max(ys))


@pytest.fixture
def sample_bank_v4():
    """Nạp kho mẫu v4 chuẩn (nếu có) hoặc tạo kho mẫu thử nghiệm."""
    path = os.path.join("local data", "kho_mau_v4.json.gz")
    if os.path.exists(path):
        return Bank(path)
    # Fallback kho mẫu tổng hợp
    synth_path = os.path.join("tests", "data", "kho_mau_tong_hop.json.gz")
    if os.path.exists(synth_path):
        return Bank(synth_path)
    b = Bank.create_empty("test_empty_bank.json.gz")
    b.xh = 7.94
    return b


@pytest.fixture
def sample_user_bank():
    """Nạp kho mẫu chu_cua_ban.json.gz (nếu có)."""
    path = "chu_cua_ban.json.gz"
    if os.path.exists(path):
        return Bank(path)
    return None


def test_digit_baseline_and_height_normalization(sample_bank_v4, sample_user_bank):
    """T003 [US1]: Kiểm tra chân chữ bám baseline và chiều cao hiển thị đồng đều cho 0-9 trên cả v4 và chu_cua_ban."""
    banks_to_check = [sample_bank_v4]
    if sample_user_bank is not None:
        banks_to_check.append(sample_user_bank)

    for b in banks_to_check:
        xh = getattr(b, "xh", 7.94) or 7.94
        wr = Writer(b, random.Random(42))

        heights = {}
        for d in "0123456789":
            # Kiểm tra qua Writer.number
            st_num, w_num, miss = wr.number(d)
            assert not miss, f"Số {d} không được thiếu mẫu"
            assert st_num, f"Số {d} phải có nét"
            min_x, max_x, min_y, max_y = get_strokes_bbox(st_num)

            # 1. Chân chữ phải chạm đúng baseline y = 0.0 (INV-001: abs(max_y) <= 0.08 * xh)
            assert abs(max_y) <= 0.08 * xh, f"Chữ số {d} không chạm baseline: max_y={max_y}, xh={xh}"

            h = max_y - min_y
            heights[d] = h
            # 2. Chiều cao nằm trong dải chuẩn (INV-002: [1.05 * xh, 1.30 * xh])
            assert 1.05 * xh <= h <= 1.30 * xh, (
                f"Chiều cao chữ số {d} ({h:.2f}) lệch ngoài dải chuẩn [{1.05*xh:.2f}, {1.30*xh:.2f}]"
            )

            # 3. Kiểm tra qua Writer.token (token đơn) và get_letter_sample / get_char_advance_width
            st_tok, w_tok, miss_tok = wr.token(d)
            assert not miss_tok
            _, _, min_y_t, max_y_t = get_strokes_bbox(st_tok)
            assert abs(max_y_t) <= 0.08 * xh, f"Token số đơn lẻ {d} không chạm baseline: max_y={max_y_t}"
            assert 1.05 * xh <= (max_y_t - min_y_t) <= 1.30 * xh

            let_sample = wr.get_letter_sample(d)
            assert let_sample is not None
            _, _, min_y_l, max_y_l = get_strokes_bbox(let_sample["s"])
            assert abs(max_y_l) <= 0.08 * xh
            assert 1.05 * xh <= (max_y_l - min_y_l) <= 1.30 * xh

        # 4. Độ phân tán chiều cao giữa chữ số cao nhất và thấp nhất <= 12% (SC-001)
        max_h = max(heights.values())
        min_h = min(heights.values())
        diff_pct = (max_h - min_h) / max_h
        assert diff_pct <= 0.12, (
            f"Độ chênh lệch chiều cao giữa các chữ số quá lớn: {diff_pct*100:.1f}% (min={min_h:.2f}, max={max_h:.2f})"
        )


def test_minus_and_percent_digit_normalization(sample_bank_v4, sample_user_bank):
    """T004 [US1]: Kiểm tra dấu '-' căn tâm tại y = -0.45*xh và '%' chuẩn hóa lining."""
    banks_to_check = [sample_bank_v4]
    if sample_user_bank is not None:
        banks_to_check.append(sample_user_bank)

    for b in banks_to_check:
        xh = getattr(b, "xh", 7.94) or 7.94
        wr = Writer(b, random.Random(42))

        # 1. Viết số âm "-25"
        st, w, miss = wr.number("-25")
        assert not miss
        minus_st = [st[0]]
        _, _, min_y_m, max_y_m = get_strokes_bbox(minus_st)
        mid_y = (min_y_m + max_y_m) / 2.0
        expected_mid = -0.45 * xh
        assert abs(mid_y - expected_mid) <= 0.15 * xh, (
            f"Dấu trừ bị lệch tâm toán học: mid_y={mid_y}, expected={expected_mid}"
        )
        assert max_y_m < -0.10 * xh, f"Dấu trừ bị kéo tụt xuống đường cơ sở: max_y={max_y_m}"

        # 2. Viết số phần trăm "25%" và token "%"
        st_pct, _, miss_pct = wr.token("%")
        assert not miss_pct
        _, _, min_y_p, max_y_p = get_strokes_bbox(st_pct)
        h_p = max_y_p - min_y_p
        assert abs(max_y_p) <= 0.08 * xh, f"Ký hiệu '%' không chạm baseline: max_y={max_y_p}"
        assert 1.05 * xh <= h_p <= 1.30 * xh, f"Chiều cao '%' ({h_p:.2f}) lệch khỏi dải đồng cao"


def _split_rendered_char_bboxes(wr: Writer, s: str, seed: int = 42) -> list[tuple[float, float, float, float]]:
    """Phân tách nét kết xuất thực tế của wr.number(s) thành bounding box từng ký tự."""
    wr.rnd = random.Random(seed)
    wr.last = {}
    st_all, _, miss = wr.number(s)
    assert not miss

    # Đếm số nét của từng ký tự với cùng hạt giống RNG
    wr_cnt = Writer(wr.b, random.Random(seed))
    bboxes: list[tuple[float, float, float, float]] = []
    cursor = 0
    for d_idx, ch in enumerate(s):
        if ch in ",.":
            lib = wr_cnt.b.punct.get(ch) or wr_cnt.b.punct.get(",") or wr_cnt.b.punct.get(".")
            g = wr_cnt.pick(lib, "p" + ch)
            n_st = len(g.get("s", []))
        else:
            lib = (
                wr_cnt.b.digits.get(ch)
                or (wr_cnt.b.punct.get(ch) if ch in "-%" else None)
                or wr_cnt.b.symbols.get(ch)
                or wr_cnt.b.words.get(ch)
            )
            g = wr_cnt.pick(lib, "d" + ch)
            _ = wr_cnt._resolve_dgap(first=(d_idx == 0 or s[d_idx - 1] in ",."), is_hyphen=(ch == "-"), digit_idx=d_idx)
            n_st = len(g.get("s", []))
        char_strokes = st_all[cursor : cursor + n_st]
        cursor += n_st
        bboxes.append(get_strokes_bbox(char_strokes))
    return bboxes


def test_inter_digit_spacing_bounds(sample_bank_v4):
    """T008 [US2]: Khoảng hở quang học thực tế giữa các nét chữ số liền kề nằm trong dải [0.10 * xh, 0.20 * xh]."""
    b = sample_bank_v4
    xh = getattr(b, "xh", 7.94) or 7.94
    wr = Writer(b, random.Random(42))

    for num_str in ("16", "25", "36", "2024"):
        bboxes = _split_rendered_char_bboxes(wr, num_str, seed=42)
        assert len(bboxes) == len(num_str)
        for idx in range(1, len(bboxes)):
            prev_max_x = bboxes[idx - 1][1]
            curr_min_x = bboxes[idx][0]
            optical_gap = curr_min_x - prev_max_x
            assert 0.10 * xh - 0.02 <= optical_gap <= 0.20 * xh + 0.02, (
                f"Khoảng hở quang học thực tế giữa {num_str[idx-1]} và {num_str[idx]} ({optical_gap:.2f}) ngoài [0.10*xh, 0.20*xh]"
            )


def test_decimal_number_spacing_harmony(sample_bank_v4):
    """T009 [US2]: Kiểm tra khoảng cách thực tế sau dấu phẩy và giữa các chữ số thập phân hài hòa <= 0.08 * xh."""
    b = sample_bank_v4
    xh = getattr(b, "xh", 7.94) or 7.94
    wr = Writer(b, random.Random(42))

    for dec_str in ("0,39", "0,0278"):
        bboxes = _split_rendered_char_bboxes(wr, dec_str, seed=42)
        # bboxes[0] = '0', bboxes[1] = ',', bboxes[2] = chữ số thập phân đầu, bboxes[3] = chữ số thập phân thứ 2
        gap_before_comma = bboxes[1][0] - bboxes[0][1]
        gap_after_comma = bboxes[2][0] - bboxes[1][1]
        assert 0.06 * xh <= gap_before_comma <= 0.12 * xh
        assert 0.08 * xh <= gap_after_comma <= 0.14 * xh

        for idx in range(3, len(bboxes)):
            inter_digit_gap = bboxes[idx][0] - bboxes[idx - 1][1]
            assert 0.10 * xh - 0.02 <= inter_digit_gap <= 0.20 * xh + 0.02
            diff = abs(inter_digit_gap - gap_after_comma)
            assert diff <= 0.08 * xh + 0.02, (
                f"Chênh lệch khoảng hở trong số thập phân {dec_str} quá lớn ({diff:.2f} > {0.08*xh:.2f})"
            )


def test_latex_parser_vietnamese_decimal_comma():
    """T010 [US2]: Kiểm tra parser nhận diện đúng số thập phân có dấu phẩy."""
    from chuviettay.math.ast import MathRow, SymbolNode, TextNode

    # 1. $0,39$ -> TextNode(text="0,39", kind="num")
    row_39 = parse_latex_math("0,39")
    if isinstance(row_39, MathRow) and len(row_39.items) == 1:
        node_39 = row_39.items[0]
    else:
        node_39 = row_39
    assert isinstance(node_39, TextNode), f"Expected TextNode, got {type(node_39)}"
    assert node_39.text == "0,39"
    assert node_39.kind == "num"

    # 2. $0,0278,$ -> TextNode("0,0278") theo sau bởi SymbolNode(",")
    row_trail = parse_latex_math("0,0278,")
    assert isinstance(row_trail, MathRow)
    assert len(row_trail.items) == 2
    assert isinstance(row_trail.items[0], TextNode)
    assert row_trail.items[0].text == "0,0278"
    assert row_trail.items[0].kind == "num"
    assert isinstance(row_trail.items[1], SymbolNode)
    assert row_trail.items[1].symbol == ","

    # 3. $(0, 1)$ -> không gộp thành số thập phân vì có khoảng trắng sau dấu phẩy
    row_coord = parse_latex_math("(0, 1)")
    symbols_or_texts = [
        item.symbol if isinstance(item, SymbolNode) else (item.text if isinstance(item, TextNode) else "")
        for item in row_coord.items
    ]
    assert "," in symbols_or_texts, f"Dấu phẩy trong (0, 1) phải là SymbolNode riêng biệt, got {symbols_or_texts}"


def test_textnode_numeric_descent_zero(sample_bank_v4):
    """T014 [US3]: Kiểm tra TextNode số học không bị gán descent ảo 0.2*xh."""
    b = sample_bank_v4
    xh = getattr(b, "xh", 7.94) or 7.94
    engine = MathLayoutEngine(b, S=1.0)

    from chuviettay.math.ast import TextNode
    for num_str in ("0", "1", "25", "36"):
        node = TextNode(num_str, kind="num")
        item = engine.measure(node)
        assert item.size.descent <= 0.05 * xh, f"Số {num_str} bị gán descent ảo: descent={item.size.descent}, xh={xh}"


def test_fraction_optical_clearance_and_overhang(sample_bank_v4):
    """T015 [US3]: Kiểm tra khoảng hở nét tử/mẫu [0.15*xh, 0.25*xh] và độ nhô gạch [0.15*xh, 0.25*xh]."""
    b = sample_bank_v4
    xh = getattr(b, "xh", 7.94) or 7.94
    engine = MathLayoutEngine(b, S=1.0)

    from chuviettay.math.ast import Fraction, TextNode
    for num_s, den_s in [("1", "36"), ("25", "36")]:
        node = Fraction(num=TextNode(num_s, kind="num"), den=TextNode(den_s, kind="num"), bar=True)
        item = engine.measure(node)

        # Thanh gạch phân số là đường line duy nhất tại y = -math_axis
        math_axis = 0.45 * xh
        assert len(item.strokes) == 1, "Phân số có thanh gạch phải có 1 đường nét stroke"
        bar_line = item.strokes[0]
        bar_y = bar_line.points[0][1]
        assert abs(bar_y - (-math_axis)) <= 0.05 * xh

        # Lấy nét tử số (y < bar_y) và mẫu số (y > bar_y)
        num_ys = [
            pt * g.scale + g.y
            for g in item.glyphs
            for st in g.strokes
            for pt in st[1::2]
            if g.y < bar_y
        ]
        den_ys = [
            pt * g.scale + g.y
            for g in item.glyphs
            for st in g.strokes
            for pt in st[1::2]
            if g.y > bar_y
        ]
        assert num_ys, "Phải có nét tử số"
        assert den_ys, "Phải có nét mẫu số"

        num_bottom_ink = max(num_ys)
        den_top_ink = min(den_ys)

        clearance_num = bar_y - num_bottom_ink
        clearance_den = den_top_ink - bar_y

        # Kiểm tra khoảng hở quang học trong dải [0.15 * xh, 0.25 * xh]
        assert 0.15 * xh <= clearance_num <= 0.25 * xh, f"Khoảng hở tử số - gạch ({clearance_num:.2f}) ngoài [0.15*xh, 0.25*xh]"
        assert 0.15 * xh <= clearance_den <= 0.25 * xh, f"Khoảng hở mẫu số - gạch ({clearance_den:.2f}) ngoài [0.15*xh, 0.25*xh]"

        # Độ nhô của gạch phân số mỗi bên: overhang = (bar_w - actual_content_w) / 2
        bar_w = bar_line.points[1][0] - bar_line.points[0][0]
        num_w = engine.measure(node.num, scale=0.80).size.width
        den_w = engine.measure(node.den, scale=0.80).size.width
        actual_content_w = max(num_w, den_w)
        overhang = (bar_w - actual_content_w) / 2.0
        assert 0.15 * xh <= overhang <= 0.25 * xh, f"Độ nhô gạch phân số ({overhang:.2f}) ngoài [0.15*xh, 0.25*xh]"

    # Edge case: phân số chứa chỉ số trên / chỉ số dưới (\frac{x^2}{2}, \frac{1}{n_1}) không bao giờ chạm gạch
    for tex in (r"\frac{x^2}{2}", r"\frac{1}{n_1}"):
        row = parse_latex_math(tex)
        item = engine.measure(row)
        bar_y = item.strokes[0].points[0][1]
        num_ys = [pt * g.scale + g.y for g in item.glyphs for st in g.strokes for pt in st[1::2] if g.y < bar_y]
        den_ys = [pt * g.scale + g.y for g in item.glyphs for st in g.strokes for pt in st[1::2] if g.y > bar_y]
        assert bar_y - max(num_ys) >= 0.15 * xh - 0.02
        assert min(den_ys) - bar_y >= 0.15 * xh - 0.02


def test_piecewise_cases_fraction_compactness(sample_bank_v4):
    """T016 [US3]: Kiểm tra chiều cao phân số trong hệ cases giảm tối thiểu 25%."""
    b = sample_bank_v4
    engine = MathLayoutEngine(b, S=1.0)

    # Biểu thức cases 2 dòng phân số
    latex = r"\begin{cases} \frac{1}{36} \\ \frac{25}{36} \end{cases}"
    row = parse_latex_math(latex)
    item = engine.measure(row)

    # Chiều cao trước đây là 56.85 pt (> 7.15 * xh).
    # Với cải tiến: triệt tiêu phantom descent, compact gap và child_scale 0.78,
    # chiều cao giảm >= 25% (<= 42.6 pt hay <= 5.4 * xh).
    assert item.size.height <= 43.0, f"Chiều cao hệ cases phân số không giảm đạt 25%: {item.size.height:.2f} > 43.0"
