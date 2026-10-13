# Contract: Phân trang Bảng Toàn vẹn & An toàn Hình học Bounding Box (CTR-036-TABLE-FULL-SCAN-AND-CELL-ID)

**Mã hợp đồng**: `CTR-036-TABLE-FULL-SCAN-AND-CELL-ID`  
**Gói công việc**: P1 & P2 - Bảng phân trang và An toàn hình thái nét  
**Ngày ban hành**: 2026-10-13  
**Trạng thái**: Ratified (Đã tinh chỉnh sau Engineering Review)

---

## 1. Tìm kiếm Ô Nguồn Tiếp nối Toàn Bảng (Full Table Scan)

### 1.1 Vị trí Áp dụng
- File: `chuviettay/layout/engine.py` (trong nhánh phân trang ô bảng biểu)

### 1.2 Đặc tả Thuật toán
```python
# Khi một ô còn dòng chưa vẽ cần chuyển tiếp sang trang tiếp theo:
rem_lines = laid_cell.rendered_lines[l_idx:]
rem_metrics = metrics_list[l_idx:]
target_sid = laid_cell.source_cell_id
found_target = False

if target_sid is not None:
    # Quét toàn bộ bảng từ hàng 0, bất kể vị trí curr_row_idx hiện tại
    for search_r in range(0, len(full_table_data.cells)):
        for orig_c in full_table_data.cells[search_r]:
            if orig_c.source_cell_id == target_sid:
                orig_c.rendered_lines = rem_lines
                orig_c.line_metrics = rem_metrics
                orig_c.is_continuation = True
                # CHÚ Ý QUAN TRỌNG: Chỉ cập nhật next_row nếu search_r >= curr_row_idx!
                # Nếu search_r < curr_row_idx (ô rowspan từ các trang trước), KHÔNG được kéo lùi next_row về search_r,
                # vì các hàng trước đó đã được cắt lát xong; việc lát cắt trang sau sẽ tự động chèn ô tiếp nối qua range(start_row_idx).
                if search_r >= curr_row_idx:
                    next_row = min(next_row, search_r)
                found_target = True
                break
        if found_target:
            break

if not found_target:
    # Tuyệt đối không fallback sang ghi đè ô cùng cột
    layout_warnings.append(
        f"Không tìm thấy ô nguồn có ID {target_sid} khi chuyển tiếp dòng ô ({laid_cell.row}, {laid_cell.col}); bảo tồn nội dung tránh ghi đè."
    )
```

### 1.3 Điều cấm (Forbidden Actions)
- **CẤM** giới hạn tìm kiếm `range(curr_row_idx, ...)` vì ô gộp hàng (`rowspan > 1`) có thể bắt đầu từ hàng $0 \le r < \text{curr\_row\_idx}$.
- **CẤM** gán `next_row = min(next_row, search_r)` vô điều kiện khi `search_r < curr_row_idx` vì sẽ làm tua ngược tiến trình phân trang về trang 1 gây lặp vô hạn.
- **CẤM** tìm kiếm fallback theo `col == laid_cell.col` để gán vào ô hàng khác, ngăn ngừa nguy cơ phá hủy nội dung ô kế cận.

---

## 2. Định danh Ô Độc lập Tầng Layout (Layout Monotonic Cell ID)

### 2.1 Vị trí Áp dụng
- File: `chuviettay/layout/table_layout.py`

### 2.2 Đặc tả Cấp phát Định danh
- Trong mỗi phiên tính toán bố cục bảng của `TableLayoutEngine`:
  - Khởi tạo bộ đếm: `self._cell_id_counter = 0`.
  - Hàm cấp phát:
    ```python
    def _next_cell_id(self) -> int:
        self._cell_id_counter += 1
        return self._cell_id_counter
    ```
  - Cấp phát ID duy nhất cho mỗi ô khi tạo `LaidOutCell`:
    `laid_cell.source_cell_id = sid`
  - Khi tách ô thành ô tiếp nối (`is_continuation = True`), ô tiếp nối giữ nguyên `source_cell_id` của ô gốc.
- **Ràng buộc mô hình IR**:
  - Xóa bỏ hoàn toàn câu lệnh `cell.source_cell_id = r * 1000 + c`.
  - Đối tượng `TableCell` trong `chuviettay/document/ir.py` được bảo toàn tính bất biến 100%.

---

## 3. An toàn Hình thái Nét vẽ & Bounding Box (No Flattening / Anti-Squash)

### 3.1 Vị trí Áp dụng
- File: `chuviettay/layout/engine.py` (hàm `_render_text_line` và tính toán dòng bảng)

### 3.2 Quy trình Xử lý Tránh Bẹt Nét
1. **Dàn trang trước khi vẽ**:
   - Nếu $y_{\text{dòng}} + h_{\text{dòng}} > y_{\text{max\_page\_y}}$, ưu tiên đẩy dòng sang trang kế tiếp.
2. **Co tỷ lệ đồng dạng (Isotropic Downscaling)**:
   - Với ô đơn không thể chuyển tiếp, tính hệ số `downscale` đồng dạng cho cả hai trục $X$ và $Y$ có tính đến phần chân chữ (descender) và độ rung nét (jitter):
     $$\text{downscale} = \max\left(0.2, \min\left(1.0, \frac{y_{\text{max\_page\_y}} - y_{\text{baseline}} - \text{jitter\_tol}}{\max(1e-6, \text{cur\_desc})}\right)\right)$$
3. **Kiểm tra Bounding Box Thực tế & Dịch chuyển Hình thái (Anti-Squash)**:
   - Sau khi áp dụng xoay, tỉ lệ và sóng dòng, kiểm tra toạ độ đáy thực tế:
     $$y_{\max,\text{actual}} = \max \{ y \mid (x, y) \in \text{stroke\_points} \}$$
   - Nếu $y_{\max,\text{actual}} > y_{\text{max\_page\_y}}$:
     Thay vì gán bẹt từng điểm $y = \min(y, y_{\text{max\_page\_y}})$ làm biến dạng các đoạn cong thành đường thẳng ngang collinear, hệ thống dịch chuyển toàn bộ nét lên trên theo hiệu số:
     $$\Delta y = y_{\max,\text{actual}} - y_{\text{max\_page\_y}}$$
     $$y_{\text{new}} = y - \Delta y$$
     Điều này bảo toàn 100% hình thái vector tự nhiên của chữ viết tay trong khi vẫn đảm bảo tuyệt đối không có điểm nào vượt mép dưới của trang.
