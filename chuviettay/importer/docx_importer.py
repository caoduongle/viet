"""Bộ nạp tài liệu Microsoft Word (.docx) sang Document IR hỗ trợ OMML và chẩn đoán."""
from __future__ import annotations

from typing import Any

from chuviettay.document.ir import (
    Block,
    Document,
    Heading,
    Inline,
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
from chuviettay.math.ast import (
    Fraction,
    MathNode,
    MathRow,
    Root,
    Subscript,
    SubSuperscript,
    Superscript,
    SymbolNode,
    TextNode,
)


def _parse_omml_element(elem: Any) -> tuple[list[MathNode], str]:
    """Phân tích một phần tử OMML đơn lẻ sang danh sách MathNode và chuỗi LaTeX tương ứng."""
    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

    if tag == "r":
        # Chạy toán học (Math Run)
        text = "".join(child.text or "" for child in elem if child.tag.endswith("t"))
        if not text and elem.text:
            text = elem.text
        if not text:
            return [], ""
        nodes = [TextNode(text)] if text.isalnum() else [SymbolNode(text)]
        return nodes, text

    elif tag == "f":
        # Phân số (Fraction)
        num_el = next((c for c in elem if c.tag.endswith("num")), None)
        den_el = next((c for c in elem if c.tag.endswith("den")), None)
        num_ast, num_ltx = _parse_omml_children(num_el) if num_el is not None else ([TextNode("1")], "1")
        den_ast, den_ltx = _parse_omml_children(den_el) if den_el is not None else ([TextNode("1")], "1")
        ast = Fraction(num=MathRow(num_ast), den=MathRow(den_ast))
        return [ast], f"\\frac{{{num_ltx}}}{{{den_ltx}}}"

    elif tag == "sSup":
        # Chỉ số trên (Superscript)
        base_el = next((c for c in elem if c.tag.endswith("e")), None)
        sup_el = next((c for c in elem if c.tag.endswith("sup")), None)
        base_ast, base_ltx = _parse_omml_children(base_el) if base_el is not None else ([TextNode("")], "")
        sup_ast, sup_ltx = _parse_omml_children(sup_el) if sup_el is not None else ([TextNode("")], "")
        base_node = base_ast[0] if len(base_ast) == 1 else MathRow(base_ast)
        ast = Superscript(base=base_node, exp=MathRow(sup_ast))
        return [ast], f"{{{base_ltx}}}^{{{sup_ltx}}}"

    elif tag == "sSub":
        # Chỉ số dưới (Subscript)
        base_el = next((c for c in elem if c.tag.endswith("e")), None)
        sub_el = next((c for c in elem if c.tag.endswith("sub")), None)
        base_ast, base_ltx = _parse_omml_children(base_el) if base_el is not None else ([TextNode("")], "")
        sub_ast, sub_ltx = _parse_omml_children(sub_el) if sub_el is not None else ([TextNode("")], "")
        base_node = base_ast[0] if len(base_ast) == 1 else MathRow(base_ast)
        ast = Subscript(base=base_node, sub=MathRow(sub_ast))
        return [ast], f"{{{base_ltx}}}_{{{sub_ltx}}}"

    elif tag == "sSubSup":
        # Cả chỉ số trên và dưới
        base_el = next((c for c in elem if c.tag.endswith("e")), None)
        sub_el = next((c for c in elem if c.tag.endswith("sub")), None)
        sup_el = next((c for c in elem if c.tag.endswith("sup")), None)
        base_ast, base_ltx = _parse_omml_children(base_el) if base_el is not None else ([TextNode("")], "")
        sub_ast, sub_ltx = _parse_omml_children(sub_el) if sub_el is not None else ([TextNode("")], "")
        sup_ast, sup_ltx = _parse_omml_children(sup_el) if sup_el is not None else ([TextNode("")], "")
        base_node = base_ast[0] if len(base_ast) == 1 else MathRow(base_ast)
        ast = SubSuperscript(base=base_node, sub=MathRow(sub_ast), exp=MathRow(sup_ast))
        return [ast], f"{{{base_ltx}}}_{{{sub_ltx}}}^{{{sup_ltx}}}"

    elif tag == "rad":
        # Căn thức (Radical / Root)
        rad_pr = next((c for c in elem if c.tag.endswith("radPr")), None)
        deg_hide = False
        if rad_pr is not None:
            deg_hide_el = next((c for c in rad_pr if c.tag.endswith("degHide")), None)
            if deg_hide_el is not None:
                val = next((v for k, v in deg_hide_el.attrib.items() if k.endswith("val")), "")
                if val in ("1", "true", "on"):
                    deg_hide = True

        deg_el = next((c for c in elem if c.tag.endswith("deg")), None)
        e_el = next((c for c in elem if c.tag.endswith("e")), None)

        deg_ast, deg_ltx = _parse_omml_children(deg_el) if (deg_el is not None and not deg_hide) else ([], "")
        e_ast, e_ltx = _parse_omml_children(e_el) if e_el is not None else ([TextNode("")], "")

        degree = MathRow(deg_ast) if deg_ast else None
        ast = Root(radicand=MathRow(e_ast), degree=degree)
        latex = f"\\sqrt[{deg_ltx}]{{{e_ltx}}}" if deg_ltx else f"\\sqrt{{{e_ltx}}}"
        return [ast], latex

    elif tag == "d":
        # Dấu đóng/mở ngoặc phân cách (Delimiter)
        beg_chr = "("
        end_chr = ")"
        d_pr = next((c for c in elem if c.tag.endswith("dPr")), None)
        if d_pr is not None:
            for c in d_pr:
                if c.tag.endswith("begChr"):
                    beg_chr = next((v for k, v in c.attrib.items() if k.endswith("val")), "(")
                elif c.tag.endswith("endChr"):
                    end_chr = next((v for k, v in c.attrib.items() if k.endswith("val")), ")")
        e_el = next((c for c in elem if c.tag.endswith("e")), None)
        e_ast, e_ltx = _parse_omml_children(e_el) if e_el is not None else ([], "")
        nodes = [SymbolNode(beg_chr)] + e_ast + [SymbolNode(end_chr)]
        return nodes, f"{beg_chr}{e_ltx}{end_chr}"

    elif tag == "t":
        txt = elem.text or ""
        nodes = [TextNode(txt)] if txt.isalnum() else [SymbolNode(txt)]
        return nodes, txt

    # Các phần tử lồng con
    return _parse_omml_children(elem)


UNSUPPORTED_OMML_TAGS = {
    "m": "matrix",
    "nary": "n-ary operator (integral/summation)",
    "limLow": "lower limit",
    "limUpp": "upper limit",
    "func": "function apply",
    "bar": "bar over/under",
    "acc": "accent",
    "groupChr": "group character",
    "eqArr": "equation array",
}


def _parse_omml_children(elem: Any) -> tuple[list[MathNode], str]:
    """Phân tích tập hợp phần tử con của OMML."""
    if elem is None:
        return [], ""
    all_ast: list[MathNode] = []
    all_ltx: list[str] = []
    for child in elem:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("r", "f", "sSup", "sSub", "sSubSup", "rad", "d", "t"):
            nodes, ltx = _parse_omml_element(child)
            all_ast.extend(nodes)
            if ltx:
                all_ltx.append(ltx)
        elif tag in (
            "num", "den", "e", "sup", "sub", "deg", "oMath", "oMathPara",
            "m", "nary", "limLow", "limUpp", "func", "bar", "acc", "groupChr", "eqArr", "mr", "fName",
        ):
            nodes, ltx = _parse_omml_children(child)
            all_ast.extend(nodes)
            if ltx:
                all_ltx.append(ltx)

    return all_ast, " ".join(all_ltx)


class DocxImporter(BaseImporter):
    """Bộ nạp tài liệu .docx bảo toàn thứ tự đoạn văn/bảng và chuyển đổi công thức OMML."""

    def __init__(self):
        require_dependency("docx", "tài liệu Word (.docx)", "docs")

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
                block = self._parse_paragraph(item, unsupported)
                if block is not None:
                    blocks.append(block)
            elif isinstance(item, docx.table.Table):
                table_block = self._parse_table(item, unsupported)
                blocks.append(table_block)

        return ImportResult(document=Document(blocks=blocks), warnings=warnings, unsupported=unsupported)

    def _parse_paragraph(self, p: Any, unsupported: list[str]) -> Block | None:
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

        inlines: list[Inline] = []
        omml_blocks: list[MathBlock] = []

        # Quét các thẻ con XML trực tiếp bên trong <w:p>
        for child in p._element:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag == "r":
                # Kiểm tra nét vẽ / hình ảnh không được hỗ trợ trong run
                for r_child in child:
                    r_tag = r_child.tag.split("}")[-1] if "}" in r_child.tag else r_child.tag
                    if r_tag in ("drawing", "pict"):
                        unsupported.append(f"{r_tag}: embedded image or drawing shape")

                text_elem = next((c for c in child if c.tag.endswith("t")), None)
                if text_elem is not None and text_elem.text:
                    inlines.append(Text(text=text_elem.text))

            elif tag in ("oMath", "oMathPara"):
                for sub_el in child.iter():
                    sub_tag = sub_el.tag.split("}")[-1] if "}" in sub_el.tag else sub_el.tag
                    if sub_tag in UNSUPPORTED_OMML_TAGS:
                        msg = f"m:{sub_tag}: unsupported OMML math element ({UNSUPPORTED_OMML_TAGS[sub_tag]})"
                        if msg not in unsupported:
                            unsupported.append(msg)

                ast_nodes, ltx = _parse_omml_children(child)
                math_ast = MathRow(ast_nodes) if len(ast_nodes) > 1 else (ast_nodes[0] if ast_nodes else MathRow([]))
                inlines.append(MathInline(latex=ltx, ast=math_ast))
                omml_blocks.append(MathBlock(latex=ltx, ast=math_ast))

            elif tag == "hyperlink":
                for r_child in child:
                    r_tag = r_child.tag.split("}")[-1] if "}" in r_child.tag else r_child.tag
                    if r_tag == "r":
                        text_elem = next((c for c in r_child if c.tag.endswith("t")), None)
                        if text_elem is not None and text_elem.text:
                            inlines.append(Text(text=text_elem.text))

            elif tag in ("drawing", "pict"):
                unsupported.append(f"{tag}: embedded image or drawing shape")

        # Nếu đoạn văn trống hoàn toàn và không có inlines
        if not inlines and not p.text.strip():
            return None

        # Nếu toàn bộ đoạn văn chỉ là 1 khối công thức toán riêng biệt
        if len(omml_blocks) == 1 and not p.text.strip():
            return omml_blocks[0]

        if level is not None:
            return Heading(level=level, inlines=inlines or [Text(text=p.text)])
        else:
            return Paragraph(inlines=inlines or [Text(text=p.text)])

    def _parse_table(self, tbl: Any, unsupported: list[str]) -> Table:
        rows: list[TableRow] = []
        seen_tc: set[Any] = set()

        for r in tbl.rows:
            cells: list[TableCell] = []
            for c in r.cells:
                if c._tc in seen_tc:
                    continue
                seen_tc.add(c._tc)

                # Quét hình ảnh bên trong các ô bảng
                for d in c._element.iter():
                    d_tag = d.tag.split("}")[-1] if "}" in d.tag else d.tag
                    if d_tag in ("drawing", "pict"):
                        unsupported.append(f"{d_tag} in table cell: embedded image or drawing shape")

                try:
                    colspan = max(1, c._tc.right - c._tc.left)
                    rowspan = max(1, c._tc.bottom - c._tc.top)
                except Exception:
                    colspan = getattr(c._tc, "grid_span", 1) or 1
                    rowspan = 1

                cell_blocks: list[Block] = []
                for p in c.paragraphs:
                    blk = self._parse_paragraph(p, unsupported)
                    if blk is not None:
                        cell_blocks.append(blk)

                if not cell_blocks and c.text.strip():
                    cell_blocks.append(Paragraph(inlines=[Text(text=c.text.strip())]))

                cells.append(TableCell(blocks=cell_blocks, colspan=colspan, rowspan=rowspan))

            if cells:
                rows.append(TableRow(cells=cells))

        return Table(rows=rows, border_style=TableBorder.ALL)
