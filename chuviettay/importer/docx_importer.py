"""Bộ nạp tài liệu Microsoft Word (.docx) sang Document IR: công thức OMML, MathType (phát hiện) và chẩn đoán."""
from __future__ import annotations

import re
from typing import Any

from chuviettay.document.ir import (
    Block,
    Document,
    Heading,
    Inline,
    LineBreak,
    MathBlock,
    MathInline,
    Paragraph,
    Table,
    TableBorder,
    TableCell,
    TableRow,
    Text,
)
from chuviettay.importer.base import BaseImporter, ImportResult
from chuviettay.importer.dependency import require_dependency
from chuviettay.importer.omml import M_NS, iter_omath, omml_to_ast
from chuviettay.math.ast import MathRow, SymbolNode
from chuviettay.math.latex_writer import to_latex

# ProgID của đối tượng OLE chứa công thức MathType / Equation Editor 3.0 (Equation.DSMT4, Equation.3, MathType...)
_EQUATION_PROGID = re.compile(r"(?i)equation|mathtype|dsmt")

MATHTYPE_WARNING = (
    "Có {n} công thức MathType/Equation Editor (đối tượng OLE) mà ứng dụng chưa đọc được nên đã thay bằng ô vuông "
    "trống (□). Cách khắc phục: trong Word dùng chức năng Convert Equations của MathType (nếu có) để đổi sang "
    "công thức gốc của Word rồi lưu lại .docx, hoặc chép công thức sang Markdown/LaTeX."
)
EQ_FIELD_WARNING = (
    "Có {n} công thức dạng trường EQ cũ của Word (mã \\EQ) chưa đọc được nên không có trong kết quả; hãy gõ lại "
    "bằng Insert > Equation."
)


def _local(tag: Any) -> str:
    return tag.split("}")[-1] if isinstance(tag, str) and "}" in tag else (tag if isinstance(tag, str) else "")


def _only_one_math(inlines: list[Inline]) -> bool:
    """Các inline chỉ gồm đúng một công thức (bỏ qua khoảng trắng / ngắt dòng)?"""
    math = [i for i in inlines if isinstance(i, MathInline)]
    others = [i for i in inlines if not isinstance(i, MathInline)
              and not isinstance(i, LineBreak) and not (isinstance(i, Text) and not i.text.strip())]
    return len(math) == 1 and not others


