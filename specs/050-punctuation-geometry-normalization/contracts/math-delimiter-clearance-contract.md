# Contract: Khoảng hở Quang học Phân cách và Dấu câu Toán học (Math Delimiter Clearance Contract)

**Feature Branch**: `050-punctuation-geometry-normalization`  
**Date**: 2026-10-20  
**Status**: Ratified  
**Spec Reference**: [specs/050-punctuation-geometry-normalization/spec.md](spec.md)

---

## 1. Mục đích & Phạm vi Hợp đồng
Hợp đồng này quy định quy tắc phân bổ khoảng cách quang học giữa các toán hạng và dấu câu / dấu ngoặc phân cách trong `chuviettay/layout/math_layout.py`, đặc biệt chống dính nét cho chữ số `1` đứng trước dấu đóng ngoặc `)` hoặc dấu phẩy `,`.

---

## 2. Các Ràng buộc Bố cục

### 2.1 Sàn Khoảng hở trong Hàng Toán học (`_m_MathRow`)
Khi bố cục danh sách các phần tử liên tiếp trong `MathRow`:
- Hệ thống duy trì tọa độ cực phải của mực phần tử đi trước: `prev_ink_max_x`.
- Khi phần tử hiện tại `it` là dấu đóng ngoặc `)` hoặc dấu phẩy `,` hoặc phần tử trước đó kết thúc bằng chữ số `1`:
  $$\text{min\_clearance} = \max(0.18 \times x_h \times \text{eff},\; 1.0 \times \text{pen\_w})$$
- Tọa độ đặt $x$ của phần tử tiếp theo phải thỏa mãn:
  $$x \ge \text{prev\_ink\_max\_x} + \text{min\_clearance} - \min(0.0, \text{it\_min\_x})$$

### 2.2 Đệm Phân cách trong Khối Đóng ngoặc (`_m_Delimited`)
Trong cấu trúc `Delimited(body, left, right)`:
- Khoảng đệm `pad` giữa `body` và dấu đóng ngoặc `right`:
  - Nếu phần tử cuối cùng của `body` là chữ số `1` (hoặc biểu thức kết thúc bằng số 1):
    $$\text{pad} = \max(1.5 \times \text{eff},\; 0.18 \times x_h \times \text{eff})$$
  - Các trường hợp thông thường:
    $$\text{pad} = \max(1.2 \times \text{eff},\; 0.14 \times x_h \times \text{eff})$$

### 2.3 Khoảng hở Dấu câu Đuôi Từ (`Writer.token`)
Trong `Writer.token()`:
- Khi phần thân `core` kết thúc bằng chữ số `1` và theo sau là dấu đóng ngoặc `)` hoặc dấu phẩy `,`:
  $$\text{clearance\_gap} \ge \max(0.18 \times x_h,\; 1.0 \times \text{pen\_w})$$
- Điểm bắt đầu vẽ dấu câu `place_x` luôn bảo đảm:
  $$\text{place\_x} \ge \text{core\_max\_x} + \text{clearance\_gap}$$
- Nét mực của hai glyph tuyệt đối không giao cắt hoặc tiếp xúc trực tiếp.

---

## 3. Tiêu chí Xác nhận Hợp đồng (Contract Verification)
- Khoảng cách hình học đo được giữa điểm x cực đại của chữ số `1` và điểm x cực tiểu của dấu `)` trong các biểu thức `P(X >= 1)`, `k!(e^\lambda - 1)`, `\log_{10}(\lfloor x \rfloor + 1)` luôn $\ge 0.18 \times x_h$ (tối thiểu 1.4pt).
- Dấu đóng ngoặc `)` vươn cao hơn đỉnh số `1` và thấp hơn đáy số `1`, không có hiện tượng chụm đầu hay hàn dính nét.
