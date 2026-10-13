# Contract CTR-037-STABLE-STROKE-GEOMETRY: Neo Ngẫu nhiên Hình học Nét chữ Bền vững

## Mục đích
Quy định nguyên tắc dẫn xuất hạt giống ngẫu nhiên cho các biến dạng hình học của nét vẽ (độ run tay, góc xoay, độ lệch $y$, độ dày nét), loại bỏ sự phụ thuộc vào chỉ số dòng `it_idx` và tọa độ Y biến thiên khi ở chế độ `stable_variants=True`.

---

## 1. Dẫn xuất Ngẫu nhiên Hình học Cấp Token

Trong `_render_text_line()`:

1. **Khi `stable_variants=True`**:
   - Khóa hạt giống hình học cho từng mục `RenderItem`:
     ```python
     geom_rng = ScopedRNG(self.effective_seed, "tok", item.token, item.occurrence, "geom")
     ```
   - Các tham số biến dạng hình học:
     ```python
     s = self.S * scale_mult * (1 + geom_rng.gauss(0, 0.02 * self.J))
     rot = geom_rng.gauss(0, 0.010 * self.J)
     dy = geom_rng.gauss(0, 0.35 * self.J)
     wscale_mult = 1 + geom_rng.gauss(0, 0.02 * self.J)
     ```
   - **Tuyệt đối không sử dụng** `it_idx` trong bất kỳ khóa ScopedRNG nào của nét chữ.

2. **Khi `stable_variants=False`**:
   - Sử dụng `self.rnd` tuần tự nguyên bản để đảm bảo tương thích 100% từng byte với golden master cũ:
     ```python
     s = self.S * scale_mult * (1 + self.rnd.gauss(0, 0.02 * self.J))
     rot = self.rnd.gauss(0, 0.010 * self.J)
     dy = self.rnd.gauss(0, 0.35 * self.J)
     wscale_mult = 1 + self.rnd.gauss(0, 0.02 * self.J)
     ```

---

## 2. Xử lý Trôi dạt Sóng dòng Vĩ mô (Line Wave & Drift)

1. **Khi `stable_variants=True`**:
   - Để bảo đảm tính bất biến khi ngắt dòng (Prepend Invariance), độ trôi `xo` và sóng lượn dòng vĩ mô được ấn định cố định:
     ```python
     slope = 0.0
     amp = 0.0
     wl = 200.0
     ph = 0.0
     xo = start_x
     ```
   - Tọa độ nét vẽ của token:
     ```python
     pt_y = base_y + dy + y
     pt_x = xo + start + x
     ```
   - Toàn bộ độ run tay tự nhiên và vi mô vẫn diễn ra đầy đủ và tự nhiên thông qua `geom_rng` (`s`, `rot`, `dy`, `wscale_mult`).

2. **Khi `stable_variants=False`**:
   - Giữ nguyên các phép sinh `slope`, `amp`, `wl`, `ph`, `xo` từ `self.rnd` như hiện nay.
