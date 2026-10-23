# Quickstart Validation Guide: Gia Cố Nền Tảng Kho Mã Nguồn (054-repo-audit-hardening)

**Feature**: [054-repo-audit-hardening](spec.md)  
**Date**: 2026-10-23  

---

## 1. Mục đích
Tài liệu hướng dẫn các kịch bản kiểm thử thực tế và các lệnh xác minh nhanh để chứng minh toàn bộ các mục tiêu gia cố của feature `054-repo-audit-hardening` hoạt động chính xác từ đầu đến cuối.

---

## 2. Chuẩn bị Môi trường

```powershell
# Kích hoạt môi trường ảo Python
.venv\Scripts\Activate.ps1

# Cài đặt hoặc cập nhật dependencies nếu cần
pip install -e .
npm install
```

---

## 3. Các Kịch bản Xác minh (Runnable Validation Scenarios)

### Kịch bản 1: Xác minh Bộ phân tách Markdown bảo vệ Code Fence và Tuyến tính $O(n)$

**Mục tiêu**: Chứng minh `_isolate_display_math_blocks` không biến đổi nội dung code fence (```` ``` ```` và `~~~`) và xử lý tài liệu lớn chứa hàng nghìn dấu `$$` dở dang trong thời gian dưới 100ms.

**Lệnh kiểm thử**:
```powershell
pytest tests/test_markdown_math_block_isolation.py -k "code_fence or unclosed or performance" -v
```

**Kết quả mong đợi**:
- Code fence chứa `prefix:$$x=1$$` giữ nguyên 100% từng ký tự.
- Tài liệu 5,000 dòng có nhiều `$$` chưa đóng xử lý xong ngay lập tức (<100ms), không có độ phức tạp bậc hai.

---

### Kịch bản 2: Xác minh Tính Bất Biến của Document IR khi Dàn Trang

**Mục tiêu**: Chứng minh việc gọi `write_document()` nhiều lần trên cùng một cây `Document` không làm thay đổi các nút `Text` nguồn và không làm lặp văn bản.

**Lệnh kiểm thử**:
```powershell
pytest tests/test_document_pipeline.py -k "immutability" -v
```

**Kết quả mong đợi**:
- Đối tượng `Document` sau 2 lần kết xuất liên tiếp giữ nguyên trạng thái ban đầu, văn bản kết xuất của 2 lần giống hệt nhau 100%.

---

### Kịch bản 3: Xác minh Khóa Cache Service Worker Tái Lập và Nhạy Cảm với Đường Dẫn

**Mục tiêu**: Chứng minh `generate_sw_js` sinh ra khóa cache ổn định và tự động thay đổi khi đổi tên/đường dẫn tệp.

**Lệnh kiểm thử**:
```powershell
pytest tests/test_build_web.py -k "sw_cache or deterministic" -v
```

**Kết quả mong đợi**:
- Hai lần build trên cùng tập tin cho ra cùng một `CACHE_NAME`.
- Thay đổi đường dẫn tệp làm `CACHE_NAME` thay đổi tương ứng.

---

### Kịch bản 4: Xác minh Bảo vệ Thư mục Đích khi Build Web

**Mục tiêu**: Chứng minh `prepare_dist_dir` từ chối xóa thư mục ngoài repo nếu không rỗng và không có cờ `--force-clean`.

**Lệnh kiểm thử**:
```powershell
pytest tests/test_build_web.py -k "prepare_dist_dir_external_safety" -v
```

**Kết quả mong đợi**:
- Gọi script build trỏ vào thư mục ngoài không rỗng ném lỗi an toàn và giữ nguyên 100% dữ liệu trong thư mục đó.

---

### Kịch bản 5: Xác minh Đồng bộ Bản xem trước theo Revision Đơn Điệu

**Mục tiêu**: Chứng minh race condition giữa cập nhật kho và render lỗi không làm mất cờ `isBankDirty`.

**Lệnh kiểm thử**:
```powershell
node --test tests/js/write_preview_sync.test.mjs
```

**Kết quả mong đợi**:
- 100% các ca kiểm thử đồng bộ giao diện và kho mẫu vượt qua cleanly.

---

## 4. Chạy Toàn Bộ Bộ Kiểm Thử Xác Minh Cuối Cùng

```powershell
# 1. Kiểm tra linter
ruff check chuviettay/ tests/ scripts/

# 2. Toàn bộ test suite Python
pytest tests/

# 3. Toàn bộ unit test JavaScript
npm run test:unit

# 4. Đóng gói phân phối Web
python scripts/build_web.py
```
