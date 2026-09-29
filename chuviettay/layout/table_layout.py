"""Động cơ đo đạc kích thước bảng, gói chữ trong ô và sinh nét viền bảng."""
from __future__ import annotations

from dataclasses import dataclass

from chuviettay.document.ir import Paragraph, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.metrics import PositionedStroke


@dataclass
class LaidOutCell:
    """Toạ độ và kích thước của một ô bảng đã được định vị."""
    x: float
    y: float
    width: float
    height: float
    text_lines: list[str]


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
        max_cols = max(len(r.cells) for r in table.rows)
        padded_rows = []
        for r in table.rows:
            curr_cells = list(r.cells)
            while len(curr_cells) < max_cols:
                curr_cells.append(TableCell(blocks=[]))
            padded_rows.append(TableRow(cells=curr_cells))
        return padded_rows

    def _extract_cell_text(self, cell: TableCell) -> str:
        """Trích xuất chuỗi văn bản thuần trong ô."""
        parts = []
        for block in cell.blocks:
            if isinstance(block, Paragraph):
                for inline in block.inlines:
                    if isinstance(inline, Text):
                        parts.append(inline.text)
        return " ".join(parts).strip()

    def compute_column_widths(self, table: Table) -> list[float]:
        """Tính toán phân bổ bề rộng cho từng cột."""
        padded_rows = self.pad_jagged_rows(table)
        if not padded_rows:
            return []
        num_cols = len(padded_rows[0].cells)

        natural_widths = [0.0] * num_cols
        min_widths = [0.0] * num_cols

        for row in padded_rows:
            for c_idx, cell in enumerate(row.cells):
                txt = self._extract_cell_text(cell)
                words = txt.split()
                longest_w = max((len(w) for w in words), default=0) * self.char_w + 2 * self.cell_padding
                full_w = len(txt) * self.char_w + 2 * self.cell_padding
                min_widths[c_idx] = max(min_widths[c_idx], max(30.0, longest_w))
                natural_widths[c_idx] = max(natural_widths[c_idx], max(40.0, full_w))

        total_natural = sum(natural_widths)
        if total_natural <= self.available_width:
            # Nếu vừa vặn, chia theo tỉ lệ tự nhiên lấp đầy bề rộng khả dụng
            scale = self.available_width / total_natural if total_natural > 0 else 1.0
            return [round(w * scale, 2) for w in natural_widths]

        # Nếu vượt quá, phân phối có cận dưới min_widths
        rem_w = max(0.0, self.available_width - sum(min_widths))
        diff_sum = sum(max(0.0, natural_widths[i] - min_widths[i]) for i in range(num_cols))
        final_widths = []
        for i in range(num_cols):
            bonus = (rem_w * (natural_widths[i] - min_widths[i]) / diff_sum) if diff_sum > 0 else (rem_w / num_cols)
            final_widths.append(round(min_widths[i] + bonus, 2))

        # Nếu tổng vượt quá do min_widths quá lớn, co lại đồng đều
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
        """Đo đạc toàn bộ bảng và bố trí vị trí các ô."""
        padded_rows = self.pad_jagged_rows(table)
        if not padded_rows:
            return TableLayoutData(x=x0, y=y0, width=0.0, height=0.0, col_widths=[], row_heights=[], cells=[])

        col_widths = self.compute_column_widths(table)
        num_cols = len(col_widths)
        total_w = sum(col_widths)

        laid_out_cells: list[list[LaidOutCell]] = []
        row_heights: list[float] = []

        cur_y = y0
        for row in padded_rows:
            # Gói text từng ô trong hàng
            row_cell_lines = []
            for c_idx, cell in enumerate(row.cells):
                txt = self._extract_cell_text(cell)
                lines = self.wrap_cell_text(txt, col_widths[c_idx])
                row_cell_lines.append(lines)

            # Chiều cao hàng = số dòng lớn nhất * line_height + 2 * padding
            max_lines = max((len(ls) for ls in row_cell_lines), default=1)
            row_h = max(self.line_height + 2 * self.cell_padding, max_lines * self.line_height + 2 * self.cell_padding)
            row_heights.append(row_h)

            row_cells: list[LaidOutCell] = []
            cur_x = x0
            for c_idx in range(num_cols):
                w = col_widths[c_idx]
                row_cells.append(LaidOutCell(x=cur_x, y=cur_y, width=w, height=row_h, text_lines=row_cell_lines[c_idx]))
                cur_x += w

            laid_out_cells.append(row_cells)
            cur_y += row_h

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
        """Tạo danh sách các đường nét vẽ thẳng (2 toạ độ điểm) làm khung viền bảng."""
        if style == TableBorder.NONE or data.width <= 0 or data.height <= 0:
            return []

        x1 = data.x
        x2 = data.x + data.width
        y1 = data.y
        y2 = data.y + data.height

        strokes: list[PositionedStroke] = []

        # 1. Đường bao trên và dưới (có trong OUTER, ALL, HORIZONTAL)
        if style in (TableBorder.OUTER, TableBorder.ALL, TableBorder.HORIZONTAL):
            strokes.append(PositionedStroke(points=[(x1, y1), (x2, y1)]))
            strokes.append(PositionedStroke(points=[(x1, y2), (x2, y2)]))

        # 2. Đường bao trái và phải (có trong OUTER, ALL)
        if style in (TableBorder.OUTER, TableBorder.ALL):
            strokes.append(PositionedStroke(points=[(x1, y1), (x1, y2)]))
            strokes.append(PositionedStroke(points=[(x2, y1), (x2, y2)]))

        # 3. Đường chia ngang giữa các hàng (có trong ALL, HORIZONTAL)
        if style in (TableBorder.ALL, TableBorder.HORIZONTAL):
            accum_y = y1
            for h in data.row_heights[:-1]:  # bỏ hàng cuối vì đã có đường đáy
                accum_y += h
                strokes.append(PositionedStroke(points=[(x1, accum_y), (x2, accum_y)]))

        # 4. Đường chia dọc giữa các cột (chỉ có trong ALL)
        if style == TableBorder.ALL:
            accum_x = x1
            for w in data.col_widths[:-1]:  # bỏ cột cuối vì đã có đường mép phải
                accum_x += w
                strokes.append(PositionedStroke(points=[(accum_x, y1), (accum_x, y2)]))

        return strokes
