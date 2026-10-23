# Tasks: Gia Cố Nền Tảng Kho Mã Nguồn Hậu Rà Soát (054-repo-audit-hardening)

**Input**: Design documents from `/specs/054-repo-audit-hardening/`  
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md  

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Có thể thực hiện song song (khác tệp tin, không phụ thuộc tác vụ đang làm dở)
- **[Story]**: Gán nhãn User Story (ví dụ [US1], [US2], [US3]...)
- Mỗi tác vụ đều có đường dẫn tệp tin cụ thể và tiêu chí hoàn thành rõ ràng

---

## Phase 1: Setup (Môi trường & Kiểm chuẩn Ban đầu)

**Mục đích**: Xác minh trạng thái CI/test nền tảng trước khi thực hiện thay đổi mã nguồn.

- [X] T001 Xác minh toàn bộ test suite hiện có của dự án vượt qua 100% bằng lệnh `pytest tests/` và `npm run test:unit`
- [X] T002 [P] Khởi tạo tệp kiểm thử bổ sung cho tính bất biến trong `tests/test_document_pipeline.py`

---

## Phase 2: Foundational (Hạ tầng Kỹ thuật Chặn)

**Mục đích**: Các tiện ích và hằng số dùng chung mà các User Story phụ thuộc.

- [X] T003 [P] Cập nhật regex `_CODE_SEGMENT` trong `chuviettay/importer/markdown_importer.py` để hỗ trợ code fence $\ge 3$ backticks/tildes và unclosed fence
- [X] T004 [P] Bổ sung biến trạng thái `bankRevision` và `lastRenderedRevision` cùng hook reset trong `webapp/js/write.js`

---

## Phase 3: User Story 1 - Tuyến tính hóa bộ tách công thức Markdown và bảo vệ khối mã (Priority: P1) 🎯 MVP

