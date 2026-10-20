# Quickstart & Verification Guide: 052-write-preview-bank-sync

Tài liệu hướng dẫn kiểm thử và xác thực hành vi đồng bộ kho mẫu và kết xuất Tab Viết chữ.

---

## 1. Môi Trường & Điều Kiện Tiên Quyết (Prerequisites)

- Node.js version >= 20.x
- Trình duyệt Chrome / Edge hoặc bộ kiểm thử tự động Playwright
- File kho mẫu kiểm thử: `tests/data/kho_mau_tong_hop.json.gz`

---

## 2. Kịch Bản Kiểm Thử Tự Động (Automated Test Scenarios)

### Kịch bản 1: Kiểm thử vòng đời nạp kho & kết xuất tự động (Unit / Integration Test)
Xác nhận rằng khi ô văn bản có nội dung từ trước, việc hoàn thành `load_bank` sẽ tự động kích hoạt `triggerPreviewImmediate` và xóa bỏ toàn bộ chip thiếu mẫu giả tạo.

**Lệnh chạy**:
```bash
node --test tests/js/write_preview_sync.test.mjs
```

**Kỳ vọng**:
- `test("tự động kích hoạt triggerPreviewImmediate khi load_bank hoàn thành")` -> PASS
- `test("switchTab('write') kích hoạt làm mới bản xem trước khi editor có chữ")` -> PASS
- `test("nhận tín hiệu BANK_SYNCHRONIZED kích hoạt làm mới Tab Viết chữ")` -> PASS

---

### Kịch bản 2: Kiểm thử hồi quy toàn bộ hệ thống Web Client
Bảo đảm các cập nhật trong `app.js` và `write.js` không gây xung đột với các tính năng quản lý kho mẫu và phục hồi Worker đã có:

**Lệnh chạy**:
```bash
npm run test:unit
```

**Kỳ vọng**:
- Toàn bộ các test suite JS (`bank_safety`, `worker_resilience`, `write_preview_sync`...) vượt qua 100%.

---

## 3. Kịch Bản Kiểm Thử Thủ Công Trên Giao Diện (Manual UI Verification)

1. Mở ứng dụng web tại trình duyệt (`http://localhost:8000` hoặc bản chạy trên Render).
2. Dán đoạn văn bản có công thức toán vào Tab Viết chữ (ví dụ nội dung ở Ảnh 1).
3. Đổi số `seed` hoặc nạp kho mẫu mới trong Tab Kho mẫu.
4. Bấm `F5` (Refresh trang).
5. **Xác nhận**:
   - Ngay sau khi trang tải xong và đèn trạng thái chuyển sang 🟢 **Sẵn sàng**, bản xem trước lập tức hiển thị đủ nét viết tay của các chữ cái và chữ số.
   - Hộp "Từ thiếu mẫu trong kho" không còn xuất hiện các chữ cái `n`, `h`, `a`, `0`, `1`...
   - Người dùng không cần phải thực hiện bất kỳ thao tác thủ công nào (như gõ thêm phím hay mở modal đổi seed) để bản xem trước hiển thị bình thường.
