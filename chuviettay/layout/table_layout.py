"""Động cơ đo đạc kích thước bảng, gói chữ trong ô và sinh nét viền bảng."""
from __future__ import annotations

import math
import random
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

    def slice_page(self, start_row_idx: int, max_height: float, new_y: float) -> tuple[TableLayoutData, int]:
        """Tạo một lát cắt bảng (sub-table) cho một trang từ hàng start_row_idx vừa trong max_height."""
        num_rows = len(self.row_heights)
        if start_row_idx >= num_rows:
            return (
                TableLayoutData(x=self.x, y=new_y, width=self.width, height=0.0, col_widths=self.col_widths, row_heights=[], cells=[]),
                num_rows,
            )

        # Ghi nhận các liên kết hàng do rowspan tạo ra để giữ tính gắn kết trang (cohesion)
        row_group_end: list[int] = list(range(num_rows))
        for r_cells in self.cells:
            for c in r_cells:
                if c.rowspan > 1:
                    end_r = min(num_rows - 1, c.row + c.rowspan - 1)
                    for r_k in range(c.row, end_r + 1):
                        row_group_end[r_k] = max(row_group_end[r_k], end_r)

        curr_h = 0.0
        end_idx = start_row_idx

        while end_idx < num_rows:
            target_end = row_group_end[end_idx]
            needed_h = sum(self.row_heights[end_idx : target_end + 1])

            # Nếu thêm cả nhóm mà vượt quá max_height và trang đã có ít nhất 1 hàng: dừng lại để sang trang mới
            if curr_h > 0 and curr_h + needed_h > max_height:
                break

            # Nếu trang chưa có hàng nào (start_row_idx == end_idx) mà needed_h > max_height:
            # Nhận ít nhất 1 hàng để bảo đảm tiến trình không bị lặp vô hạn
            if curr_h == 0 and needed_h > max_height:
                end_idx += 1
                curr_h += self.row_heights[start_row_idx]
                break

            curr_h += needed_h
            end_idx = target_end + 1

        if end_idx == start_row_idx:
            end_idx = start_row_idx + 1
            curr_h = self.row_heights[start_row_idx]

        sliced_row_heights = self.row_heights[start_row_idx:end_idx]
        sliced_cells: list[list[LaidOutCell]] = []

        cur_row_y = new_y
        for r_offset, r in enumerate(range(start_row_idx, end_idx)):
            row_cells = []
            for cell in self.cells[r]:
                eff_rs = min(cell.rowspan, end_idx - r)
                cell_h = sum(self.row_heights[r : r + eff_rs])
                row_cells.append(
                    LaidOutCell(
                        x=cell.x,
                        y=cur_row_y,
                        width=cell.width,
                        height=cell_h,
                        text_lines=cell.text_lines,
                        cell=cell.cell,
                        col=cell.col,
                        row=r_offset,
                        colspan=cell.colspan,
                        rowspan=eff_rs,
                        rendered_lines=cell.rendered_lines,
                    )
                )
            sliced_cells.append(row_cells)
            cur_row_y += self.row_heights[r]

        return (
            TableLayoutData(
                x=self.x,
                y=new_y,
                width=self.width,
                height=curr_h,
                col_widths=self.col_widths,
                row_heights=sliced_row_heights,
                cells=sliced_cells,
            ),
            end_idx,
        )


