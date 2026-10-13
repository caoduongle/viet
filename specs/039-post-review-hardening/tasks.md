# Implementation Tasks: Củng cố và xử lý các vấn đề sau rà soát bản Web-only (Post-Review Hardening)

**Feature**: `039-post-review-hardening` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tài liệu này định nghĩa danh sách các đầu việc phụ thuộc có thể thực thi tuần tự nhằm giải quyết triệt để 5 nhóm vấn đề sau rà soát.

---

## Phase 1: Setup (Cấu hình Phiên bản & Metadata)

**Mục đích**: Đồng bộ hóa nguồn phiên bản chính thống trước khi điều chỉnh mã nguồn.

- [X] T001 [P] Nâng số phiên bản từ `2.0.0` lên `2.1.0` trong `pyproject.toml`
- [X] T002 [P] Nâng số phiên bản từ `1.0.0` lên `2.1.0` trong `package.json`
- [X] T003 [P] Cập nhật hàm `generate_version_json()` trong `scripts/build_web.py` để nạp động `chuviettay.__version__`

---

## Phase 2: Foundational (Hợp đồng Lõi & Hạ tầng Kiểm thử)

**Mục đích**: Xây dựng các lớp kiểm định và sửa đổi cấu trúc dữ liệu nền tảng làm tiền đề cho tất cả các User Stories.

**⚠️ CRITICAL**: Các công việc trong giai đoạn này là điều kiện tiên quyết trước khi triển khai chi tiết từng User Story.

- [X] T004 Bổ sung hỗ trợ thao tác cắt lát `slice` (`item[:3]`, `item[1:4]`) và chỉ số âm (`item[-1]`) trong `RenderItem.__getitem__()` tại `chuviettay/layout/engine.py`
- [X] T005 [P] Xây dựng bộ kiểm thử đơn vị `tests/test_render_item.py` kiểm chứng toàn diện hành vi `slice`, chỉ số âm, `len()`, và `IndexError` của `RenderItem`
- [X] T006 [P] Xây dựng bài kiểm thử tự động `tests/test_version_metadata.py` đối chiếu tính đồng nhất phiên bản giữa `chuviettay/__init__.py`, `pyproject.toml`, `package.json`, `CHANGELOG.md`, và `version.json`

**Checkpoint**: Nền tảng hợp đồng dữ liệu và kiểm định phiên bản đã sẵn sàng.

---

## Phase 3: User Story 1 - Phân định rõ phạm vi DOCX trên Web-only (Priority: P1) 🎯 MVP

**Mục tiêu**: Làm rõ ranh giới Web Client chỉ hỗ trợ Content-First Import, cập nhật thông điệp giao diện và tài liệu, đánh dấu module `fidelity/` là legacy/archive.

**Kiểm chứng độc lập**: Mở tệp DOCX trên Web Client thấy thông điệp Content-First Import rõ ràng; đọc `README.md` thấy phạm vi Web-only chính xác; bài kiểm thử `tests/test_docx_fidelity.py` tiếp tục pass độc lập mà không ảnh hưởng Web.

- [X] T007 [P] [US1] Thêm docstring cảnh báo legacy / archive trong `chuviettay/fidelity/__init__.py` và docstring lưu ý offline-only cho `AppController.write_docx_fidelity()` trong `chuviettay/controller/app_controller.py`
- [X] T008 [P] [US1] Cập nhật tài liệu `README.md` loại bỏ cam kết đưa Fidelity lên Web tĩnh và giải thích rõ ràng cơ chế Content-First Markdown Import cho tệp DOCX
- [X] T009 [US1] Cập nhật thông báo người dùng khi nạp tệp DOCX trong `webapp/js/write.js` và nhãn tooltip trong `webapp/index.html` nêu rõ chế độ nhập nội dung sang Markdown
- [X] T010 [US1] Kiểm tra và xác nhận tính toàn vẹn của luồng nhập DOCX thông qua `tests/test_importer_docx.py` và `tests/test_docx_table_import.py`

