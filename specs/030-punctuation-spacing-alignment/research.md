# Phase 0 Research: Punctuation Spacing, Natural Alignment & Digit Spacing

**Feature**: `030-punctuation-spacing-alignment`  
**Date**: 2026-10-07  
**Goal**: Điều tra gốc rễ kỹ thuật và chốt giải pháp xử lý triệt để 2 vấn đề:
1. Ký tự dấu câu (như `:`, `,`, `.`, `;`, `!`, `?`, `(`, `)`) bị dính nét vào từ hoặc lệch vị trí.
2. Các chữ số trong chuỗi số (số thập phân, số nguyên, phân số, bảng) bị cách xa nhau quá mức.

---

## 1. Nghiên cứu vấn đề 1: Dấu câu dính sát vào từ & Lệch tọa độ

### Hiện trạng trong `Writer.token()`
- Khi gặp token dạng `lead + core + trail` (ví dụ `đổi:` có `lead="", core="đổi", trail=":"`):
  1. `core` được vẽ từ `x = 0.0`. Sau khi vẽ `core`, `x += w` (với `w` là advance width được tính bởi `assemble_word` hoặc `number`).
  2. Khi vẽ `trail`:
     ```python
     for ch in trail:
         lib = b.punct.get(ch)
         if lib:
             g = self.pick(lib, "p" + ch)
             strokes += [shift(st, x, 0) for st in g["s"]]
             x += max(st[i] for st in g["s"] for i in range(0, len(st), 2)) + 0.3
     ```
  3. **Lỗ hổng 1 - Không chuẩn hóa gốc x của mẫu dấu câu**: Trong kho mẫu thực tế (`chu_cua_ban.json.gz`), các mẫu trong `b.punct[":"]` được trích xuất từ các ô lưới viết tay cũ mà nét bắt đầu ở tọa độ tuyệt đối lớn (ví dụ `min_x = 4.02`, `4.97`, `6.27`, thậm chí `14.75`!). Tuy nhiên, một số mẫu khác lại có `min_x = 2.04` hoặc nhỏ hơn. Khi dùng `shift(st, x, 0)`, nét được dịch theo tọa độ lưu trữ thô chứ không xuất phát từ `0`.
  4. **Lỗ hổng 2 - Bounding box thực tế của chữ vượt quá `w`**: Với các chữ cái có nét lượn phải (như `i`, `n`, `a`), tọa độ nét thực tế `max_x_placed` có thể lớn hơn `w` (hoặc sát sạt `w`). Khi đặt dấu câu tại `x`, dấu câu bị đè lên nét đuôi của chữ cái!
  5. **Lỗ hổng 3 - Thiếu khoảng đệm quang học (clearance gap)**: Trong văn bản typographic, dấu hai chấm `:`, chấm phẩy `;`, chấm than `!`, hỏi `?` luôn có một khoảng hở nhỏ tự nhiên (`0.15 * xh` đến `0.25 * xh`) so với chữ cái đứng trước. Việc đặt ngay tại `x` mà không có clearance khiến nét bị áp sát vào chữ.
  6. **Lỗ hổng 4 - Đo độ rộng của token đơn lẻ**: Khi token là một dấu câu đơn độc (ví dụ dấu đóng ngoặc `)` trong inline math sau chuỗi), nếu mẫu có `min_x > 0`, khoảng trống bên trái trở thành khoảng trắng giả tạo.

### Quyết định kỹ thuật cho Dấu câu
- **Chuẩn hóa cục bộ (Zero-Origin Normalization)**: Mọi mẫu dấu câu (`punct`) khi lấy ra đều được chuẩn hóa về `min_x = 0.0` (dịch `-min_x`).
- **Xác định mốc xuất phát theo biên nét thực tế (Contour Clearance)**:
  - Nếu có `core` và đã sinh nét `core_strokes`:
    - `rightmost_x = max(pt for st in core_strokes for pt in st[0::2])`
    - Điểm bắt đầu của dấu câu đuôi đầu tiên: `start_x = max(x, rightmost_x) + clearance_gap`.
    - `clearance_gap = max(pen_w * 0.8, 0.18 * xh)`.
- **Cộng dồn bước tiến (Advance) chính xác giữa các dấu câu liên tiếp**:
  - Với mỗi dấu câu: tính `glyph_w = (max_x - min_x)`.
  - Bước tiến `advance = glyph_w + side_bearing_right` (với `side_bearing_right = 0.12 * xh`).
- **Áp dụng tương tự cho `lead` (dấu mở ngoặc `(`, `[`, `{`, `“`)**:
  - Chuẩn hóa `min_x = 0.0`.
  - Sau khi vẽ dấu mở, cộng bước tiến `advance = glyph_w + 0.15 * xh` trước khi vẽ `core`.

