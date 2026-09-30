"""Kiểm thử tính tỷ lệ hình học và co giãn đồng bộ (User Story 5 - L4, L5, R8, R9, v2.1)."""
import math
import random
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, MathBlock, Paragraph, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.engine import DocumentLayoutEngine
from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.layout.table_layout import TableLayoutEngine
from chuviettay.math.ast import TextNode


def test_proportional_line_height_scaling(tiny_bank):
    """L4: Bước dòng mặc định phải nhân theo opts.scale khi người dùng không chỉ định --line."""
    base_line = float(tiny_bank.d["line"])

    # Scale 1.0 -> line_h = base_line
    engine_1 = DocumentLayoutEngine(tiny_bank, WriteOptions(scale=1.0))
    assert engine_1.line_h == pytest.approx(base_line, abs=0.01)

    # Scale 2.0 không có --line -> line_h = base_line * 2.0
    engine_2 = DocumentLayoutEngine(tiny_bank, WriteOptions(scale=2.0))
    assert engine_2.line_h == pytest.approx(base_line * 2.0, abs=0.01)

    # Scale 2.0 nhưng có --line cụ thể -> tôn trọng giá trị --line của người dùng
    engine_custom = DocumentLayoutEngine(tiny_bank, WriteOptions(scale=2.0, line=35.0))
    assert engine_custom.line_h == pytest.approx(35.0, abs=0.01)


def test_uniform_math_block_scaling(tiny_bank):
    """L5: Công thức toán (MathBlock và MathLayoutEngine) phải co giãn đồng bộ theo scale."""
    engine_1 = MathLayoutEngine(tiny_bank, S=1.0)
    engine_2 = MathLayoutEngine(tiny_bank, S=2.0)

    node = TextNode("x")
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]

    item_1 = engine_1.measure(node)
    item_2 = engine_2.measure(node)

    # Cỡ x2 thì chiều rộng và chiều cao phải gấp đôi, không bị kẹt ở ~1.0
    assert item_2.size.width == pytest.approx(item_1.size.width * 2.0, abs=0.05)
    assert item_2.size.ascent == pytest.approx(item_1.size.ascent * 2.0, abs=0.05)
    assert item_2.glyphs[0].scale == pytest.approx(item_1.glyphs[0].scale * 2.0, abs=0.05)


def test_math_ascent_descent_from_actual_strokes(tiny_bank):
    """R9: Chiều cao chữ trong công thức tính từ hộp bao nét thật (bounding box) thay vì cố định xh."""
    engine = MathLayoutEngine(tiny_bank, S=1.0)
    # Chữ 'h' cao vượt xh (stroke lên tới y = -15, trong khi xh = 7.0)
    tiny_bank.words["h"] = [{"s": [[0, 0, 0, -15, 5, -15, 5, 0]], "w": 8.0}]

    item = engine.measure(TextNode("h"))
    # Ascent phải đo được chiều cao thật 15.0 chứ không bị cắt cụt ở 0.9 * 7 = 6.3
    assert item.size.ascent >= 14.5


def test_table_column_measurement_with_actual_stroke_bounds(tiny_bank):
    """R8: Bảng đo bề rộng cột từ nét vẽ thật (calc_text_bounds) thay vì ước tính sơ sài theo số ký tự."""
    # Giả lập từ rất dài "nghiêng" có bề rộng nét thật là 85.0
    def mock_calc_bounds(word: str) -> float:
        if word == "nghiêng":
            return 85.0
        return len(word) * 8.0

    tbl = Table(
        rows=[
            TableRow(cells=[TableCell(blocks=[Paragraph(inlines=[Text("nghiêng")])])]),
        ]
    )

    # TableLayoutEngine với calc_text_bounds
    engine = TableLayoutEngine(available_width=300.0, line_height=25.0, calc_text_bounds=mock_calc_bounds)
    widths = engine.compute_column_widths(tbl)
    # Cột chứa từ "nghiêng" (85.0 pt + padding 12.0 pt = 97.0 pt) phải đủ rộng để chứa nét thật
    assert widths[0] >= 95.0


def test_table_border_deterministic_jitter():
    """Viền bảng run tay theo jitter và tất định theo seed."""
    from chuviettay.layout.table_layout import LaidOutCell, TableLayoutData

    data = TableLayoutData(
        x=50.0,
        y=100.0,
        width=200.0,
        height=100.0,
        col_widths=[100.0, 100.0],
        row_heights=[50.0, 50.0],
        cells=[
            [
                LaidOutCell(x=50.0, y=100.0, width=100.0, height=50.0, text_lines=["a"]),
                LaidOutCell(x=150.0, y=100.0, width=100.0, height=50.0, text_lines=["b"]),
            ],
            [
                LaidOutCell(x=50.0, y=150.0, width=100.0, height=50.0, text_lines=["c"]),
                LaidOutCell(x=150.0, y=150.0, width=100.0, height=50.0, text_lines=["d"]),
            ],
        ],
    )

    engine = TableLayoutEngine(available_width=300.0, line_height=25.0)

    # 1. Jitter = 0.0 -> nét thẳng hoàn hảo (chỉ 2 điểm mỗi đoạn)
    straight_strokes = engine.generate_border_strokes(data, TableBorder.ALL, jitter=0.0)
    for st in straight_strokes:
        assert len(st.points) == 2

    # 2. Jitter > 0 -> có các điểm trung gian rung nhẹ
    jitter_strokes_1 = engine.generate_border_strokes(data, TableBorder.ALL, jitter=1.0, seed=123)
    jitter_strokes_2 = engine.generate_border_strokes(data, TableBorder.ALL, jitter=1.0, seed=123)
    jitter_strokes_diff = engine.generate_border_strokes(data, TableBorder.ALL, jitter=1.0, seed=456)

    has_multi_pt = any(len(st.points) > 2 for st in jitter_strokes_1)
    assert has_multi_pt, "Viền bảng có jitter phải sinh các điểm trung gian rung nhẹ"

    # Tính tất định: cùng seed sinh toạ độ giống hệt nhau
    assert jitter_strokes_1 == jitter_strokes_2
    # Khác seed sinh toạ độ khác nhau
    assert jitter_strokes_1 != jitter_strokes_diff
