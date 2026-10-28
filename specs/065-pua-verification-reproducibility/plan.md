# Implementation Plan: Đo lường trực tiếp bộ nhớ PUA và kịch bản tái lập benchmark độc lập

**Branch**: `065-pua-verification-reproducibility` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/065-pua-verification-reproducibility/spec.md`

---

## Summary

Feature 065 hoàn thiện hai điểm cải thiện P3 được nêu trong đợt đánh giá commit `a8c167d`:
1. **Kiểm thử trực tiếp số lượng phần tử và đo lường bộ nhớ đỉnh**: Tách hàm nội bộ `MarkdownImporter._collect_used_pua_codepoints(text) -> set[int]` để kiểm thử trực tiếp số phần tử của `used_cps` (khẳng định chỉ chứa đúng điểm mã PUA mà không chứa ký tự ngoài dải) và bổ sung bài kiểm thử định lượng mức tăng bộ nhớ đỉnh phân bổ bằng `tracemalloc` ($\le 50\text{KB}$).
2. **Kịch bản benchmark độc lập có khả năng tái lập**: Xây dựng script `scripts/benchmark_pua_memory.py` sử dụng thuần thư viện chuẩn của Python, tự động ghi nhận thông tin môi trường thực thi và đo lường so sánh định lượng cả 3 phương án: Baseline `set(text)`, Regex `findall()` và Regex `finditer()` có thoát sớm trên cả tài liệu đa ngữ lẫn kịch bản đối kháng 100.000 ký tự PUA.
3. **Phân định rõ ràng trong tài liệu kỹ thuật**: Làm rõ sự khác biệt giữa `finditer` (lặp luồng đối sánh, không sinh list trung gian) và `findall` (sinh list trung gian lớn khi gặp nhiều PUA) trong `research.md`, cung cấp đầy đủ thông tin môi trường đo đạc.

---

## Technical Context

**Language/Version**: Python 3.10+ (Đã kiểm chứng tương thích CPython 3.10, 3.12, 3.13, 3.14 và Pyodide 314.0.7 / WebAssembly).

**Primary Dependencies**: Không thêm bất kỳ thư viện bên ngoài mới nào. Toàn bộ giải pháp sử dụng thư viện chuẩn của Python (`re`, `tracemalloc`, `time`, `platform`, `sys`, `gc`).

**Storage**: Bộ nhớ RAM trong tiến trình xử lý văn bản (không có cơ sở dữ liệu hay lưu trữ file mới).

**Testing**: `pytest` kết hợp module chuẩn `tracemalloc` để đo lường bộ nhớ đỉnh.

**Target Platform**: Desktop (Windows, macOS, Linux) & Web Browser Client (Pyodide WebAssembly).

**Project Type**: Thư viện lõi xử lý văn bản Markdown (`chuviettay/importer/markdown_importer.py`) và kịch bản hỗ trợ kiểm chứng (`scripts/benchmark_pua_memory.py`).

**Performance Goals**:
- Tốc độ trích xuất điểm mã PUA trên văn bản 1MB đạt dưới 10ms.
- Bộ nhớ phụ cho tập hợp PUA bị chặn cứng $\le 6.400$ số nguyên (dưới 50KB RAM).
- Kịch bản benchmark độc lập chạy hoàn tất trong dưới 15 giây.

**Constraints**:
- Giữ nguyên 100% tính tương thích ngược và chữ ký của hàm công khai `_choose_fake_close_placeholder(text)`.
- Không tạo thêm phụ thuộc bên ngoài vào `requirements.txt` hay `requirements-dev.txt`.
- Không ảnh hưởng đến các bất biến xử lý công thức toán LaTeX và dấu đóng giả blockquote.

**Scale/Scope**: Giới hạn trong 3 tệp chính:
- `chuviettay/importer/markdown_importer.py`: Bổ sung phương thức `_collect_used_pua_codepoints`.
- `tests/test_markdown_math_block_isolation.py`: Bổ sung kiểm thử đơn vị cho hàm mới và kiểm thử `tracemalloc`.
- `scripts/benchmark_pua_memory.py`: Kịch bản benchmark độc lập mới.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp (Constitution Principle) | Đánh giá Tuân thủ | Ghi chú & Biện minh |
| :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | **PASS** | Tách hàm `_collect_used_pua_codepoints` giúp mã nguồn rõ ràng, tuân thủ Single Responsibility, có docstring giải thích chi tiết cơ chế bộ nhớ. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Tận dụng trực tiếp biểu thức chính quy sẵn có `_PUA_RE`, không xây dựng cấu trúc abstraction phức tạp, không thêm thư viện thứ ba. |
| **III. Comprehensive Automated Testing** | **PASS** | Bổ sung kiểm thử đơn vị đo lường trực tiếp kích thước tập hợp và kiểm thử đo lường bộ nhớ đỉnh `tracemalloc` chạy tự động trong CI. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Hàm `_collect_used_pua_codepoints` gắn kết chặt chẽ với nhiệm vụ trích xuất điểm mã PUA của importer Markdown, tách rời khỏi logic chọn ký tự thay thế. |
| **CI & Quality Verification Workflow** | **PASS** | Toàn bộ kiểm thử unit, integration, linting và web client build đều được xác thực trong CI. |

---

## Project Structure

### Documentation (this feature)

```text
specs/065-pua-verification-reproducibility/
├── plan.md              # Kế hoạch triển khai kiến trúc chi tiết
├── research.md          # Phân tích thực nghiệm, so sánh 3 phương án và môi trường đo
├── data-model.md        # Mô hình dữ liệu used_cps, BenchmarkMetricReport và các bất biến
├── quickstart.md        # Hướng dẫn kiểm chứng từng bước
├── contracts/
│   └── pua-verification-contract.md  # Hợp đồng giao diện Python và CLI benchmark
├── checklists/
│   └── requirements.md  # Danh mục thẩm định chất lượng đặc tả
└── tasks.md             # Danh sách nhiệm vụ chi tiết (sẽ sinh bởi /speckit-tasks)
```

### Source Code (repository root)

```text
chuviettay/importer/
└── markdown_importer.py              # Bổ sung _collect_used_pua_codepoints, gọi từ _choose_fake_close_placeholder

tests/
└── test_markdown_math_block_isolation.py  # Thêm test_pua_codepoint_collection_direct_and_bounded & tracemalloc

scripts/
└── benchmark_pua_memory.py           # Kịch bản benchmark độc lập, tái lập số liệu hiệu năng
```

**Structure Decision**: Giữ nguyên kiến trúc module hiện tại của repository. Chỉ tách nhỏ một helper method trong `markdown_importer.py`, bổ sung bài test trong `tests/` và thêm một công cụ hỗ trợ tái lập trong `scripts/`.

---

## Complexity Tracking

> Không có vi phạm kiến trúc nào cần biện minh. Toàn bộ thiết kế tuân thủ nghiêm ngặt nguyên lý KISS, YAGNI và bảo vệ tối đa tính ổn định của hệ thống.
