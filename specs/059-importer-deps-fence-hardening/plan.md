# Implementation Plan: Bảo toàn tính tùy chọn của phụ thuộc tài liệu và đồng bộ nhận diện khối mã trong bộ nhập Markdown

**Branch**: `059-importer-deps-fence-hardening` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/059-importer-deps-fence-hardening/spec.md`

---

## Summary

Feature 059 giải quyết triệt để 3 vấn đề kỹ thuật được phát hiện sau khi rà soát commit `62a93b7` và bổ sung 3 nhóm kiểm thử phòng vệ:
1. **Bảo toàn tính tùy chọn của thư viện Markdown (P1)**: Loại bỏ câu lệnh `from markdown_it.rules_block.table import escapedSplit` ở cấp module trong `chuviettay/importer/markdown_importer.py` và chuyển vào hàm trợ giúp `_escaped_split_table_row()` chỉ được gọi khi xử lý bảng sau khi đã kiểm tra `require_dependency("markdown_it", ...)`. Đảm bảo môi trường chỉ cài gói lõi (không cài extra `docs`) vẫn nạp được `chuviettay.importer`, `TxtImporter`, `get_importer_for_path(..., format_name="txt")` và controller bình thường, còn tính năng Markdown báo lỗi `OptionalDependencyError` đúng thiết kế.
2. **Xác minh ngữ cảnh trích dẫn (blockquote depth) khi đóng code fence và hỗ trợ khối mã thụt lề trong blockquote (P2)**: Theo dõi độ sâu trích dẫn (`bq_depth`, tức số lượng dấu `>`) của dòng mở code fence; chỉ đóng khối mã khi dòng đóng có cùng `bq_depth` (không đóng sớm trước dòng đóng giả ở cấp sâu hơn như `>> ``` `), hoặc tự đóng khi thoát khỏi khối trích dẫn chứa nó (`line_bq_depth < open_bq_depth`). Đồng thời mở rộng nhận diện khối mã thụt lề sau tiền tố trích dẫn (`>     code`) ở cả hai bước tiền xử lý.
3. **Đồng bộ điều kiện mở/đóng code fence giữa hai bước tiền xử lý (P2)**: Dùng chung các phương thức trợ giúp `_match_bq_prefix()`, `_parse_fence_open()` và `_is_fence_close()` cho cả `_split_code_segments()` và `_isolate_display_math_blocks()`, đảm bảo quy tắc CommonMark (rào chắn mở bằng backtick không được chứa backtick trong chuỗi thông tin phía sau) được áp dụng nhất quán tuyệt đối.
4. **Bổ sung 3 nhóm kiểm thử (Môi trường tối giản, Đối kháng cú pháp Markdown, Hiệu năng đối kháng đa độ dài backtick & dòng dài)**: Kiểm tra toàn diện cả nội dung văn bản sau từng bước tiền xử lý lẫn cấu trúc `Document` IR đầu ra và tỷ lệ thời gian tuyến tính $T(4N)/T(N) \le 6.0$.

---

## Technical Context

**Language/Version**: Python >= 3.10 (CI: Python 3.12, 3.13, 3.14; `.python-version`: `3.13`)

**Primary Dependencies**: Python Standard Library (`re`, `importlib`, `os`), phụ thuộc tùy chọn nhóm `docs` (`markdown-it-py`, `mdit-py-plugins`), `pytest`

**Storage**: N/A (xử lý văn bản trong bộ nhớ)

**Testing**: `pytest` (unit, integration, minimal-environment simulation & adversarial $O(n)$ complexity tests), `node --test` (`npm run test:unit`), `node scripts/test_golden_pyodide.mjs`

**Target Platform**: Môi trường cài đặt gói lõi tối giản (không có `docs` extra), GitHub Actions Ubuntu runners, Browser WebAssembly (Pyodide)

**Project Type**: Document Importer Pipeline & Web Application

**Performance Goals**: Tiền xử lý Markdown (`_split_code_segments`, `_normalize_math_delimiters`, `_isolate_display_math_blocks`, `_sanitize_html`) đạt độ phức tạp tuyến tính $O(n)$ trên cả dữ liệu nhiều độ dài backtick không đóng và dòng dài ($T(4N)/T(N) \le 6.0$).

**Constraints**: Không import bất kỳ thư viện thuộc nhóm tùy chọn `docs` ở cấp module; bảo toàn 100% mã băm SHA-256 cho 8 ca Golden Master; giữ nguyên giao diện công khai của `chuviettay.importer`.

**Scale/Scope**: 2 tệp chính (`chuviettay/importer/markdown_importer.py`, `tests/test_markdown_math_block_isolation.py`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc trong Constitution | Đánh giá Trước Phase 0 | Đánh giá Sau Phase 1 | Ghi chú tuân thủ |
| :--- | :---: | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | PASS | PASS | Hợp nhất logic nhận diện blockquote prefix, mở/đóng fence vào các hàm trợ giúp dùng chung rõ ràng, tránh trùng lặp logic giữa `_split_code_segments()` và `_isolate_display_math_blocks()`. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | PASS | Sửa trực tiếp tại `markdown_importer.py`, không thêm lớp trừu tượng dư thừa hay phụ thuộc mới. |
| **III. Comprehensive Automated Testing** | PASS | PASS | Bổ sung đầy đủ 3 nhóm kiểm thử: môi trường thiếu `markdown-it-py`, đối kháng cú pháp blockquote/fence/indented code, và hiệu năng tuyến tính dữ liệu bất lợi. |
| **IV. Loose Coupling & High Cohesion** | PASS | PASS | Khôi phục sự tách biệt hoàn toàn giữa gói lõi (`TxtImporter`, `base`, controller) và thư viện tùy chọn `markdown-it-py`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/059-importer-deps-fence-hardening/
├── plan.md                                    # Kế hoạch triển khai kỹ thuật (/speckit-plan)
├── research.md                                # Quyết định kỹ thuật Phase 0
├── data-model.md                              # Mô hình trạng thái & phụ thuộc Phase 1
├── quickstart.md                              # Hướng dẫn chạy kiểm chứng nhanh Phase 1
├── contracts/
│   └── importer-and-parser-contract.md        # Hợp đồng phụ thuộc tùy chọn & nhận diện khối mã
└── checklists/
    └── requirements.md                        # Checklist chất lượng đặc tả
```

### Source Code (repository root)

```text
chuviettay/
└── importer/
    ├── __init__.py                            # Giữ nguyên xuất công khai, nạp an toàn không cần markdown-it-py
    ├── base.py                                # Điều phối get_importer_for_path()
    ├── dependency.py                          # Kiểm tra phụ thuộc tùy chọn require_dependency()
    ├── txt_importer.py                        # Bộ nhập văn bản thuần hoạt động độc lập
    └── markdown_importer.py                   # Chuyển escapedSplit vào hàm sau kiểm tra phụ thuộc; đồng bộ fence & blockquote
tests/
└── test_markdown_math_block_isolation.py      # Kiểm thử môi trường tối giản, đối kháng blockquote/fence & hiệu năng O(n)
```

**Structure Decision**: Chỉnh sửa trực tiếp trên `chuviettay/importer/markdown_importer.py` và mở rộng bộ kiểm thử trong `tests/test_markdown_math_block_isolation.py`, giữ nguyên cấu trúc thư mục hiện hữu của dự án.

---

## Complexity Tracking

> Không có vi phạm Constitution Check. Bảng dưới đây để trống theo quy định.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
