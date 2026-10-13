# Implementation Plan: Củng cố và xử lý các vấn đề sau rà soát bản Web-only (Post-Review Hardening)

**Branch**: `039-post-review-hardening` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/039-post-review-hardening/spec.md`

---

## Summary

Triển khai giải pháp kỹ thuật toàn diện nhằm xử lý 5 nhóm vấn đề còn tồn đọng sau cuộc rà soát commit `46467eb`:
1. **Phân định rõ phạm vi DOCX trên Web-only (P1 - Q1: Option A)**: Xác định rõ Web Client chỉ hỗ trợ phương thức Content-First Import (chuyển đổi văn bản, bảng biểu, công thức sang Markdown); cập nhật giao diện người dùng và `README.md` loại bỏ cam kết giữ nguyên toạ độ in Word (Fidelity Layout); đánh dấu module `chuviettay/fidelity/` là legacy/archive.
2. **Chuẩn hóa khóa RNG Hình học theo `token_id` và loại nội dung (P2)**: Tạo không gian tên khóa phân biệt (`text:`, `sym:`, `cell:`) trong `RenderItem.token_id`, sử dụng trực tiếp `token_id` trong `_render_text_line()` để chống va chạm giữa các khối nội dung khác nhau.
3. **Độc lập hóa hạt giống cho công thức toán học lặp lại (P2)**: Đưa bộ đếm số lần xuất hiện `occurrence` vào hàm sinh seed của `MathInline` và `MathBlock` trong `DocumentLayoutEngine`, giúp các công thức giống nhau có nét viết tay đa dạng tự nhiên mà vẫn đảm bảo tính bất biến khi chèn từ phía trước (Prepend Invariance).
4. **Đồng bộ hóa metadata phiên bản toàn diện (P2 - Q2: Option A)**: Thống nhất nguồn phiên bản chính duy nhất là `2.1.0` trên toàn bộ dự án (`pyproject.toml`, `package.json`, `chuviettay/__init__.py`, `CHANGELOG.md`, `version.json`), cập nhật `scripts/build_web.py` nạp động phiên bản và bổ sung bài kiểm thử tự động `tests/test_version_metadata.py`.
5. **Củng cố hợp đồng dữ liệu `RenderItem` (P3)**: Bổ sung hỗ trợ thao tác cắt lát `slice` (ví dụ `item[:3]`, `item[1:4]`) và chỉ số âm trong `RenderItem.__getitem__()`, khớp 100% với docstring và quy ước tuần tự Python.

---

## Technical Context

**Language/Version**: Python 3.10+ (Lõi xử lý & Pyodide 314.0.7), JavaScript (ES Modules), HTML5 / CSS3  
**Primary Dependencies**: Standard Library (`hashlib`, `math`, `secrets`, `random`, `dataclasses`). **Zero runtime external dependencies** cho Core Engine. Phụ thuộc tài liệu: `python-docx>=1.1.0`, `markdown-it-py>=3.0.0`, `mdit-py-plugins>=0.4.0`.  
**Storage**: Trình duyệt `IndexedDB` (lưu kho mẫu đang kích hoạt `active_bank`), xuất/nhập tệp `.json.gz` (Schema v3).  
**Testing**: `pytest>=8.0.0`, `pytest-timeout>=2.3.1`, `playwright>=1.40.0` (E2E), `node --test` (JS unit tests).  
**Target Platform**: Web Client chạy trên trình duyệt hiện đại (Chrome, Edge, Firefox, Safari) thông qua WebAssembly / Pyodide.  
**Project Type**: Static Web Application / Typography & Layout Engine.  
**Performance Goals**: Quá trình băm khóa RNG dưới microsecond; thời gian thực thi toàn bộ test suite cục bộ dưới 45 giây; thời gian build web tĩnh dưới 5 giây.  
**Constraints**:
- Duy trì 100% tính bất biến Prepend Invariance cho chế độ `stable_variants=True`.
- Không làm thay đổi hash kết xuất khi `stable_variants=False` (`test_golden_master_real_path.py` phải giữ nguyên).
- Hỗ trợ cắt lát `item[:3]` trên `RenderItem` mà không làm giảm hiệu năng truy cập số nguyên `item[0]`.  
**Scale/Scope**: Tác động trực tiếp đến 4 module cốt lõi (`chuviettay/layout/engine.py`, `chuviettay/fidelity/__init__.py`, `scripts/build_web.py`, `webapp/js/write.js`), tài liệu (`README.md`), và 2 tệp cấu hình (`pyproject.toml`, `package.json`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến chương | Đánh giá | Ghi chú cụ thể |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | **PASS** | `RenderItem` được sửa lỗi không hỗ trợ slice, bảo vệ tính toàn vẹn của hợp đồng. Khóa `ScopedRNG` được phân chia không gian tên tường minh (`text:`, `sym:`, `cell:`). Toàn bộ phiên bản được thống nhất về một nguồn duy nhất `2.1.0`. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Tận dụng cơ chế `tuple(self)[idx]` có sẵn trong Python cho slice mà không cần thêm thư viện phức tạp. Đánh dấu `fidelity/` là legacy, không xây dựng cầu nối COM phức tạp trên trình duyệt. |
| **III. Comprehensive Automated Testing** | **PASS** | Bổ sung đầy đủ kiểm thử đơn vị cho `RenderItem` slice, kiểm thử biến thể toán học lặp lại, kiểm thử độc lập khóa RNG giữa các khối, và kiểm thử tính nhất quán của metadata phiên bản. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Tách bạch rõ ràng ranh giới nhập dữ liệu của Web Client (Content-First) với module lưu trữ Fidelity. `RenderItem` giữ vai trò cấu trúc dữ liệu hiển thị nội bộ độc lập. |
| **Quality Gates & CI Verification** | **PASS** | Xác nhận 100% test suite lõi (1.209+ tests), kiểm thử kiến trúc cấm Tkinter/Desktop, JS unit tests, và linter Ruff đều vượt qua kiểm tra tự động. |

*Kết luận*: **100% GATES PASS.** Không có bất kỳ vi phạm nào cần miễn trừ.

---

## Project Structure

### Documentation (this feature)

```text
specs/039-post-review-hardening/
├── spec.md                  # Đặc tả tính năng và yêu cầu người dùng
├── plan.md                  # Kế hoạch triển khai chi tiết này
├── research.md              # Phase 0: Phân tích kỹ thuật và quyết định thiết kế
├── data-model.md            # Phase 1: Mô hình thực thể và quy ước khóa ScopedRNG
├── quickstart.md            # Phase 1: Hướng dẫn kiểm chứng nhanh độc lập
├── contracts/               # Phase 1: Các hợp đồng ràng buộc giao diện
│   ├── rng-keying-contract.md
│   ├── release-metadata-contract.md
│   └── docx-web-boundary-contract.md
└── checklists/
    └── requirements.md      # Bảng kiểm tra chất lượng đặc tả
