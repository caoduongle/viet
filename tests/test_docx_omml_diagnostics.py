"""Kiểm thử phát hiện và phân loại các thẻ OMML chưa được hỗ trợ vào ImportResult.unsupported."""
import pytest

pytest.importorskip("docx", reason="Cần cài đặt python-docx để chạy kiểm thử định dạng Word")

from docx import Document as DocxDoc  # noqa: E402
from docx.oxml import parse_xml  # noqa: E402

from chuviettay.importer.docx_importer import DocxImporter  # noqa: E402



def test_docx_omml_unsupported_tags_logged(tmp_path):
    doc_path = str(tmp_path / "omml_unsupported.docx")
    doc = DocxDoc()
    p = doc.add_paragraph("Tích phân và ma trận:")

    # Chèn thẻ m:nary (tích phân/tổng) và m:m (ma trận)
    omml_xml = (
        '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        '  <m:nary>'
        '    <m:naryPr><m:chr m:val="∫"/></m:naryPr>'
        '    <m:sub><m:r><m:t>0</m:t></m:r></m:sub>'
        '    <m:sup><m:r><m:t>1</m:t></m:r></m:sup>'
        '    <m:e><m:r><m:t>x dx</m:t></m:r></m:e>'
        '  </m:nary>'
        '  <m:m>'
        '    <m:mr><m:e><m:r><m:t>1</m:t></m:r></m:e></m:mr>'
        '  </m:m>'
        '</m:oMath>'
    )
    p._element.append(parse_xml(omml_xml))
    doc.save(doc_path)

    importer = DocxImporter()
    res = importer.import_file(doc_path)

    assert len(res.unsupported) >= 2
    unsupp_str = " ".join(res.unsupported)
    assert "m:nary" in unsupp_str
    assert "m:m" in unsupp_str


def test_docx_omml_supported_tags_not_in_unsupported(tmp_path):
    doc_path = str(tmp_path / "omml_supported.docx")
    doc = DocxDoc()
    p = doc.add_paragraph("Phương trình cơ bản:")

    # Phân số m:f và số mũ m:sSup
    omml_xml = (
        '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        '  <m:f>'
        '    <m:num><m:r><m:t>a</m:t></m:r></m:num>'
        '    <m:den><m:r><m:t>b</m:t></m:r></m:den>'
        '  </m:f>'
        '</m:oMath>'
    )
    p._element.append(parse_xml(omml_xml))
    doc.save(doc_path)

    importer = DocxImporter()
    res = importer.import_file(doc_path)

    assert len(res.unsupported) == 0
