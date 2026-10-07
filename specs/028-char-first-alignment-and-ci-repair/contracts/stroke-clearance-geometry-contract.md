# Contract: Stroke Clearance Geometry Verification

**Specification Version**: 1.0.0  
**Feature**: 028-char-first-alignment-and-ci-repair  
**Module**: `chuviettay.model.text_utils`  

---

## 1. Overview
Hợp đồng này quy định chi tiết thuật toán hình học xác định khoảng cách tối thiểu giữa các nét viết tay kế cận khi ghép từ trong `Writer.assemble_word()`. Thay thế heuristic đo khoảng cách điểm rời rạc bằng phép tính khoảng cách giữa các đoạn thẳng 2D (segment-to-segment distance) kết hợp tỉa bớt hình chữ nhật bao quanh (bounding box pruning).

---

## 2. API Signatures

### 2.1 `segment_distance(p1: Point, p2: Point, q1: Point, q2: Point) -> float`
Tính khoảng cách ngắn nhất giữa đoạn thẳng $S_1 = [P_1, P_2]$ và đoạn thẳng $S_2 = [Q_1, Q_2]$ trong không gian 2D.

- **Toán học & Xử lý đoạn suy biến (Degenerate Handling)**:
  1. Nếu $\|P_2 - P_1\|^2 < 10^{-10}$ và $\|Q_2 - Q_1\|^2 < 10^{-10}$: Cả hai đoạn đều là điểm suy biến $\to$ khoảng cách điểm-điểm $\|P_1 - Q_1\|$.
  2. Nếu $\|P_2 - P_1\|^2 < 10^{-10}$: $S_1$ là điểm $P_1$ $\to$ chiếu $P_1$ lên đoạn $S_2$ với tham số $t = \text{clamp}\left(\frac{(P_1 - Q_1) \cdot (Q_2 - Q_1)}{\|Q_2 - Q_1\|^2}, 0, 1\right)$.
  3. Nếu $\|Q_2 - Q_1\|^2 < 10^{-10}$: $S_2$ là điểm $Q_1$ $\to$ chiếu $Q_1$ lên đoạn $S_1$ với tham số $s = \text{clamp}\left(\frac{(Q_1 - P_1) \cdot (P_2 - P_1)}{\|P_2 - P_1\|^2}, 0, 1\right)$.
  4. Nếu cả hai đoạn không suy biến: Giải bài toán cực tiểu hóa khoảng cách Euclid tham số $(s^*, t^*) \in [0, 1] \times [0, 1]$.
- **Độ phức tạp**: $O(1)$, thực thi an toàn trong Pure Python không có rủi ro `ZeroDivisionError`.

### 2.2 `min_stroke_clearance(strokes_a: list[Stroke], strokes_b: list[Stroke], max_segments: int = 40) -> float`
Tính khoảng cách nhỏ nhất giữa hai tập nét viết tay phẳng `strokes_a` và `strokes_b`.

- **Quy trình tối ưu hoá**:
  1. Trích xuất các đoạn thẳng từ `strokes_a` và `strokes_b`.
  2. Bounding Box Pruning:
     - Tính $X_{max}(A) = \max_{P \in A}(x_P)$ và $X_{min}(B) = \min_{Q \in B}(x_Q)$.
     - Chỉ giữ các đoạn thẳng của $A$ có $x \ge X_{max}(A) - 4.0$ và các đoạn của $B$ có $x \le X_{min}(B) + 4.0$.
  3. Lọc nhanh bounding box giữa từng cặp đoạn: nếu $\text{bbox\_dist}(seg_A, seg_B) \ge min\_dist$, bỏ qua tính chi tiết.
  4. Tính `segment_distance` cho các cặp đoạn còn lại.
  5. Trả về khoảng cách nhỏ nhất (làm tròn 2 chữ số thập phân). Nếu rỗng, trả về `999.0`.

---

## 3. Tiêu Chuẩn Khe Hở Vật Lý (Physical Clearance Floor) & Hướng Dịch Chuyển

Trong `Writer.assemble_word()`:
$$clearance\_floor = pen\_clearance\_factor \cdot pen\_width$$
(Với $pen\_width \approx 1.41$, $pen\_clearance\_factor \approx 0.6 \implies clearance\_floor \approx 0.85$).

1. **Dấu thanh trên** (sắc, huyền, hỏi, ngã, mũ):
   Nếu $\text{min\_stroke\_clearance}(body\_strokes, placed\_mark) < clearance\_floor$:
   $$\Delta y = -(clearance\_floor - \text{dist\_mark})$$
   $c_y \leftarrow c_y + \Delta y$ (đẩy lên trên theo chiều âm của $y$).
2. **Dấu nặng** ($T == NANG$):
   Nếu $\text{min\_stroke\_clearance}(body\_strokes, placed\_mark) < clearance\_floor$:
   $$\Delta y = +(clearance\_floor - \text{dist\_mark})$$
   $c_y \leftarrow c_y + \Delta y$ (đẩy xuống dưới theo chiều dương của $y$).
3. **Ký tự liền kề ngang**:
   Nếu $\text{min\_stroke\_clearance}(prev\_strokes, curr\_strokes) < clearance\_floor$:
   $$\Delta x = clearance\_floor - \text{min\_stroke\_clearance} + 0.1$$
   Tịnh tiến ký tự hiện tại sang phải và cập nhật vị trí tiến $cur\_x$.
   Đảm bảo văn bản viết ra không bao giờ bị dính mực giữa hai nét liền kề.