**Mục tiêu**: Bảo đảm bộ tách khối công thức không làm thay đổi nội dung code fence (```` ``` ```` và `~~~`) và code span (`` ` ``), xử lý tài liệu lớn chứa hàng nghìn `$$` dở dang với thời gian tuyến tính $O(n)$, và hỗ trợ an toàn ngắt dòng CRLF.  
**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py -k "code_fence or unclosed or performance"` xác nhận code fence nguyên vẹn và tài liệu 5,000 dòng có nhiều `$$` dở dang hoàn thành <100ms.

### Tests for User Story 1 🧪
- [X] T005 [P] [US1] Thêm test case kiểm tra bảo toàn code fence (3, 4+ backticks, tildes, info string) và unclosed fence trong `tests/test_markdown_math_block_isolation.py`
- [X] T006 [P] [US1] Thêm test case đo hiệu năng tuyến tính $O(n)$ với 5,000 dòng chứa `$$` mở không đóng và kiểm thử CRLF (`\r\n`) trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1
- [X] T007 [US1] Cài đặt chuẩn hóa CRLF và máy trạng thái một lượt (`NORMAL`, `FENCED_CODE`, `DISPLAY_MATH`) trong `_isolate_display_math_blocks` tại `chuviettay/importer/markdown_importer.py`
- [X] T008 [US1] Bảo toàn bảng GFM (kể cả hàng không có `|` ngoài cùng), thụt lề danh sách, và nhãn hai chấm dẫn nhập trong máy trạng thái tại `chuviettay/importer/markdown_importer.py`

**Checkpoint**: User Story 1 hoàn thành độc lập; code fence không bị đột biến và không còn nguy cơ $O(n^2)$ treo Web Worker.

---

## Phase 4: User Story 2 - Bảo đảm tính bất biến của Document IR khi dàn trang (Priority: P1)

**Mục tiêu**: Loại bỏ việc thay đổi trực tiếp (mutation) lên thuộc tính `text` của đối tượng `Text` trong `_layout_inlines`, bảo đảm tái sử dụng cùng một cây `Document` qua nhiều lần render không làm nhân bản văn bản.  
**Independent Test**: Chạy `pytest tests/test_document_pipeline.py -k "immutability"` xác nhận đối tượng `Document` sau 2 lần kết xuất liên tiếp giữ nguyên trạng thái ban đầu và cho ra kết quả giống hệt nhau 100%.

### Tests for User Story 2 🧪
- [X] T009 [P] [US2] Thêm test case kiểm tra tính bất biến của Document IR và tính lũy đẳng qua nhiều lần gọi `render()` trong `tests/test_document_pipeline.py`

### Implementation for User Story 2
- [X] T010 [US2] Chỉnh sửa `_layout_inlines` trong `chuviettay/layout/engine.py` để tạo thể hiện `Text` mới độc lập khi gộp các text liền kề thay vì gán nối chuỗi tại chỗ

**Checkpoint**: User Story 1 và 2 đều hoạt động độc lập và ổn định; cây tài liệu do caller sở hữu được bảo vệ bất biến.

---

## Phase 5: User Story 3 - Chuẩn hóa khóa cache Service Worker tái lập (Priority: P2)

**Mục tiêu**: Khóa `CACHE_NAME` và manifest của Service Worker được sinh ra bằng cách sắp xếp đường dẫn tương đối chuẩn tắc trước khi băm, nhạy cảm với việc đổi đường dẫn tệp và đồng nhất giữa các môi trường build khác nhau.  
**Independent Test**: Chạy `pytest tests/test_build_web.py -k "sw_cache or deterministic"` xác nhận tính tái lập và phát hiện đổi tên file.

### Tests for User Story 3 🧪
- [X] T011 [P] [US3] Thêm test case kiểm tra tính tái lập của khóa cache Service Worker và độ nhạy khi đổi đường dẫn tệp trong `tests/test_build_web.py`

### Implementation for User Story 3
- [X] T012 [US3] Cập nhật `generate_sw_js` trong `scripts/build_web.py` để chuẩn hóa đường dẫn POSIX, sắp xếp tăng dần và băm cặp `relative_path:sha256`

**Checkpoint**: Service Worker cache key đạt tính tái lập 100% trên mọi nền tảng hệ điều hành.

---

## Phase 6: User Story 4 - Bảo vệ an toàn đường dẫn khi Build Web (Priority: P2)

**Mục tiêu**: Script `build_web.py` chỉ tự động xóa thư mục phân phối mặc định `webapp/dist`; từ chối xóa thư mục ngoài repo nếu không rỗng và thiếu cờ `--force-clean` hoặc tệp marker `.chuviettay_build_dist`.  
**Independent Test**: Chạy `pytest tests/test_build_web.py -k "prepare_dist_dir_external_safety"` xác nhận script từ chối xóa thư mục ngoài không rỗng.

### Tests for User Story 4 🧪
- [X] T013 [P] [US4] Thêm test case kiểm tra cơ chế bảo vệ thư mục ngoài, cờ `--force-clean` và marker `.chuviettay_build_dist` trong `tests/test_build_web.py`

### Implementation for User Story 4
- [X] T014 [US4] Cập nhật `prepare_dist_dir` và bổ sung tham số `--force-clean` trong `scripts/build_web.py`, ghi tệp marker `.chuviettay_build_dist` sau khi khởi tạo

**Checkpoint**: Quy trình đóng gói web được bảo vệ an toàn, không có rủi ro xóa nhầm dữ liệu người dùng ngoài repo.

---

## Phase 7: User Story 5 - Đồng bộ Preview theo số hiệu phiên bản kho mẫu đơn điệu (Priority: P2)

**Mục tiêu**: Tab Viết sử dụng `bankRevision` tăng đơn điệu; chỉ xóa cờ `isBankDirty` khi phiên bản render hoàn tất khớp với phiên bản kho hiện hành, giữ nguyên trạng thái bẩn khi render thất bại hoặc bị chen ngang.  
**Independent Test**: Chạy `node --test tests/js/write_preview_sync.test.mjs` xác nhận không có race condition làm mất cờ dirty.

### Tests for User Story 5 🧪
- [X] T015 [P] [US5] Thêm test case mô phỏng race condition cập nhật kho mẫu trong lúc đang render và kiểm tra giữ cờ dirty khi render lỗi trong `tests/js/write_preview_sync.test.mjs`

### Implementation for User Story 5
- [X] T016 [US5] Triển khai logic chụp `requestRevision`, so sánh với `bankRevision` trong `requestRender()`, và cập nhật `resetWriteSyncStateForTesting()` tại `webapp/js/write.js`

**Checkpoint**: Giao diện Tab Viết luôn phản ánh trung thực tính đồng bộ của bản xem trước trên màn hình.

---

## Phase 8: User Story 6 - Minh bạch hóa hợp đồng nhập tài liệu Word (Priority: P3)

**Mục tiêu**: Báo cáo cảnh báo minh bạch cho người dùng về việc giản lược các phần tử đồ họa (`drawing`/`pict`) và bảng lồng nhau trong chế độ Content-First.  
**Independent Test**: Chạy `pytest tests/test_importer_docx.py -k "content_first_warnings"` xác nhận importer ghi nhận đầy đủ các cảnh báo.

### Tests for User Story 6 🧪
- [X] T017 [P] [US6] Thêm test case xác minh danh sách `warnings` khi nạp tài liệu DOCX chứa hình ảnh đồ họa và bảng lồng nhau trong `tests/test_importer_docx.py`

### Implementation for User Story 6
- [X] T018 [US6] Chuẩn hóa và làm rõ thông điệp cảnh báo cho các đối tượng `drawing`, `pict`, và bảng lồng nhau trong `chuviettay/importer/docx_importer.py`

**Checkpoint**: Hợp đồng Content-First của DOCX importer được ghi nhận rõ ràng và thông báo minh bạch cho người dùng.

---

## Phase 9: Polish & Cross-Cutting Verification

**Mục đích**: Hoàn thiện toàn bộ các kiểm tra chất lượng mã nguồn, tài liệu và đóng gói phân phối.

- [X] T019 [P] Chạy kiểm tra linter toàn diện không lỗi với `ruff check chuviettay/ tests/ scripts/`
- [X] T020 [P] Đóng gói lại Web Client và kiểm tra tính toàn vẹn của `chuviettay.zip` qua `python scripts/build_web.py`
- [X] T021 Thực hiện kiểm thử toàn bộ các kịch bản trong `specs/054-repo-audit-hardening/quickstart.md`
- [X] T022 Chạy toàn bộ test suite của dự án (`pytest tests/` và `npm run test:unit`), bảo đảm 100% bài kiểm thử tiếp tục vượt qua cleanly

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Có thể thực hiện ngay lập tức.
- **Phase 2 (Foundational)**: Phụ thuộc vào Phase 1; chuẩn bị các biểu thức regex và biến trạng thái nền tảng.
- **Phase 3 (US1 - Markdown Parser)**: Phụ thuộc Phase 2; đây là hạt nhân **MVP**.
- **Phase 4 (US2 - Immutability)**: Phụ thuộc Phase 2; có thể chạy song song với Phase 3 (khác tệp: `engine.py`).
- **Phase 5 (US3 - SW Cache)**: Phụ thuộc Phase 2; có thể chạy song song với Phase 3, 4 (khác tệp: `build_web.py`).
- **Phase 6 (US4 - Build Dir Safety)**: Phụ thuộc Phase 5 (cùng tệp `build_web.py`).
- **Phase 7 (US5 - Preview Sync)**: Phụ thuộc Phase 2; có thể chạy song song với các phase Python (tệp JS: `write.js`).
- **Phase 8 (US6 - DOCX Contract)**: Phụ thuộc Phase 2; có thể chạy độc lập (tệp: `docx_importer.py`).
- **Phase 9 (Polish)**: Phụ thuộc hoàn thành toàn bộ các User Story mong muốn.

### User Story Dependencies
```mermaid
flowchart TD
    Setup[Phase 1: Setup] --> Foundation[Phase 2: Foundational]
    Foundation --> US1[Phase 3: US1 - Markdown Parser O(n) & Code Fence]
    Foundation --> US2[Phase 4: US2 - Document IR Immutability]
    Foundation --> US3[Phase 5: US3 - Service Worker Cache Key]
    US3 --> US4[Phase 6: US4 - Build Dir Safety Guard]
    Foundation --> US5[Phase 7: US5 - Preview Bank Revision Sync]
    Foundation --> US6[Phase 8: US6 - DOCX Content-First Transparency]
    US1 --> Polish[Phase 9: Polish & Full Verification]
    US2 --> Polish
    US4 --> Polish
    US5 --> Polish
    US6 --> Polish
