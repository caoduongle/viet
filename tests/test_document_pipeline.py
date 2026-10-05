"""Kiểm thử tích hợp luồng Document IR: Importer -> Layout Engine -> .xopp."""
import gzip
import os
import xml.etree.ElementTree as ET
import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Paragraph, Text
from chuviettay.importer.txt_importer import TxtImporter


def test_write_document_from_ir(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="xin chào bạn")]),
        Paragraph(inlines=[Text(text="ba bà chào")]),
    ])

    out = str(tmp_path / "doc_test.xopp")
    opts = WriteOptions(seed=42)
    res = ctl.write_document(doc, opts, out)

    assert res.n_lines >= 2
    assert res.n_strokes > 0

    # Kiểm tra tính hợp lệ của file XML đã nén
    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    assert root.tag == "xournal"
    pages = root.findall("page")
    assert len(pages) >= 1
    layer = pages[0].find("layer")
    assert layer is not None
    strokes = layer.findall("stroke")
    assert len(strokes) > 0


def test_write_document_from_txt_importer(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    importer = TxtImporter()
    import_res = importer.import_text("xin ba bà\n\nxin chào")
    out = str(tmp_path / "txt_importer_test.xopp")
    res = ctl.write_document(import_res.document, WriteOptions(seed=7), out)

    assert res.n_lines >= 2
    assert res.n_strokes > 0


def test_write_empty_document(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[])
    out = str(tmp_path / "empty.xopp")
    res = ctl.write_document(doc, WriteOptions(), out)

    assert res.n_lines == 0
    assert res.n_strokes == 0
    # Phải có 1 trang giấy trắng hợp lệ
    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    pages = root.findall("page")
    assert len(pages) == 1


def test_write_document_with_table(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import Table, TableBorder, TableCell, TableRow
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Bảng điểm danh:")]),
        Table(
            rows=[
                TableRow(cells=[TableCell.from_text("Tên"), TableCell.from_text("Chào")]),
                TableRow(cells=[TableCell.from_text("ba"), TableCell.from_text("bà")]),
            ],
            border_style=TableBorder.ALL,
        ),
    ])

    out = str(tmp_path / "table_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_strokes > 0

    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    layer = root.find("page/layer")
    assert layer is not None
    strokes = layer.findall("stroke")
    # Phải có cả nét viền và nét chữ
    assert len(strokes) >= 6


def test_write_document_with_math_block(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import MathBlock
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Công thức nghiệm:")]),
        MathBlock(latex="x = \\frac{-b}{2a}"),
    ])

    out = str(tmp_path / "math_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_strokes > 0

    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    layer = root.find("page/layer")
    assert layer is not None
    strokes = layer.findall("stroke")
    assert len(strokes) >= 1


def test_write_document_with_list_block(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import ListBlock
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        ListBlock(
            ordered=True,
            items=[
                [Paragraph(inlines=[Text(text="mục thứ nhất")])],
                [Paragraph(inlines=[Text(text="mục thứ hai")])],
            ],
            start=1,
        ),
        ListBlock(
            ordered=False,
            items=[
                [Paragraph(inlines=[Text(text="gạch đầu dòng A")])],
                [Paragraph(inlines=[Text(text="gạch đầu dòng B")])],
            ],
        ),
    ])

    out = str(tmp_path / "list_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_lines >= 4
    assert res.n_strokes > 0


def test_write_document_with_inline_math_and_symbols(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import MathInline, Symbol
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[
            Text(text="xin chào"),
            MathInline(latex="\\Delta = b^2 - 4ac"),
            Symbol(symbol="≤"),
            Text(text="1"),
        ])
    ])

    out = str(tmp_path / "inline_math_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_strokes > 0
    assert "≤" in res.missing_symbols
    assert res.missing_symbols["≤"] >= 1


def test_write_document_table_pagination(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import Table, TableBorder, TableCell, TableRow
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    # Bảng 5 hàng với khoảng cách dòng 800pt -> tổng chiều cao > 3000pt (MAXH) -> ngắt trang
    rows = [TableRow(cells=[TableCell.from_text(f"xin {i}"), TableCell.from_text(f"ba {i}")]) for i in range(5)]
    doc = Document(blocks=[Table(rows=rows, border_style=TableBorder.ALL)])

    out = str(tmp_path / "paginated_table.xopp")
    res = ctl.write_document(doc, WriteOptions(line=800, seed=12), out)
    assert res.n_tables == 1
    assert res.n_strokes > 0

    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    pages = root.findall("page")
    assert len(pages) > 1, "Bảng lớn vượt quá chiều cao trang phải được chia thành nhiều trang"
    for p in pages:
        layer = p.find("layer")
        assert layer is not None
        strokes = layer.findall("stroke")
        assert len(strokes) > 0, "Mỗi trang phải có nét viền và nội dung ô"


def test_write_document_split_ordered_list_numbering(tiny_bank_path, tmp_path):
    """Kiểm thử tích hợp: danh sách có thứ tự bị ngắt bởi bảng giữ nguyên số thứ tự 1..5 trong pipeline Document."""
    pytest.importorskip("markdown_it", reason="Cần cài đặt markdown-it-py để chạy kiểm thử định dạng Markdown")
    from chuviettay.importer.markdown_importer import MarkdownImporter
    importer = MarkdownImporter()
    md = """1. Mục một
2. Mục hai
3. Mục ba

| Cột A | Cột B |
|---|---|
| A | B |

4. Mục bốn
5. Mục năm"""
    res_import = importer.import_text(md)
    doc = res_import.document
    assert len(doc.blocks) == 3
    assert doc.blocks[0].start == 1
    assert doc.blocks[2].start == 4

    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    out = str(tmp_path / "split_list.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_lines >= 5
    assert res.n_strokes > 0
    assert os.path.exists(out)


def test_write_document_paper_sizes_and_orientations(tiny_bank_path, tmp_path):
    """Kiểm thử tích hợp: kích thước và chiều giấy (A4, A3, A5, Custom, Portrait, Landscape) ghi chuẩn xác vào XML .xopp."""
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Văn bản kiểm tra khổ giấy và chiều giấy.")]),
    ])

    # 1. A4 Portrait
    out_a4_p = str(tmp_path / "a4_portrait.xopp")
    ctl.write_document(doc, WriteOptions(paper="a4", orientation="portrait"), out_a4_p)
    raw = gzip.decompress(open(out_a4_p, "rb").read()).decode("utf-8")
    assert '<page width="595.28" height="841.89">' in raw

    # 2. A4 Landscape
    out_a4_l = str(tmp_path / "a4_landscape.xopp")
    ctl.write_document(doc, WriteOptions(paper="a4", orientation="landscape"), out_a4_l)
    raw = gzip.decompress(open(out_a4_l, "rb").read()).decode("utf-8")
    assert '<page width="841.89" height="595.28">' in raw

    # 3. A3 Portrait
    out_a3_p = str(tmp_path / "a3_portrait.xopp")
    ctl.write_document(doc, WriteOptions(paper="a3", orientation="portrait"), out_a3_p)
    raw = gzip.decompress(open(out_a3_p, "rb").read()).decode("utf-8")
    assert '<page width="841.89" height="1190.55">' in raw

    # 4. A5 Portrait
    out_a5_p = str(tmp_path / "a5_portrait.xopp")
    ctl.write_document(doc, WriteOptions(paper="a5", orientation="portrait"), out_a5_p)
    raw = gzip.decompress(open(out_a5_p, "rb").read()).decode("utf-8")
    assert '<page width="419.53" height="595.28">' in raw

    # 5. Custom paper
    out_custom = str(tmp_path / "custom.xopp")
    ctl.write_document(
        doc,
        WriteOptions(paper="custom", paper_width=500.0, paper_height=700.0, orientation="portrait"),
        out_custom,
    )
    raw = gzip.decompress(open(out_custom, "rb").read()).decode("utf-8")
    assert '<page width="500" height="700">' in raw or '<page width="500.0" height="700.0">' in raw


def test_write_document_native_background_xml(tiny_bank_path, tmp_path):
    """Kiểm thử tích hợp: thẻ <background> sinh tự nhiên và không vẽ thêm bất kỳ nét giả lập nền nào."""
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Dòng chữ trên nền ô li 5mm.")]),
    ])

    # 1. Graph / Ô Li 5mm (14.17 pt)
    out_graph = str(tmp_path / "graph_5mm.xopp")
    res_graph = ctl.write_document(
        doc,
        WriteOptions(paper="a4", background="graph", background_spacing=14.17),
        out_graph,
    )
    raw = gzip.decompress(open(out_graph, "rb").read()).decode("utf-8")
    assert 'style="graph"' in raw
    assert 'config="r1=14.17"' in raw
    assert 'color="#ffffffff"' in raw

    # Không sinh nét vẽ thừa nào cho nền (chỉ có nét viết tay của chữ)
    root = ET.fromstring(raw.encode("utf-8"))
    layer = root.find(".//layer")
    assert layer is not None
    assert len(layer.findall("stroke")) == res_graph.n_strokes

    # 2. Ruled with margin
    out_ruled = str(tmp_path / "ruled_margin.xopp")
    ctl.write_document(
        doc,
        WriteOptions(paper="a4", background="ruled", background_spacing=24.0, background_margin=72.0),
        out_ruled,
    )
    raw_ruled = gzip.decompress(open(out_ruled, "rb").read()).decode("utf-8")
    assert 'style="ruled"' in raw_ruled
    assert 'r1=24' in raw_ruled
    assert 'm1=72' in raw_ruled


