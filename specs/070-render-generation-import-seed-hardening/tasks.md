---
description: "Task list for Feature 070: Render Generation, Export Stale Guard, Import Seed Reset & Test Hardening"
---

# Tasks: Feature 070 - Render Generation, Export Stale Guard & Import Seed Hardening

**Input**: Design documents from `specs/070-render-generation-import-seed-hardening/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)  
**Prerequisites**: `spec.md` (required), `plan.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  

---

## Phase 1: Setup (Môi trường & Tiền điều kiện)

**Purpose**: Xác nhận môi trường thực thi và trạng thái sạch của kho mã nguồn trước khi triển khai.

- [x] T001 Kiểm tra môi trường Node.js 20+, Python 3.10+, Playwright và xác nhận nhánh git `070-render-generation-import-seed-hardening` sạch sẽ

---

## Phase 2: Foundational (Hạ tầng cốt lõi & Hợp đồng giao tiếp)

**Purpose**: Khởi tạo biến trạng thái tính mới của bản kết xuất và xây dựng hàm kiểm tra an toàn xuất file.

**⚠️ CRITICAL**: Các User Stories phía sau phụ thuộc vào các hợp đồng cơ sở này.

- [x] T002 Khai báo biến trạng thái `renderedGeneration = 0` và `isRenderStale = false` trong `webapp/js/write.js`, và xây dựng hàm `canExport()` tập trung kiểm tra tính mới trước khi xuất file
- [x] T003 Cập nhật hàm `clearPreview()` trong `webapp/js/write.js`: tăng `currentRenderGeneration++`, đặt lại `isRenderStale = true`, `renderedGeneration = 0`, `currentXoppBase64 = ""`, `currentDoc = null` và cập nhật trạng thái các nút xuất

**Checkpoint**: Hạ tầng kiểm soát tính mới của bản kết xuất đã sẵn sàng cho các User Stories.

---

## Phase 3: User Story 1 - Ngăn chặn kết quả cũ ghi đè sau giải nén XOPP và Khóa xuất tệp khi nội dung bị cũ (Priority: P1) 🎯 MVP

**Goal**: Triển khai Two-Stage Stale Guard và Atomic State Commit trong `write.js`, loại bỏ triệt để race condition trong khoảng chờ giải nén XOPP, và kích hoạt Export Stale Guard chặn xuất tệp (.xopp, .pdf, .png, .svg, .zip) khi nội dung soạn thảo chưa khớp với bản kết xuất.

**Independent Test**: Chạy bài kiểm thử đơn vị Node.js `tests/js/render_generation.test.mjs` xác nhận kết quả cũ của tài liệu A bị hủy bỏ sau khi giải nén xong nếu tài liệu B đã được yêu cầu, và các nút xuất bị khóa khi `isRenderStale === true`.

### Tests cho User Story 1 (TDD - Viết test trước) 🧪

- [x] T004 [P] [US1] Viết bài kiểm thử đơn vị Node.js trong `tests/js/render_generation.test.mjs` kiểm chứng Giai đoạn 2 của Stale Guard (sau giải nén XOPP) và kiểm chứng `canExport()` trả về `false` khi `isRenderStale === true` hoặc `isRendering === true`

### Implementation cho User Story 1

- [x] T005 [US1] Tái cấu trúc khối xử lý kết quả Worker trong `requestRender()` tại `webapp/js/write.js`: giải nén `decompressXoppBase64` và parse XML vào biến cục bộ `parsedDoc` trước khi chạm vào trạng thái toàn cục
- [x] T006 [US1] Triển khai Atomic State Commit trong `requestRender()` tại `webapp/js/write.js`: kiểm tra lại lần thứ hai (`thisGeneration === currentRenderGeneration` và `textarea.value === currentRenderSnapshot.text`), chỉ khi hợp lệ mới commit đồng thời `currentXoppBase64 = res.xopp_base64`, `currentDoc = parsedDoc`, `renderedGeneration = thisGeneration`, `isRenderStale = false` và cập nhật SVG
- [x] T007 [US1] Bổ sung cơ chế bảo vệ trong `webapp/js/write.js`: bọc khối giải nén bằng `try...catch` an toàn không gán `currentXoppBase64` nếu giải nén lỗi; đánh dấu `isRenderStale = true` ngay khi người dùng gõ vào ô soạn thảo; cập nhật `setupExportButtons()` chặn xuất file và hiển thị cảnh báo nếu `!canExport()`
- [x] T008 [US1] Chạy kiểm thử đơn vị Node.js `node --test tests/js/render_generation.test.mjs` xác nhận toàn bộ các kịch bản Two-Stage Stale Guard và Export Stale Guard đạt 100% PASS

