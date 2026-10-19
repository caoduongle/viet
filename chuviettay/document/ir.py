"""Document Intermediate Representation (IR) cho chữ viết tay.

Định nghĩa các khối (Block) và phần tử nội dòng (Inline) độc lập với định dạng tệp nguồn (TXT, Markdown, DOCX)
và độc lập với công cụ hiển thị (Layout Engine, Xournal++ XML).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TableBorder(str, Enum):
    """Kiểu viền bảng khi vẽ ra nét bút."""
    NONE = "none"              # Không vẽ đường kẻ
    OUTER = "outer"            # Chỉ vẽ 4 cạnh khung bao quanh
    ALL = "all"                # Vẽ đầy đủ lưới ô (cả viền ngoài và các đường chia trong)
    HORIZONTAL = "horizontal"  # Chỉ vẽ các đường kẻ ngang (kiểu bảng báo cáo/bài báo khoa học)


# ------------------------------------------------------------------ Gốc
@dataclass
class Node:
    """Nút gốc trừu tượng cho mọi thành phần trong cây Document IR."""
    stable_id: str | None = field(default=None, kw_only=True)


@dataclass
class Block(Node):
    """Nút cấp khối tham gia phân bố dòng và phân trang theo chiều dọc."""


@dataclass
class Inline(Node):
    """Nút nội dòng nằm trong Paragraph, Heading, hoặc TableCell."""


# ------------------------------------------------------------------ Inline Nodes
@dataclass
class Text(Inline):
    """Văn bản ký tự thông thường."""
    text: str
    token_occurrences: list[int] | None = field(default=None, kw_only=True)


@dataclass
class MathInline(Inline):
    """Công thức toán học nội dòng (kẹp giữa $...$)."""
    latex: str
    ast: Any = None
    occurrence: int | None = field(default=None, kw_only=True)


@dataclass
class Symbol(Inline):
    """Ký hiệu toán học hoặc glyph đặc biệt rời rạc (ví dụ: ≤, ∑, π, α)."""
    symbol: str
    occurrence: int | None = field(default=None, kw_only=True)

    @property
    def name(self) -> str:
        """Bí danh tương thích cho thuộc tính symbol."""
        return self.symbol


@dataclass
class LineBreak(Inline):
    """Ngắt dòng cứng thủ công bên trong đoạn văn hoặc ô bảng."""


# ------------------------------------------------------------------ Block Nodes
@dataclass
class Paragraph(Block):
    """Đoạn văn chứa danh sách các phần tử nội dòng."""
    inlines: list[Inline] = field(default_factory=list)
    align: str = "left"  # "left", "center", "right", "justify"


@dataclass
class Heading(Block):
    """Tiêu đề có phân cấp (cấp 1 đến 6)."""
    level: int = 1
    inlines: list[Inline] = field(default_factory=list)

    def __post_init__(self):
        if not (1 <= self.level <= 6):
            raise ValueError(f"Cấp tiêu đề (level) phải từ 1 đến 6, nhận được: {self.level}")


@dataclass
class ListBlock(Block):
    """Khối danh sách có thứ tự (1, 2, 3...) hoặc không có thứ tự (bullet)."""
    ordered: bool = False
    items: list[list[Block]] = field(default_factory=list)
    start: int = 1


@dataclass
class TableCell:
    """Ô trong hàng của bảng."""
    blocks: list[Block] = field(default_factory=list)
    colspan: int = 1
    rowspan: int = 1
    source_cell_id: int | None = None

    @classmethod
    def from_text(cls, text: str) -> TableCell:
        """Tạo nhanh ô chứa một đoạn văn bản thuần."""
        lines = text.split("\n")
        if len(lines) > 1:
            return cls(blocks=[Paragraph(inlines=[Text(text=line)]) for line in lines])
        return cls(blocks=[Paragraph(inlines=[Text(text=text)])])


@dataclass
class TableRow:
    """Hàng chứa danh sách các ô trong bảng."""
    cells: list[TableCell] = field(default_factory=list)


@dataclass
class Table(Block):
    """Bảng dữ liệu nhiều hàng, nhiều cột."""
    rows: list[TableRow] = field(default_factory=list)
    border_style: TableBorder = TableBorder.ALL
    col_alignments: list[str] = field(default_factory=list)  # "left", "center", "right"
    occurrence: int | None = field(default=None, kw_only=True)


@dataclass
class MathBlock(Block):
    """Khối công thức toán học đứng riêng một dòng (kẹp giữa $$...$$ hoặc \\[...\\])."""
    latex: str
    ast: Any = None
    occurrence: int | None = field(default=None, kw_only=True)


@dataclass
class PageBreak(Block):
    """Yêu cầu ngắt trang chủ động trong tài liệu."""


# ------------------------------------------------------------------ Document Root
@dataclass
class Document:
    """Gốc của tài liệu đã phân tích, chứa danh sách tuần tự các khối."""
    blocks: list[Block] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def align_document_seeds(base_doc: Document, edited_doc: Document) -> Document:
    """Đối chiếu hai tài liệu bằng thuật toán Longest Common Subsequence (LCS)
    sử dụng difflib.SequenceMatcher để bảo toàn occurrence của các phần tử cũ
    khi người dùng chèn thêm nội dung (kể cả từ/ký hiệu/công thức trùng lặp).
    """
    import copy
    import difflib
    import unicodedata

    def _normalize_text(text: str) -> str:
        for a, b in (("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'"), ("\u2013", "-"),
                     ("\u2014", "-"), ("\u00a0", " "), ("\t", "    ")):
            text = text.replace(a, b)
        text = "".join(c for c in text if unicodedata.category(c) != "Cf")
        return unicodedata.normalize("NFC", text.replace("\r", ""))

    result_doc = copy.deepcopy(edited_doc)

    def extract_doc_elements(doc: Document) -> tuple[list[dict], dict[tuple[str, str], int]]:
        elements = []
        counts: dict[tuple[str, str], int] = {}

        def _extract_blocks(blocks: list[Block], context_prefix: str = "text") -> None:
            for block in blocks:
                if isinstance(block, (Paragraph, Heading)):
                    for inline in block.inlines:
                        if isinstance(inline, Text):
                            norm = _normalize_text(inline.text or "")
                            for tok_idx, tok in enumerate(norm.split()):
                                occ = counts.get((context_prefix, tok), 0)
                                counts[(context_prefix, tok)] = occ + 1
                                elements.append({
                                    "content_type": context_prefix,
                                    "element_id": tok,
                                    "occ": occ,
                                    "node": inline,
                                    "tok_idx": tok_idx,
                                })
                        elif isinstance(inline, Symbol):
                            occ = counts.get(("sym", inline.symbol), 0)
                            counts[("sym", inline.symbol)] = occ + 1
                            elements.append({
                                "content_type": "sym",
                                "element_id": inline.symbol,
                                "occ": occ,
                                "node": inline,
                            })
                        elif isinstance(inline, MathInline):
                            occ = counts.get(("math_inline", inline.latex), 0)
                            counts[("math_inline", inline.latex)] = occ + 1
                            elements.append({
                                "content_type": "math_inline",
                                "element_id": inline.latex,
                                "occ": occ,
                                "node": inline,
                            })
                elif isinstance(block, ListBlock):
                    for item_blocks in block.items:
                        _extract_blocks(item_blocks, context_prefix=context_prefix)
                elif isinstance(block, MathBlock):
                    occ = counts.get(("math_block", block.latex), 0)
                    counts[("math_block", block.latex)] = occ + 1
                    elements.append({
                        "content_type": "math_block",
                        "element_id": block.latex,
                        "occ": occ,
                        "node": block,
                    })
                elif isinstance(block, Table):
                    num_cols = len(block.rows[0].cells) if block.rows else 0
                    first_row_texts = []
                    if block.rows:
                        for cell in block.rows[0].cells:
                            for b in cell.blocks:
                                if isinstance(b, Paragraph):
                                    for inl in b.inlines:
                                        if isinstance(inl, Text) and inl.text:
                                            first_row_texts.append(inl.text.strip())
                    first_row_sig = "-".join(first_row_texts)[:30]
                    tbl_sig = f"tbl:cols:{num_cols}|r0:{first_row_sig}"
                    occ = counts.get(("table", tbl_sig), 0)
                    counts[("table", tbl_sig)] = occ + 1
                    elements.append({
                        "content_type": "table",
                        "element_id": tbl_sig,
                        "occ": occ,
                        "node": block,
                    })
                    for row in block.rows:
                        for cell in row.cells:
                            _extract_blocks(cell.blocks, context_prefix="cell")

        _extract_blocks(doc.blocks, context_prefix="text")
        return elements, counts

    base_elems, base_counts = extract_doc_elements(base_doc)
    edited_elems, _ = extract_doc_elements(result_doc)

    base_keys = [(e["content_type"], e["element_id"]) for e in base_elems]
    edited_keys = [(e["content_type"], e["element_id"]) for e in edited_elems]

    matcher = difflib.SequenceMatcher(None, base_keys, edited_keys)
    assigned_occs = [None] * len(edited_elems)

    # 1. Gán occurrence cho các khối trùng khớp LCS
    for match in matcher.get_matching_blocks():
        for k in range(match.size):
            base_idx = match.a + k
            edited_idx = match.b + k
            assigned_occs[edited_idx] = base_elems[base_idx]["occ"]

    # 2. Gán occurrence mới cho các phần tử chèn thêm (unmatched)
    curr_max_counts = dict(base_counts)
    for idx, e in enumerate(edited_elems):
        if assigned_occs[idx] is None:
            key = (e["content_type"], e["element_id"])
            next_occ = curr_max_counts.get(key, 0)
            assigned_occs[idx] = next_occ
            curr_max_counts[key] = next_occ + 1

    # 3. Gắn assigned_occs trở lại các node trong result_doc
    text_token_maps: dict[int, list[tuple[int, int]]] = {}
    for idx, e in enumerate(edited_elems):
        occ = assigned_occs[idx]
        node = e["node"]
        if e["content_type"] in ("text", "cell") and isinstance(node, Text):
            nid = id(node)
            if nid not in text_token_maps:
                text_token_maps[nid] = []
            text_token_maps[nid].append((e["tok_idx"], occ))
        elif isinstance(node, (Symbol, MathInline, MathBlock, Table)):
            node.occurrence = occ

    for e in edited_elems:
        node = e["node"]
        if isinstance(node, Text) and id(node) in text_token_maps:
            pairs = sorted(text_token_maps[id(node)], key=lambda x: x[0])
            node.token_occurrences = [p[1] for p in pairs]

    return result_doc