**Checkpoint**: User Story 1 hoàn tất — phạm vi DOCX minh bạch 100%, không còn gây hiểu nhầm về tính năng.

---

## Phase 4: User Story 2 - Đảm bảo tính độc lập & ổn định biến thể nét chữ & công thức toán (Priority: P2)

**Mục tiêu**: Sử dụng `token_id` có tiền tố không gian tên làm khóa `ScopedRNG`, cấp phát seed độc lập cho các công thức toán lặp lại, và bảo toàn Prepend Invariance.

**Kiểm chứng độc lập**: Hai từ giống nhau ở hai đoạn khác nhau và hai công thức toán giống nhau sở hữu biến thể nét khác biệt; thao tác chèn từ ở đầu tài liệu không làm đổi nét của các từ và công thức phía sau.

- [X] T011 [US2] Cập nhật `_layout_inlines()` trong `chuviettay/layout/engine.py` để hỗ trợ tiền tố không gian tên (`text:`, `sym:`, `cell:`) và quản lý bộ đếm `doc_token_counts` tích lũy toàn tài liệu
- [X] T012 [US2] Cập nhật hàm `_render_text_line()` trong `chuviettay/layout/engine.py` sử dụng trực tiếp `item.token_id` làm khóa cho `ScopedRNG` hình học nét
- [X] T013 [US2] Bổ sung bộ đếm số lần xuất hiện của biểu thức toán học (`_math_inline_counts` và `_math_block_counts`) trong `DocumentLayoutEngine` tại `chuviettay/layout/engine.py` để cấp phát hạt giống toán học độc lập
- [X] T014 [P] [US2] Bổ sung bài kiểm thử tích hợp `test_repeated_math_formula_independent_variants` trong `tests/test_stable_variants.py` kiểm chứng các công thức toán trùng nội dung có biến thể nét riêng biệt
- [X] T015 [US2] Bổ sung bài kiểm thử `test_cross_block_rng_independence` và xác minh Prepend Invariance với jitter trong `tests/test_stable_variants.py`

**Checkpoint**: User Story 2 hoàn tất — nét chữ tự nhiên, phong phú, không còn trùng lặp jitter đơn điệu.

---

## Phase 5: User Story 3 - Đồng bộ hóa Metadata Phiên bản Phát hành (Priority: P2)

**Mục tiêu**: Thực thi kiểm định tự động bảo đảm 100% các tệp khai báo phiên bản và bản build web đều mang số phiên bản `2.1.0`.

**Kiểm chứng độc lập**: Chạy `python scripts/build_web.py` và `pytest tests/test_version_metadata.py` đạt kết quả xanh 100%.

- [X] T016 [US3] Thực thi `python scripts/build_web.py` và kiểm tra tệp `webapp/dist/version.json` ghi nhận đúng `version: "2.1.0"`
- [X] T017 [US3] Thực thi bài kiểm thử `pytest tests/test_version_metadata.py` xác nhận tính khớp nối giữa toàn bộ các nguồn metadata

**Checkpoint**: User Story 3 hoàn tất — toàn bộ sản phẩm thống nhất một phiên bản duy nhất `2.1.0`.

---

## Phase 6: User Story 4 - Hoàn thiện Hợp đồng Dữ liệu RenderItem (Priority: P3)

**Mục tiêu**: Xác nhận đối tượng `RenderItem` tương thích hoàn toàn với các thao tác tuần tự cũ và cú pháp giải nén tuple.

**Kiểm chứng độc lập**: Chạy `pytest tests/test_render_item.py` và các bài kiểm thử bố cục bảng biểu/văn bản hiện có.

- [X] T018 [US4] Xác minh toàn bộ các thao tác giải nén `start, st, w = item[:3]` và truy cập `item[-1]` hoạt động chính xác trong `tests/test_render_item.py`

**Checkpoint**: User Story 4 hoàn tất — hợp đồng dữ liệu hiển thị vững chắc.

---

## Phase 7: User Story 5 - Xác thực Toàn diện CI và Kiểm định Kiến trúc (Priority: P3)

