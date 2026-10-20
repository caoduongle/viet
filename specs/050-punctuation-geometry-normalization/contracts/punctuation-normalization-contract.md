# Contract: Chuẩn hóa Hình học Mẫu Dấu câu (Punctuation Normalization Contract)

**Feature Branch**: `050-punctuation-geometry-normalization`  
**Date**: 2026-10-20  
**Status**: Ratified  
**Spec Reference**: [specs/050-punctuation-geometry-normalization/spec.md](spec.md)

---

## 1. Mục đích & Phạm vi Hợp đồng
Hợp đồng này quy định giao diện, hành vi, tiền điều kiện và hậu điều kiện của hàm chuẩn hóa mẫu dấu câu `_normalize_punct_sample` trong `chuviettay/model/writer.py`.

---

## 2. Giao diện Phương thức

```python
def _normalize_punct_sample(
    self,
    inst: dict,
    char: str | None = None,
) -> tuple[list[Stroke], float]:
    """
    Chuẩn hóa hình học mẫu dấu câu theo nhóm hình học ngữ nghĩa của ký tự.
    
    Args:
        inst: Dictionary chứa thông tin mẫu nét gốc ("s": list[Stroke], "w": float).
        char: Ký tự dấu câu cần chuẩn hóa (ví dụ: '(', ')', ',', '.', ':', ';', '!', '?').
              Nếu None, cố gắng suy ra từ inst.get("char") hoặc coi như dấu chung.
              
    Returns:
        tuple[list[Stroke], float]:
            - list[Stroke]: Danh sách nét đã được chuẩn hóa về hoành độ x >= 0 và cao độ y chuẩn.
            - float: Độ rộng tiến bước thực tế (advance width) đã tính cả khoảng đệm thích hợp.
    """
```

---

## 3. Tiền điều kiện (Preconditions)
1. `inst` là một dictionary chứa khóa `"s"` đại diện cho các nét vẽ (danh sách các danh sách tọa độ phẳng `[x0, y0, x1, y1, ...]`).
2. Kích thước tham chiếu `self.b.xh` (x-height) là một số thực dương (`> 0.0`), mặc định `7.94pt` nếu kho mẫu chưa xác định.
3. Tọa độ đường cơ sở là `y = 0.0` (chiều âm hướng lên đỉnh chữ, chiều dương hướng xuống chân chữ).

---

## 4. Hậu điều kiện (Postconditions)

### 4.1 Bất biến Tọa độ Ngang
- Hoành độ cực tiểu của toàn bộ nét vẽ sau chuẩn hóa luôn bắt đầu tại `x = 0.0` ($\min_{pt} x_{pt} = 0.0$).
- Độ rộng trả về $\text{adv\_w} \ge \max_{pt} x_{pt}$.

### 4.2 Bất biến Dấu ngoặc (`() [] {}`)
- Chiều cao tổng thể đạt tối thiểu $1.35 \times x_h$ (mục tiêu $1.45 \times x_h$).
- Đỉnh dấu ngoặc $\min_{pt} y_{pt} \le -1.20 \times x_h$ (cao hơn đỉnh chữ số $-1.20 \times x_h$).
- Chân dấu ngoặc $\max_{pt} y_{pt} \ge +0.15 \times x_h$ (vượt xuống dưới đường cơ sở).

### 4.3 Bất biến Dấu phẩy (`,`)
- Đỉnh dấu phẩy nằm trên đường cơ sở: $\min_{pt} y_{pt} < 0.0$ (khoảng $-0.14 \times x_h$).
- Đuôi dấu phẩy móc xuống dưới đường cơ sở: $\max_{pt} y_{pt} > 0.0$ (khoảng $+0.24 \times x_h$).
- Không có bất kỳ nét nào của dấu phẩy lơ lửng hoàn toàn trên đường cơ sở ($\max_{pt} y_{pt} \le 0.0$ là bị cấm).

### 4.4 Bất biến Dấu chấm (`.`)
- Đáy của dấu chấm bám sát đường cơ sở: $|\max_{pt} y_{pt}| \le 0.05 \times x_h$.
- Chiều cao dấu chấm gọn gàng: $h \le 0.22 \times x_h$.

### 4.5 Bất biến Bảo toàn Golden Master (Invariance Guard)
- Đối với các mẫu chuẩn trong bộ test chuẩn `tiny_bank` (nơi dấu chấm và dấu phẩy đã có gốc tại $y = 0.0$ và kích thước hợp lệ), thuật toán **tuyệt đối không làm thay đổi tọa độ dọc y**, bảo đảm kết xuất byte-for-byte hoàn toàn tương thích và giữ nguyên mã băm SHA-256 của toàn bộ 9 ca kiểm thử Golden Master.