def test_write_text_unifies_into_document_pipeline_with_paper_and_background(tiny_bank_path, tmp_path):
    """Kiểm thử tích hợp: ctl.write_text() đi qua Document IR pipeline và áp dụng đúng khổ giấy, hướng giấy, nền XML."""
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    out_path = str(tmp_path / "write_text_a3_graph.xopp")
    text = "Dòng 1 văn bản trực tiếp\n\nDòng 2 đoạn văn mới"
    opts = WriteOptions(
        paper="a3",
        orientation="landscape",
        background="graph",
        background_spacing=14.17,
        seed=42,
    )
    res = ctl.write_text(text, opts, out_path)
    assert res.n_lines >= 2
    assert os.path.exists(out_path)

    raw = gzip.decompress(open(out_path, "rb").read()).decode("utf-8")
    assert '<page width="1190.55" height="841.89">' in raw
    assert 'style="graph"' in raw
    assert 'config="r1=14.17"' in raw


def test_d4a_missing_grid_false_does_not_create_thieu_file(tiny_bank_path, tmp_path):
    """[D4a] Khi missing_grid=False, write_text không sinh file _thieu.xopp."""
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    out = str(tmp_path / "out_d4a.xopp")
    res = ctl.write_text("zebra quokka", WriteOptions(seed=1, missing_grid=False), out)
    assert res.missing_grid_path is None
    assert not os.path.exists(str(tmp_path / "out_d4a_thieu.xopp"))