**Mục tiêu**: Đảm bảo toàn bộ test suite, kiểm tra kiến trúc cấm Tkinter, kiểm tra JavaScript unit tests, và linter đều đạt kết quả 100% thành công.

**Kiểm chứng độc lập**: Toàn bộ các lệnh kiểm thử tự động trả về mã thoát `0`.

- [X] T019 [P] [US5] Thực thi kiểm tra kiến trúc `pytest tests/test_architecture.py` xác nhận không có bất kỳ vi phạm kiến trúc nào
- [X] T020 [P] [US5] Thực thi kiểm thử đơn vị JavaScript `npm run test:unit`
- [X] T021 [US5] Thực thi toàn bộ bộ kiểm thử lõi `pytest tests/ -k "not web and not browser and not benchmark" -q`
- [X] T022 [P] [US5] Thực thi kiểm tra chất lượng mã nguồn qua `ruff check .`

**Checkpoint**: User Story 5 hoàn tất — kho mã sạch sẽ, không còn lỗi tiềm ẩn.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Mục đích**: Hoàn thiện tài liệu lịch sử thay đổi và kiểm chứng các kịch bản tổng thể.

- [X] T023 [P] Cập nhật tệp `CHANGELOG.md` ghi nhận đầy đủ các cải tiến của phiên bản 2.1.0
- [X] T024 Thực hiện kịch bản kiểm chứng độc lập theo hướng dẫn tại `specs/039-post-review-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────┐
                             ▼
Phase 2: Foundational ───────┴───────────────┐
                                             ▼
                 ┌───────────────────────────┴───────────────────────────┐
                 ▼                                                       ▼
Phase 3: User Story 1 (P1 - MVP)                       Phase 4: User Story 2 (P2 - RNG/Math)
                 │                                                       │
                 ▼                                                       ▼
Phase 5: User Story 3 (P2 - Metadata)                  Phase 6: User Story 4 (P3 - RenderItem)
                 │                                                       │
                 └───────────────────────────┬───────────────────────────┘
                                             ▼
                               Phase 7: User Story 5 (P3 - CI Verification)
                                             │
                                             ▼
                               Phase 8: Polish & Quickstart
```

### Parallel Opportunities

- **Trong Phase 1**: T001, T002, T003 có thể thực hiện song song (các tệp cấu hình độc lập).
- **Trong Phase 2**: T005 và T006 có thể viết song song ngay sau khi T004 hoàn thành.
- **Sau Phase 2**: User Story 1 (tài liệu & UI DOCX) và User Story 2 (lõi bố cục & RNG) có thể tiến hành độc lập.
- **Trong Phase 7**: T019, T020, T022 có thể chạy song song.

---

## Implementation Strategy (Chiến lược Triển khai)

### 1. MVP First (Phase 1, 2, 3)
1. Cập nhật số phiên bản `2.1.0` trên `pyproject.toml`, `package.json`, `build_web.py`.
2. Sửa `RenderItem` hỗ trợ slice và thêm test `test_render_item.py`.
3. Phân định rõ phạm vi DOCX trên `README.md`, `write.js`, và đánh dấu legacy cho `fidelity/`.
4. **Dừng và kiểm chứng**: Kiểm tra DOCX import và các test cơ bản.

### 2. Lõi Ổn định & Biến thể Tự nhiên (Phase 4)
1. Thêm tiền tố namespace `text:`, `sym:`, `cell:` và đếm token tích lũy toàn tài liệu.
2. Dùng `item.token_id` trực tiếp trong `_render_text_line()`.
3. Độc lập hóa hạt giống công thức toán học lặp lại.
4. Chạy `tests/test_stable_variants.py`.

### 3. Đồng bộ & Hoàn thiện CI (Phase 5, 6, 7, 8)
1. Kiểm chứng `build_web.py` và `test_version_metadata.py`.
2. Chạy toàn bộ 1.200+ bài kiểm thử lõi, kiểm tra kiến trúc và ruff lint.
3. Hoàn tất `CHANGELOG.md` và chạy kịch bản `quickstart.md`.
