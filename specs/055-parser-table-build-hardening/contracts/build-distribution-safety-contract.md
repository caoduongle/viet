# Contract: Build Distribution & Service Worker Cleanliness

**Feature**: `055-parser-table-build-hardening`  
**Module**: `scripts/build_web.py`  
**Consumers**: Service Worker precache (`webapp/dist/sw.js`), static web deployment

---

## 1. Specification

### 1.1 Tệp Định Danh Nội Bộ (.chuviettay_build_dist)
- Tệp `.chuviettay_build_dist` được sinh ra trong `dist_dir` khi `prepare_dist_dir()` hoàn tất nhằm đánh dấu thư mục build hợp lệ cho các lần build kế tiếp.
- Tệp này CHỈ có mục đích nội bộ trong quy trình đóng gói và dọn dẹp thư mục ngoài.

### 1.2 Quy Tắc Loại Trừ Khỏi Gói Phân Phối & Precache
1. Hàm `generate_sw_js(dist_dir)` TUYỆT ĐỐI KHÔNG thu thập tệp `.chuviettay_build_dist` hoặc bất kỳ tệp/thư mục ẩn nào bắt đầu bằng dấu chấm (`.`) vào:
   - Danh sách tệp tính mã băm `CACHE_NAME`.
   - Danh sách mảng nạp trước `PRECACHE_URLS`.
   - Danh sách mảng nạp trễ `OPTIONAL_LAZY_URLS`.
2. Mọi gói nén phân phối (zip) hoặc xuất bản web KHÔNG ĐƯỢC chứa tệp marker nội bộ.

---

## 2. Test Invariants

1. Đọc tệp `sw.js` sinh ra từ bản build:
   - `".chuviettay_build_dist" not in sw_content`.
   - Mọi URL trong `PRECACHE_URLS` và `OPTIONAL_LAZY_URLS` đều không chứa `/.`.
2. Chạy `prepare_dist_dir(external_dir)` nhiều lần:
   - Tệp `.chuviettay_build_dist` tiếp tục phục vụ chính xác chức năng nhận diện an toàn thư mục ngoài mà không ảnh hưởng tới người dùng cuối.
