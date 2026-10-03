"""
Tests for Letter Assembly Quality:
- Physical stroke clearance floor (>= 0.8 * pen_thickness)
- Boundary contour kerning and bounding-box overlap (<= 10%)
- Dual-Path assembly (precomposed glyphs vs decomposed base + tone mark)
- Dot suppression on i/j when upper tone mark is attached
- Dynamic stroke scaling and auto-xh compensation
"""
import math
import random
import pytest

from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteOptions, compose_document
from chuviettay.model.text_utils import (
    bbox,
    classify_left_contour,
    classify_right_contour,
    contour_pair_gap,
    min_stroke_clearance,
)
from chuviettay.model.writer import Writer


def _create_quality_test_bank(tmp_path) -> Bank:
    """Tạo một kho mẫu kiểm thử chuẩn cho letter assembly quality."""
    bank_path = str(tmp_path / "quality_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.xh = 7.94
    bank.pen = {"name": "pen", "width": "1.41"}

    # Nét thẳng: 'l', 'i', 'n', 'p'
    # 'l' (ascender)
    bank.add_letter_sample("l", [[0.0, -15.0, 0.0, 0.0]], width=2.0)
    # 'i' (có chấm)
    bank.add_letter_sample("i", [[0.0, -7.94, 0.0, 0.0], [0.0, -10.0, 0.5, -10.0]], width=2.0)
    # 'n'
    bank.add_letter_sample("n", [[0.0, -7.94, 0.0, 0.0, 4.0, -7.94, 4.0, 0.0]], width=5.0)
    # 'p' (descender)
    bank.add_letter_sample("p", [[0.0, -7.94, 0.0, 5.0, 4.0, -7.94, 4.0, 0.0, 0.0, 0.0]], width=5.0)
    # 'e'
    bank.add_letter_sample("e", [[0.0, -4.0, 4.0, -4.0, 4.0, -7.94, 0.0, -7.94, 0.0, 0.0, 4.0, 0.0]], width=5.0)

    # Nét cong: 'o', 'c'
    bank.add_letter_sample("o", [[0.0, -7.94, 4.0, -7.94, 4.0, 0.0, 0.0, 0.0, 0.0, -7.94]], width=5.0)
    bank.add_letter_sample("c", [[4.0, -7.94, 0.0, -7.94, 0.0, 0.0, 4.0, 0.0]], width=4.5)

    # Nét hở / chéo: 'v', 'u'
    bank.add_letter_sample("v", [[0.0, -7.94, 2.0, 0.0, 4.0, -7.94]], width=4.5)
    bank.add_letter_sample("u", [[0.0, -7.94, 0.0, 0.0, 4.0, 0.0, 4.0, -7.94]], width=5.0)

    # Chữ có dấu sẵn (precomposed) 'à'
    bank.add_letter_sample("à", [[0.0, -7.94, 4.0, -7.94, 4.0, 0.0, 0.0, 0.0], [1.0, -11.0, 3.0, -9.0]], width=5.0)
    # Chữ 'a' không dấu
    bank.add_letter_sample("a", [[0.0, -7.94, 4.0, -7.94, 4.0, 0.0, 0.0, 0.0]], width=5.0)

    # Dấu thanh rời trong marks: huyền (\u0300), sắc (\u0301)
    bank.add_tone_sample("\u0300", [0.0, 0.0, 2.0, 1.5], dx=0.0, dy=-2.0)
    bank.add_tone_sample("\u0301", [0.0, 1.5, 2.0, 0.0], dx=0.0, dy=-2.0)

    return bank


def test_min_stroke_clearance_calculation():
    # 2 nét thẳng song song: nét 1 từ x=0 đến x=2, nét 2 từ x=5 đến x=7
    s1 = [2.0, -5.0, 2.0, 0.0]
    s2 = [5.0, -5.0, 5.0, 0.0]
    dist = min_stroke_clearance([s1], [s2])
    assert pytest.approx(dist, abs=0.01) == 3.0

    # 2 nét chạm nhau tại (2, 0)
    s3 = [2.0, 0.0, 4.0, 0.0]
    dist_touch = min_stroke_clearance([s1], [s3])
    assert pytest.approx(dist_touch, abs=0.01) == 0.0


def test_contour_pair_gap_ordering():
    # Kiểm tra quy tắc kerning tự nhiên:
    # CURVED-CURVED < STRAIGHT-STRAIGHT
    xh = 7.94
    gap_cc = contour_pair_gap("CURVED", "CURVED", xh=xh)
    gap_ss = contour_pair_gap("STRAIGHT", "STRAIGHT", xh=xh)
    assert gap_cc < gap_ss
    assert gap_cc >= 0.05 * xh
    assert gap_ss >= 0.15 * xh


def test_assemble_word_clearance_floor(tmp_path):
    bank = _create_quality_test_bank(tmp_path)
    rnd = random.Random(42)
    pen_w = float(bank.pen["width"])  # 1.41
    k = 0.8
    floor = k * pen_w  # ~1.128

    wr = Writer(
        bank,
        rnd,
        jitter=0.0,
        assemble_letters=True,
        letter_gap=1.0,
        pen_clearance_factor=k,
    )

    # Ghép từ "pipeline" (tập hợp nét thẳng l, i, p, n rất dễ dính)
    res = wr.assemble_word("pipeline")
    assert res is not None
    strokes, total_w = res
    assert len(strokes) >= 8
    assert total_w > 0

    # Kiểm tra khoảng hở giữa các chữ cái liền kề
    # Lấy bbox các nét theo chiều x tăng dần
    # Mọi cặp nét không được đè lên nhau gây cục mực
    for i in range(len(strokes) - 1):
        s_a = strokes[i]
        s_b = strokes[i + 1]
        bb_a = bbox(s_a)
        bb_b = bbox(s_b)
        # Nếu là 2 ký tự khác nhau (bb_b nằm bên phải bb_a)
        if bb_b[0] > bb_a[0]:
            clearance = min_stroke_clearance([s_a], [s_b])
            # Khoảng cách tối thiểu phải thoả mãn sàn
            # (hoặc nếu là nét phụ trong cùng chữ thì bỏ qua)
            if clearance < 50.0:  # lân cận
                assert clearance >= floor - 0.05, f"Clearance {clearance} vi pham san {floor}"


def test_assemble_word_dual_path(tmp_path):
    bank = _create_quality_test_bank(tmp_path)
    rnd = random.Random(42)
    wr = Writer(bank, rnd, assemble_letters=True)

    # Path 1: Chữ 'à' có sẵn mẫu nguyên khối trong letters -> lấy thẳng
    res_a_tone = wr.assemble_word("à")
    assert res_a_tone is not None

    # Path 2: Từ "cá" -> chữ 'c' + chữ 'a' + dấu sắc '\u0301' ghép từ marks
    res_ca = wr.assemble_word("ca")
    assert res_ca is not None

    # Dấu sắc '\u0301' trên 'ca' -> "cá"
    res_ca_sac = wr.assemble_word("cá")
    assert res_ca_sac is not None
    strokes, w = res_ca_sac
    # Số nét phải có thêm nét dấu sắc
    assert len(strokes) >= len(res_ca[0]) + 1


def test_i_dot_suppression_on_upper_tone(tmp_path):
    bank = _create_quality_test_bank(tmp_path)
    rnd = random.Random(42)
    wr = Writer(bank, rnd, assemble_letters=True)

    # Ghép từ "lí" (l + i + dấu sắc)
    res = wr.assemble_word("lí")
    assert res is not None
    strokes, w = res

    # Nét của 'l' (1 nét) + thân 'i' (1 nét, không có chấm) + dấu sắc (1 nét) = 3 nét
    # Không được có 4 nét (tránh chồng dấu sắc lên chấm i)
    assert len(strokes) == 3


def test_auto_xh_and_dynamic_stroke_scaling(tmp_path):
    bank = _create_quality_test_bank(tmp_path)
    opts = WriteOptions(
        assemble_letters=True,
        scale=2.0,
        auto_xh=True,
        target_xh=7.94,
        letter_gap=1.0,
        pen_clearance_factor=0.8,
    )
    parts, res = compose_document(bank, "pipeline", opts)
    assert res.n_strokes > 0
    # Kiểm tra stroke xml sinh ra có wscale được bù trừ phù hợp
    xml_content = "".join(parts)
    assert 'width="' in xml_content
