# Contract: External Dist Directory Data Safety & Artifact Cleanliness

**Feature**: `056-build-safety-and-markdown-hardening`  
**Module**: `scripts/build_web.py`  
**Consumers**: CLI build tool, CI/CD pipelines, static deployment workflows

---

## 1. Specification

### 1.1 Quản lý Thư mục Phân phối (`prepare_dist_dir`)
1. **Thư mục mặc định (`webapp/dist`)**: Được coi là thư mục xuất xưởng chính thức của repository, luôn được tự động làm sạch và tái tạo.
2. **Thư mục ngoài (`--dist <path>`)**:
   - Nếu thư mục chưa tồn tại hoặc là thư mục rỗng: Cho phép tạo và ghi tệp bình thường.
   - Nếu thư mục đang chứa dữ liệu: **BẮT BUỘC** phải có cờ `--force-clean` tại chính lần gọi đó. Nếu không có cờ `--force-clean`, chương trình PHẢI dừng ngay lập tức với lỗi `SystemExit` và in cảnh báo an toàn.
   - Tuyệt đối không xóa thư mục ngoài chỉ dựa trên tệp marker cũ.
3. **Thư mục xuất xưởng sạch**:
   - Không tạo tệp marker `.chuviettay_build_dist` vào trong thư mục `dist_dir`.
   - Thư mục `dist_dir` chỉ chứa các tài nguyên web thực sự phục vụ ứng dụng.

### 1.2 Lọc Thư mục Ẩn trong Service Worker (`generate_sw_js`)
1. Vòng lặp `os.walk(dist_dir)` PHẢI thực hiện cắt tỉa danh sách thư mục con `dirs[:] = [d for d in dirs if not d.startswith('.')]`.
2. Không duyệt vào bất kỳ thư mục con nào bắt đầu bằng dấu chấm (`.internal/`, `.git/`, v.v.).

---

## 2. Test Invariants

1. Thư mục ngoài đã có build cũ, người dùng thêm `user_file.txt`, chạy lại không có `--force-clean`:
   - Ném ngoại lệ `SystemExit`.
   - `user_file.txt` tiếp tục tồn tại nguyên vẹn 100%.
2. Build thành công:
   - `(dist_dir / ".chuviettay_build_dist").exists() == False`.
   - `sw.js` không chứa bất kỳ URL nào có chứa `/.`.
