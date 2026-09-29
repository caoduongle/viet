"""Kiểm thử bộ nạp tài liệu Word (.docx) và chuyển đổi OMML."""
import io
import pytest

from chuviettay.document.ir import Heading, MathBlock, Paragraph, Table, Text
from chuviettay.importer.dependency import require_dependency


@pytest.fixture(autouse=True)
def require_docx():
    require_dependency("docx", "tài liệu Word (.docx)", "docs")


def test_import_docx_sequential_order(tmp_path):
    import docx
    from chuviettay.importer.docx_importer import DocxImporter

    doc_path = str(tmp_path / "sequential.docx")
    doc = docx.Document()
    doc.add_paragraph("Đoạn mở đầu 1")
    tbl = doc.add_table(rows=2, cols=2)
    tbl.cell(0, 0).text = "A1"
    tbl.cell(0, 1).text = "B1"
    tbl.cell(1, 0).text = "A2"
    tbl.cell(1, 1).text = "B2"
    doc.add_paragraph("Đoạn giữa 2")
    doc.save(doc_path)

    importer = DocxImporter()
    res = importer.import_file(doc_path)

    assert len(res.document.blocks) == 3
    assert isinstance(res.document.blocks[0], Paragraph)
    assert res.document.blocks[0].inlines[0].text == "Đoạn mở đầu 1"

    assert isinstance(res.document.blocks[1], Table)
    table_block = res.document.blocks[1]
    assert len(table_block.rows) == 2
    assert table_block.rows[0].cells[0].blocks[0].inlines[0].text == "A1"
    assert table_block.rows[1].cells[1].blocks[0].inlines[0].text == "B2"

    assert isinstance(res.document.blocks[2], Paragraph)
    assert res.document.blocks[2].inlines[0].text == "Đoạn giữa 2"


def test_import_docx_headings_and_styles(tmp_path):
    import docx
    from chuviettay.importer.docx_importer import DocxImporter

    doc_path = str(tmp_path / "headings.docx")
    doc = docx.Document()
    doc.add_heading("Tiêu đề 1", level=1)
    doc.add_heading("Tiêu đề 2", level=2)
    doc.add_paragraph("Nội dung thường")
    doc.save(doc_path)

    importer = DocxImporter()
    res = importer.import_file(doc_path)

    assert len(res.document.blocks) == 3
    assert isinstance(res.document.blocks[0], Heading)
    assert res.document.blocks[0].level == 1
    assert res.document.blocks[0].inlines[0].text == "Tiêu đề 1"

    assert isinstance(res.document.blocks[1], Heading)
    assert res.document.blocks[1].level == 2
    assert res.document.blocks[1].inlines[0].text == "Tiêu đề 2"

    assert isinstance(res.document.blocks[2], Paragraph)
    assert res.document.blocks[2].inlines[0].text == "Nội dung thường"


def test_import_docx_omml_equations(tmp_path):
    import docx
    from docx.oxml import parse_xml
    from chuviettay.importer.docx_importer import DocxImporter
    from chuviettay.math.ast import Fraction, MathRow, Root

    doc_path = str(tmp_path / "math.docx")
    doc = docx.Document()
    p = doc.add_paragraph("Phương trình: ")

    # Chèn OMML phân số và căn thức vào đoạn văn
    omml_xml = (
        '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        '  <m:f>'
        '    <m:num><m:r><m:t>1</m:t></m:r></m:num>'
        '    <m:den><m:r><m:t>2</m:t></m:r></m:den>'
        '  </m:f>'
        '</m:oMath>'
    )
    p._element.append(parse_xml(omml_xml))

    # Chèn OMML căn thức ở đoạn riêng
    p2 = doc.add_paragraph()
    omml_rad = (
        '<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        '  <m:oMath>'
        '    <m:rad>'
        '      <m:radPr><m:degHide m:val="1"/></m:radPr>'
        '      <m:deg/>'
        '      <m:e><m:r><m:t>x</m:t></m:r></m:e>'
        '    </m:rad>'
        '  </m:oMath>'
        '</m:oMathPara>'
    )
    p2._element.append(parse_xml(omml_rad))

    doc.save(doc_path)

    importer = DocxImporter()
    res = importer.import_file(doc_path)

    # Kiểm tra phương trình inline trong p
    assert len(res.document.blocks) >= 2
    p_block = res.document.blocks[0]
    assert isinstance(p_block, Paragraph)

    # Đoạn thứ 2 chứa math block căn thức
    math_block = res.document.blocks[1]
    assert isinstance(math_block, (Paragraph, MathBlock))


def test_import_docx_unsupported_elements(tmp_path):
    import docx
    from docx.oxml import parse_xml
    from chuviettay.importer.docx_importer import DocxImporter

    doc_path = str(tmp_path / "unsupported.docx")
    doc = docx.Document()
    p = doc.add_paragraph("Có hình vẽ kèm theo:")
    # Chèn phần tử vẽ w:drawing giả lập
    drawing_xml = (
        '<w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '  <wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
        '    <wp:docPr id="1" name="Picture 1"/>'
        '  </wp:inline>'
        '</w:drawing>'
    )
    p._element.append(parse_xml(drawing_xml))
    doc.save(doc_path)

    importer = DocxImporter()
    res = importer.import_file(doc_path)

    assert len(res.unsupported) > 0
    assert any("drawing" in item.lower() or "picture" in item.lower() for item in res.unsupported)
