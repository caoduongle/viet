# Contract: Punctuation & Math Optical Clearance

## Context
Bố cục dấu câu trong `Writer.number()`, `Writer.token()`, và `MathLayoutEngine`.

## Invariant 1: Decimal Clearance
Trong chuỗi số có dấu phẩy hoặc chấm thập phân:
1. Khoảng hở hình học giữa biên phải nét chữ số trước $\text{max\_x}(D_1)$ và biên trái dấu phẩy $\text{min\_x}(P)$:
   $$\text{min\_x}(P) - \text{max\_x}(D_1) \ge \max(0.10 \cdot xh,\, 0.80 \cdot \text{pen\_w})$$
2. Khoảng hở hình học giữa biên phải dấu phẩy $\text{max\_x}(P)$ và biên trái chữ số sau $\text{min\_x}(D_2)$:
   $$\text{min\_x}(D_2) - \text{max\_x}(P) \ge \max(0.10 \cdot xh,\, 0.75 \cdot \text{pen\_w})$$

## Invariant 2: Math Delimiter Clearance
Trong bố cục biểu thức toán học (`MathLayoutEngine`):
1. Giữa dấu ngoặc mở `(` (hoặc `[`) và phần tử nội dung liền kề bên trong:
   $$\text{min\_x}(\text{inner}) - \text{max\_x}(\text{open}) \ge \max(0.12 \cdot xh \cdot \text{eff},\, 0.85 \cdot \text{pen\_w})$$
2. Giữa phần tử nội dung liền kề bên trong và dấu ngoặc đóng `)` (hoặc `]`):
   $$\text{min\_x}(\text{close}) - \text{max\_x}(\text{inner}) \ge \max(0.12 \cdot xh \cdot \text{eff},\, 0.85 \cdot \text{pen\_w})$$

## Invariant 3: Trailing Punctuation Clearance
Trong `Writer.token()`:
1. Giữa biên phải nét chữ của phần thân $\text{max\_x}(\text{core})$ và biên trái dấu kết thúc $\text{min\_x}(P)$:
   $$\text{min\_x}(P) - \text{max\_x}(\text{core}) \ge \max(0.85 \cdot \text{pen\_w},\, 0.20 \cdot xh)$$
2. Giữa hai dấu kết thúc liên tiếp $P_1$ và $P_2$:
   $$\text{min\_x}(P_2) - \text{max\_x}(P_1) \ge \max(0.60 \cdot \text{pen\_w},\, 0.14 \cdot xh)$$

## Invariant 4: Golden Master Invariant
Mọi công thức khoảng hở phải bảo toàn 100% kết quả mã băm SHA-256 của các ca kiểm thử Golden Master trên fixture `tiny_bank` (`test_golden_master_real_path.py`).