**Checkpoint**: User Story 1 hoàn tất độc lập. Hiện tượng ghi đè render cũ trong lúc giải nén và rủi ro xuất nhầm tệp cũ bị triệt tiêu hoàn toàn.

---

## Phase 4: User Story 2 - Chặn nạp tệp khi reset seed lỗi và Kiểm chứng E2E Race Condition xác định (Priority: P1)

**Goal**: Nâng cấp luồng nạp tệp dừng ngay khi lệnh đặt lại lịch sử hạt giống gặp lỗi, và xây dựng kịch bản kiểm thử E2E race condition có tính xác định (deterministic) cùng kiểm chứng Export Stale Guard trên trình duyệt.

**Independent Test**: Chạy `npx playwright test tests/e2e/write.spec.ts` xác nhận 100% kịch bản kiểm thử E2E về reset seed, race condition xác định và khóa xuất file đều xanh.

### Implementation & Test cho User Story 2

- [x] T009 [US2] Cập nhật `handleFileImport()` trong `webapp/js/write.js` cho cả `.txt`, `.md` và `.docx`: kiểm tra giá trị trả về của `resetDocumentSeedHistory()`, nếu `false` thì hiển thị thông báo lỗi cảnh báo và dừng ngay thao tác nạp tệp, không gán textarea và không gọi render
- [x] T010 [US2] Nâng cấp kịch bản kiểm thử E2E race condition trong `tests/e2e/write.spec.ts`: kích hoạt tức thời yêu cầu render cho văn bản dài $A$ và xác nhận Worker đã tiếp nhận yêu cầu trước khi mở file mới $B$, loại bỏ hoàn toàn sự phụ thuộc vào độ trễ debounce 250ms
- [x] T011 [US2] Bổ sung kịch bản kiểm thử E2E trong `tests/e2e/write.spec.ts` kiểm chứng Export Stale Guard: khi gõ sửa văn bản trong lúc chưa render xong, bấm nút xuất file `.xopp` bị chặn và hiển thị cảnh báo, không xuất file cũ
- [x] T012 [US2] Thực thi bộ kiểm thử E2E bằng lệnh `npx playwright test tests/e2e/write.spec.ts` xác nhận toàn bộ các kịch bản đều đạt PASS

**Checkpoint**: User Story 2 hoàn tất độc lập. An toàn nạp tệp khi reset seed lỗi và race condition được kiểm chứng E2E xác định 100%.

---

## Phase 5: User Story 3 - Kiểm thử đơn vị với Fixture XOPP hợp lệ và Dọn dẹp Timer Worker (Priority: P2)

**Goal**: Nâng cấp bộ test đơn vị Node.js sử dụng fixture XOPP gzip chuẩn chứng minh trọn vẹn chu trình giải nén, parse XML và cập nhật `currentDoc` thành công, đồng thời dọn dẹp triệt để các timer Worker để không giữ tiến trình Node.js 60 giây.

**Independent Test**: Chạy `node --test tests/js/render_generation.test.mjs` xác nhận test hoàn thành trong $< 500$ ms, không có timer treo.

### Implementation & Test cho User Story 3

- [x] T013 [P] [US3] Xây dựng hàm trợ giúp `createValidXoppBase64(xmlContent)` sử dụng `node:zlib.gzipSync` trong `tests/js/render_generation.test.mjs` để tạo fixture XOPP gzip chuẩn chứa XML stroke
- [x] T014 [US3] Nâng cấp `SyncMockWorker` và các ca kiểm thử trong `tests/js/render_generation.test.mjs`: tự động phản hồi cho `clear_document_history` ngay lập tức để giải phóng timer 60s của `app.js`, bổ sung mock DOM methods (`replaceChildren`, `querySelector`) và khẳng định `currentDoc !== null`, `canExport() === true` sau khi tài liệu B hoàn tất
- [x] T015 [US3] Chạy kiểm thử đơn vị Node.js `node --test tests/js/render_generation.test.mjs` xác nhận toàn bộ bài test vượt qua trong thời gian dưới 500ms mà không bị treo tiến trình

