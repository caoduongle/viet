"""Bộ tạo tệp nền tài liệu không chứa chữ in (Whiteout Background Generator).

Thực hiện biến đổi Whiteout Run Transform trực tiếp ở cấp ZIP/OpenXML:
chỉ sửa màu của text run (<w:r>, <a:r>) và của công thức Office Math (<m:r> cùng ký tự cấu trúc
trong <m:ctrlPr>: gạch phân số, dấu căn, ngoặc...) thành trắng (#FFFFFF),
giữ nguyên 100% từng byte của các thành phần đồ họa (ảnh, biểu đồ,
SmartArt, shapes, themes, relationships) mà không parse/save lại toàn bộ tài liệu
bằng python-docx.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
import zipfile
from typing import Set

_log = logging.getLogger(__name__)

# Standard OpenXML Namespaces
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

# QNames
QN_W_R = f"{{{W_NS}}}r"
QN_W_RPR = f"{{{W_NS}}}rPr"
QN_W_COLOR = f"{{{W_NS}}}color"
QN_W_VAL = f"{{{W_NS}}}val"
QN_W_THEME_COLOR = f"{{{W_NS}}}themeColor"
QN_W_THEME_TINT = f"{{{W_NS}}}themeTint"
QN_W_THEME_SHADE = f"{{{W_NS}}}themeShade"
QN_W_HIGHLIGHT = f"{{{W_NS}}}highlight"
QN_W_SHD = f"{{{W_NS}}}shd"

QN_M_RPR = f"{{{M_NS}}}rPr"
QN_M_CTRLPR = f"{{{M_NS}}}ctrlPr"

# Thẻ cấu trúc OMML có phần thuộc tính <m:{tên}Pr> (chứa <m:ctrlPr> định dạng ký tự cấu trúc)
_MATH_STRUCTURES = (
    "f", "d", "nary", "rad", "acc", "bar", "groupChr", "limLow", "limUpp", "m", "eqArr",
    "sSup", "sSub", "sSubSup", "sPre", "box", "borderBox", "phant", "func",
)
# Phần tử đứng SAU <w:color> trong lược đồ CT_RPr: chèn màu trước chúng để giữ đúng thứ tự schema
_RPR_AFTER_COLOR = frozenset({
    "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd",
    "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath",
})

QN_A_R = f"{{{A_NS}}}r"
QN_A_RPR = f"{{{A_NS}}}rPr"
QN_A_SOLID_FILL = f"{{{A_NS}}}solidFill"
QN_A_SRGB_CLR = f"{{{A_NS}}}srgbClr"

# Target parts containing printable text runs that must be whitened
TARGET_EXACT_PARTS: Set[str] = {
    "word/document.xml",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "word/comments.xml",
    "word/glossary/document.xml",
}
TARGET_HEADER_FOOTER_RE = re.compile(r"^word/(header|footer)\d*\.xml$", re.IGNORECASE)


def is_target_xml_part(filename: str) -> bool:
    """Xác định tệp XML trong gói DOCX có chứa text runs cần làm trắng hay không."""
    fn_lower = filename.lower().replace("\\", "/")
    if fn_lower in TARGET_EXACT_PARTS:
        return True
    if TARGET_HEADER_FOOTER_RE.match(fn_lower):
        return True
    return False


def _set_rpr_white(rpr) -> None:
    """Đặt <w:color w:val="FFFFFF"> trong một <w:rPr>, giữ đúng thứ tự phần tử theo schema; bỏ highlight/shd."""
    from lxml import etree

    color = rpr.find(QN_W_COLOR)
    if color is None:
        color = etree.Element(QN_W_COLOR)
        anchor = next((c for c in rpr
                       if isinstance(c.tag, str) and c.tag.split("}")[-1] in _RPR_AFTER_COLOR), None)
        if anchor is not None:
            anchor.addprevious(color)
        else:
            rpr.append(color)
    color.set(QN_W_VAL, "FFFFFF")
    for attr in (QN_W_THEME_COLOR, QN_W_THEME_TINT, QN_W_THEME_SHADE):
        if attr in color.attrib:
            del color.attrib[attr]
    for tag in (QN_W_HIGHLIGHT, QN_W_SHD):
        child = rpr.find(tag)
        if child is not None:
            rpr.remove(child)


def _whiten_math(root, ns) -> None:
    """Làm trắng công thức OMML: chạy toán <m:r> (w:rPr nằm sau m:rPr, trước m:t) và <m:ctrlPr> của cấu trúc.

    Theo lược đồ OOXML; Word áp màu này, còn LibreOffice bỏ qua màu chữ trong công thức (đã thử nghiệm)."""
    from lxml import etree

    for m_r in root.xpath(".//m:r", namespaces=ns):
        w_rpr = m_r.find(QN_W_RPR)
        if w_rpr is None:
            w_rpr = etree.Element(QN_W_RPR)
            m_rpr = m_r.find(QN_M_RPR)
            if m_rpr is not None:
                m_rpr.addnext(w_rpr)
            else:
                m_r.insert(0, w_rpr)
        _set_rpr_white(w_rpr)

    for name in _MATH_STRUCTURES:
        for struct in root.xpath(f".//m:{name}", namespaces=ns):
            pr_tag = f"{{{M_NS}}}{name}Pr"
            pr = struct.find(pr_tag)
            if pr is None:
                pr = etree.Element(pr_tag)
                struct.insert(0, pr)
            ctrl = pr.find(QN_M_CTRLPR)
            if ctrl is None:
                ctrl = etree.SubElement(pr, QN_M_CTRLPR)      # ctrlPr luôn là phần tử cuối của *Pr
            w_rpr = ctrl.find(QN_W_RPR)
            if w_rpr is None:
                w_rpr = etree.SubElement(ctrl, QN_W_RPR)
            _set_rpr_white(w_rpr)


def _whiten_xml_bytes(xml_bytes: bytes) -> bytes:
    """Phẫu thuật làm trắng các text run trong một XML part, bảo tồn tiền tố namespace và cấu trúc schema."""
    from lxml import etree

    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False, no_network=True)
    root = etree.fromstring(xml_bytes, parser=parser)
    ns = {"w": W_NS, "a": A_NS, "m": M_NS}

    # 1. Làm trắng toàn bộ WordprocessingML runs (<w:r>)
    for r in root.xpath(".//w:r", namespaces=ns):
        # OpenXML schema: <w:rPr> phải đứng đầu tiên trong <w:r> (trước <w:t>, <w:drawing>, v.v.)
        rPr = r.find(QN_W_RPR)
        if rPr is None:
            rPr = etree.Element(QN_W_RPR)
            r.insert(0, rPr)

        # Xử lý <w:color>
        color = rPr.find(QN_W_COLOR)
        if color is None:
            color = etree.Element(QN_W_COLOR)
            rPr.append(color)
        color.set(QN_W_VAL, "FFFFFF")

        # Xóa thuộc tính themeColor/themeTint/themeShade để Word không ưu tiên màu theme
        for attr in (QN_W_THEME_COLOR, QN_W_THEME_TINT, QN_W_THEME_SHADE):
            if attr in color.attrib:
                del color.attrib[attr]

        # Xóa hoặc làm sạch highlight
        highlight = rPr.find(QN_W_HIGHLIGHT)
        if highlight is not None:
            rPr.remove(highlight)

        # Xóa shading nền text nếu có
        shd = rPr.find(QN_W_SHD)
        if shd is not None:
            rPr.remove(shd)

    # 2. Làm trắng toàn bộ DrawingML runs (<a:r>)
    for a_r in root.xpath(".//a:r", namespaces=ns):
        a_rPr = a_r.find(QN_A_RPR)
        if a_rPr is None:
            a_rPr = etree.Element(QN_A_RPR)
            a_r.insert(0, a_rPr)
        # Loại bỏ các kiểu fill cũ (solidFill, gradFill, blipFill, pattFill, noFill)
        for child in list(a_rPr):
            tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag_name in ("solidFill", "gradFill", "blipFill", "pattFill", "noFill"):
                a_rPr.remove(child)
        solid_fill = etree.Element(QN_A_SOLID_FILL)
        srgb_clr = etree.Element(QN_A_SRGB_CLR)
        srgb_clr.set("val", "FFFFFF")
        solid_fill.append(srgb_clr)
        a_rPr.append(solid_fill)

    # 3. Làm trắng công thức Office Math (<m:r> và ký tự cấu trúc qua <m:ctrlPr>)
    _whiten_math(root, ns)

    return etree.tostring(root, xml_declaration=True, encoding="utf-8", standalone="yes")


class WhiteoutBackgroundGenerator:
    """Tạo bản sao DOCX đã làm trắng chữ in để làm nền cho Xournal++."""

    @classmethod
    def create_whiteout_docx(cls, docx_path: str, output_path: str | None = None) -> str:
        """Đổi toàn bộ text runs trong DOCX thành màu trắng qua phẫu thuật ZIP cấp thấp và lưu ra file mới."""
        docx_abs = os.path.abspath(docx_path)
        if not os.path.exists(docx_abs):
            raise FileNotFoundError(f"Không tìm thấy tệp DOCX: {docx_path}")

        cleanup_temp = False
        if output_path is None:
            fd, output_path = tempfile.mkstemp(prefix="whiteout_", suffix=".docx")
            os.close(fd)
            cleanup_temp = True

        output_abs = os.path.abspath(output_path)
        tmp_out = output_abs + ".tmp"

        try:
            with zipfile.ZipFile(docx_abs, "r") as in_zip:
                with zipfile.ZipFile(tmp_out, "w", compression=zipfile.ZIP_DEFLATED) as out_zip:
                    for info in in_zip.infolist():
                        raw_data = in_zip.read(info.filename)
                        if is_target_xml_part(info.filename):
                            try:
                                whitened_data = _whiten_xml_bytes(raw_data)
                                out_zip.writestr(info, whitened_data)
                            except Exception as parse_err:
                                _log.warning("Không thể phân tích XML part %s, giữ nguyên: %s", info.filename, parse_err)
                                out_zip.writestr(info, raw_data)
                        else:
                            # Pass-through nguyên vẹn 100% từng byte (ảnh, bảng biểu, shapes, _rels...)
                            out_zip.writestr(info, raw_data)

            if os.path.exists(output_abs):
                try:
                    os.remove(output_abs)
                except OSError:
                    pass
            os.replace(tmp_out, output_abs)
            return output_abs

        except Exception as e:
            _log.error("Lỗi khi tạo whiteout DOCX: %s", e)
            if os.path.exists(tmp_out):
                try:
                    os.remove(tmp_out)
                except OSError:
                    pass
            if cleanup_temp and os.path.exists(output_abs):
                try:
                    os.remove(output_abs)
                except OSError:
                    pass
            raise RuntimeError(f"Không thể làm trắng chữ in trong DOCX ({docx_path}): {e}") from e
