# Data Model & Configuration Schemas: Python Version Metadata

**Feature**: `057-fix-ci-python-version`  
**Date**: 2026-10-27  
**Status**: Completed  

---

## 1. Entities & Configuration Formats

### 1.1 PythonVersionFile (`.python-version`)

Tệp cấu hình môi trường chuẩn quy định phiên bản Python mặc định của repository.

```text
Format: Plain text (UTF-8, LF)
Pattern: ^\d+\.\d+$
Current Valid Value: "3.13"
```

- **Ràng buộc**:
  - Không chứa khoảng trắng thừa hoặc ký tự dòng trống ở đầu.
  - Phải là định dạng dòng phiên bản thứ cấp (Major.Minor), không ghim cứng bản vá vi mô (Patch).

---

### 1.2 RenderEnvironmentVariable (`render.yaml`)

Cấu hình khai báo biến môi trường cho dịch vụ Render Static Site.

```yaml
envVars:
  - key: PYTHON_VERSION
    value: "3.13"
```

- **Ràng buộc**:
  - Giá trị biến `PYTHON_VERSION` phải tương thích với giá trị trong `.python-version`.

---

## 2. Decision & Resolution Flow

```mermaid
flowchart TD
    Start["actions/setup-python@v5 reads '.python-version'"] --> Parse["Đọc chuỗi phiên bản: '3.13'"]
    Parse --> CheckLocal{"Có Python 3.13.x trong Local Cache không?"}
    CheckLocal -- Có --> UseCache["Sử dụng bản 3.13.x mới nhất từ Local Cache (< 1s)"]
    CheckLocal -- Không --> QueryManifest["Truy vấn versions-manifest.json"]
    QueryManifest --> FindMatch{"Tìm thấy bản vá 3.13.* tương thích cho Ubuntu runner?"}
    FindMatch -- Có --> DownloadBinary["Tải bản nhị phân dựng sẵn và thiết lập PATH"]
    FindMatch -- Không --> Error["Error (Không xảy ra vì 3.13 luôn được hỗ trợ)"]
    UseCache --> SetupSuccess["Môi trường Python sẵn sàng -> Chạy tests/lint"]
    DownloadBinary --> SetupSuccess
```
