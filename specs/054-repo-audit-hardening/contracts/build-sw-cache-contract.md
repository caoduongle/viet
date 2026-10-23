# Contract: Chuẩn Hóa Khóa Cache Service Worker và An Toàn Thư Mục Build

**Feature**: [054-repo-audit-hardening](../spec.md)  
**Target Module**: `scripts/build_web.py`  

---

## 1. Mục đích
Quy định thuật toán tính toán khóa cache Service Worker tái lập và chính sách bảo vệ an toàn thư mục phân phối khi thực thi script đóng gói PWA.

## 2. Đặc tả Giao diện

```python
def generate_sw_js(dist_dir: Path) -> None:
    """Tạo tệp sw.js với CACHE_NAME có tính tái lập và danh sách precache/lazy chuẩn tắc."""

def prepare_dist_dir(dist_dir: Path, force_clean: bool = False) -> None:
    """Kiểm tra an toàn đường dẫn và dọn sạch thư mục dist.
    
    Từ chối xóa thư mục ngoài repo nếu không rỗng và thiếu cờ force_clean."""
```

## 3. Quy tắc Tính toán Khóa Cache Tái lập

1. **Thu thập danh sách tệp**:
   - Quét đệ quy tất cả các tệp trong `dist_dir` (ngoại trừ chính tệp `sw.js`).
   - Chuẩn hóa đường dẫn tương đối theo dạng POSIX: `rel_path = fpath.relative_to(dist_dir).as_posix()`.
2. **Sắp xếp thứ tự danh mục**:
   - Danh sách tệp bắt buộc phải được sắp xếp tăng dần theo `rel_path` trước khi tiến hành băm.
3. **Cơ chế băm danh mục**:
   - Đối với từng tệp `(rel_path, sha256_file(fpath))`:
     `hasher.update(f"{rel_path}:{sha}\n".encode("utf-8"))`
   - Khóa cache có định dạng: `chuviettay-cache-{hasher.hexdigest()[:12]}`.
4. **Bảo đảm tính tái lập**:
   - Hai lần build trên cùng một cây mã nguồn và môi trường tệp tin PHẢI cho ra cùng một khóa `CACHE_NAME` và nội dung `sw.js` giống hệt nhau.

## 4. Chính sách An toàn Thư mục Đầu ra

1. **Thư mục mặc định (`webapp/dist`)**: Tự động dọn dẹp và tái tạo.
2. **Thư mục tùy ý khác**:
   - Nếu chưa tồn tại hoặc là thư mục rỗng: Cho phép tạo/sử dụng.
   - Nếu tồn tại và có tệp `.chuviettay_build_dist`: Được coi là thư mục build cũ, cho phép xóa và tái tạo.
   - Nếu tồn tại, không rỗng, và không có marker `.chuviettay_build_dist`:
     - Nếu `force_clean is True`: Cho phép xóa.
     - Nếu `force_clean is False`: Báo lỗi an toàn và dừng chương trình (`sys.exit`), bảo vệ 100% dữ liệu.
