# Implementation Plan: Khôi phục dấu đóng giả bằng dấu giữ chỗ riêng, bảo toàn nguyên vẹn công thức LaTeX

**Branch**: `062-fake-close-placeholder-restore` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/062-fake-close-placeholder-restore/spec.md`

---

## Summary

Commit `518a7e3` bảo vệ dấu đóng giả lồng nhau (`>> $$` trong khối toán mở ở `> $$`) bằng cách escape thành `\$\$`, rồi khôi phục bằng `replace(r"\$\$", "$$")` trên **toàn bộ** nội dung `MathBlock`. Vì `\$\$` cũng là LaTeX hợp lệ, công thức người dùng như `$$\text{\$\$}$$` bị đổi thành `\text{$$}` (đã tái hiện ở dạng một dòng, nhiều dòng, trong trích dẫn).

Cách tiếp cận (chi tiết: [research.md](./research.md)):
1. **Dấu giữ chỗ không thể va chạm**: thay `$$` của dấu đóng giả bằng một ký tự PUA (U+E000…U+F8FF) được chọn động sao cho không có trong đầu vào. `dollarmath` không nhận nó là dấu đóng.
2. **Khôi phục một điểm, toàn cây**: ngay sau `md.parse()`, duyệt đệ quy cây token và đổi dấu giữ chỗ về `$$` — bao phủ cả trường hợp khối toán không đóng làm các dòng rơi vào đoạn văn.
3. **Gỡ phép `replace` toàn cục** trong `_parse_blocks()`: `MathBlock.latex = tok.content.strip()`.
4. **Siết kiểm thử**: so sánh `==` toàn bộ chuỗi sau cô lập và `MathBlock.latex` cho ca lồng nhau; thêm hồi quy cho `\$\$` hợp lệ, ca kết hợp, va chạm và rò rỉ.

---

## Technical Context

**Language/Version**: Python ≥ 3.10 (CI: 3.12, 3.13, 3.14; Pyodide 314.0.7)

**Primary Dependencies**: `markdown-it-py` 4.2.0, `mdit-py-plugins` 0.6.1 (dollarmath, amsmath) — không thêm phụ thuộc

**Storage**: N/A

**Testing**: `pytest`, `ruff`, `npm run test:unit`, `npm run test:browser`, `node scripts/test_golden_pyodide.mjs`, `npm run test:e2e`

**Target Platform**: CPython (Windows dev, Ubuntu CI) và Pyodide/WebAssembly trong Web Client

**Project Type**: Document importer pipeline (thư viện nội bộ) + test suite

**Performance Goals**: Thêm chi phí O(n) cho chọn dấu giữ chỗ và O(số token) cho khôi phục; benchmark `T(4N)/T(N) ≤ 6.0` giữ nguyên

**Constraints**: Không đổi chữ ký `import_text`/`import_file`; tham số mới của `_isolate_display_math_blocks` là keyword tùy chọn (tương thích mọi lời gọi hiện có); Golden Master 8/8 không đổi mã băm; không sửa thư viện bên thứ ba

**Scale/Scope**: 2 tệp mã: `chuviettay/importer/markdown_importer.py`, `tests/test_markdown_math_block_isolation.py`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Trước Phase 0 | Sau Phase 1 | Ghi chú |
| :--- | :---: | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | PASS | PASS | Loại bỏ phép thay thế mơ hồ; cơ chế đánh dấu/khôi phục có tên rõ ràng và một điểm khôi phục duy nhất. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | PASS | 1 ký tự giữ chỗ + 1 hàm duyệt token; loại bỏ phương án ánh xạ dòng/`token.map` phức tạp. Không phụ thuộc mới. |
| **III. Comprehensive Automated Testing** | PASS | PASS | 10 ca hợp đồng (C5) với so sánh bằng tuyệt đối; giữ 32 test hiện có; đủ cổng chất lượng. |
| **IV. Loose Coupling & High Cohesion** | PASS | PASS | `_parse_blocks`/`_parse_inlines` không biết về dấu giữ chỗ; không dùng trạng thái instance (truyền tham số tường minh). |

Không có vi phạm.

---

## Project Structure

### Documentation (this feature)

```text
specs/062-fake-close-placeholder-restore/
├── spec.md
├── plan.md                                   # Tệp này
├── research.md                               # R1–R6: nguyên nhân, lựa chọn dấu giữ chỗ, phạm vi khôi phục
├── data-model.md                             # Fake Close Marker, Internal Placeholder, bất biến INV-1..3
├── quickstart.md                             # Lệnh kiểm chứng
├── contracts/
│   └── fake-close-placeholder-contract.md    # C1–C5: hợp đồng hàm nội bộ + bảng ca kiểm thử chính xác
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
chuviettay/
└── importer/
    └── markdown_importer.py
        # + _FAKE_CLOSE_PUA_START / _FAKE_CLOSE_PUA_END (U+E000..U+F8FF)
        # + _choose_fake_close_placeholder(text)
        # ~ _isolate_display_math_blocks(seg, fake_close_placeholder="")  — thay "\$\$" bằng placeholder
        # + _restore_fake_close_placeholder(tokens, placeholder)  — khôi phục trên cả token.content và token.info
        # ~ import_text(): chọn placeholder, truyền xuống, khôi phục sau md.parse()
        # ~ _parse_blocks(): bỏ .replace(r"\$\$", "$$")
tests/
└── test_markdown_math_block_isolation.py
    # ~ test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close: so sánh == (T-ISO, T-NEST, T-PUNCT)
    # + test hồi quy \$\$ hợp lệ (T-ESC1..3, T-MULTI, T-COMBO)
    # + test va chạm / rò rỉ dấu giữ chỗ (T-COLL, T-LEAK)
```

---

## Risks & Mitigations

| Rủi ro | Giảm thiểu |
| :--- | :--- |
| Dấu giữ chỗ rò rỉ khi khối toán không đóng | Khôi phục trên toàn cây token (R3); test T-LEAK |
| Đầu vào chứa sẵn ký tự PUA | Chọn động (R2); test T-COLL |
| Hành vi có sẵn (tiền tố `> ` trong `MathBlock`, `$$a\$\$$$`) bị nhầm là hồi quy | Ghi nhận ngoài phạm vi (R5); giá trị mong đợi phản ánh hành vi hiện tại |
| Golden Master đổi mã băm | Không chứa dấu đóng giả/`\$\$`; nếu đổi → điều tra, không cập nhật mã băm |

---

## Complexity Tracking

> Không có vi phạm Constitution Check.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
