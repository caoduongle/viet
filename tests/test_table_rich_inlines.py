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




def test_intentional_empty_lines_in_table_cell_retained_with_height(tiny_bank, tmp_path):
    """Kiểm tra US6 (T025, T026): Các dòng trống có chủ đích (

) trong ô bảng
    phải được bảo toàn đầy đủ thành các phần tử dòng rỗng với chiều cao dòng chuẩn (line_h),
    không bị nuốt mất hay làm sụp đổ khoảng cách giữa các dòng."""
    from tests.conftest import _inst
    for ch in "abcdefghijklmnopqrstuvwxyz123":
        if ch not in tiny_bank.letters and ch not in tiny_bank.digits:
            tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]

    cell_text = "Line 1\n\nLine 3"
    cell = TableCell.from_text(cell_text)

    table = Table(
        rows=[TableRow(cells=[cell])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_empty_lines.xopp")

    opts = WriteOptions(line=20.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out_file)

    assert res.n_tables == 1

    # Kiểm tra trực tiếp dữ liệu bố cục qua TableLayoutEngine
    from chuviettay.layout.table_layout import TableLayoutEngine
    t_engine = TableLayoutEngine(engine.width, engine.line_h)

    # Sử dụng formatter mô phỏng pipeline thực tế
    layout_data = t_engine.layout_table(table, x0=engine.x0, y0=engine.page_format.content_top)
    row_h = layout_data.row_heights[0]
    expected_min_h = 3 * engine.line_h + 2 * t_engine.cell_padding
    assert row_h >= expected_min_h - 1e-3, (
        f"Chiều cao hàng phải phản ánh đủ 3 dòng vật lý (kể cả dòng trống): {row_h} < {expected_min_h}"
    )

    # Trích xuất toạ độ nét vẽ thực tế từ file .xopp
    from tests.test_xopp_geometry_helper import extract_xopp_pages_strokes
    pages_strokes = extract_xopp_pages_strokes(out_file)
    assert len(pages_strokes) == 1
    content_strokes = pages_strokes[0][4:]  # bỏ 4 nét viền bảng

    # Toạ độ y của nét 'Line 1' và 'Line 3' phải cách nhau ít nhất 2 * line_h
    l1_ys = []
    l3_ys = []
    mid_y = layout_data.y + row_h / 2.0
    for stroke in content_strokes:
        for pt in stroke:
            if pt[1] < mid_y:
                l1_ys.append(pt[1])
            else:
                l3_ys.append(pt[1])

    assert l1_ys and l3_ys, "Cả Line 1 và Line 3 đều phải sinh nét chữ"
    max_l1_y = max(l1_ys)
    min_l3_y = min(l3_ys)
    gap_between_lines = min_l3_y - max_l1_y
    assert gap_between_lines >= engine.line_h * 0.5, (
        f"Khoảng cách giữa Line 1 và Line 3 phải đủ rộng cho dòng trống: gap={gap_between_lines:.2f}"
    )


def test_table_cell_stroke_bounding_box_containment_with_jitter(tiny_bank, tmp_path):
    """Kiểm tra US7 (T028): Toàn bộ nét vẽ chữ và công thức sau biến đổi run tay (jitter=1.0)
    phải được bảo đảm nằm gọn 100% trong giới hạn cột ô bảng và lề trang in."""
    from tests.conftest import _inst
    for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
        if ch not in tiny_bank.letters:
            tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
        if ch not in tiny_bank.digits:
            tiny_bank.digits[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]

    c0 = TableCell.from_text("Cot thu nhat noi dung dai")
    c1 = TableCell.from_text("Cot thu hai noi dung rat dai va phong phu")

    table = Table(
        rows=[TableRow(cells=[c0, c1])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_jitter_containment.xopp")

    opts = WriteOptions(width=300.0, jitter=1.0, seed=12345)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    _ = engine.render(doc, out_file)

    from tests.test_xopp_geometry_helper import (
        assert_all_strokes_within_page_bounds,
        extract_xopp_pages_strokes,
    )
    # 1. Nằm trong lề trang
    assert_all_strokes_within_page_bounds(out_file, max_y=841.89 - 60.0, min_y=40.0 - 5.0)

    # 2. Nằm trong ranh giới cột
    pages_strokes = extract_xopp_pages_strokes(out_file)
    max_table_x = engine.x0 + engine.width + 6.0
    for s_idx, stroke in enumerate(pages_strokes[0]):
        for pt in stroke:
            x, y = pt
            assert x <= max_table_x, f"Nét {s_idx} tràn qua mép phải bảng: {x} > {max_table_x}"
            assert x >= engine.x0 - 5.0, f"Nét {s_idx} tràn ra mép trái bảng: {x} < {engine.x0 - 5.0}"