```

### Source Code Changes (repository root)

```text
chuviettay/
├── __init__.py              # Giữ nguyên __version__ = "2.1.0" làm nguồn chuẩn
├── layout/
│   └── engine.py            # Hỗ trợ slice trong RenderItem; khóa token_id có tiền tố; math occurrence
└── fidelity/
    └── __init__.py          # Thêm docstring cảnh báo legacy / archive code

scripts/
└── build_web.py             # Đọc động version từ chuviettay.__version__ khi sinh version.json

webapp/
├── index.html               # Cập nhật thông điệp nhập DOCX (Content-First)
└── js/write.js              # Cập nhật thông báo hướng dẫn khi người dùng mở tệp DOCX

pyproject.toml               # Nâng version = "2.1.0"
package.json                 # Nâng version = "2.1.0"
README.md                    # Cập nhật mô tả DOCX và định hướng Web-only

tests/
├── test_render_item.py      # Kiểm thử mới: slice indexing & tuple unpacking trên RenderItem
├── test_version_metadata.py # Kiểm thử mới: xác minh đồng bộ phiên bản trên toàn bộ tệp
└── test_stable_variants.py  # Bổ sung kiểm thử: math lặp lại có biến thể riêng; phân biệt khối RNG
```

---

## Complexity Tracking

> **Không có vi phạm Hiến chương nào cần theo dõi.** Các giải pháp được thiết kế theo đúng nguyên tắc KISS, tận dụng tối đa cơ sở hạ tầng hiện có của dự án.
