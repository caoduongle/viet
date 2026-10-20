"""Bộ kiểm thử gia cố hệ thống toàn diện cho Feature 046:
- US3: Cô lập Seed Namespace giữa Heading và Paragraph
- US3: Chuyển tiếp occurrence/stable_id của MathBlock trong ô bảng
- US3: Phản ánh sub_index vào định danh hình học của chunk
- US4: Chuẩn hóa chữ số cực đoan bằng co giãn thích ứng trực tiếp
- US4: Thu hẹp khoảng cách dấu âm '-' ở đầu số
- US4: Đồng bộ hóa 100% giữa measure_text_width() và number()
"""
from __future__ import annotations

import copy
import os
import random
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer
from chuviettay.document.ir import (
    Document,
    Heading,
    Paragraph,
    Table,
    TableRow,
    TableCell,
    Text,
    MathBlock,
    MathInline,
    align_document_seeds,
)
from chuviettay.layout.engine import DocumentLayoutEngine


@pytest.fixture
def sample_bank_v4():
    """Nạp kho mẫu v4 chuẩn hoặc kho tổng hợp."""
    path = os.path.join("local data", "kho_mau_v4.json.gz")
    if os.path.exists(path):
        return Bank(path)
    synth_path = os.path.join("tests", "data", "kho_mau_tong_hop.json.gz")
    if os.path.exists(synth_path):
        return Bank(synth_path)
    b = Bank.create_empty("test_empty.json.gz")
    b.xh = 7.94
    return b


def get_strokes_bbox(strokes: list) -> tuple[float, float, float, float]:
    """Tính bounding box (min_x, max_x, min_y, max_y) cho danh sách nét vẽ."""
    if not strokes:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [pt for st in strokes for pt in st[0::2]]
    ys = [pt for st in strokes for pt in st[1::2]]
    if not xs or not ys:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), max(xs), min(ys), max(ys))


# ---------------------------------------------------------------------------
# USER STORY 3: Seed Namespace Isolation (T014 - T017)
# ---------------------------------------------------------------------------

def test_seed_heading_paragraph_isolation(sample_bank_v4, tmp_path):
    """T014/T015/T016: Heading có seed namespace 'heading' riêng biệt, độc lập với Paragraph 'text'."""
    # 1. Kiểm tra align_document_seeds phân tách namespace
    doc1 = Document(blocks=[
        Heading(level=1, inlines=[Text("Chương 1")]),
        Paragraph(inlines=[Text("Chương 1")]),
    ])
    doc2 = Document(blocks=[
        Paragraph(inlines=[Text("Đoạn văn mới thêm có chứa Chương 1 phía trước")]),
        Heading(level=1, inlines=[Text("Chương 1")]),
        Paragraph(inlines=[Text("Đoạn văn mới thêm"), Text("Chương 1")]),
    ])

    aligned = align_document_seeds(doc1, doc2)
    heading_text = aligned.blocks[1].inlines[0]
    para_text = aligned.blocks[2].inlines[1]

    # Heading vẫn giữ occurrence = [0, 0] dù Paragraph phía trước đã xuất hiện "Chương 1"
    assert heading_text.token_occurrences == [0, 0]
    assert para_text.token_occurrences == [0, 0]

    # 2. Kiểm tra nét kết xuất của Heading hoàn toàn bất biến trước và sau khi thêm nội dung vào đoạn văn
    opts = WriteOptions(seed=12345, stable_variants=True, jitter=0.2)
    engine1 = DocumentLayoutEngine(sample_bank_v4, opts)
    h_items1, _, _ = engine1._layout_inlines(
        doc1.blocks[0].inlines, scale_mult=1.35, context_prefix="heading"
    )
    out1 = str(tmp_path / "doc1.xopp")
    engine1.render(doc1, out1)

    engine2 = DocumentLayoutEngine(sample_bank_v4, opts)
    # Dù đoạn văn trước đã layout "Chương 1" trong namespace "text", Heading vẫn tạo đúng nét cũ
    engine2._layout_inlines(aligned.blocks[0].inlines, scale_mult=1.0, context_prefix="text")
    h_items2, _, _ = engine2._layout_inlines(
        aligned.blocks[1].inlines, scale_mult=1.35, context_prefix="heading"
    )
    assert [it.strokes for it in h_items1] == [it.strokes for it in h_items2], (
        "Nét chữ tiêu đề phải bất biến 100% khi chèn nội dung trùng từ vào đoạn văn"
    )
    out2 = str(tmp_path / "doc2.xopp")
    engine2.render(aligned, out2)

    assert os.path.exists(out1)
    assert os.path.exists(out2)