def test_d4b_does_not_overwrite_user_handwriting_in_missing_grid(tiny_bank_path, tmp_path):
    """[D4b] Khi _thieu.xopp đã có nét vẽ của người dùng, không ghi đè mà ghi ra _thieu_2.xopp."""
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    out = str(tmp_path / "out_d4b.xopp")
    res1 = ctl.write_text("zebra quokka", WriteOptions(seed=1), out)
    grid_1 = res1.missing_grid_path
    assert grid_1 and os.path.exists(grid_1)
    # Giả lập người dùng viết nét vào grid_1
    xml = gzip.decompress(open(grid_1, "rb").read()).decode("utf-8")
    marker = '<stroke tool="pen" color="#000000ff" width="1.41">60 100 70 90 80 100</stroke>\n'
    xml = xml.replace("</layer>", marker + "</layer>", 1)
    with gzip.open(grid_1, "wt", encoding="utf-8") as f:
        f.write(xml)
    bytes_before = open(grid_1, "rb").read()

    # Chạy lại write_text
    res2 = ctl.write_text("zebra quokka", WriteOptions(seed=1, scale=1.1), out)
    assert res2.missing_grid_path == str(tmp_path / "out_d4b_thieu_2.xopp")
    assert os.path.exists(res2.missing_grid_path)
    # File cũ có nét của người dùng còn nguyên
    assert open(grid_1, "rb").read() == bytes_before




