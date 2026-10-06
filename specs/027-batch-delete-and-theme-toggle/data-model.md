# Data Model: Xóa Hàng Loạt & Chủ Đề Giao Diện

**Feature**: `027-batch-delete-and-theme-toggle`
**Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

---

## 1. Các Cấu Trúc Dữ Liệu Lõi (Core Data Structures)

### 1.1 `BatchDropRequest`
Đại diện cho danh sách yêu cầu xóa nhiều ký tự được gửi từ tầng giao diện xuống tầng điều khiển:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class BatchDropItem:
    label: str           # Nhãn ký tự (ví dụ: 'a', '1', ',', 'α', 'dấu huyền')
    category: str | None = None  # Nhóm nếu đã xác định trước: 'letters', 'digits', 'punct', 'symbols', 'marks'
```

### 1.2 `BatchDropResult` (hoặc mở rộng `DropResult`)
Báo cáo kết quả chi tiết sau khi thực hiện xóa hàng loạt:

```python
from dataclasses import dataclass, field

@dataclass
class DropResult:
    removed: dict[str, int] = field(default_factory=dict)  # {label: số_mẫu_đã_xóa}
    total_removed_samples: int = 0                         # Tổng số mẫu nét bị xóa
    total_removed_chars: int = 0                           # Tổng số ký tự bị xóa hoàn toàn khỏi kho
```

### 1.3 `ThemeMode`
Trạng thái chủ đề giao diện người dùng:

```python
from typing import Literal

ThemeMode = Literal["light", "dark", "system"]
```

Bảng thuộc tính màu (`ThemePalette`):
- `bg_main`: Màu nền cửa sổ chính / ứng dụng
- `bg_panel`: Màu nền khung thẻ, bảng, thẻ tab
- `fg_text`: Màu chữ chính
- `fg_muted`: Màu chữ phụ / ghi chú mờ
- `border`: Màu đường viền widget
- `canvas_bg`: Màu nền khung vẽ nét tay
- `canvas_guide`: Màu đường kẻ mốc (chân chữ, ascender, descender)
- `btn_bg`, `btn_fg`: Màu nền và chữ cho nút bấm

---

## 2. Mô Hình Lưu Trữ Cấu Hình Người Dùng (Preferences Storage)

### 2.1 Web Client (`localStorage`)
Khóa lưu trữ:
- Key: `"chuviettay_theme"`
- Value: `"light"` | `"dark"` | `"system"`

### 2.2 Desktop GUI (`user_config.json`)
Lưu tại đường dẫn `paths.config_dir() / "user_config.json"`:

```json
{
  "theme": "dark",
  "window_geometry": "1000x700"
}
```

---

## 3. Trạng Thái Giao Diện (UI State Machine)

### 3.1 Trạng thái chọn ký tự trong Tab Kho mẫu
```text
[Không chọn mục nào] ── (Tích chọn mục) ──> [Đang chọn N mục] ── (Nhấn "Xóa") ──> [Hộp thoại xác nhận]
        ▲                                          │                                    │
        │                                          │                                (Đồng ý)
        └──────────── (Bỏ chọn / Hoàn tất xóa) ─────┴───────────────────────────────────┘
```
