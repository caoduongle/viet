# Contract: Khoảng Hở Quang Học Cận Bên Toán Tử Lớn

**Module**: `chuviettay.layout.math_layout.MathLayoutEngine`  
**Consumers**: Math Renderer, Page Layout Engine  

---

## 1. Phương thức `_m_NAry`

### Chữ ký hàm (Signature):
```python
def _m_NAry(self, node: NAry, scale: float, eff: float, depth: int) -> MathLayoutItem:
    """
    Bố cục toán tử n-ary (∑, ∏, ∫...).
    - Nếu stacked = True: Cận trên và cận dưới xếp chồng trên/dưới op.
    - Nếu stacked = False: Cận trên và cận dưới đặt ở góc bên phải (side limits).
      Khi có cả hai cận, bắt buộc phải bảo đảm khoảng hở quang học tối thiểu,
      ngăn ngừa nét mực đè lên nhau.
    """
```

### Ràng buộc khoảng hở quang học (Optical Clearance Guarantee):

Cho toán tử $O$ có chỉ số trên $S_{up}$ và chỉ số dưới $S_{ub}$ tại cùng hoành độ bên phải (áp dụng khi `sup_dx == 0.0`, tức các toán tử thẳng hàng dọc như $\sum, \prod$ không thuộc nhóm tích phân `SIDE_LIMIT_OPERATORS`):

$$\text{gap} = \text{sub\_top} - \text{sup\_bot} \ge \text{min\_gap}$$

Trong đó:
- $\text{min\_gap} = \max(3.5 \times \text{eff}, 0.40 \times \text{xh} \times \text{eff})$
- $\text{sup\_bot} = \text{sup\_y} + \max(S_{up}.\text{descent}, \text{ink\_bot}(S_{up}))$
- $\text{sub\_top} = \text{sub\_y} + \min(-S_{ub}.\text{ascent}, \text{ink\_top}(S_{ub}))$
- Đối với toán tử tích phân (`SIDE_LIMIT_OPERATORS`), độ lệch ngang `sup_dx` đã tạo khoảng cách tự nhiên nên giữ nguyên độ lệch dọc chuẩn.

### Hợp đồng phân phối dịch chuyển (Shift Distribution):
Khi $\text{gap} < \text{min\_gap}$, độ thiếu hụt $\text{deficit} = \text{min\_gap} - \text{gap}$ được bù trừ bằng:
- $\text{sub\_y} \mathrel{+}= \text{deficit} \times 0.65$ (đẩy chỉ số dưới xuống)
- $\text{sup\_y} \mathrel{-}= \text{deficit} \times 0.35$ (đẩy chỉ số trên lên)
- Cập nhật lại `ascent` và `descent` của `MathLayoutItem` đảm bảo bao trọn cả hai chỉ số.
