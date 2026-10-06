# Hướng dẫn xác thực nhanh (Quickstart Guide)

**Feature**: `specs/023-write-preview-paper-geometry`
**Date**: 2026-10-06

## 1. Khởi động môi trường thử nghiệm

1. Cài đặt các gói phụ thuộc nếu chưa cài:
   ```bash
   npm install
   ```
2. Build web client:
   ```bash
   python scripts/build_web.py
   ```
3. Khởi động máy chủ phát triển cục bộ:
   ```bash
   node scripts/serve.mjs
   ```
   Máy chủ lắng nghe tại: `http://localhost:8000`

---

## 2. Các kịch bản kiểm tra nghiệm thu (Acceptance Scenarios)

### Kịch bản 1: Đo kích thước giấy ở zoom 100% (Khổ A4)
- Mở `http://localhost:8000` trên trình duyệt Chromium với viewport 1920×1020 và 1366×768.
- Chuyển sang tab "Viết chữ".
- Tải tệp kho mẫu thử: `tests/data/kho_mau_tong_hop.json.gz` qua `#input-welcome-file` hoặc modal nạp kho.
- Nhập một đoạn văn bản vào `#editor-text`.
- Bấm vào nút điều khiển zoom để đặt về 100%.
- Kiểm tra phần tử `.paper-frame` và `#paper-svg-wrapper svg`:
  - Chiều rộng đo được qua `getBoundingClientRect().width` phải xấp xỉ `793.7px` ($\ge 700\text{ px}$, sai lệch $< 2\text{ px}$).
  - Chiều cao đo được xấp xỉ `1122.5px`.
  - Tỷ lệ khung hình chuẩn ~ 1.414.

### Kịch bản 2: Kiểm tra chế độ Fit và co giãn khi thay đổi kích thước cửa sổ
- Bấm nút `Vừa khung` (`#btn-zoom-fit`).
- Kiểm tra phần tử `#preview-stage`:
  - `scrollWidth <= clientWidth` (không xuất hiện thanh cuộn ngang).
  - Giấy hiển thị vừa vặn chiều rộng khung nhìn, có khoảng đệm 2 bên.
- Đổi kích thước viewport từ 1920 sang 1366.
- Kiểm tra giấy tự động co lại cho vừa khung nhìn mới mà không cần bấm lại nút.

### Kịch bản 3: Kiểm tra các mức zoom `−` và `+`
- Bấm nút `+` nhiều lần: nhãn phần trăm tăng lên (110%, 120%, ...), tối đa 300%. Khung xem trước cho phép cuộn ngang và cuộn dọc để xem chi tiết.
- Bấm nút `−` nhiều lần: nhãn phần trăm giảm xuống, tối thiểu 50%.

### Kịch bản 4: Kiểm tra kiểu giấy `lined` vs `ruled`
- Chọn kiểu giấy `lined`: Giấy xuất hiện các đường kẻ ngang và 1 vạch kẻ lề dọc màu đỏ bên trái.
- Chọn kiểu giấy `ruled`: Giấy chỉ có các đường kẻ ngang, không có vạch kẻ lề màu đỏ.

---

## 3. Lệnh chạy kiểm thử tự động

```bash
# Kiểm tra lint / type / unit test nếu có
npm run test:e2e
# Kiểm tra bộ test kiến trúc & unit test Python
pytest -m "not benchmark"
```
