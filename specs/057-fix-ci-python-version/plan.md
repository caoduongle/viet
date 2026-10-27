# Implementation Plan: Chuẩn Hóa Phiên Bản Python Trên CI và Render (057-fix-ci-python-version)

**Branch**: `057-fix-ci-python-version` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/057-fix-ci-python-version/spec.md`

---

## Summary

Kế hoạch này giải quyết dứt điểm lỗi CI `actions/setup-python@v5` không tìm thấy phiên bản `3.13.5` trên Ubuntu runner bằng cách:
1. Chuẩn hóa định dạng phiên bản trong `.python-version` thành `3.13` (minor version), giúp `setup-python` tự động phân giải bản vá tương thích mới nhất có sẵn trong cache/manifest của runner.
2. Đồng bộ hóa biến môi trường `PYTHON_VERSION` trong `render.yaml` thành `3.13`.
3. Bổ sung bài kiểm tra tự động trong `tests/test_version_metadata.py` để bảo đảm `.python-version` luôn tuân thủ chuẩn `Major.Minor`.

---

## Technical Context

**Language/Version**: Python 3.10-3.14 (với `.python-version` chuẩn hóa thành `3.13`), Node.js 20+  
**Primary Dependencies**: `actions/setup-python@v5`, `actions/checkout@v4`  
**Storage**: N/A  
**Testing**: `pytest`, `pytest-timeout`, `ruff`  
**Target Platform**: GitHub Actions CI (`ubuntu-latest`), Render Static Site  
**Project Type**: Web Application / Python Core Library  
**Performance Goals**: Thời gian thiết lập môi trường Python trên CI < 10 giây  
**Constraints**: 0 lỗi phân giải phiên bản trên mọi runner distro  
**Scale/Scope**: `.python-version`, `render.yaml`, `tests/test_version_metadata.py`  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Định dạng `3.13` là chuẩn ngành phổ biến cho `setup-python`, `pyenv`, `uv`, giảm thiểu nợ kỹ thuật ghim cứng phiên bản.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Giải pháp đơn giản, trực diện vào gốc rễ vấn đề, không bổ sung script phức tạp hay dependencies không cần thiết.
- [x] **III. Comprehensive Automated Testing**: Bổ sung unit test xác thực định dạng `.python-version` trong test suite.
- [x] **IV. Loose Coupling & High Cohesion**: Phân định rõ ràng giữa cấu hình CI/deployment và logic mã nguồn ứng dụng.

---

## Project Structure

### Documentation (this feature)

```text
specs/057-fix-ci-python-version/
├── plan.md                                          # Kế hoạch thực hiện tổng thể
├── research.md                                      # Kết quả nghiên cứu kỹ thuật Phase 0
├── data-model.md                                    # Mô hình cấu hình Phase 1
├── quickstart.md                                    # Hướng dẫn xác minh nhanh
└── contracts/                                       # Hợp đồng giao tiếp Phase 1
    └── python-version-contract.md                   # Hợp đồng phiên bản Python
```

### Source Code Layout (affected paths)

```text
.python-version                                      # Đổi 3.13.5 thành 3.13
render.yaml                                          # Đổi PYTHON_VERSION thành 3.13
tests/
└── test_version_metadata.py                         # Thêm test kiểm tra định dạng .python-version
```

**Structure Decision**: Thay đổi trực tiếp các tệp cấu hình tại thư mục gốc và bổ sung kiểm thử vào module metadata hiện có.

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*Không có vi phạm nguyên tắc kiến trúc.*
