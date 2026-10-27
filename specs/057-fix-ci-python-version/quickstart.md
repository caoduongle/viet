# Quickstart: Xác Minh Chuẩn Hóa Phiên Bản Python (057-fix-ci-python-version)

Hướng dẫn kiểm tra và xác minh nhanh sau khi cập nhật cấu hình phiên bản Python.

---

## 1. Kiểm tra nội dung tệp cấu hình

```powershell
# Kiểm tra nội dung .python-version
Get-Content .python-version

# Kết quả kỳ vọng:
# 3.13
```

```powershell
# Kiểm tra biến PYTHON_VERSION trong render.yaml
Select-String -Path render.yaml -Pattern "PYTHON_VERSION" -Context 0,1

# Kết quả kỳ vọng:
# value: 3.13
```

---

## 2. Kiểm tra bộ test metadata phiên bản

```powershell
pytest tests/test_version_metadata.py -v
```

*Kết quả kỳ vọng*: Toàn bộ các bài kiểm tra metadata (bao gồm bài test định dạng `.python-version`) đều **PASS**.

---

## 3. Chạy toàn bộ test suite

```powershell
pytest tests/
npm run test:unit
ruff check .
```

*Kết quả kỳ vọng*: 100% tests và linter vượt qua mà không có bất kỳ lỗi nào.
