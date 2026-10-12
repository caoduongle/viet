"""Kiểm thử bố cục các phần tử nội dòng (toán học, ký hiệu, ngắt dòng) bên trong ô bảng."""
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, MathInline, Paragraph, Symbol, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.engine import DocumentLayoutEngine


def test_table_cell_with_math_inline_and_symbols(tiny_bank, tmp_path):
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["giá"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 15.0}]
    tiny_bank.words["trị"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 15.0}]

    cell = TableCell(blocks=[
        Paragraph(inlines=[
            Text("giá trị"),
            MathInline(latex="x^2"),
            Symbol(symbol="≤"),
            Text("10"),
        ])
    ])
    table = Table(
        rows=[TableRow(cells=[cell])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out = str(tmp_path / "table_math.xopp")

    opts = WriteOptions(scale=1.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out)

    assert res.n_tables == 1
    assert res.n_strokes > 4, "Phải sinh cả nét viền bảng và các nét chữ, toán học bên trong ô"


def test_table_cell_tall_formula_expands_row_height(tiny_bank, tmp_path):
    """Kiểm tra ô chứa công thức toán cao (như phân số) tự động mở rộng chiều cao hàng."""
    tiny_bank.words["a"] = [{"s": [[0, 0, 5, -8, 10, 0]], "w": 10.0}]
    tiny_bank.words["b"] = [{"s": [[0, 0, 0, -15, 8, 0]], "w": 10.0}]

    plain_cell = TableCell(blocks=[Paragraph(inlines=[Text("Chữ thường")])])
    math_cell = TableCell(blocks=[Paragraph(inlines=[MathInline(latex=r"\frac{a}{b}")])])

    table = Table(
        rows=[TableRow(cells=[plain_cell, math_cell])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out = str(tmp_path / "table_tall_math.xopp")

    opts = WriteOptions(scale=1.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out)

    assert res.n_tables == 1

    from chuviettay.layout.table_layout import TableLayoutEngine
    t_engine = TableLayoutEngine(engine.width, engine.line_h)
    layout = t_engine.layout_table(table, x0=engine.x0, y0=engine.page_format.content_top)

    # 1. Chiều cao của hàng phải được tự động mở rộng theo công thức
    std_row_h = engine.line_h + 2 * t_engine.cell_padding
    assert layout.row_heights[0] >= std_row_h, f"Hàng có công thức cao phải có chiều cao >= {std_row_h}, nhận được {layout.row_heights[0]}"

    # 2. Kiểm tra nét công thức nằm gọn trong ô cột 1
    col0_w, col1_w = layout.col_widths[0], layout.col_widths[1]
    cell1_x0 = engine.x0 + col0_w
    cell1_x1 = cell1_x0 + col1_w
    cell1_y0 = layout.y
    cell1_y1 = cell1_y0 + layout.row_heights[0]

    from tests.test_xopp_geometry_helper import extract_xopp_pages_strokes
    pages_strokes = extract_xopp_pages_strokes(out)
    assert len(pages_strokes) == 1

    content_strokes = pages_strokes[0][5:]
    for s_idx, stroke in enumerate(content_strokes):
        xs = [pt[0] for pt in stroke]
        ys = [pt[1] for pt in stroke]
        if min(xs) >= cell1_x0:
            assert max(xs) <= cell1_x1 + 1e-2, f"Nét {s_idx} vượt quá mép phải ô: {max(xs)} > {cell1_x1}"
            assert min(xs) >= cell1_x0 - 1e-2, f"Nét {s_idx} lấn sang mép trái ô: {min(xs)} < {cell1_x0}"
            assert min(ys) >= cell1_y0 - 1e-2, f"Nét {s_idx} vượt quá mép trên ô: {min(ys)} < {cell1_y0}"
            assert max(ys) <= cell1_y1 + 1e-2, f"Nét {s_idx} vượt quá mép đáy ô: {max(ys)} > {cell1_y1}"


@pytest.mark.parametrize(
    "scale,auto_xh",
    [
        (0.5, False),
        (1.0, False),
        (1.5, False),
        (1.0, True),
    ],
)
@pytest.mark.parametrize(
    "latex",
    [
        r"\frac{a}{b}",
        r"\sqrt{\frac{a}{b}}",
        r"\int_{0}^{1} x dx",
    ],
)
def test_table_cell_tall_formula_multi_scale_boundary(tiny_bank, tmp_path, scale, auto_xh, latex):
    """Kiểm tra công thức cao (phân số, căn thức, tích phân) ở các tỷ lệ viết (0.5, 1.0, 1.5, auto_xh)
    luôn nằm gọn trong trang in và không gây va chạm toạ độ.
    """
    from tests.test_xopp_geometry_helper import (
        assert_all_strokes_within_page_bounds,
        extract_xopp_pages_strokes,
    )

    tiny_bank.words["a"] = [{"s": [[0, 0, 5, -8, 10, 0]], "w": 10.0}]
    tiny_bank.words["b"] = [{"s": [[0, 0, 0, -15, 8, 0]], "w": 10.0}]
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["0"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["1"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["d"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]

    plain_cell = TableCell(blocks=[Paragraph(inlines=[Text("T")])])
    math_cell = TableCell(blocks=[Paragraph(inlines=[MathInline(latex=latex)])])

    table = Table(
        rows=[TableRow(cells=[plain_cell, math_cell])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    safe_name = latex.replace("\\", "").replace("{", "").replace("}", "").replace("^", "").replace("_", "")
    out = str(tmp_path / f"tall_math_s{scale}_xh{auto_xh}_{safe_name}.xopp")

    opts = WriteOptions(scale=scale, auto_xh=auto_xh, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out)

    assert res.n_tables == 1
    assert_all_strokes_within_page_bounds(out, max_y=841.89 - 60.0, min_y=40.0)

    pages = extract_xopp_pages_strokes(out)
    assert len(pages) == 1
    strokes = pages[0]
    assert len(strokes) >= 4, "Phải có nét viền và nét công thức"


def test_table_descenders_and_formulas_boundary_clamping_at_page_bottom(tiny_bank, tmp_path):
    """Kiểm tra US2 & US4: Chữ có phần đuôi vươn xuống (descenders như 'quốc gia'),
    công thức toán học cao và hiệu ứng jitter gần mép đáy trang:
    100% toạ độ nét vẽ phải thỏa mãn y <= max_page_y (841.89 - 60.0),
    không bị lọt/văng ra ngoài lề đáy trang giấy hay đè qua ranh giới ô."""
    from tests.conftest import _inst
    for ch in "abcdefghijklmnopqrstuvwxyzgiátrịquốc":
        if ch not in tiny_bank.letters:
            tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
    # Nét của chữ 'g', 'q', 'y' vươn sâu xuống dưới baseline (descent = 6.0)
    tiny_bank.letters["g"] = [_inst(4.0, [[0, 0, 2, 6, 4, 0]])]
    tiny_bank.letters["q"] = [_inst(4.0, [[0, 0, 2, 6, 4, 0]])]
    tiny_bank.words["quốc"] = [{"s": [[0, 0, 5, -8, 10, 0]], "w": 15.0}]
    tiny_bank.words["gia"] = [{"s": [[0, 0, 5, 8, 10, 0]], "w": 15.0}]
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["y"] = [{"s": [[0, 0, 5, 8, 10, 0]], "w": 10.0}]

    from tests.test_xopp_geometry_helper import assert_all_strokes_within_page_bounds

    # Tạo bảng nằm gần đáy trang bằng cách thêm các đoạn văn bản đệm phía trước
    paras = [Paragraph(inlines=[Text(f"Doan van ban dem thu {i}")]) for i in range(25)]
    cell_desc = TableCell(blocks=[Paragraph(inlines=[Text("quốc gia Việt Nam")])])
    cell_math = TableCell(blocks=[Paragraph(inlines=[MathInline(latex=r"\frac{\sqrt{x}}{y^2}")])])

    table = Table(
        rows=[TableRow(cells=[cell_desc, cell_math])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[*paras, table])
    out = str(tmp_path / "clamping_bottom_boundary.xopp")

    opts = WriteOptions(scale=1.0, jitter=1.0, line=22.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out)

    assert res.n_tables == 1
    # 100% toạ độ nét vẽ trên toàn bộ các trang nằm trong khoảng an toàn đáy trang in
    assert_all_strokes_within_page_bounds(out, max_y=841.89 - 60.0, min_y=40.0 - 5.0)


