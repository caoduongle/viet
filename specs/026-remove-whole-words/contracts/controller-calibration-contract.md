# Contract: Calibration & Inspection API

**Modules**: `chuviettay.controller.app_controller`, `chuviettay.browser.bridge`, `chuviettay.model.xopp`
**Feature**: `026-remove-whole-words`
**Date**: 2026-10-06

## 1. API Hiệu chỉnh Cỡ tay (`Calibration`)

### Chữ ký trong `AppController`
```python
def pick_calibration_char(self) -> str | None:
    """Chọn ký tự mốc ổn định trong `bank.letters` để đo hệ số cỡ tay phiên hiện tại.
    
    Returns:
        str | None: Nhãn chữ cái (ví dụ 'o', 'a', 'n') hoặc None nếu chưa có mẫu nào.
    """
```

### Chữ ký trong `Bridge` (Web Client)
```python
def pick_calibration_char(self) -> dict[str, Any]:
    """Cung cấp ký tự mốc cho Web Worker.
    
    Response format:
        {
            "ok": True,
            "char": "o" | None
        }
    """
```

### Chữ ký trong `xopp.py`
```python
def pick_calibration_char(bank: Bank) -> str | None:
    """Thuật toán chọn chữ cái mốc:
    - Tìm trong bank.letters.
    - Ưu tiên các chữ cái x-height ổn định: 'o', 'a', 'e', 'n', 'u', 'c', 'm'.
    - Lọc những chữ có ít nhất 3 mẫu, tính độ biến thiên độ rộng.
    - Trả về chữ cái có điểm cao nhất hoặc None.
    """
```

---

## 2. API Kiểm tra Kho Mẫu (`export_check`)

### Chữ ký trong `AppController`
```python
def export_check(self, out_path: str) -> CheckResult:
    """Xuất file lưới ô xem lại toàn bộ ký tự đã học (chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh).
    
    Tạo lưới hw3 với:
    - Tất cả chữ cái trong bank.letters
    - Tất cả chữ số trong bank.digits
    - Tất cả dấu câu trong bank.punct
    - Tất cả ký hiệu trong bank.symbols
    - Tất cả dấu thanh trong bank.marks
    
    TUYỆT ĐỐI KHÔNG xuất `bank.words`.
    """
```

### Dữ liệu trả về `CheckResult`
```python
@dataclass
class CheckResult:
    out_path: str
    n_chars: int
    n_samples: int
```
