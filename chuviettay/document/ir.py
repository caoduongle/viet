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


@dataclass
class MathInline(Inline):
    """Công thức toán học nội dòng (kẹp giữa $...$)."""
    latex: str
    ast: Any = None


@dataclass
class Symbol(Inline):
    """Ký hiệu toán học hoặc glyph đặc biệt rời rạc (ví dụ: ≤, ∑, π, α)."""
    symbol: str

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
    level: int
    inlines: list[Inline] = field(default_factory=list)

    def __post_init__(self):
        if not (1 <= self.level <= 6):
            raise ValueError(f"Cấp tiêu đề (level) phải từ 1 đến 6, nhận được: {self.level}")


@dataclass
class ListBlock(Block):
    """Khối danh sách có thứ tự (1, 2, 3...) hoặc không có thứ tự (bullet)."""
    ordered: bool
    items: list[list[Block]] = field(default_factory=list)
    start: int = 1


@dataclass
class TableCell:
    """Ô trong hàng của bảng."""
    blocks: list[Block] = field(default_factory=list)
    colspan: int = 1
    rowspan: int = 1

    @classmethod
    def from_text(cls, text: str) -> TableCell:
        """Tạo nhanh ô chứa một đoạn văn bản thuần."""
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


@dataclass
class MathBlock(Block):
    """Khối công thức toán học đứng riêng một dòng (kẹp giữa $$...$$ hoặc \\[...\\])."""
    latex: str
    ast: Any = None


@dataclass
class PageBreak(Block):
    """Yêu cầu ngắt trang chủ động trong tài liệu."""


# ------------------------------------------------------------------ Document Root
@dataclass
class Document:
    """Gốc của tài liệu đã phân tích, chứa danh sách tuần tự các khối."""
    blocks: list[Block] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