```

---

## Parallel Execution Opportunities

- **Nhóm Python Core**: US1 (`markdown_importer.py`) và US2 (`engine.py`) tác động lên 2 tệp hoàn toàn khác nhau, có thể triển khai song song.
- **Nhóm Build Script**: US3 và US4 triển khai tuần tự trong `scripts/build_web.py`.
- **Nhóm Web Frontend**: US5 hoàn toàn độc lập trong `webapp/js/write.js`, có thể phát triển và kiểm thử song song với nhóm Python.
- **Nhóm Kiểm thử**: Toàn bộ các tác vụ viết test `[P]` (T005, T006, T009, T011, T013, T015, T017) có thể được soạn thảo song song trước khi triển khai code.

---

## Implementation Strategy

### MVP First (User Story 1 & User Story 2)
1. Hoàn thành Phase 1 & Phase 2.
2. Hoàn thành User Story 1: Khắc phục triệt để nguy cơ $O(n^2)$ và bảo vệ code fence trong `MarkdownImporter`.
3. Hoàn thành User Story 2: Loại bỏ in-place mutation trong `DocumentLayoutEngine`.
4. **Kiểm thử độc lập**: Chạy test hồi quy cho US1 và US2. Đây là 2 vấn đề P1 trọng yếu nhất của đợt rà soát.

### Gia cố Toàn diện (User Story 3 -> 6 & Polish)
1. Hoàn thành US3 và US4 trong `scripts/build_web.py`.
2. Hoàn thành US5 trong `webapp/js/write.js`.
3. Hoàn thành US6 trong `chuviettay/importer/docx_importer.py`.
4. Chạy Phase 9: xác minh 100% test suites (Python, JS, linter, build web).
