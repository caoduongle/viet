# Contract: Product Release Metadata and Version Synchronization

**Contract ID**: `CTR-039-RELEASE-METADATA`  
**Status**: Enforced  
**Applies to**: `pyproject.toml`, `package.json`, `chuviettay/__init__.py`, `CHANGELOG.md`, `scripts/build_web.py`, `webapp/dist/version.json`

---

## 1. Mục đích

Hợp đồng này quy định nguyên tắc Nguồn Thông tin Phiên bản Duy nhất (Single Source of Truth) cho sản phẩm Chữ Viết Tay, đảm bảo loại bỏ tình trạng lệch số phiên bản giữa các tầng công nghệ (Python backend vs. Web frontend) và tránh gây nhầm lẫn khi triển khai hoặc báo cáo lỗi.

---

## 2. Nguồn phiên bản chính (Single Source of Truth)

1. Hằng số `chuviettay.__version__` trong tệp `chuviettay/__init__.py` là nguồn tham chiếu phiên bản duy nhất cho toàn bộ kho mã nguồn.
2. Giá trị phiên bản chuẩn hiện tại: `"2.1.0"`.

---

## 3. Quy tắc Đồng bộ hóa (Synchronization Rules)

| Tệp đích | Vị trí trường | Giá trị yêu cầu | Cơ chế cập nhật |
|---|---|---|---|
| `pyproject.toml` | `[project] version = "..."` | Khớp 100% với `__version__` | Khai báo tĩnh |
| `package.json` | `"version": "..."` | Khớp 100% với `__version__` | Khai báo tĩnh |
| `CHANGELOG.md` | Tiêu đề phiên bản gần nhất (H2) | Chứa số phiên bản `2.1.0` | Nhật ký thay đổi |
| `webapp/dist/version.json` | `"version": "..."` | Khớp 100% với `__version__` | Sinh động bởi `scripts/build_web.py` |

---

## 4. Kiểm định Tự động (Automated Verification)

1. Bài kiểm thử `tests/test_version_metadata.py` được thực thi trong mọi quy trình kiểm tra CI.
2. Bài kiểm thử sẽ thất bại (Fail) ngay lập tức nếu phát hiện bất kỳ sự sai lệch nào giữa các tệp trên.
