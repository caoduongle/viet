"""Động cơ đo đạc kích thước bảng, gói chữ trong ô và sinh nét viền bảng."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chuviettay.document.ir import MathBlock, MathInline, Paragraph, Symbol, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.metrics import PositionedStroke


@dataclass
class LaidOutCell:
    """Toạ độ và kích thước của một ô bảng đã được định vị."""
    x: float
    y: float
    width: float
    height: float
    text_lines: list[str]
    cell: TableCell | None = None
    col: int = 0
    row: int = 0
    colspan: int = 1
    rowspan: int = 1
    rendered_lines: list[Any] = field(default_factory=list)


@dataclass
class TableLayoutData:
    """Dữ liệu hình học sau khi hoàn thành tính toán bố cục cho toàn bộ bảng."""
    x: float
    y: float
    width: float
    height: float
    col_widths: list[float]
    row_heights: list[float]
    cells: list[list[LaidOutCell]]


class TableLayoutEngine:
    """Tính toán kích thước cột/hàng, ngắt dòng nội dung ô và sinh nét vẽ viền bảng."""

    def __init__(self, available_width: float, line_height: float, cell_padding: float = 6.0):
        self.available_width = max(50.0, available_width)
        self.line_height = max(10.0, line_height)
        self.cell_padding = cell_padding
        self.char_w = self.line_height * 0.45  # ước lượng tương đối độ rộng ký tự

    def pad_jagged_rows(self, table: Table) -> list[TableRow]:
        """Tự động đệm thêm ô rỗng cho các hàng ngắn hơn hàng dài nhất."""
        if not table.rows:
            return []
        max_cols = max((sum(max(1, getattr(c, "colspan", 1)) for c in r.cells) for r in table.rows), default=1)
        padded_rows = []
        for r in table.rows:
            curr_cells = list(r.cells)
            curr_cols = sum(max(1, getattr(c, "colspan", 1)) for c in curr_cells)
            while curr_cols < max_cols:
                curr_cells.append(TableCell(blocks=[]))
                curr_cols += 1
            padded_rows.append(TableRow(cells=curr_cells))
        return padded_rows

    def _extract_cell_text(self, cell: TableCell) -> str:
        """Trích xuất chuỗi văn bản đại diện trong ô."""
        parts = []
        for block in cell.blocks:
            if isinstance(block, Paragraph):
                for inline in block.inlines:
                    if isinstance(inline, Text):
                        parts.append(inline.text)
                    elif isinstance(inline, MathInline):
                        parts.append(inline.latex or "math")
                    elif isinstance(inline, Symbol):
                        parts.append(inline.symbol)
            elif isinstance(block, MathBlock):
                parts.append(block.latex or "math")
        return " ".join(parts).strip()

    def compute_column_widths(self, table: Table) -> list[float]:
        """Tính toán phân bổ bề rộng cho từng cột xét cả colspan."""
        padded_rows = self.pad_jagged_rows(table)
        if not padded_rows:
            return []
        num_cols = max((sum(max(1, getattr(c, "colspan", 1)) for c in r.cells) for r in padded_rows), default=1)

        natural_widths = [0.0] * num_cols
        min_widths = [0.0] * num_cols

        for row in padded_rows:
            c_idx = 0
            for cell in row.cells:
                cs = max(1, getattr(cell, "colspan", 1))
                txt = self._extract_cell_text(cell)
                words = txt.split()
                longest_w = max((len(w) for w in words), default=0) * self.char_w + 2 * self.cell_padding
                full_w = len(txt) * self.char_w + 2 * self.cell_padding

                # Phân bổ đều cho các cột spanned
                per_col_min = max(30.0, longest_w / cs)
                per_col_nat = max(40.0, full_w / cs)
                for k in range(cs):
                    if c_idx + k < num_cols:
                        min_widths[c_idx + k] = max(min_widths[c_idx + k], per_col_min)
                        natural_widths[c_idx + k] = max(natural_widths[c_idx + k], per_col_nat)
                c_idx += cs

        total_natural = sum(natural_widths)
        if total_natural <= self.available_width:
            scale = self.available_width / total_natural if total_natural > 0 else 1.0
            return [round(w * scale, 2) for w in natural_widths]

        rem_w = max(0.0, self.available_width - sum(min_widths))
        diff_sum = sum(max(0.0, natural_widths[i] - min_widths[i]) for i in range(num_cols))
        final_widths = []
        for i in range(num_cols):
            bonus = (rem_w * (natural_widths[i] - min_widths[i]) / diff_sum) if diff_sum > 0 else (rem_w / num_cols)
            final_widths.append(round(min_widths[i] + bonus, 2))

        tot = sum(final_widths)
        if tot > self.available_width:
            factor = self.available_width / tot
            final_widths = [round(w * factor, 2) for w in final_widths]

        return final_widths

    def wrap_cell_text(self, text: str, width: float) -> list[str]:
        """Ngắt dòng văn bản thô theo bề rộng cột trừ đi khoảng đệm."""
        usable_w = max(10.0, width - 2 * self.cell_padding)
        words = text.split()
        if not words:
            return []
        lines: list[str] = []
        cur_line = []
        cur_w = 0.0

        for w in words:
            w_len = len(w) * self.char_w
            space_len = self.char_w * 0.8
            if cur_line and cur_w + space_len + w_len > usable_w:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_w = w_len
            else:
                cur_line.append(w)
                cur_w += (space_len if len(cur_line) > 1 else 0.0) + w_len

        if cur_line:
            lines.append(" ".join(cur_line))
        return lines

    def layout_table(self, table: Table, x0: float, y0: float) -> TableLayoutData:
        """Đo đạc toàn bộ bảng và bố trí vị trí các ô xét cả colspan và rowspan."""
        padded_rows = self.pad_jagged_rows(table)
        if not padded_rows:
            return TableLayoutData(x=x0, y=y0, width=0.0, height=0.0, col_widths=[], row_heights=[], cells=[])

        col_widths = self.compute_column_widths(table)
        num_cols = len(col_widths)
        total_w = sum(col_widths)

        # 1. Tính toán chiều cao ước tính sơ bộ của các hàng
        row_heights: list[float] = []
        row_cell_lines_all: list[list[list[str]]] = []

        for row in padded_rows:
            row_cell_lines = []
            c_idx = 0
            for cell in row.cells:
                cs = max(1, getattr(cell, "colspan", 1))
                spanned_w = sum(col_widths[c_idx : c_idx + cs]) if c_idx + cs <= num_cols else col_widths[c_idx]
                txt = self._extract_cell_text(cell)
                lines = self.wrap_cell_text(txt, spanned_w)
                row_cell_lines.append(lines)
                c_idx += cs

            max_lines = max((len(ls) for ls in row_cell_lines), default=1)
            row_h = max(self.line_height + 2 * self.cell_padding, max_lines * self.line_height + 2 * self.cell_padding)
            row_heights.append(row_h)
            row_cell_lines_all.append(row_cell_lines)

        # 2. Định vị toạ độ cho từng ô trong bảng
        laid_out_cells: list[list[LaidOutCell]] = []
        cur_y = y0

        for r_idx, row in enumerate(padded_rows):
            row_cells: list[LaidOutCell] = []
            c_idx = 0
            for cell_idx, cell in enumerate(row.cells):
                cs = max(1, getattr(cell, "colspan", 1))
                rs = max(1, getattr(cell, "rowspan", 1))
                cell_x = x0 + sum(col_widths[:c_idx])
                cell_y = cur_y
                cell_w = sum(col_widths[c_idx : c_idx + cs])
                cell_h = sum(row_heights[r_idx : r_idx + rs])

                c_lines = row_cell_lines_all[r_idx][cell_idx] if cell_idx < len(row_cell_lines_all[r_idx]) else []
                row_cells.append(
                    LaidOutCell(
                        x=cell_x,
                        y=cell_y,
                        width=cell_w,
                        height=cell_h,
                        text_lines=c_lines,
                        cell=cell,
                        col=c_idx,
                        row=r_idx,
                        colspan=cs,
                        rowspan=rs,
                    )
                )
                c_idx += cs

            laid_out_cells.append(row_cells)
            cur_y += row_heights[r_idx]

        total_h = cur_y - y0
        return TableLayoutData(
            x=x0,
            y=y0,
            width=total_w,
            height=total_h,
            col_widths=col_widths,
            row_heights=row_heights,
            cells=laid_out_cells,
        )

    def generate_border_strokes(self, data: TableLayoutData, style: TableBorder) -> list[PositionedStroke]:
        """Tạo danh sách các đường nét vẽ thẳng (2 toạ độ điểm) làm khung viền bảng, ẩn nét trong ô gộp."""
        if style == TableBorder.NONE or data.width <= 0 or data.height <= 0:
            return []

        x1 = data.x
        x2 = data.x + data.width
        y1 = data.y
        y2 = data.y + data.height

        strokes: list[PositionedStroke] = []

        # 1. Khung bao quanh ngoài (OUTER, ALL, HORIZONTAL)
        if style in (TableBorder.OUTER, TableBorder.ALL, TableBorder.HORIZONTAL):
            strokes.append(PositionedStroke(points=[(x1, y1), (x2, y1)]))
            strokes.append(PositionedStroke(points=[(x1, y2), (x2, y2)]))

        if style in (TableBorder.OUTER, TableBorder.ALL):
            strokes.append(PositionedStroke(points=[(x1, y1), (x1, y2)]))
            strokes.append(PositionedStroke(points=[(x2, y1), (x2, y2)]))

        # Bản đồ các ô và vùng gộp để ẩn nét kẻ bên trong
        num_rows = len(data.row_heights)
        num_cols = len(data.col_widths)

        col_xs = [x1]
        for w in data.col_widths:
            col_xs.append(col_xs[-1] + w)

        row_ys = [y1]
        for h in data.row_heights:
            row_ys.append(row_ys[-1] + h)

        # 2. Đường chia ngang giữa các hàng (ALL, HORIZONTAL) theo từng phân đoạn cột
        if style in (TableBorder.ALL, TableBorder.HORIZONTAL):
            for r_idx in range(num_rows - 1):
                div_y = row_ys[r_idx + 1]
                cur_seg_start: float | None = None
                for c_idx in range(num_cols):
                    # Kiểm tra xem ô tại (r_idx, c_idx) có đang gộp vượt qua hàng này không (rowspan)
                    is_spanned = False
                    for r_cells in data.cells:
                        for cell in r_cells:
                            if cell.col <= c_idx < cell.col + cell.colspan:
                                if cell.row <= r_idx < cell.row + cell.rowspan - 1:
                                    is_spanned = True
                                    break
                        if is_spanned:
                            break

                    if not is_spanned:
                        if cur_seg_start is None:
                            cur_seg_start = col_xs[c_idx]
                    else:
                        if cur_seg_start is not None:
                            strokes.append(PositionedStroke(points=[(cur_seg_start, div_y), (col_xs[c_idx], div_y)]))
                            cur_seg_start = None

                if cur_seg_start is not None:
                    strokes.append(PositionedStroke(points=[(cur_seg_start, div_y), (col_xs[num_cols], div_y)]))

        # 3. Đường chia dọc giữa các cột (chỉ có trong ALL) theo từng phân đoạn hàng
        if style == TableBorder.ALL:
            for c_idx in range(num_cols - 1):
                div_x = col_xs[c_idx + 1]
                cur_seg_start = None
                for r_idx in range(num_rows):
                    # Kiểm tra xem ô tại (r_idx, c_idx) có đang gộp vượt qua cột này không (colspan)
                    is_spanned = False
                    for r_cells in data.cells:
                        for cell in r_cells:
                            if cell.row <= r_idx < cell.row + cell.rowspan:
                                if cell.col <= c_idx < cell.col + cell.colspan - 1:
                                    is_spanned = True
                                    break
                        if is_spanned:
                            break

                    if not is_spanned:
                        if cur_seg_start is None:
                            cur_seg_start = row_ys[r_idx]
                    else:
                        if cur_seg_start is not None:
                            strokes.append(PositionedStroke(points=[(div_x, cur_seg_start), (div_x, row_ys[r_idx])]))
                            cur_seg_start = None

                if cur_seg_start is not None:
                    strokes.append(PositionedStroke(points=[(div_x, cur_seg_start), (div_x, row_ys[num_rows])]))

        return strokes