def test_seed_table_mathblock_occurrence_forwarding(sample_bank_v4, tmp_path):
    """T014/T016: MathBlock trong ô bảng chuyển tiếp đầy đủ occurrence và stable_id."""
    from tests.test_stable_variants import create_multivariant_bank

    mv_bank = create_multivariant_bank(tmp_path)
    mb = MathBlock(latex="x^2 + y^2 = z^2", stable_id="mb_tbl_01")
    cell = TableCell(blocks=[mb])
    table = Table(rows=[TableRow(cells=[cell])])

    doc1 = Document(blocks=[table])
    doc2 = Document(blocks=[
        Paragraph(inlines=[Text("Nội dung bổ sung phía trước bảng")]),
        MathBlock(latex="x^2 + y^2 = z^2"),
        copy.deepcopy(table),
    ])

    aligned = align_document_seeds(doc1, doc2)
    prepended_mb = aligned.blocks[1]
    table_block = aligned.blocks[2]
    mb_aligned = table_block.rows[0].cells[0].blocks[0]
    assert hasattr(mb_aligned, "occurrence")
    assert mb_aligned.occurrence == 0
    assert mb_aligned.stable_id == "mb_tbl_01"
    assert prepended_mb.occurrence == 1

    # Xác minh MathInline được tạo từ MathBlock trong ô bảng bảo toàn đúng nét vẽ (seed)
    opts = WriteOptions(seed=999, stable_variants=True, jitter=0.2)
    engine_before = DocumentLayoutEngine(mv_bank, opts)
    inl_before = MathInline(
        latex=mb.latex, ast=mb.ast, occurrence=0, stable_id=mb.stable_id
    )
    items_before, _, _ = engine_before._layout_inlines([inl_before], scale_mult=1.0, context_prefix="cell")

    engine_after = DocumentLayoutEngine(mv_bank, opts)
    # Giả lập đã render MathBlock chèn phía trước
    engine_after._layout_inlines(
        [MathInline(latex=prepended_mb.latex, occurrence=prepended_mb.occurrence)],
        scale_mult=1.0,
        context_prefix="text",
    )
    inl_after = MathInline(
        latex=mb_aligned.latex,
        ast=mb_aligned.ast,
        occurrence=mb_aligned.occurrence,
        stable_id=mb_aligned.stable_id,
    )
    items_after, _, _ = engine_after._layout_inlines([inl_after], scale_mult=1.0, context_prefix="cell")
    assert [it.strokes for it in items_before] == [it.strokes for it in items_after], (
        "Nét biểu thức toán trong ô bảng phải bất biến nhờ bảo toàn occurrence và stable_id"
    )

    out_path = str(tmp_path / "table_math.xopp")
    engine_after.render(aligned, out_path)
    assert os.path.exists(out_path)


def test_seed_chunk_geometry_differentiation(sample_bank_v4):
    """T014/T017: Các chunk lặp trong token dài mang token_id phân biệt bằng chunk_idx."""
    opts = WriteOptions(seed=42, stable_variants=True)
    engine = DocumentLayoutEngine(sample_bank_v4, opts)

    long_token = "ABCDEFGHIJKLMN" * 4
    # Bố cục với max_item_width nhỏ để ép ngắt chunk
    items, _, _ = engine._layout_inlines(
        [Text(text=long_token)],
        scale_mult=1.0,
        max_item_width=50.0,
        context_prefix="text",
    )

    assert len(items) > 1, "Token dài phải được chia thành nhiều chunk"
    token_ids = [item.token_id for item in items]
    # Kiểm tra mỗi chunk có hậu tố :0, :1, :2...
    assert token_ids[0].endswith(":0")
    assert token_ids[1].endswith(":1")
    # Tất cả token_id phải duy nhất
    assert len(token_ids) == len(set(token_ids))


# ---------------------------------------------------------------------------
# USER STORY 4: Robust Digit Typography & Hyphen Spacing (T018 - T021)
# ---------------------------------------------------------------------------

