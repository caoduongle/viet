# Interface Contract: Typography Spacing & Punctuation Alignment

**Feature**: `030-punctuation-spacing-alignment`  
**Date**: 2026-10-07

## 1. Writer Module Contract (`chuviettay/model/writer.py`)

### `Writer.token(tok: str) -> tuple[list[Stroke], float, list[str]]`
- **Đầu vào**: `tok` (chuỗi ký tự của 1 token, ví dụ: `"đổi:"`, `"(bằng"`, `":"`, `")"`, `"184,05"`, `"181"`).
- **Hành vi**:
  1. Với token đơn ký tự là dấu câu (`len(tok) == 1` và `tok in b.punct`):
     - Chuẩn hóa tọa độ x về gốc `0.0`.
     - Trả về nét xuất phát từ `0.0` và độ rộng thực tế `bbox_w + side_bearing` (thay vì mang theo khoảng trống ảo bên trái từ ô mẫu cũ).
  2. Với token hỗn hợp (`lead + core + trail`):
     - `lead`: Chuẩn hóa về gốc 0, duy trì khoảng đệm an toàn `0.15 * xh` trước khi vẽ `core`.
     - `core`: Ghép thân từ hoặc số.
     - `trail`: Điểm bắt đầu tính từ `max(core_w, max_x_placed) + clearance_gap`, trong đó `clearance_gap = max(pen_w * 0.8, 0.18 * xh)` đối với dấu câu đầu tiên.
- **Đầu ra**:
  - `strokes`: Danh sách nét đã dịch vị trí tuyệt đối trong hệ tọa độ token (bắt đầu từ `0.0`).
  - `total_width`: Tổng độ rộng tiến của toàn bộ token.
  - `missing`: Danh sách ký tự thiếu mẫu.
- **Bất biến**:
  - Không có bất kỳ nét nào của `trail` bị thụt lùi đè lên nét của `core` (`dist(core, trail) >= pen_w * 0.5`).
  - Điểm cực tiểu `min_x` của toàn bộ nét trong token phải `>= 0.0`.

### `Writer.number(s: str) -> tuple[list[Stroke], float, list[str]]`
- **Đầu vào**: `s` (chuỗi số khớp `NUMRE`, ví dụ: `"181"`, `"0,12"`, `"-228"`, `"00144"`).
- **Hành vi**:
  - Khoảng cách giữa 2 chữ số liên tiếp `dgap` luôn bị chặn chặt chẽ trong khoảng `[0.08 * xh, 0.22 * xh]`.
  - Dấu phẩy hoặc chấm ngăn cách: được chuẩn hóa gốc `0.0` và đặt cân đối ngay sau chữ số đứng trước với khoảng đệm `0.10 * xh`.
- **Đầu ra**:
  - `strokes`: Danh sách nét của chuỗi số.
  - `total_width`: Độ rộng của chuỗi số.
  - `missing`: Danh sách ký tự số/dấu thiếu mẫu.
- **Bất biến**:
  - Khoảng cách giữa tâm/biên 2 chữ số liên tiếp không bao giờ vượt quá `0.25 * xh + max(w1, w2)`.

---

## 2. Layout Engine Invariant Contract (`chuviettay/layout/engine.py` & `math_layout.py`)

- Khi `MathLayoutEngine` render `TextNode(kind='num')`, việc gọi qua `Writer.number()` bảo đảm các con số toán học có kích thước khoảng cách đồng nhất với số trong văn bản thường.
- Không gây phá vỡ định dạng bảng biểu `TableLayoutEngine`: độ rộng cell và căn lề cột của bảng giữ nguyên tính cân đối, chữ số hiển thị gọn gàng trong ô.
