# Quickstart & Verification Guide: Khắc Phục Lỗi Xóa Hàng Loạt Web Client

**Feature Branch**: `specs/029-fix-batch-delete-refresh`
**Date**: 2026-10-07

## 1. Mục đích
Hướng dẫn các bước chạy kiểm tra và xác thực tính năng xóa hàng loạt trên Web Client, đảm bảo không còn lỗi `refreshBankTab is not defined`.

---

## 2. Các Bước Kiểm Chứng Tự Động (Automated Verification)

### Bước 1: Kiểm tra cú pháp và loại trừ tham chiếu lỗi
Chạy lệnh tìm kiếm trong toàn bộ mã nguồn để đảm bảo chuỗi `refreshBankTab` đã bị loại bỏ 100%:
```powershell
Get-ChildItem -Path webapp -Recurse | Select-String "refreshBankTab"
# Kỳ vọng: Không trả về bất kỳ kết quả nào.
```

### Bước 2: Tái xây dựng gói Web Client phân phối
Chạy script build web để đồng bộ hóa mã nguồn `webapp/js/` sang `webapp/dist/`:
```powershell
py -3.12 scripts/build_web.py
# Kỳ vọng: Hoàn tất build và cập nhật hash cache thành công.
```

### Bước 3: Chạy Kiểm thử Playwright E2E cho Tab Kho Mẫu
Chạy kịch bản kiểm thử E2E của tab kho mẫu bao gồm thao tác xóa hàng loạt:
```powershell
npx playwright test tests/e2e/bank.spec.ts
# Kỳ vọng: 1 passed (toàn bộ các kịch bản kiểm tra giao diện, chọn và xóa đều thành công).
```

### Bước 4: Kiểm tra Linter toàn diện
```powershell
ruff check .
# Kỳ vọng: All checks passed!
```

---

## 3. Các Bước Kiểm Chứng Thủ Công (Manual Verification)

1. Khởi động máy chủ tĩnh:
   ```powershell
   node scripts/serve.mjs
   ```
2. Mở trình duyệt tại `http://localhost:8000`.
3. Chuyển sang tab **Kho mẫu**.
4. Tick chọn checkbox "Chọn tất cả hiển thị" hoặc tick chọn một số thẻ ký tự.
5. Bấm nút màu đỏ **"Xoá đã chọn (N)"**.
6. Bấm "OK" trên hộp thoại xác nhận.
7. **Quan sát**:
   - Không có hộp thoại lỗi `Lỗi khi xoá hàng loạt: refreshBankTab is not defined`.
   - Các thẻ đã chọn biến mất ngay lập tức.
   - Thanh chọn hàng loạt được làm mới về `(Đã chọn 0)` và nút xóa bị ẩn.