class TableLayoutEngine:
    """Tính toán kích thước cột/hàng, ngắt dòng nội dung ô và sinh nét vẽ viền bảng."""

    def __init__(
        self,
        available_width: float,
        line_height: float,
        cell_padding: float = 6.0,
        calc_text_bounds: Any = None,
    ):
        self.available_width = max(50.0, available_width)
        self.line_height = max(10.0, line_height)
        self.cell_padding = cell_padding
        self.char_w = self.line_height * 0.45  # ước lượng tương đối độ rộng ký tự
        self.calc_text_bounds = calc_text_bounds

    def _resolve_occupancy(self, table: Table) -> tuple[list[tuple[int, int, int, int, TableCell]], int]:
        """Phân giải ma trận chiếm chỗ 2D cho toàn bộ bảng. Trả về (placements, num_cols)."""
        if not table.rows:
            return [], 0

        occupied: set[tuple[int, int]] = set()
        placements: list[tuple[int, int, int, int, TableCell]] = []
        max_c = 0

        for r_idx, row in enumerate(table.rows):
            c_cursor = 0
            for cell in row.cells:
                while (r_idx, c_cursor) in occupied:
                    c_cursor += 1
                cs = max(1, getattr(cell, "colspan", 1))
                rs = max(1, getattr(cell, "rowspan", 1))
                placements.append((r_idx, c_cursor, rs, cs, cell))
                for dr in range(rs):
                    for dc in range(cs):
                        occupied.add((r_idx + dr, c_cursor + dc))
                c_cursor += cs
                max_c = max(max_c, c_cursor)

        num_cols = max(max_c, 1)
        return placements, num_cols

    def pad_jagged_rows(self, table: Table) -> list[TableRow]:
        """Tự động đệm thêm ô rỗng cho các hàng ngắn hơn hàng dài nhất, tính đến cả rowspan."""
        if not table.rows:
            return []
        placements, num_cols = self._resolve_occupancy(table)
        occupied_by_row: list[set[int]] = [set() for _ in range(len(table.rows))]
        for r, c, rs, cs, _cell in placements:
            for dr in range(rs):
                if r + dr < len(table.rows):
                    for dc in range(cs):
                        occupied_by_row[r + dr].add(c + dc)

        padded_rows = []
        for r_idx, row in enumerate(table.rows):
            curr_cells = list(row.cells)
            vacant_count = sum(1 for c in range(num_cols) if c not in occupied_by_row[r_idx])
            for _ in range(vacant_count):
                curr_cells.append(TableCell(blocks=[]))
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
        """Tính toán phân bổ bề rộng cho từng cột xét cả colspan và vị trí thực theo occupancy grid."""
        if not table.rows:
            return []
        placements, num_cols = self._resolve_occupancy(table)

        natural_widths = [0.0] * num_cols
        min_widths = [0.0] * num_cols

        for r, c, rs, cs, cell in placements:
            eff_cs = min(cs, num_cols - c)
            if eff_cs <= 0:
                continue
            txt = self._extract_cell_text(cell)
            words = txt.split()
            if self.calc_text_bounds is not None and words:
                longest_w = max((self.calc_text_bounds(w) for w in words), default=0.0) + 2 * self.cell_padding
                full_w = sum(self.calc_text_bounds(w) for w in words) + max(0, len(words) - 1) * (self.char_w * 0.8) + 2 * self.cell_padding
            else:
                longest_w = max((len(w) for w in words), default=0) * self.char_w + 2 * self.cell_padding
                full_w = len(txt) * self.char_w + 2 * self.cell_padding

            per_col_min = max(30.0, longest_w / eff_cs)
            per_col_nat = max(40.0, full_w / eff_cs)
            for k in range(eff_cs):
                col_idx = c + k
                min_widths[col_idx] = max(min_widths[col_idx], per_col_min)
                natural_widths[col_idx] = max(natural_widths[col_idx], per_col_nat)

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

    def layout_table(
        self,
        table: Table,
        x0: float,
        y0: float,
        cell_inlines_formatter: Any = None,
    ) -> TableLayoutData:
        """Đo đạc toàn bộ bảng và bố trí vị trí các ô xét cả colspan và rowspan dựa trên ma trận chiếm chỗ."""
        if not table.rows:
            return TableLayoutData(x=x0, y=y0, width=0.0, height=0.0, col_widths=[], row_heights=[], cells=[])

        placements, num_cols = self._resolve_occupancy(table)
        col_widths = self.compute_column_widths(table)
        total_w = sum(col_widths)
        num_rows = len(table.rows)

        # 1. Tính toán nội dung ô và chiều cao từng hàng
        row_heights = [max(10.0, self.line_height + 2 * self.cell_padding)] * num_rows
        prepared_cells: list[dict[str, Any]] = []

        for r, c, rs, cs, cell in placements:
            eff_cs = min(cs, num_cols - c)
            spanned_w = sum(col_widths[c : c + eff_cs]) if eff_cs > 0 else col_widths[min(c, num_cols - 1)]
            usable_w = max(10.0, spanned_w - 2 * self.cell_padding)

            rendered_lines = []
            text_lines = []
            if cell_inlines_formatter is not None:
                rendered_lines = cell_inlines_formatter(cell, usable_w)
                num_lines = max(len(rendered_lines), 1)
            else:
                txt = self._extract_cell_text(cell)
                text_lines = self.wrap_cell_text(txt, spanned_w)
                num_lines = max(len(text_lines), 1)

            needed_h = num_lines * self.line_height + 2 * self.cell_padding

            if rs == 1:
                row_heights[r] = max(row_heights[r], needed_h)

            prepared_cells.append({
                "r": r,
                "c": c,
                "rs": rs,
                "cs": eff_cs,
                "cell": cell,
                "text_lines": text_lines,
                "rendered_lines": rendered_lines,
                "needed_h": needed_h,
            })

        # Đối với các ô rowspan > 1, đảm bảo sum(row_heights[r : r+rs]) >= needed_h
        for item in prepared_cells:
            r = item["r"]
            rs = min(item["rs"], num_rows - r)
            needed_h = item["needed_h"]
            span_curr_h = sum(row_heights[r : r + rs])
            if span_curr_h < needed_h:
                diff = needed_h - span_curr_h
                per_row_add = diff / rs
                for k in range(rs):
                    row_heights[r + k] += per_row_add

        # 2. Định vị toạ độ tuyệt đối cho từng ô
        laid_out_cells: list[list[LaidOutCell]] = [[] for _ in range(num_rows)]

        row_y_offsets = [y0]
        for h in row_heights:
            row_y_offsets.append(row_y_offsets[-1] + h)

        for item in prepared_cells:
            r = item["r"]
            c = item["c"]
            rs = min(item["rs"], num_rows - r)
            cs = item["cs"]
            cell_x = x0 + sum(col_widths[:c])
            cell_y = row_y_offsets[r]
            cell_w = sum(col_widths[c : c + cs])
            cell_h = sum(row_heights[r : r + rs])

            laid_out_cells[r].append(
                LaidOutCell(
                    x=cell_x,
                    y=cell_y,
                    width=cell_w,
                    height=cell_h,
                    text_lines=item["text_lines"],
                    cell=item["cell"],
                    col=c,
                    row=r,
                    colspan=cs,
                    rowspan=rs,
                    rendered_lines=item["rendered_lines"],
                )
            )

        total_h = sum(row_heights)
        return TableLayoutData(
            x=x0,
            y=y0,
            width=total_w,
            height=total_h,
            col_widths=col_widths,
            row_heights=row_heights,
            cells=laid_out_cells,
        )

    def generate_border_strokes(
        self,
        data: TableLayoutData,
        style: TableBorder = TableBorder.ALL,
        jitter: float = 0.0,
        seed: int | None = None,
    ) -> list[PositionedStroke]:
        """Tạo danh sách các đường nét vẽ thẳng hoặc hơi run tay (jitter) làm khung viền bảng, ẩn nét trong ô gộp."""
        if style == TableBorder.NONE or data.width <= 0 or data.height <= 0:
            return []

        rnd = random.Random(seed if seed is not None else 42)

        def jitter_segment(p1: tuple[float, float], p2: tuple[float, float]) -> list[tuple[float, float]]:
            if jitter <= 0.0:
                return [p1, p2]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = math.hypot(dx, dy)
            if dist < 15.0:
                return [p1, p2]
            num_steps = max(2, int(dist / 25.0))
            pts = [p1]
            for step in range(1, num_steps):
                t = step / num_steps
                bx = p1[0] + dx * t
                by = p1[1] + dy * t
                nx = -dy / dist
                ny = dx / dist
                offset = rnd.gauss(0, 0.35 * jitter)
                pts.append((round(bx + nx * offset, 2), round(by + ny * offset, 2)))
            pts.append(p2)
            return pts

        x1 = data.x
        x2 = data.x + data.width
        y1 = data.y
        y2 = data.y + data.height

        strokes: list[PositionedStroke] = []

        # 1. Khung bao quanh ngoài (OUTER, ALL, HORIZONTAL)
        if style in (TableBorder.OUTER, TableBorder.ALL, TableBorder.HORIZONTAL):
            strokes.append(PositionedStroke(points=jitter_segment((x1, y1), (x2, y1))))
            strokes.append(PositionedStroke(points=jitter_segment((x1, y2), (x2, y2))))

        if style in (TableBorder.OUTER, TableBorder.ALL):
            strokes.append(PositionedStroke(points=jitter_segment((x1, y1), (x1, y2))))
            strokes.append(PositionedStroke(points=jitter_segment((x2, y1), (x2, y2))))

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
                            strokes.append(PositionedStroke(points=jitter_segment((cur_seg_start, div_y), (col_xs[c_idx], div_y))))
                            cur_seg_start = None

                if cur_seg_start is not None:
                    strokes.append(PositionedStroke(points=jitter_segment((cur_seg_start, div_y), (col_xs[num_cols], div_y))))

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
                            strokes.append(PositionedStroke(points=jitter_segment((div_x, cur_seg_start), (div_x, row_ys[r_idx]))))
                            cur_seg_start = None

                if cur_seg_start is not None:
                    strokes.append(PositionedStroke(points=jitter_segment((div_x, cur_seg_start), (div_x, row_ys[num_rows]))))

        return strokes