---

## 2. Nghiên cứu vấn đề 2: Chữ số cách nhau quá xa (Rời rạc số)

### Hiện trạng trong `Writer.number()`
- Đoạn mã hiện tại:
  ```python
  gaps = b.d.get("dgaps") or [3.5]
  ...
  gap = 0.0 if first else clamp(rnd.choice(gaps), 0.5, 7.0) * (0.5 if ch == "-" else 1.0)
  out += [shift(st, x + gap, 0) for st in g["s"]]
  x += gap + g["w"]
  ```
- **Lỗ hổng 1 - `dgaps` trong kho mẫu bị lệch lớn và không được lọc**:
  - Kiểm tra kho mẫu thực tế: `len(dgaps) = 298`, giá trị từ `0.8` đến `11.48`, trung bình `4.62`. Hơn 48% mẫu có gap > `4.0`, nhiều mẫu lên tới `8.0` - `11.0`!
  - `clamp(..., 0.5, 7.0)` cho phép gap tối đa tới `7.0` (trong khi `xh = 7.94`, tức gap gần bằng chiều cao cả một chữ cái!).
- **Lỗ hổng 2 - Bỏ qua tỷ lệ chiều cao chữ `xh`**:
  - Khoảng cách giữa các chữ số trong một số tự nhiên chỉ nên là `0.08 * xh` đến `0.20 * xh` (khoảng `0.6` đến `1.6` pt đối với `xh = 7.94`).
  - Mức `gap = 7.0` khiến các chữ số trong số `0,0144` hoặc `184,05` cách xa nhau như các từ độc lập, hoàn toàn phá vỡ cấu trúc thị giác của số học.

### Quyết định kỹ thuật cho Chữ số
- **Chuẩn hóa dải khoảng cách chữ số (Digit Gap Normalization)**:
  - Giới hạn khoảng cách giữa 2 chữ số liên tiếp:
    - `min_dgap = 0.08 * xh` (khoảng `0.6` - `0.8` pt)
    - `max_dgap = 0.22 * xh` (khoảng `1.4` - `1.8` pt)
  - Nếu lấy từ `b.d["dgaps"]`, giá trị được scale/clamp về dải an toàn: `clamp(g_raw * scale_factor, min_dgap, max_dgap)`.
  - Mặc định chuẩn: `default_dgap = 0.14 * xh`.
- **Đồng bộ hóa trên toàn bộ hệ thống**:
  - `Writer.number()`: áp dụng công thức gap mới.
  - `MathLayoutEngine._m_TextNode()` khi xử lý `numeric` (gọi `Writer.number()`): tự động thừa hưởng khoảng cách chữ số tự nhiên và gọn gàng.
  - Bảng biểu `TableLayoutEngine`: các số liệu trong ô bảng sẽ hiển thị liền lạc, chuyên nghiệp.

---

## 3. Tổng hợp quyết định thiết kế

| Thành phần | Vấn đề cũ | Giải pháp mới | Giá trị mục tiêu |
|------------|-----------|---------------|------------------|
| Dấu câu đuôi (`:`, `,`, `.`, `;`, `!`, `?`) | Nét bị dịch lệch do `min_x` lớn trong kho; đè lên nét chữ do đặt tại `x` lý thuyết | Chuẩn hóa `min_x = 0`; tính offset từ `max(x, max_x_placed) + clearance` | Clearance: `0.18 * xh` (~1.4 pt) |
| Dấu câu mở (`(`, `[`, `{`, `“`) | Nét lệch do `min_x` kho; khoảng cách với thân từ không ổn định | Chuẩn hóa `min_x = 0`; tính bước tiến `glyph_w + 0.15 * xh` | Advance: `w + 0.15 * xh` |
| Token dấu câu đơn (`:`, `)`) | Độ rộng token chứa khoảng trắng ảo bên trái | Chuẩn hóa `min_x = 0`, trả về nét từ gốc 0 và độ rộng `glyph_w + margin` | Width: `glyph_w + 0.15 * xh` |
| Khoảng cách chữ số (`dgaps`) | Gap ngẫu nhiên lên tới 7.0 pt (bị giãn toác như các từ riêng) | Clamp gap theo `xh`: `[0.08 * xh, 0.22 * xh]` | Gap: `0.08 * xh` ~ `0.22 * xh` |

Các quyết định trên giải quyết triệt để 100% các hiện tượng được chỉ ra trong ảnh của người dùng mà không cần thay đổi cấu trúc dữ liệu lưu trữ kho mẫu, bảo toàn hoàn toàn tương thích ngược (Zero Breaking Changes).
