# Implementation Plan: Rà soát Toàn diện Dự án và Kế hoạch Cải thiện Chất lượng (Project Audit & Hardening)

**Branch**: `040-project-audit-hardening` | **Date**: 2026-10-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/040-project-audit-hardening/spec.md`

---

## Summary

Triển khai kế hoạch cải thiện chất lượng toàn diện và dọn dẹp triệt để các cơ chế desktop cũ:
1. **Bảo toàn toàn vẹn DOCX sang Markdown qua Round-trip escaping (P1 - US1)**: Xử lý `MathBlock` (`$$...$$`), `Heading` (`#`..`######`), escape các ký tự đặc biệt Markdown (`*`, `_`, `~`, `#`, `$`, `\`, `|`) khi serialize; chuyển `LineBreak` trong ô bảng thành khoảng trắng và escape `\|` trong LaTeX để bảng không bị vỡ.
2. **Căn lề đoạn văn ở cấp Core Engine & IR (P1 - US2)**: Hỗ trợ `Paragraph.align` (`left`, `center`, `right`, `justify`) trong `DocumentLayoutEngine.render_paragraph_inlines`, phân bổ word gaps cho dòng tràn trong `justify` (bỏ qua dòng có `LineBreak` hoặc dòng cuối), đồng bộ tọa độ chính xác cho `token_layout_callback`, bảo đảm căn trái giữ nguyên Golden Master.
3. **Bảo mật DOM chống XSS và Hiển thị SVG Xem thử thật trong Quản lý Kho mẫu (P1 - US3)**: Tách module `escapeHtml` dùng chung tại `webapp/js/html-utils.js`, áp dụng cho toàn bộ các sink trong `bank.js`; tích hợp pipeline giải nén và dựng SVG từ `paper.js` vào modal xem thử ngẫu nhiên với `missing_grid: false` và viewBox cắt gọn theo nét vẽ.
4. **Kích hoạt gạch ngang `strikethrough` và Cảnh báo định dạng giàu trong `MarkdownImporter` (P2 - US4)**: Bật plugin `.enable("strikethrough")` của `markdown-it-py`, loại bỏ cặp dấu `~~` thừa trong nét viết tay, và ghi nhận cảnh báo vào `ImportResult.warnings` khi tài liệu sử dụng định dạng kiểu chữ giàu.
5. **Dọn dẹp cơ chế Desktop cũ & Chuẩn hóa kho mã nguồn (P3 - US5)**:
   - Đổi mặc định `WriteOptions.missing_grid = False`, chấm dứt hoàn toàn việc đẻ file `*_thieu.xopp` gây rác MEMFS của Pyodide trên Web.
   - Bỏ hoàn toàn nhánh sinh lưới cũ `hw2` trong `chuviettay/model/xopp.py` (chỉ tạo chuẩn `hw3`), cập nhật thông điệp hướng dẫn trên trang lưới ô theo đúng nhãn giao diện Web hiện hành.
   - Di chuyển test còn thiếu từ `tests/test_web_parse_seed.test.mjs` sang `tests/js/parse_seed.test.mjs` rồi xóa file trùng.
   - Di chuyển các ca kiểm thử hồi quy từ `repro_viet_baseline.py` vào `tests/test_regression_audit.py` rồi xóa `repro_viet_baseline.py`.
   - Giữ package `chuviettay/fidelity/` làm archive cách ly.

---

## Technical Context