**Checkpoint**: User Story 3 hoàn tất. Bộ kiểm thử đơn vị đạt chất lượng cao, phản ánh đúng dữ liệu nhị phân thực tế và giải phóng tài nguyên sạch sẽ.

---

## Phase 6: User Story 4 - Chuẩn hóa Bền vững Kiểm thử Nét vẽ và Benchmark (Priority: P3)

**Goal**: Duy trì tính bền vững của thuật toán phân nhóm nét vẽ theo không gian trục X và tính nhất quán 100% của số liệu benchmark 3.520 mẫu nét.

**Independent Test**: Chạy `pytest tests/test_stable_variants.py tests/test_performance_regression.py -v` xác nhận 100% PASS.

### Implementation & Test cho User Story 4

- [x] T016 [P] [US4] Rà soát và đảm bảo hàm `group_strokes_by_word_proximity` trong `tests/test_stable_variants.py` và số liệu 3.520 mẫu nét trong `tests/test_performance_regression.py` duy trì ổn định không bị ảnh hưởng bởi thay đổi ở tầng giao diện
- [x] T017 [US4] Chạy kiểm thử Python `pytest tests/test_stable_variants.py tests/test_performance_regression.py -v` xác nhận PASS

**Checkpoint**: User Story 4 hoàn tất. Hệ thống kiểm thử nét vẽ và benchmark duy trì độ ổn định tuyệt đối.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Đóng gói phân phối web sạch và kiểm thử hồi quy toàn diện trên toàn bộ kho mã nguồn.

- [x] T018 Đóng gói phân phối tĩnh Web Client sạch bằng `python scripts/build_web.py`
- [x] T019 Chạy kiểm tra ruff lint `python -m ruff check chuviettay tests`
- [x] T020 Chạy kiểm thử đơn vị & Golden Master Node.js (`npm run test:unit`, `npm run test:browser`, `npm run test:golden`)
- [x] T021 Chạy kiểm thử hồi quy toàn diện Playwright E2E (`npx playwright test`) đảm bảo toàn bộ bài test đạt 100% PASS
- [x] T022 Chạy kiểm thử hồi quy toàn diện bộ test Python (`pytest`) đảm bảo toàn bộ 1.427+ bài test đạt 100% PASS
- [x] T023 [P] Cập nhật bảng ghi nhận kết quả kiểm chứng thực tế và đồng bộ số lượng bài test trong `specs/070-render-generation-import-seed-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc — chạy đầu tiên.
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1 — khối hạ tầng bắt buộc trước khi triển khai các User Story.
- **User Story 1 (Phase 3)**: Phụ thuộc vào Phase 2 — triển khai Two-Stage Stale Guard và Export Stale Guard.
- **User Story 2 (Phase 4)**: Phụ thuộc vào Phase 2 và Phase 3 — nâng cấp xử lý lỗi reset seed và kiểm thử E2E xác định.
- **User Story 3 (Phase 5)**: Phụ thuộc vào Phase 3 — hoàn thiện fixture XOPP và dọn dẹp timer.
- **User Story 4 (Phase 6)**: Độc lập với các tầng UI — có thể chạy song song.
- **Polish (Phase 7)**: Phụ thuộc vào việc hoàn tất toàn bộ các User Story trước đó.

### Parallel Opportunities

- `T004` (Test US1) có thể viết song song với việc thiết kế chi tiết.
- `T013` (Fixture XOPP) có thể triển khai song song với `T009`.
- `T016` (Python tests) chạy độc lập với mã nguồn JavaScript.
- `T023` (Cập nhật quickstart) thực hiện song song khi chạy các bài test hồi quy.

---

## Implementation Strategy

### MVP First (User Story 1 & Foundational)
1. Hoàn thành Phase 1 & Phase 2.
2. Hoàn thành Phase 3 (User Story 1): Triệt tiêu race condition sau giải nén XOPP và khóa xuất tệp khi stale.
3. Chạy `node --test tests/js/render_generation.test.mjs` nghiệm thu MVP độc lập.

### Incremental Delivery
1. Sau khi MVP vững chắc, tiếp tục bổ sung Phase 4 (Chặn nạp file khi reset lỗi & E2E xác định).
2. Hoàn thiện Phase 5 (Fixture XOPP hợp lệ & dọn timer).
3. Đóng gói phân phối web và thực thi toàn bộ kiểm thử hồi quy Phase 7.
