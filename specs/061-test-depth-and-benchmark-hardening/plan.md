# Implementation Plan: Gia cố kiểm thử đóng khối toán theo độ sâu và bổ sung bất biến công thức trong benchmark

**Branch**: `061-test-depth-and-benchmark-hardening` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/061-test-depth-and-benchmark-hardening/spec.md`

---

## Summary

Feature 061 hoàn thiện tính đúng đắn và tính chặt chẽ của bộ xử lý Markdown và bộ kiểm thử sau đợt rà soát commit `3cfdcd0`:
1. **Bảo vệ khối toán trích dẫn trước dấu đóng giả ở độ sâu lồng nhau và siết chặt kiểm thử (P2)**:
   - Trong `MarkdownImporter._isolate_display_math_blocks()`, khi `in_display_math` đang mở tại độ sâu `math_bq_depth`, nếu gặp một dòng có `bq_depth > math_bq_depth` kết thúc bằng `$$` (như `>> $$`), đây là dấu đóng giả ở cấp lồng nhau. Bộ tiền xử lý thoát ký tự `$$` thành `\$\$` để `dollarmath_plugin` của `markdown-it-py` không ngắt khối sớm.
   - Trong `MarkdownImporter._parse_blocks()`, hoàn nguyên `\$\$` về `$$` khi tạo `MathBlock`.
   - Trong `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close()`, thay thế assertion lỏng `assert isolated_nested.endswith("$$")` bằng việc kiểm tra toàn diện cấu trúc đầu ra của `_isolate_display_math_blocks()` và kiểm tra danh sách `MathBlock` qua `import_text()` (`len(math_blocks) == 1`, chứa cả `x = 1` và `x = 2`).
2. **Bổ sung bất biến công thức toán học trong benchmark (P3)**:
   - Trong `test_adversarial_complexity_multi_length_backticks_and_long_lines()`, bổ sung các khẳng định kiểm tra số lượng xuất hiện của các công thức toán học hiển thị hợp lệ sau tiền xử lý (`$$display_formula$$` và `$$x=1$$`) trên cả 3 kích thước $N, 2N, 4N$.
3. **Bảo toàn trạng thái Garbage Collector ban đầu (P3)**:
   - Lưu trạng thái `was_gc_enabled = gc.isenabled()` trước khi đo trong cả hai bài benchmark đối kháng và khôi phục đúng trạng thái ban đầu trong khối `finally`.

---

## Technical Context

**Language/Version**: Python >= 3.10 (CI: Python 3.12, 3.13, 3.14; `.python-version`: `3.13`)

**Primary Dependencies**: Python Standard Library (`re`, `gc`, `time`), phụ thuộc tùy chọn nhóm `docs` (`markdown-it-py`, `mdit-py-plugins`), `pytest`

**Storage**: N/A (bộ nhớ trong)

**Testing**: `pytest`, `ruff`, `npm run test:unit`, `npm run test:browser`, `node scripts/test_golden_pyodide.mjs`, `npm run test:e2e`

**Target Platform**: GitHub Actions Ubuntu runners, Môi trường Windows phát triển, Browser WebAssembly (Pyodide 314.0.7)

**Project Type**: Document Importer Pipeline & Test Suite

**Performance Goals**: Benchmark duy trì tỷ lệ tăng trưởng tuyến tính $T(4N)/T(N) \le 6.0$ trên dữ liệu đối kháng $N=1000, 2N=2000, 4N=4000$ dòng.

**Constraints**: Bảo toàn 100% mã băm SHA-256 của 8 ca Golden Master; giữ nguyên tính độc lập của môi trường kiểm thử (test suite isolation); không thay đổi giao diện công khai của `chuviettay.importer`.

**Scale/Scope**: 2 tệp (`chuviettay/importer/markdown_importer.py`, `tests/test_markdown_math_block_isolation.py`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc trong Constitution | Đánh giá Trước Phase 0 | Đánh giá Sau Phase 1 | Ghi chú tuân thủ |
| :--- | :---: | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | PASS | PASS | Các bài kiểm thử viết rõ ràng, tự tài liệu hóa và cô lập trạng thái môi trường sạch sẽ. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | PASS | Thoát dấu đóng giả bằng cơ chế chuẩn của bộ tiền xử lý, không thêm phụ thuộc hay trừu tượng phức tạp. |
| **III. Comprehensive Automated Testing** | PASS | PASS | Khóa chặt các ca kiểm thử biên (closing delimiter at deeper blockquote depth) và bổ sung bất biến công thức toán trực tiếp. |
| **IV. Loose Coupling & High Cohesion** | PASS | PASS | Khôi phục đúng trạng thái GC ban đầu, ngăn chặn việc làm ô nhiễm trạng thái toàn cục giữa các bài kiểm thử. |

---

## Project Structure

### Documentation (this feature)

```text
specs/061-test-depth-and-benchmark-hardening/
├── plan.md                                                  # Kế hoạch triển khai kỹ thuật (/speckit-plan)
├── research.md                                              # Quyết định kỹ thuật Phase 0
├── data-model.md                                            # Bất biến kiểm thử và máy trạng thái GC Phase 1
├── quickstart.md                                            # Hướng dẫn chạy kiểm chứng nhanh Phase 1
├── contracts/
│   └── test-depth-and-benchmark-contract.md                # Hợp đồng kiểm thử độ sâu & bất biến benchmark
└── checklists/
    └── requirements.md                                      # Checklist chất lượng đặc tả
```

### Source Code (repository root)

```text
chuviettay/
└── importer/
    └── markdown_importer.py                                 # Thoát dấu đóng giả khi bq_depth > math_bq_depth và hoàn nguyên khi tạo MathBlock
tests/
└── test_markdown_math_block_isolation.py                    # Nâng cấp độ chặt test đóng lồng nhau, bất biến công thức và GC hygiene
```

---

## Complexity Tracking

> Không có vi phạm Constitution Check. Bảng dưới đây để trống theo quy định.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