**Language/Version**: Python 3.12 (CI/Dev), Pyodide 314.0.7 (Web Worker - Python 3.14), JavaScript (ES Modules), HTML5 / SVG / CSS3  
**Primary Dependencies**: Thư viện chuẩn Python (`hashlib`, `math`, `secrets`, `dataclasses`). Thư viện phân tích định dạng: `markdown-it-py>=3.0.0`, `mdit-py-plugins>=0.4.0`, `python-docx>=1.1.0`. Frontend: Trình duyệt chuẩn (ESM, DecompressionStream/DOMParser, Canvas/SVG).  
**Storage**: Trình duyệt `IndexedDB` (hồ sơ và kho mẫu hoạt động), xuất/nhập tệp nén `.json.gz` (Schema v3) và `.xopp` (Gzip XML).  
**Testing**: `pytest>=8.0.0`, `pytest-timeout>=2.3.1`, `playwright>=1.40.0` (E2E), `node --test` (JS unit tests).  
**Target Platform**: Web Client tĩnh chạy hoàn toàn trên trình duyệt người dùng qua WebAssembly (Pyodide), không phụ thuộc backend server.  
**Project Type**: Static Web Typography Application & Layout Engine.  
**Performance Goals**: Tốc độ dàn trang đoạn văn dưới 5ms; giải nén và dựng SVG trong modal xem thử dưới 50ms; toàn bộ test suite thực thi dưới 45 giây.  
**Constraints**:
- Giữ nguyên 100% tính tương thích ngược với các bản xuất `.xopp` chuẩn Xournal++.
- Căn lề trái (`align="left"`) phải giữ nguyên tuyệt đối tọa độ của các bản test hiện hữu (không làm vỡ Golden Master).
- Giữ nguyên phiên bản `"pyodide": "314.0.7"` và quy ước phiên bản `2.1.0`.
- Không gọi bất kỳ CDN ngoài nào tại runtime.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến chương | Đánh giá | Ghi chú cụ thể |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | **PASS** | Tách `escapeHtml` dùng chung, xóa bỏ file trùng lặp và script chẩn đoán ở thư mục gốc, loại bỏ hoàn toàn cơ chế tự sinh file `*_thieu.xopp` làm rò rỉ bộ nhớ. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Giữ `fidelity/` làm archive, loại bỏ nhánh sinh lưới cũ `hw2`, tái sử dụng pipeline SVG từ `paper.js`. |
| **III. Comprehensive Automated Testing** | **PASS** | TDD: Viết test round-trip DOCX, test căn lề hình học, test XSS JS, test strikethrough trước khi sửa code. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Không cơi nới cú pháp Markdown trái phép; giữ ranh giới rõ ràng giữa IR, Importer, Layout Engine và Browser Bridge. |
| **Quality Gates & CI Verification** | **PASS** | Tất cả các cổng chất lượng (`ruff`, `compileall`, `pytest`, `build_web.py`, `npm test`) duy trì mã thoát 0. |

*Kết luận*: **100% GATES PASS.**

---

## Project Structure

### Documentation (this feature)

```text
specs/040-project-audit-hardening/
├── spec.md                  # Đặc tả tính năng và yêu cầu người dùng
├── plan.md                  # Kế hoạch triển khai chi tiết
├── research.md              # Phân tích kỹ thuật và quyết định thiết kế
├── data-model.md            # Mô hình thực thể và cấu trúc chuyển đổi
├── quickstart.md            # Hướng dẫn kiểm chứng nhanh độc lập
├── contracts/               # Các hợp đồng ràng buộc giao diện
│   ├── docx-import-ir-contract.md
│   ├── layout-alignment-contract.md
│   └── bank-ui-safety-contract.md
├── checklists/
│   └── requirements.md      # Bảng kiểm tra chất lượng đặc tả
└── tasks.md                 # Danh sách công việc triển khai chi tiết
```

### Source Code Changes (repository root)

```text
chuviettay/
├── browser/
│   └── bridge.py            # Round-trip escaping cho MathBlock, Heading, Text, TableCell, LineBreak
├── layout/
│   └── engine.py            # Hỗ trợ Paragraph.align (left, center, right, justify); bỏ text CLI cũ
├── importer/
    └── markdown_importer.py # Bật strikethrough; phát cảnh báo khi làm phẳng rich text
├── model/
│   ├── composer.py          # Đổi mặc định missing_grid = False
│   └── xopp.py              # Bỏ nhánh sinh lưới cũ hw2 (chỉ tạo hw3)

webapp/
└── js/
    ├── html-utils.js        # Module mới: escapeHtml dùng chung
    ├── write.js             # Import escapeHtml từ html-utils.js
    └── bank.js              # escapeHtml chống XSS; giải nén và vẽ SVG thật với missing_grid: false

tests/
├── test_regression_audit.py # Kiểm thử mới: căn lề đoạn văn, round-trip DOCX, gạch ngang, missing_grid=False
└── js/
    ├── parse_seed.test.mjs  # Tích hợp test thứ 5 từ test_web_parse_seed
    └── bank_safety.test.mjs # Kiểm thử mới: escapeHtml và hiển thị nhãn đặc biệt

# Dọn dẹp:
# - Xóa: tests/test_web_parse_seed.test.mjs
# - Xóa: repro_viet_baseline.py
```
