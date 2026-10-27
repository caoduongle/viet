# Implementation Plan: Khôi phục CI xanh, sửa cấu hình Render và siết các trường hợp biên của Markdown importer

**Branch**: `058-ci-e2e-render-markdown-hardening` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/058-ci-e2e-render-markdown-hardening/spec.md`

---

## Summary

Feature 058 giải quyết triệt để 5 vấn đề kỹ thuật còn tồn đọng sau đợt rà soát commit `8a46ab0`:
1. **Playwright E2E Build Safety (P1)**: Cập nhật `runBuildWeb(distDir: string, forceClean = false)` trong `tests/e2e/sw-update.spec.ts` để truyền `--force-clean` ở lần build thứ hai trên cùng thư mục tạm `tmpDist`, khôi phục trạng thái xanh cho job Web Client CI mà vẫn bảo toàn 100% quy tắc bảo vệ của `prepare_dist_dir()`.
2. **Cấu hình Python trên Render (P1)**: Xóa khai báo biến môi trường `PYTHON_VERSION: 3.13` khỏi `render.yaml` để Render tự động đọc tệp `.python-version` (`3.13`), tránh lỗi biến môi trường `PYTHON_VERSION` trên Render bắt buộc định dạng đầy đủ `Major.Minor.Patch`. Cập nhật bài test tương ứng trong `tests/test_version_metadata.py`.
3. **Bảo vệ Indented Code Block trong `_isolate_display_math_blocks()` (P1)**: Bổ sung trạng thái nhận diện khối mã thụt lề (`in_indented_code` theo chuẩn CommonMark 4.4) vào máy trạng thái dòng của `MarkdownImporter._isolate_display_math_blocks()`, bảo đảm các chuỗi `prefix:$$x=1$$`, `$$y=2$$`, `\[z=3\]`, và thẻ giống HTML trong khối mã thụt lề được giữ nguyên từng ký tự qua toàn bộ luồng `import_text()`.
4. **Siết Nhận diện Ngữ cảnh Bảng GFM (P2)**: Chỉ đánh dấu các dòng thuộc bảng trong `table_line_indices` khi xác nhận đúng cấu trúc gồm dòng tiêu đề `h = d - 1` ngay trước dòng phân cách `d`, có số cột khớp nhau ($C_{\text{header}} == C_{\text{delim}} \ge 1$), và các dòng dữ liệu liền sau; không đánh dấu nhầm đoạn văn chứa `|` đứng trước bảng hoặc đứng trước chuỗi giả phân cách.
5. **Độ phức tạp Tuyến tính $O(n)$ cho Bộ Tách Code (P2)**: Loại bỏ hoàn toàn thao tác cắt lát chuỗi `text[i:]` ở mỗi đầu dòng trong `_split_code_segments()` (thay bằng `Pattern.match(text, i, eol)`), tối ưu bước nhảy qua dòng trống trong khối mã thụt lề, và bổ sung bộ nhớ đệm vị trí backtick tối đa (`backticks_scanned` + `backticks_max_pos`) trong `_split_code_segments()` và `_find_code_spans()` để đạt độ phức tạp $O(n)$ nghiêm ngặt ngay cả trên đầu vào bất lợi có nhiều dấu backtick mở không có dấu đóng.

---

## Technical Context

**Language/Version**: Python >= 3.10 (CI: Python 3.12, 3.13, 3.14; `.python-version`: `3.13`), TypeScript / JavaScript ES2022 (Node.js 24.x, Playwright E2E)

**Primary Dependencies**: Python Standard Library (`re`), `markdown-it-py`, `mdit-py-plugins`, `pytest`, `@playwright/test`

**Storage**: N/A (xử lý văn bản trong bộ nhớ và tệp cấu hình tĩnh)

**Testing**: `pytest` (unit, integration & `@pytest.mark.benchmark`), `node --test` (`npm run test:unit`), `node scripts/test_golden_pyodide.mjs`, `npx playwright test`

**Target Platform**: GitHub Actions Ubuntu runners (`ubuntu-latest`), Render Static Site build, Local Desktop & Browser WebAssembly (Pyodide 314.0.7)

**Project Type**: Hybrid Desktop Application & Static Web Client + Document Importer Pipeline

**Performance Goals**: Tiền xử lý Markdown (`_split_code_segments`, `_normalize_math_delimiters`, `_isolate_display_math_blocks`, `_sanitize_html`) đạt độ phức tạp thời gian và bộ nhớ tuyến tính $O(n)$; khi kích thước đầu vào bất lợi tăng $4\times$, thời gian xử lý tăng $\le 6\times$.

**Constraints**: Tuyệt đối không nới lỏng quy tắc bảo vệ trong `prepare_dist_dir()` của `scripts/build_web.py`; bảo toàn 100% SHA-256 cho 8 ca Golden Master.

**Scale/Scope**: 4 tệp mã nguồn/cấu hình/kiểm thử chính (`tests/e2e/sw-update.spec.ts`, `render.yaml`, `tests/test_version_metadata.py`, `chuviettay/importer/markdown_importer.py`, `tests/test_markdown_math_block_isolation.py`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc trong Constitution | Đánh giá Trước Phase 0 | Đánh giá Sau Phase 1 | Ghi chú tuân thủ |
| :--- | :---: | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | PASS | PASS | Máy trạng thái rõ ràng, regex biên dịch sẵn cấp lớp, chú thích ngắn gọn giải thích lý do thiết kế. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | PASS | Sửa trực tiếp tại đúng điểm gây lỗi, không thêm lớp trừu tượng hay thư viện ngoài. |
| **III. Comprehensive Automated Testing** | PASS | PASS | Có đầy đủ unit test, integration test qua `import_text()`, benchmark `@pytest.mark.benchmark` cho đầu vào bất lợi, và E2E test Playwright. |
| **IV. Loose Coupling & High Cohesion** | PASS | PASS | Giữ nguyên giao diện công khai của `MarkdownImporter` và `prepare_dist_dir()`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/058-ci-e2e-render-markdown-hardening/
├── plan.md                                  # Kế hoạch triển khai kỹ thuật (/speckit-plan)
├── research.md                              # Quyết định kỹ thuật Phase 0
├── data-model.md                            # Mô hình trạng thái & cấu trúc dữ liệu Phase 1
├── quickstart.md                            # Hướng dẫn chạy kiểm chứng nhanh Phase 1
├── contracts/
│   └── build-and-markdown-contract.md       # Hợp đồng an toàn build, cấu hình Render & Markdown importer
└── checklists/
    └── requirements.md                      # Checklist chất lượng đặc tả
```

### Source Code (repository root)

```text
.python-version                              # Giữ nguyên "3.13" (Single Source of Truth)
render.yaml                                  # Bỏ biến môi trường PYTHON_VERSION để dùng .python-version
scripts/
└── build_web.py                             # Giữ nguyên 100% cơ chế bảo vệ prepare_dist_dir()
chuviettay/
└── importer/
    └── markdown_importer.py                 # Bảo vệ indented code, siết nhận diện bảng GFM, tối ưu O(n)
tests/
├── test_version_metadata.py                 # Kiểm tra .python-version và đảm bảo render.yaml hợp lệ
├── test_markdown_math_block_isolation.py    # Unit/integration tests & adversarial O(n) benchmarks
└── e2e/
    └── sw-update.spec.ts                    # Bổ sung forceClean cho runBuildWeb() ở lần build thứ hai
```

**Structure Decision**: Chỉnh sửa tập trung trên cấu trúc repository hiện hữu, không tạo thêm module hay tệp mã nguồn mới ngoài các bài kiểm thử bổ sung trong tệp test sẵn có.

---

## Complexity Tracking

> Không có vi phạm Constitution Check. Bảng dưới đây để trống theo quy định.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
