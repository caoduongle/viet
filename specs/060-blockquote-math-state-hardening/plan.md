# Implementation Plan: Theo dõi độ sâu trích dẫn cho trạng thái khối toán nhiều dòng và gia cố kiểm thử bảo toàn đầu ra Markdown

**Branch**: `060-blockquote-math-state-hardening` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/060-blockquote-math-state-hardening/spec.md`

---

## Summary

Feature 060 giải quyết triệt để điểm còn tồn đọng trong máy trạng thái của bộ cô lập công thức toán và nâng cấp độ chặt của bộ kiểm thử sau đợt rà soát commit `863ea25`:
1. **Theo dõi độ sâu trích dẫn (`math_bq_depth`) cho trạng thái `in_display_math` (P2)**: Lưu độ sâu trích dẫn `math_bq_depth` khi bắt đầu khối toán hiển thị nhiều dòng (`$$`) trong `MarkdownImporter._isolate_display_math_blocks()`. Khi dòng hiện tại có `bq_depth < math_bq_depth` (thoát khỏi khối trích dẫn chứa công thức hoặc gặp dòng trống không có `>`), hệ thống lập tức kết thúc trạng thái `in_display_math`, chèn dòng phân cách chống *lazy continuation* nếu cần và đưa dòng hiện tại trở lại luồng xử lý thông thường (để các dòng như `Ngoài trích dẫn:$$y=2$$` được tách thành `MathBlock` chính xác). Đồng thời chỉ chấp nhận dòng đóng `$$` khi `bq_depth == math_bq_depth`.
2. **Gia cố kiểm thử bảo toàn đầu ra và bất biến nội dung**:
   - Bổ sung kiểm thử đơn vị và tích hợp cho trường hợp `in_display_math` thoát khỏi trích dẫn (từ `>` ra cấp gốc, từ `>>` về `>`, và qua dòng trống).
   - Cập nhật `test_code_fence_in_blockquote_auto_closes_on_dedent()` để xác nhận tường minh cả hai khối công thức `x=2` và `y=3`.
   - Bổ sung kiểm thử xác nhận bảo toàn chính xác từng ký tự của các đoạn code fence và indented code block qua toàn bộ pipeline, cùng việc trích xuất chính xác các công thức ngoài vùng mã.
   - Bổ sung các khẳng định bất biến nội dung cụ thể cho `out_n`, `out_2n`, `out_4n` trong `test_adversarial_complexity_multi_length_backticks_and_long_lines()`.

---

## Technical Context

**Language/Version**: Python >= 3.10 (CI: Python 3.12, 3.13, 3.14; `.python-version`: `3.13`)

**Primary Dependencies**: Python Standard Library (`re`, `importlib`, `os`), phụ thuộc tùy chọn nhóm `docs` (`markdown-it-py`, `mdit-py-plugins`), `pytest`

**Storage**: N/A (xử lý văn bản trong bộ nhớ)

**Testing**: `pytest`, `ruff`, `npm run test:unit`, `npm run test:browser`, `node scripts/test_golden_pyodide.mjs`, `npm run test:e2e`

**Target Platform**: Môi trường cài đặt gói lõi tối giản, GitHub Actions Ubuntu runners, Browser WebAssembly (Pyodide 314.0.7)

**Project Type**: Document Importer Pipeline & Static Web Application

**Performance Goals**: Tiền xử lý Markdown duy trì độ phức tạp thời gian tuyến tính $O(n)$ ($T(4N)/T(N) \le 6.0$) đồng thời thỏa mãn 100% bất biến bảo toàn nội dung đầu ra.

**Constraints**: Bảo toàn tính tùy chọn của `markdown-it-py` đã thiết lập ở Feature 059; khớp 100% mã băm SHA-256 cho 8 ca Golden Master; không mở rộng phạm vi ngoài `markdown_importer.py` và bộ kiểm thử liên quan.

**Scale/Scope**: 2 tệp mã nguồn và kiểm thử (`chuviettay/importer/markdown_importer.py`, `tests/test_markdown_math_block_isolation.py`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc trong Constitution | Đánh giá Trước Phase 0 | Đánh giá Sau Phase 1 | Ghi chú tuân thủ |
| :--- | :---: | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | PASS | PASS | Đồng bộ quy tắc quản lý độ sâu trích dẫn giữa `in_fence` (`fence_bq_depth`) và `in_display_math` (`math_bq_depth`) trong cùng một máy trạng thái một lượt. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | PASS | Chỉ thêm biến trạng thái `math_bq_depth` và nhánh kiểm tra thoát blockquote trực tiếp trong `_isolate_display_math_blocks()`. |
| **III. Comprehensive Automated Testing** | PASS | PASS | Kiểm tra đầy đủ cả thời gian chạy lẫn bất biến nội dung đầu ra và danh sách `MathBlock` hoàn chỉnh. |
| **IV. Loose Coupling & High Cohesion** | PASS | PASS | Giữ nguyên giao diện công khai và cơ chế nạp phụ thuộc trì hoãn của `chuviettay.importer`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/060-blockquote-math-state-hardening/
├── plan.md                                                  # Kế hoạch triển khai kỹ thuật (/speckit-plan)
├── research.md                                              # Quyết định kỹ thuật Phase 0
├── data-model.md                                            # Máy trạng thái DisplayMathState Phase 1
├── quickstart.md                                            # Hướng dẫn chạy kiểm chứng nhanh Phase 1
├── contracts/
│   └── blockquote-math-and-test-invariants-contract.md      # Hợp đồng trạng thái khối toán & bất biến kiểm thử
└── checklists/
    └── requirements.md                                      # Checklist chất lượng đặc tả
```

### Source Code (repository root)

```text
chuviettay/
└── importer/
    └── markdown_importer.py                                 # Bổ sung math_bq_depth và xử lý thoát blockquote cho in_display_math
tests/
└── test_markdown_math_block_isolation.py                    # Kiểm thử thoát blockquote cho display math & bất biến bảo toàn nội dung
```

**Structure Decision**: Chỉnh sửa trực tiếp trên `chuviettay/importer/markdown_importer.py` và `tests/test_markdown_math_block_isolation.py`, giữ nguyên cấu trúc dự án.

---

## Complexity Tracking

> Không có vi phạm Constitution Check. Bảng dưới đây để trống theo quy định.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