class DocxImporter(BaseImporter):
    """Bộ nạp tài liệu .docx bảo toàn thứ tự đoạn văn/bảng và chuyển đổi công thức OMML."""

    def __init__(self):
        require_dependency("docx", "tài liệu Word (.docx)", "docs")
        self._reset_state()

    def _reset_state(self) -> None:
        self._mathtype_count = 0
        self._eq_field_count = 0

    def import_file(self, path: str) -> ImportResult:
        import docx

        doc = docx.Document(path)
        return self._parse_document(doc)

    def import_text(self, text: str) -> ImportResult:
        import docx

        # Cho chuỗi nhị phân bytes hoặc văn bản
        doc = docx.Document()
        doc.add_paragraph(text)
        return self._parse_document(doc)

    def _parse_document(self, doc: Any) -> ImportResult:
        import docx.table
        import docx.text.paragraph

        self._reset_state()
        blocks: list[Block] = []
        warnings: list[str] = []
        unsupported: list[str] = []

        # 1. Thu thập tuần tự qua iter_inner_content hoặc fallback doc.element.body
        elements: list[Any] = []
        if hasattr(doc, "iter_inner_content"):
            try:
                elements = list(doc.iter_inner_content())
            except Exception:
                elements = []

        if not elements:
            # Fallback cho các bản docx cũ hơn
            for child in doc.element.body:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "p":
                    elements.append(docx.text.paragraph.Paragraph(child, doc))
                elif tag == "tbl":
                    elements.append(docx.table.Table(child, doc))

        for item in elements:
            if isinstance(item, docx.text.paragraph.Paragraph):
                blocks.extend(self._parse_paragraph_blocks(item, unsupported))
            elif isinstance(item, docx.table.Table):
                table_block = self._parse_table(item, unsupported)
                blocks.append(table_block)

        if self._mathtype_count:
            warnings.append(MATHTYPE_WARNING.format(n=self._mathtype_count))
        if self._eq_field_count:
            warnings.append(EQ_FIELD_WARNING.format(n=self._eq_field_count))
        return ImportResult(document=Document(blocks=blocks), warnings=warnings, unsupported=unsupported)

    # ------------------------------------------------------------------ đối tượng OLE (MathType) và trường EQ
    @staticmethod
    def _ole_progid(elem: Any) -> str | None:
        """ProgID của ``o:OLEObject`` nằm trong ``elem`` (None nếu không có đối tượng OLE)."""
        for d in elem.iter():
            if _local(d.tag) == "OLEObject":
                return d.get("ProgID") or ""
        return None

    def _handle_ole(self, elem: Any, unsupported: list[str]) -> list[Inline]:
        progid = self._ole_progid(elem)
        if progid is not None and _EQUATION_PROGID.search(progid):
            self._mathtype_count += 1
            unsupported.append(f"mathtype: OLE equation object (ProgID={progid}) replaced by an empty box")
            return [MathInline(latex="\\square", ast=MathRow([SymbolNode("□")]))]
        if progid is not None:
            unsupported.append(f"object: embedded OLE object (ProgID={progid or 'unknown'})")
        else:
            unsupported.append("object: embedded object")
        return []

    def _extract_inlines_from_run(self, r_elem: Any, unsupported: list[str]) -> list[Inline]:
        """Trích xuất toàn bộ phần tử nội dòng từ một <w:r> (chữ, tab, ngắt dòng mềm), lọc delText/instrText."""
        inlines: list[Inline] = []
        for c in r_elem:
            ctag = c.tag.split("}")[-1] if "}" in c.tag else c.tag
            if ctag == "t":
                txt = c.text or ""
                if txt:
                    inlines.append(Text(text=txt))
            elif ctag == "tab":
                inlines.append(Text(text="    "))
            elif ctag in ("br", "cr"):
                inlines.append(LineBreak())
            elif ctag == "object" or (ctag == "pict" and self._ole_progid(c) is not None):
                inlines.extend(self._handle_ole(c, unsupported))
            elif ctag in ("drawing", "pict"):
                unsupported.append(f"{ctag}: embedded image or drawing shape")
            elif ctag == "delText":
                # Bản ghi xoá trong tracked change - bỏ qua không in
                pass
            elif ctag == "instrText":
                # Mã lệnh trường Word - bỏ qua không in lộ text thô, ghi vào unsupported
                if (c.text or "").strip().upper().startswith("EQ"):
                    self._eq_field_count += 1
                    unsupported.append("field: Word EQ equation field (not read)")
                elif "field_instruction: Word field code" not in unsupported:
                    unsupported.append("field_instruction: Word field code")
        return inlines

    # ------------------------------------------------------------------ công thức OMML
    def _omml_math(self, container: Any, unsupported: list[str]) -> list[tuple[MathRow, str]]:
        """Chuyển mọi ``m:oMath`` trong ``container`` sang (AST, LaTeX); công thức rỗng bị bỏ."""
        out: list[tuple[MathRow, str]] = []
        for om in iter_omath(container):
            ast, unsup = omml_to_ast(om)
            for tag in unsup:
                msg = f"m:{tag}: unsupported OMML math element"
                if msg not in unsupported:
                    unsupported.append(msg)
            if ast.items:
                out.append((ast, to_latex(ast)))
        return out

    # ------------------------------------------------------------------ đoạn văn
    def _parse_paragraph_blocks(self, p: Any, unsupported: list[str]) -> list[Block]:
        style_name = p.style.name if p.style else ""
        level: int | None = None
        if style_name.startswith("Heading"):
            try:
                parts = style_name.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    level = max(1, min(6, int(parts[1])))
                else:
                    level = 1
            except Exception:
                level = 1

        align = "left"
        p_pr = next((c for c in p._element if c.tag.endswith("pPr")), None)
        if p_pr is not None:
            jc = next((c for c in p_pr if c.tag.endswith("jc")), None)
            if jc is not None:
                val = next((v for k, v in jc.attrib.items() if k.endswith("val")), "").lower()
                if val == "center":
                    align = "center"
                elif val == "right":
                    align = "right"
                elif val in ("both", "distribute"):
                    align = "justify"

        pieces: list[Any] = []              # xen kẽ: list[Inline] (chữ) và MathBlock (công thức display)
        inlines: list[Inline] = []
        omml_blocks: list[MathBlock] = []   # công thức inline (m:oMath trực tiếp trong đoạn)

        def collect_runs(elem: Any) -> None:
            nonlocal inlines
            for child in elem:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "r" and not child.tag.startswith("{" + M_NS):
                    inlines.extend(self._extract_inlines_from_run(child, unsupported))
                elif tag in ("ins", "smartTag", "hyperlink", "fldSimple"):
                    if tag == "fldSimple" and (child.get(f"{{{child.nsmap.get('w', '')}}}instr") or "").strip().upper().startswith("EQ"):
                        self._eq_field_count += 1
                        unsupported.append("field: Word EQ equation field (not read)")
                    collect_runs(child)
                elif tag == "sdt":
                    sdt_content = next((c for c in child if c.tag.endswith("sdtContent")), None)
                    if sdt_content is not None:
                        collect_runs(sdt_content)
                elif tag == "oMathPara":
                    maths = self._omml_math(child, unsupported)
                    if maths:
                        if any(not isinstance(i, LineBreak) and not (isinstance(i, Text) and not i.text.strip()) for i in inlines):
                            pieces.append(inlines)
                        inlines = []
                        for ast, ltx in maths:
                            pieces.append(MathBlock(latex=ltx, ast=ast))
                elif tag == "oMath":
                    for ast, ltx in self._omml_math(child, unsupported):
                        inlines.append(MathInline(latex=ltx, ast=ast))
                        omml_blocks.append(MathBlock(latex=ltx, ast=ast))
                elif tag in ("drawing", "pict"):
                    unsupported.append(f"{tag}: embedded image or drawing shape")
                elif tag == "del":
                    # Tracked change deletion container - bỏ qua
                    pass

        collect_runs(p._element)
        if inlines or not pieces:
            pieces.append(inlines)

        # Nhận diện danh sách có bullet hoặc numbering
        is_list = False
        if p_pr is not None:
            num_pr = next((c for c in p_pr if c.tag.endswith("numPr")), None)
            if num_pr is not None:
                is_list = True
        if not is_list and style_name.lower().startswith("list"):
            is_list = True

        blocks: list[Block] = []
        first_text_piece = True
        for piece in pieces:
            if isinstance(piece, MathBlock):
                blocks.append(piece)
                continue
            piece_inlines: list[Inline] = []
            for inl in piece:      # Gộp các Text inline liền kề để tránh chèn khoảng trắng giả tạo (L6)
                if isinstance(inl, Text) and piece_inlines and isinstance(piece_inlines[-1], Text):
                    piece_inlines[-1] = Text(text=piece_inlines[-1].text + inl.text)
                else:
                    piece_inlines.append(inl)

            if is_list and first_text_piece and piece_inlines:
                first_txt = piece_inlines[0].text if isinstance(piece_inlines[0], Text) else ""
                if not first_txt.startswith(("•", "-", "*", "1.", "2.", "3.", "4.", "5.")):
                    piece_inlines.insert(0, Text(text="• "))

            if not piece_inlines and (len(pieces) > 1 or not p.text.strip()):
                continue      # đoạn trống (hoặc phần chữ rỗng kế bên công thức display)

            # Toàn bộ đoạn văn chỉ là 1 khối công thức toán riêng biệt
            if len(pieces) == 1 and len(omml_blocks) == 1 and not p.text.strip() and _only_one_math(piece_inlines):
                blocks.append(omml_blocks[0])
                continue

            if level is not None and first_text_piece:
                blocks.append(Heading(level=level, inlines=piece_inlines or [Text(text=p.text)]))
            else:
                blocks.append(Paragraph(inlines=piece_inlines or [Text(text=p.text)], align=align))
            first_text_piece = False
        return blocks

    def _parse_table(self, tbl: Any, unsupported: list[str]) -> Table:
        rows: list[TableRow] = []
        seen_tc: set[Any] = set()

        for r in tbl.rows:
            cells: list[TableCell] = []
            for c in r.cells:
                if c._tc in seen_tc:
                    continue
                seen_tc.add(c._tc)

                # Quét hình ảnh bên trong các ô bảng (đối tượng OLE/MathType được báo riêng khi đọc đoạn văn)
                for d in c._element.iter():
                    d_tag = d.tag.split("}")[-1] if "}" in d.tag else d.tag
                    if d_tag in ("drawing", "pict") and self._ole_progid(d) is None:
                        unsupported.append(f"{d_tag} in table cell: embedded image or drawing shape")

                try:
                    colspan = max(1, c._tc.right - c._tc.left)
                    rowspan = max(1, c._tc.bottom - c._tc.top)
                except Exception:
                    colspan = getattr(c._tc, "grid_span", 1) or 1
                    rowspan = 1

                cell_blocks: list[Block] = []
                for p in c.paragraphs:
                    cell_blocks.extend(self._parse_paragraph_blocks(p, unsupported))

                if not cell_blocks and c.text.strip():
                    cell_blocks.append(Paragraph(inlines=[Text(text=c.text.strip())]))

                cells.append(TableCell(blocks=cell_blocks, colspan=colspan, rowspan=rowspan))

            if cells:
                rows.append(TableRow(cells=cells))

        return Table(rows=rows, border_style=TableBorder.ALL)