def test_digit_extreme_samples_adaptive_scaling(sample_bank_v4):
    """T018/T019/T024: Mẫu chữ số cực nhỏ (0.10*xh, 0.01*xh) hoặc cực lớn (5.0*xh, 20.0*xh) đạt ~ 1.20 * xh."""
    w = Writer(sample_bank_v4)
    xh = getattr(sample_bank_v4, "xh", 7.94) or 7.94
    target_h = 1.20 * xh

    # 1. Mẫu nhỏ: sample_h = 0.10 * xh
    tiny_sample = {
        "s": [[0.0, 0.0, 1.0, 0.0, 1.0, 0.10 * xh, 0.0, 0.10 * xh]],
        "w": 1.0,
    }
    st_tiny, w_tiny = w._normalize_digit_sample(tiny_sample, "5", xh=xh)
    _, _, min_y, max_y = get_strokes_bbox(st_tiny)
    actual_h_tiny = max_y - min_y
    assert abs(actual_h_tiny - target_h) <= 0.15 * target_h, f"Tiny sample height {actual_h_tiny} out of expected range"

    # 2. Mẫu lớn: sample_h = 5.0 * xh
    huge_sample = {
        "s": [[0.0, 0.0, 10.0, 0.0, 10.0, 5.0 * xh, 0.0, 5.0 * xh]],
        "w": 10.0,
    }
    st_huge, w_huge = w._normalize_digit_sample(huge_sample, "5", xh=xh)
    _, _, min_y_huge, max_y_huge = get_strokes_bbox(st_huge)
    actual_h_huge = max_y_huge - min_y_huge
    assert 1.05 * xh <= actual_h_huge <= 1.35 * xh, f"Huge sample height {actual_h_huge} out of expected range"

    # 3. Mẫu cực đoan siêu nhỏ: sample_h = 0.01 * xh (tỷ lệ > 15x)
    ultra_tiny = {
        "s": [[0.0, 0.0, 0.5, 0.0, 0.5, 0.01 * xh, 0.0, 0.01 * xh]],
        "w": 0.5,
    }
    st_ut, w_ut = w._normalize_digit_sample(ultra_tiny, "5", xh=xh)
    _, _, min_y_ut, max_y_ut = get_strokes_bbox(st_ut)
    actual_h_ut = max_y_ut - min_y_ut
    assert abs(actual_h_ut - target_h) <= 0.10 * target_h, f"Ultra-tiny height {actual_h_ut} != {target_h}"
    assert 0.35 * xh <= w_ut <= 0.95 * xh, f"Ultra-tiny width {w_ut} out of safe bounds"

    # 4. Mẫu cực đoan khổng lồ: sample_h = 20.0 * xh (tỷ lệ < 0.10x)
    ultra_huge = {
        "s": [[0.0, 0.0, 20.0, 0.0, 20.0, 20.0 * xh, 0.0, 20.0 * xh]],
        "w": 20.0,
    }
    st_uh, w_uh = w._normalize_digit_sample(ultra_huge, "5", xh=xh)
    _, _, min_y_uh, max_y_uh = get_strokes_bbox(st_uh)
    actual_h_uh = max_y_uh - min_y_uh
    assert abs(actual_h_uh - target_h) <= 0.10 * target_h, f"Ultra-huge height {actual_h_uh} != {target_h}"
    assert 0.35 * xh <= w_uh <= 0.95 * xh, f"Ultra-huge width {w_uh} out of safe bounds"


def test_negative_number_hyphen_spacing(sample_bank_v4):
    """T018/T020/T024: Đo trực tiếp khoảng hở bounding box thực tế giữa dấu '-' và chữ số đầu tiên."""
    w = Writer(sample_bank_v4, stable_variants=True, seed=123)
    xh = getattr(sample_bank_v4, "xh", 7.94) or 7.94

    st_neg, total_w_neg, _ = w.number("-5")
    assert len(st_neg) >= 2, "Phải có ít nhất nét dấu '-' và nét chữ số '5'"

    # Xác định số lượng nét của dấu '-' để tách nét dấu '-' và nét chữ số '5' trong kết quả render
    st_only_dash, _, _ = w.number("-")
    n_dash = len(st_only_dash)
    assert n_dash >= 1 and len(st_neg) > n_dash

    dash_strokes = st_neg[:n_dash]
    digit_strokes = st_neg[n_dash:]
    _, dash_max_x, dash_min_y, dash_max_y = get_strokes_bbox(dash_strokes)
    digit_min_x, _, _, _ = get_strokes_bbox(digit_strokes)

    # Kiểm tra khoảng hở quang học thực tế trên bounding box đã kết xuất
    actual_bbox_gap = digit_min_x - dash_max_x
    assert 0.02 * xh <= actual_bbox_gap <= 0.12 * xh, (
        f"Actual rendered bbox gap between '-' and '5' is {actual_bbox_gap:.3f}, "
        f"expected within [0.02*xh, 0.12*xh] ([{0.02 * xh:.3f}, {0.12 * xh:.3f}])"
    )
    # Kiểm tra tâm dọc của dấu '-' nằm tại trục toán học -0.45 * xh
    dash_mid_y = (dash_min_y + dash_max_y) / 2.0
    assert abs(dash_mid_y - (-0.45 * xh)) <= 0.05 * xh


def test_measure_text_width_number_sync(sample_bank_v4):
    """T018/T021: measure_text_width() và number() đồng bộ 100% với sai lệch <= 0.05 * xh."""
    w = Writer(sample_bank_v4, stable_variants=True, seed=456)
    xh = getattr(sample_bank_v4, "xh", 7.94) or 7.94

    test_numbers = ["0,39", "0,0278", "-5", "-123,45", "123456789"]
    for num_str in test_numbers:
        measured_w = w.measure_text_width(num_str)
        _, rendered_w, _ = w.number(num_str)
        diff = abs(measured_w - rendered_w)
        assert diff <= 0.05 * xh, (
            f"Number '{num_str}': measured_w={measured_w:.3f}, rendered_w={rendered_w:.3f}, "
            f"diff={diff:.3f} exceeds tolerance {0.05 * xh:.3f}"
        )


