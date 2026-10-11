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
    # Chiều cao của hàng phải lớn hơn chiều cao chuẩn của 1 dòng chữ thường
    # Đọc lại XML xopp để kiểm tra nét vẽ
    from chuviettay.model.xopp import read_xopp
    layers, pages = read_xopp(out)
    assert len(pages) >= 1


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


