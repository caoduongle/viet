"""Kiểm thử chẩn đoán OMML: thẻ chưa biết được báo vào ImportResult.unsupported, thẻ đã hỗ trợ thì chuyển đổi thật."""
import pytest

pytest.importorskip("docx", reason="Cần cài đặt python-docx để chạy kiểm thử định dạng Word")

from docx import Document as DocxDoc  # noqa: E402
from docx.oxml import parse_xml  # noqa: E402

from chuviettay.importer.docx_importer import DocxImporter  # noqa: E402



def _import_omml(tmp_path, omml_xml, name="omml.docx"):
    doc_path = str(tmp_path / name)
    doc = DocxDoc()
    p = doc.add_paragraph("Công thức:")
    p._element.append(parse_xml(omml_xml))
    doc.save(doc_path)
    return DocxImporter().import_file(doc_path)


def test_docx_omml_unknown_tags_logged(tmp_path):
    """Thẻ OMML thật sự chưa biết vẫn phải được báo vào unsupported (không bỏ im lặng)."""
    res = _import_omml(
        tmp_path,
        '<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        '  <m:futureStructure><m:e><m:r><m:t>x</m:t></m:r></m:e></m:futureStructure>'
        '</m:oMath>',
    )
    assert any("m:futureStructure" in item for item in res.unsupported)


def test_docx_omml_nary_and_matrix_are_converted_not_unsupported(tmp_path):
    """m:nary (tích phân/tổng) và m:m (ma trận) đã được hỗ trợ: chuyển đổi thật, không còn nằm trong unsupported."""
    res = _import_omml(
        tmp_path,
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
        '</m:oMath>',
    )
    assert res.unsupported == []
    from chuviettay.math.ast import Matrix, NAry, walk

    math = [i for b in res.document.blocks for i in getattr(b, "inlines", []) if hasattr(i, "ast")][0]
    kinds = {type(n) for n in walk(math.ast)}
    assert NAry in kinds and Matrix in kinds
    nary = next(n for n in walk(math.ast) if isinstance(n, NAry))
    assert nary.op == "∫" and nary.sub is not None and nary.sup is not None


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
