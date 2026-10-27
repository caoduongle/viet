# Contract: Python Version Resolution & Compatibility

**Feature**: `057-fix-ci-python-version`  
**Consumers**: GitHub Actions workflows (`.github/workflows/ci.yml`), Render deployment (`render.yaml`), Local development tools (`pyenv`, `uv`, `mise`)

---

## 1. Specification

### 1.1 Tệp `.python-version`
1. Tệp `.python-version` nằm tại thư mục gốc của repository.
2. Nội dung tệp là chuỗi phiên bản dạng `Major.Minor` (ví dụ `3.13`), kết thúc bằng ký tự ngắt dòng.
3. Tuyệt đối không ghim bản vá vi mô (`3.13.x` cụ thể như `3.13.5`) để bảo đảm tính linh hoạt và khả dụng trên mọi runner CI.

### 1.2 Tệp `render.yaml`
1. Biến môi trường `PYTHON_VERSION` trong dịch vụ `chuviettay-web` phải có giá trị là `3.13`.

---

## 2. Test Invariants

1. Tệp `.python-version` tồn tại và nội dung đọc được sau khi strip khớp với biểu thức chính quy `^\d+\.\d+$`.
2. Giá trị trong `.python-version` thuộc danh sách các phiên bản Python được hỗ trợ trong `pyproject.toml` (tối thiểu là `3.10` trở lên, cụ thể là `3.13`).
