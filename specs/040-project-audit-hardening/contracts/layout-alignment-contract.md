# Contract: Paragraph Alignment in Layout Engine

**Scope**: Ràng buộc hình học căn lề trong `DocumentLayoutEngine.render_paragraph_inlines`.

---

## 1. Công thức Hình học Căn lề Dòng

Cho một dòng chữ chứa danh sách các mục kết xuất `cur_line`:
- Tọa độ lề trái cơ sở: `base_x = self.x0 + indent`
- Bề rộng khả dụng: `avail_w = max(self.width - indent, 1.0)`
- Bề rộng thực tế của dòng: `curw = cur_line[-1].start + cur_line[-1].width`
- Khoảng trống còn lại: `rem_space = max(0.0, avail_w - curw)`

### 1.1 Căn trái (`"left"`)
$$line\_start\_x = base\_x$$
$$start'_i = start_i$$

### 1.2 Căn giữa (`"center"`)
$$line\_start\_x = base\_x + \frac{rem\_space}{2}$$
$$start'_i = start_i$$

### 1.3 Căn phải (`"right"`)
$$line\_start\_x = base\_x + rem\_space$$
$$start'_i = start_i$$

### 1.4 Căn đều hai bên (`"justify"`)
- Nếu dòng kết thúc bởi `LineBreak`, hoặc dòng cuối đoạn (`is_last_line = True`), hoặc số từ $N \le 1$, hoặc $rem\_space \le 0$:
  $$line\_start\_x = base\_x$$
  $$start'_i = start_i$$
- Nếu dòng là dòng tràn giữa đoạn ($N > 1$):
  $$line\_start\_x = base\_x$$
  $$start'_i = start_i + i \cdot \frac{rem\_space}{N - 1}$$

## 2. Ràng buộc Tương thích
- Dòng chữ sau khi căn chỉnh phải truyền đúng tọa độ hình học tuyệt đối sang hàm `token_layout_callback` để hộp bao quanh từ thiếu mẫu (missing token boxes) khớp chính xác với nét chữ trên trang viết.
- Khi `align == "left"` (mặc định), kết quả tọa độ và nét vẽ phải khớp 100% với phiên bản hiện tại, không gây hồi quy cho các bài kiểm thử Golden Master.
