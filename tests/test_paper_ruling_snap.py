import gzip
import pytest
import xml.etree.ElementTree as ET
from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteOptions
from chuviettay.layout.engine import DocumentLayoutEngine, TokenBox
from chuviettay.document.page_format import PageFormat, PageBackground, PAPER_SIZES
from chuviettay.document.ir import Document, Paragraph, Text


def test_ruled_baseline_snapping_exact_multiples(tmp_path, real_bank):
    """Kiểm tra mọi baseline y trên nền ruled đều thoả (y - 80) chia hết cho r1 với sai số < 0.05."""
    tokens_recorded: list[TokenBox] = []

    def callback(tb: TokenBox):
        tokens_recorded.append(tb)

    opts = WriteOptions(
        paper="a4",
        background="ruled",
        background_spacing=24.0,
        jitter=0.0,
        snap_to_ruling=True,
    )
    engine = DocumentLayoutEngine(real_bank, opts, token_layout_callback=callback)

    # 5 dòng văn bản
    doc = Document(blocks=[
        Paragraph(inlines=[Text(text=f"Dòng thứ {i} trên giấy kẻ ngang xin chào bạn.")])
        for i in range(1, 6)
    ])

    out_file = str(tmp_path / "ruled_snap.xopp")
    engine.render(doc, out_file)

    assert len(tokens_recorded) > 0

    baselines_by_line: dict[tuple[int, float], float] = {}
    for tb in tokens_recorded:
        baseline = round(tb.y + tb.height, 2)
        # Kiểm tra (baseline - 80) chia hết cho 24.0
        rem = (baseline - 80.0) % 24.0
        dist_to_multiple = min(rem, 24.0 - rem)
        assert dist_to_multiple < 0.05, f"Baseline {baseline} không trùng dòng kẻ r1=24 (sai lệch {dist_to_multiple})"
        baselines_by_line[(tb.page, baseline)] = baseline

    # Dòng đầu tiên phải ở 80.0
    first_baseline = min(b for (p, b) in baselines_by_line.keys() if p == 0)
    assert abs(first_baseline - 80.0) < 0.05, f"Dòng đầu tiên {first_baseline} không nằm tại 80.0"


def test_ruled_custom_spacing_r1_18(tmp_path, real_bank):
    """Kiểm tra snapping với r1=18 (lined_narrow)."""
    tokens_recorded: list[TokenBox] = []

    opts = WriteOptions(
        paper="a4",
        background="ruled",
        background_spacing=18.0,
        jitter=0.0,
        snap_to_ruling=True,
    )
    engine = DocumentLayoutEngine(real_bank, opts, token_layout_callback=lambda tb: tokens_recorded.append(tb))

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text=f"Đoạn văn số {i} với khổ kẻ hẹp xin chào bạn.")])
        for i in range(1, 4)
    ])

    out_file = str(tmp_path / "ruled_18.xopp")
    engine.render(doc, out_file)

    assert len(tokens_recorded) > 0
    for tb in tokens_recorded:
        baseline = round(tb.y + tb.height, 2)
        rem = (baseline - 80.0) % 18.0
        dist = min(rem, 18.0 - rem)
        assert dist < 0.05, f"Baseline {baseline} không trùng dòng kẻ r1=18 (sai lệch {dist})"


def test_lined_positive_margin_clamping(tmp_path, real_bank):
    """Kiểm tra giấy lined với m1=72: lề trái nội dung bắt đầu bên phải đường kẻ (x >= m1 + 8 = 80)."""
    tokens_recorded: list[TokenBox] = []

    opts = WriteOptions(
        paper="a4",
        background="lined",
        background_spacing=24.0,
        background_margin=72.0,
        margin_left=36.0,  # Nhỏ hơn m1, phải được clamp lên >= 80.0
        jitter=0.0,
        snap_to_ruling=True,
    )
    engine = DocumentLayoutEngine(real_bank, opts, token_layout_callback=lambda tb: tokens_recorded.append(tb))

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Nội dung phải nằm sau vạch kẻ lề đỏ xin chào.")])
    ])

    out_file = str(tmp_path / "lined_m1_pos.xopp")
    engine.render(doc, out_file)

    assert len(tokens_recorded) > 0
    for tb in tokens_recorded:
        assert tb.x >= 72.0 + 8.0 - 0.1, f"Token {tb.token} x={tb.x} bị đè hoặc nằm trước đường lề đứng m1=72"


def test_lined_negative_margin_clamping(tmp_path, real_bank):
    """Kiểm tra giấy lined với m1=-72: lề phải nội dung không vượt quá pageWidth + m1 - 8."""
    tokens_recorded: list[TokenBox] = []

    opts = WriteOptions(
        paper="a4",
        background="lined",
        background_spacing=24.0,
        background_margin=-72.0,
        jitter=0.0,
        snap_to_ruling=True,
    )
    engine = DocumentLayoutEngine(real_bank, opts, token_layout_callback=lambda tb: tokens_recorded.append(tb))

    # Văn bản dài để kiểm tra ngắt dòng trước lề phải
    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="xin chào bạn " * 20)])
    ])

    out_file = str(tmp_path / "lined_m1_neg.xopp")
    engine.render(doc, out_file)

    a4_width = PAPER_SIZES["a4"].width  # 595.28
    right_limit = a4_width - 72.0 - 8.0  # ~515.28

    assert len(tokens_recorded) > 0
    for tb in tokens_recorded:
        assert tb.x + tb.width <= right_limit + 1.0, (
            f"Token {tb.token} vượt quá lề phải m1=-72: x_end={tb.x + tb.width} > limit={right_limit}"
        )


def test_plain_background_invariance_no_snap(tmp_path, real_bank):
    """Kiểm tra nền plain không bị snap baseline (giữ nguyên vị trí tự nhiên 40 + 24 = 64)."""
    tokens_recorded: list[TokenBox] = []

    opts = WriteOptions(
        paper="a4",
        background="plain",
        margin_top=40.0,
        jitter=0.0,
        snap_to_ruling=True,  # Bật snap nhưng nền plain thì không áp dụng
    )
    engine = DocumentLayoutEngine(real_bank, opts, token_layout_callback=lambda tb: tokens_recorded.append(tb))

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="xin chào bạn trên giấy trơn.")])
    ])

    out_file = str(tmp_path / "plain_no_snap.xopp")
    engine.render(doc, out_file)

    assert len(tokens_recorded) > 0
    first_baseline = round(tokens_recorded[0].y + tokens_recorded[0].height, 2)
    # Vị trí tự nhiên: margin_top(40) + line_h(24) = 64.0
    assert abs(first_baseline - 64.0) < 0.1, f"Nền plain phải giữ nguyên baseline tự nhiên 64.0, nhận được: {first_baseline}"