def test_degenerate_digit_sample_sanitization(sample_bank_v4):
    """T021/T024 [US5]: Chuẩn hóa an toàn mẫu chữ số suy biến (sample_h <= 1e-3 hoặc bbox_w <= 1e-3) đạt chiều cao 1.20 * xh."""
    w = Writer(sample_bank_v4, stable_variants=True, seed=42)
    xh = getattr(sample_bank_v4, "xh", 7.94) or 7.94
    target_h = 1.20 * xh

    # 1. Mẫu suy biến chiều cao (đoạn thẳng ngang sample_h = 0)
    flat_inst = {"s": [[0.0, -5.0, 4.0, -5.0]], "w": 4.0}
    norm_st, adv_w = w._normalize_digit_sample(flat_inst, "3", xh=xh)
    assert len(norm_st) > 0, "Phải trả về nét fallback hợp lệ cho mẫu suy biến chiều cao"
    assert adv_w >= 0.50 * xh, f"adv_w ({adv_w}) phải đạt tối thiểu 0.50 * xh"
    _, _, min_y_f, max_y_f = get_strokes_bbox(norm_st)
    assert abs((max_y_f - min_y_f) - target_h) <= 0.10 * target_h, "Mẫu phẳng phải được chuẩn hóa về chiều cao 1.20 * xh"

    # 2. Mẫu suy biến chiều rộng (đường thẳng dọc bbox_w = 0)
    dot_inst = {"s": [[2.0, 0.0, 2.0, -8.0]], "w": 0.0}
    norm_st_dot, adv_w_dot = w._normalize_digit_sample(dot_inst, "1", xh=xh)
    assert len(norm_st_dot) > 0, "Phải trả về nét fallback hợp lệ cho mẫu suy biến chiều rộng"
    assert adv_w_dot >= 0.50 * xh, f"adv_w_dot ({adv_w_dot}) phải đạt tối thiểu 0.50 * xh"
    _, _, min_y_d, max_y_d = get_strokes_bbox(norm_st_dot)
    assert abs((max_y_d - min_y_d) - target_h) <= 0.10 * target_h, "Mẫu dọc phải được chuẩn hóa về chiều cao 1.20 * xh"

    # 3. Dấu trừ suy biến
    minus_dot = {"s": [[2.0, -3.0, 2.0, -3.0]], "w": 0.0}
    norm_m, adv_m = w._normalize_digit_sample(minus_dot, "-", xh=xh)
    assert len(norm_m) > 0, "Phải trả về nét fallback hợp lệ cho dấu trừ suy biến"
    assert adv_m >= 0.40 * xh, f"adv_m ({adv_m}) phải đạt tối thiểu 0.40 * xh"


def test_measure_text_width_multivariant_bank_sync(tmp_path):
    """T021/T023 [US5]: measure_text_width() đồng bộ 100% với number() trên kho mẫu đa biến thể (cả stable_variants=True và False)."""
    from tests.test_stable_variants import create_multivariant_bank

    b = create_multivariant_bank(tmp_path)
    b.d["dgaps"] = [0.7, 1.4, 2.1]
    # Biến đổi độ rộng của các biến thể chữ số để tạo độ đa dạng
    for ch, samples in b.digits.items():
        if len(samples) > 1:
            samples[1]["w"] = samples[0]["w"] + 2.0
            samples[1]["s"] = [[pt * 1.5 if i % 2 == 0 else pt for i, pt in enumerate(st)] for st in samples[1]["s"]]

    xh = getattr(b, "xh", 7.0) or 7.0
    test_numbers = ["0,39", "0,0278", "-5", "-123,45", "123456789"]

    for stable_mode in (True, False):
        w = Writer(b, random.Random(456), stable_variants=stable_mode, seed=456)
        for num_str in test_numbers:
            counts_before = dict(w._token_counts)
            last_before = dict(w.last)

            measured_w = w.measure_text_width(num_str)

            # Khẳng định không làm đột biến state
            assert w._token_counts == counts_before, "measure_text_width không được làm biến đổi _token_counts"
            assert w.last == last_before, "measure_text_width không được làm biến đổi last"

            _, rendered_w, _ = w.number(num_str)
            diff = abs(measured_w - rendered_w)
            assert diff <= 0.05 * xh, (
                f"Multi-variant (stable={stable_mode}) '{num_str}': measured_w={measured_w:.3f}, "
                f"rendered_w={rendered_w:.3f}, diff={diff:.3f} exceeds tolerance {0.05 * xh:.3f}"
            )

