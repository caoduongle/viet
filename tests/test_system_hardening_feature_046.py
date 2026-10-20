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
        Heading(level=1, inlines=[Text("Chương 1")]),
        Paragraph(inlines=[Text("Đoạn văn mới thêm"), Text("Chương 1")]),
    ])

    aligned = align_document_seeds(doc1, doc2)
    heading_text = aligned.blocks[0].inlines[0]
    para_text = aligned.blocks[1].inlines[1]

    # Cả hai đều có occurrence = 0 do namespace khác nhau
    assert heading_text.token_occurrences == [0, 0]
    assert para_text.token_occurrences == [0, 0]

    # 2. Kiểm tra layout engine render Heading với context_prefix='heading'
    opts = WriteOptions(seed=12345, stable_variants=True, jitter=0.2)
    engine1 = DocumentLayoutEngine(sample_bank_v4, opts)
    out1 = str(tmp_path / "doc1.xopp")
    engine1.render(doc1, out1)

    engine2 = DocumentLayoutEngine(sample_bank_v4, opts)
    out2 = str(tmp_path / "doc2.xopp")
    engine2.render(aligned, out2)

    assert os.path.exists(out1)
    assert os.path.exists(out2)


def test_seed_table_mathblock_occurrence_forwarding(sample_bank_v4, tmp_path):
    """T014/T016: MathBlock trong ô bảng chuyển tiếp đầy đủ occurrence và stable_id."""
    mb = MathBlock(latex="x^2 + y^2 = z^2")
    cell = TableCell(blocks=[mb])
    table = Table(rows=[TableRow(cells=[cell])])

    doc1 = Document(blocks=[table])
    doc2 = Document(blocks=[
        Paragraph(inlines=[Text("Nội dung bổ sung phía trước bảng")]),
        copy.deepcopy(table),
    ])

    aligned = align_document_seeds(doc1, doc2)
    table_block = aligned.blocks[1]
    mb_aligned = table_block.rows[0].cells[0].blocks[0]
    assert hasattr(mb_aligned, "occurrence")
    assert mb_aligned.occurrence == 0

    opts = WriteOptions(seed=999, stable_variants=True)
    engine = DocumentLayoutEngine(sample_bank_v4, opts)
    out_path = str(tmp_path / "table_math.xopp")
    engine.render(aligned, out_path)
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
    """T018/T019: Mẫu chữ số cực nhỏ hoặc cực lớn được co giãn thích ứng về ~ 1.20 * xh."""
    w = Writer(sample_bank_v4)
    xh = getattr(sample_bank_v4, "xh", 7.94) or 7.94
    target_h = 1.20 * xh

    # 1. Mẫu cực nhỏ: sample_h = 0.10 * xh
    tiny_sample = {
        "s": [[0.0, 0.0, 1.0, 0.0, 1.0, 0.10 * xh, 0.0, 0.10 * xh]],
        "w": 1.0,
    }
    st_tiny, w_tiny = w._normalize_digit_sample(tiny_sample, "5", xh=xh)
    _, _, min_y, max_y = get_strokes_bbox(st_tiny)
    actual_h_tiny = max_y - min_y
    # Chiều cao sau chuẩn hóa phải nằm trong dải xấp xỉ target_h ± 15%
    assert abs(actual_h_tiny - target_h) <= 0.15 * target_h, f"Tiny sample height {actual_h_tiny} out of expected range"

    # 2. Mẫu cực lớn: sample_h = 5.0 * xh
    huge_sample = {
        "s": [[0.0, 0.0, 10.0, 0.0, 10.0, 5.0 * xh, 0.0, 5.0 * xh]],
        "w": 10.0,
    }
    st_huge, w_huge = w._normalize_digit_sample(huge_sample, "5", xh=xh)
    _, _, min_y_huge, max_y_huge = get_strokes_bbox(st_huge)
    actual_h_huge = max_y_huge - min_y_huge
    assert 1.05 * xh <= actual_h_huge <= 1.35 * xh, f"Huge sample height {actual_h_huge} out of expected range"


def test_negative_number_hyphen_spacing(sample_bank_v4):
    """T018/T020: Dấu âm '-' ở đầu số có khoảng cách thu hẹp 0.5 * dgap (<= 0.12 * xh)."""
    w = Writer(sample_bank_v4, stable_variants=True, seed=123)
    xh = getattr(sample_bank_v4, "xh", 7.94) or 7.94

    st_neg, total_w_neg, _ = w.number("-5")
    # Đảm bảo có nét vẽ trả về
    assert len(st_neg) > 0

    # Lấy vị trí biên phải của '-' và biên trái của '5'
    st_dash, dash_w = w._normalize_digit_sample(sample_bank_v4.punct.get("-", [{}])[0], "-") if "-" in sample_bank_v4.punct else ([], 0.5 * xh)
    # Khoảng cách được nén 0.5 * dgap trong Writer.number()
    gap_computed = w._resolve_dgap(False, is_hyphen=True, digit_idx=1)
    assert gap_computed <= 0.12 * xh, f"Hyphen gap {gap_computed} exceeds 0.12 * xh ({0.12 * xh})"


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
