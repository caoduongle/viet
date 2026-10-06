# Data Model: Thuần Ký Tự & Nạp Lưới Tạo Kho

**Feature**: `specs/024-kho-ky-tu`

---

## 1. Entities & Data Structures

### 1.1. `CharSet` and `CharCatalog`
Định nghĩa tập hợp các ký tự tiêu chuẩn trong `chuviettay/model/char_catalog.py`:

```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass(frozen=True)
class CharCatalogGroup:
    id: str           # e.g. "co_ban", "toan_hy_lap", "mo_rong", "day_du"
    name: str         # Tên hiển thị (Tiếng Việt)
    description: str  # Mô tả tóm tắt
    chars: List[str]  # Danh sách ký tự đơn

# Danh mục các bộ:
# 1. 'co_ban': Chữ cái tiếng Việt, chữ số, dấu câu cơ bản (~140 ký tự)
# 2. 'toan_hy_lap': Ký hiệu toán học, chữ Hy Lạp cơ bản
# 3. 'mo_rong': Ký tự đặc biệt mở rộng
# 4. 'day_du': Hợp nhất tất cả các bộ trên
```

### 1.2. `GridImportResult`
Dataclass báo cáo kết quả nạp file lưới `.xopp` vào kho:

```python
@dataclass
class GridImportResult:
    total_cells: int          # Tổng số ô lưới quét được
    cells_with_ink: int       # Số ô người dùng có viết nét mực
    added_samples: int        # Số mẫu ký tự mới được thêm thành công vào kho
    duplicate_samples: int    # Số mẫu bị bỏ qua do trùng nét
    empty_cells: int          # Số ô không có nét mực
    skipped_multi_char: int   # Số ô có label nhiều hơn 1 ký tự (ô từ cụm cũ) bị bỏ qua
    rejected_cells: int       # Số ô có nét mực nhưng không hợp lệ (ngoài lề, lỗi bbox)
    errors: List[str]         # Danh sách thông báo lỗi hoặc cảnh báo chi tiết
    updated_xh: Optional[float] = None  # x-height mới của kho nếu có cập nhật
```

### 1.3. `CharSample` (Refactored LetterSample)
Cấu trúc mẫu ký tự lưu trữ trong `Bank`:

```python
@dataclass
class CharSample:
    label: str                # Ký tự đơn (len == 1 hoặc ký tự dấu thanh)
    category: str             # 'letters' | 'digits' | 'punct' | 'symbols' | 'marks'
    strokes: List[List[Tuple[float, float]]]  # Danh sách nét tọa độ tương đối
    lsb: float                # Left side bearing (tối đa 0.3 * xh)
    rsb: float                # Right side bearing (tối đa 0.3 * xh)
    bbox: Tuple[float, float, float, float]   # (min_x, min_y, max_x, max_y)
    baseline: float           # Đường cơ sở (chuẩn hóa = 0 hoặc tương đối)
```

### 1.4. `Bank` Storage Schema (`kho_mau.json.gz`)
Cấu trúc từ điển JSON của kho mẫu:

```json
{
  "version": 2,
  "xh": 16.5,
  "letters": {
    "a": [ /* list of CharSample dicts */ ],
    "b": [ /* ... */ ]
  },
  "digits": {
    "0": [ /* ... */ ]
  },
  "punct": {
    ".": [ /* ... */ ]
  },
  "symbols": {
    "+": [ /* ... */ ]
  },
  "marks": {
    "\\u0300": [ /* ... */ ]
  },
  "words": {
    /* Lưu bảo toàn dữ liệu kho cũ (không dùng khi viết, không hiển thị trong UI) */
  }
}
```

---

## 2. Validation & Classification Rules

1. **Đơn ký tự (Single Character)**:
   - Một ô lưới chỉ được nhập vào kho nếu `len(label) == 1` hoặc `label` là tổ hợp ký tự dấu kết hợp (combining mark).
   - Nếu `len(label) > 1`, `import_char_grid` tăng đếm `skipped_multi_char` và ghi log cảnh báo, không nạp vào `letters`.
2. **Quy tắc phân loại (`classify_char`)**:
   - Nếu ký tự nằm trong dải combining accent marks (`\u0300`, `\u0301`, `\u0303`, `\u0309`, `\u0323`, v.v.) $\rightarrow$ `'marks'`.
   - Nếu Unicode category bắt đầu bằng `'L'` $\rightarrow$ `'letters'`.
   - Nếu Unicode category bắt đầu bằng `'N'` $\rightarrow$ `'digits'`.
   - Nếu Unicode category bắt đầu bằng `'P'` $\rightarrow$ `'punct'`.
   - Nếu Unicode category bắt đầu bằng `'S'` $\rightarrow$ `'symbols'`.
   - Mặc định còn lại $\rightarrow$ `'symbols'`.
3. **Giới hạn Side Bearing (LSB/RSB)**:
   - $0 \le lsb \le 0.3 \times xh$.
   - $0 \le rsb \le 0.3 \times xh$.
   - Nếu khoảng cách tính từ lề lớn hơn ngưỡng này, tự động kẹp về giá trị trần để ngăn lỗi giãn chữ.
