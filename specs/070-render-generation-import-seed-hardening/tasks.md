---
description: "Task list for Feature 070: Render Generation, Import Generation, Export Stale Guard & Test Hardening"
---

# Tasks: Feature 070 - Render Generation, Import Generation, Export Stale Guard & Test Hardening

**Input**: Design documents from `specs/070-render-generation-import-seed-hardening/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)  
**Prerequisites**: `spec.md` (required), `plan.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  

---

## Phase 1: Setup (Môi trường & Tiền điều kiện)

**Purpose**: Xác nhận môi trường thực thi và trạng thái sạch của kho mã nguồn trước khi triển khai.

- [x] T001 Kiểm tra môi trường Node.js 20+, Python 3.10+, Playwright và xác nhận nhánh git `070-render-generation-import-seed-hardening` sạch sẽ

---

## Phase 2: Foundational (Hạ tầng Cốt lõi & Bản chụp Trạng thái Bất biến)

**Purpose**: Khởi tạo biến lưu trữ bản chụp đã cam kết, bộ đếm thế hệ nhập tệp, và các hàm tiện ích so sánh sâu tùy chọn viết chữ.

**⚠️ CRITICAL**: Các User Stories phía sau phụ thuộc vào các hợp đồng cơ sở này.

- [x] T002 Khai báo `renderedSnapshot = null`, `currentImportGeneration = 0`, hằng số bản mẫu `DEFAULT_WRITE_OPTIONS`, và xây dựng các hàm tiện ích `cloneWriteOptions(opts)`, `areWriteOptionsEqual(opt1, opt2)` trong `webapp/js/write.js`
- [x] T003 Nâng cấp hàm dọn dẹp kiểm thử `resetWriteSyncStateForTesting()` trong `webapp/js/write.js`: xóa `debounceTimer`, khôi phục `DEFAULT_WRITE_OPTIONS`, `currentFormat = "md"`, `currentImportGeneration = 0`, `renderedSnapshot = null`, `renderedGeneration = 0`, `isRenderStale = false`, `xoppDecompressor = null`, và `activeRenderBarrier = null`

**Checkpoint**: Hạ tầng bản chụp đã cam kết và tiện ích so sánh tùy chọn sẵn sàng.

---

## Phase 3: User Story 1 - Khóa xuất tệp nghiêm ngặt theo Thế hệ Kết xuất và Bản chụp Tùy chọn Đầy đủ (Priority: P1) 🎯 MVP

**Goal**: Triển khai `canExport()` kiểm tra đủ 7 điều kiện bất biến (đối chiếu `renderedGeneration === currentRenderGeneration` và so sánh sâu `renderedSnapshot` gồm text, format, options); lưu trữ `renderedSnapshot` tại thời điểm Atomic Commit; đánh dấu `isRenderStale = true` ngay khi người dùng chỉnh sửa tùy chọn viết chữ hoặc khi yêu cầu kết xuất mới bắt đầu/thất bại.

**Independent Test**: Chạy `node --test tests/js/render_generation.test.mjs` xác nhận `canExport()` trả về `false` khi thay đổi cỡ chữ/seed/màu sắc/khổ giấy, khi đổi định dạng, hoặc khi kết xuất mới bị lỗi từ Worker.

### Tests cho User Story 1 (TDD - Viết test trước) 🧪

- [x] T004 [P] [US1] Bổ sung các ca kiểm thử đơn vị trong `tests/js/render_generation.test.mjs` kiểm chứng `canExport()` trả về `false` khi thay đổi `writeOptions` (cỡ chữ, seed, màu sắc, khổ giấy), khi đổi `currentFormat`, hoặc khi yêu cầu kết xuất mới nhất bị thất bại (Worker error)

### Implementation cho User Story 1

- [x] T005 [US1] Triển khai lưu trữ bản chụp bất biến `renderedSnapshot` trong `requestRender()` tại `webapp/js/write.js` khi Atomic Commit thành công (bao gồm `generation`, `text`, `format` và bản sao sâu `options`)
- [x] T006 [US1] Đánh dấu `isRenderStale = true` và gọi `updateExportButtonsState()` khi bắt đầu `requestRender()`, và trong toàn bộ các bộ lắng nghe sự kiện thay đổi tùy chọn viết chữ tại `setupOptionsModal()` trong `webapp/js/write.js`
- [x] T007 [US1] Nâng cấp hàm `canExport()` trong `webapp/js/write.js` kiểm tra đầy đủ 7 điều kiện bất biến (`!isRendering`, `!isRenderStale`, `renderedGeneration > 0 && renderedGeneration === currentRenderGeneration`, dữ liệu hợp lệ, `textarea.value === renderedSnapshot.text`, `currentFormat === renderedSnapshot.format`, và `areWriteOptionsEqual`)
- [x] T008 [US1] Thực thi kiểm thử đơn vị `node --test tests/js/render_generation.test.mjs` xác nhận toàn bộ các kịch bản của User Story 1 đạt 100% PASS

**Checkpoint**: User Story 1 hoàn tất độc lập. Rủi ro xuất nhầm tệp cũ khi đổi tùy chọn hoặc khi render mới bị lỗi bị triệt tiêu 100%.

---

## Phase 4: User Story 2 - Chống ghi đè khi Mở nhiều Tệp liên tiếp và Bảo toàn Hạt giống khi Nhập tệp (Priority: P1)

**Goal**: Triển khai bộ đếm thế hệ nhập tệp `currentImportGeneration` trong `handleFileImport()`, đảm bảo chỉ có tệp được chọn cuối cùng mới được áp dụng vào ô soạn thảo và kết xuất; hủy bỏ mọi kết quả hoàn tất muộn của tệp cũ (kể cả khi `.docx` hoàn tất chậm hơn `.txt` hoặc ngược lại); dừng nạp tệp nếu reset hạt giống thất bại; cập nhật `currentFormat` độc lập DOM và không để nhánh `.docx` cũ tắt nhầm đèn báo kết xuất của tệp mới.

**Independent Test**: Chạy `node --test tests/js/render_generation.test.mjs` xác nhận khi mở tệp $A$ (`.docx`) rồi mở tiếp $B$ (`.txt`) và ngược lại, chỉ có tệp mở sau cùng được giữ lại trong ô soạn thảo.

### Tests cho User Story 2 (TDD - Viết test trước) 🧪

- [x] T009 [P] [US2] Bổ sung các bài kiểm thử đơn vị trong `tests/js/render_generation.test.mjs` mô phỏng mở liên tiếp 2 tệp lệch thứ tự hoàn tất (.docx chậm hơn .txt và .txt chậm hơn .docx), khẳng định chỉ có tệp mở sau cùng được cập nhật vào textarea

### Implementation cho User Story 2

- [x] T010 [US2] Tái cấu trúc `handleFileImport()` trong `webapp/js/write.js`: gán `const thisImportGen = ++currentImportGeneration;`, kiểm tra `thisImportGen === currentImportGeneration` sau mọi điểm `await` (đọc text, reset seed, đọc buffer, `import_docx`)
- [x] T011 [US2] Cập nhật `handleFileImport()` trong `webapp/js/write.js`: gán `currentFormat` trực tiếp theo phần mở rộng tệp độc lập với `#select-format`; không gọi `clearPreview()` hoặc sửa `pendingImportNotices` nếu thế hệ nhập tệp đã cũ; trong khối `finally` của `.docx` chỉ gọi `showRenderingIndicator(false)` khi `!isRendering && thisImportGen === currentImportGeneration`
- [x] T012 [US2] Thực thi kiểm thử đơn vị `node --test tests/js/render_generation.test.mjs` xác nhận các kịch bản mở nhiều tệp liên tiếp và xử lý lỗi reset hạt giống đạt 100% PASS

**Checkpoint**: User Story 2 hoàn tất độc lập. Thứ tự mở tệp được bảo toàn an toàn tuyệt đối, loại trừ hoàn toàn race condition nhập tệp.

---

## Phase 5: User Story 3 - Kiểm thử Xác định 100% cho Race Condition và Giải phóng Tài nguyên Kiểm thử (Priority: P2)

**Goal**: Cung cấp hook `setXoppDecompressorForTesting` để kiểm chứng trực tiếp Stage 2 Stale Guard (sau giải nén XOPP) trong kiểm thử đơn vị; cung cấp hook `installRenderBarrierForTesting` theo cơ chế one-shot để xác định hóa 100% bài kiểm thử E2E race condition trên trình duyệt.

**Independent Test**: Chạy `node --test tests/js/render_generation.test.mjs` và `npx playwright test tests/e2e/write.spec.ts` xác nhận 100% kịch bản đạt PASS ổn định không phụ thuộc vào `setTimeout` phỏng đoán.

### Implementation & Test cho User Story 3

- [x] T013 [P] [US3] Bổ sung hook `setXoppDecompressorForTesting` trong `webapp/js/write.js` và viết bài kiểm thử đơn vị trong `tests/js/render_generation.test.mjs` tạm dừng bước giải nén XOPP của tài liệu $A$, kích hoạt $B$, chứng minh Stage 2 loại bỏ $A$ sau khi giải nén xong
- [x] T014 [US3] Bổ sung hook `installRenderBarrierForTesting` theo cơ chế tiêu thụ một lần (one-shot) trong `webapp/js/write.js` cho phép bắt giữ và tạm giữ phản hồi của yêu cầu kết xuất đang in-flight
- [x] T015 [US3] Nâng cấp bài kiểm thử E2E race condition trong `tests/e2e/write.spec.ts`: sử dụng `installRenderBarrierForTesting` để xác nhận Worker đang bận xử lý $A$ trước khi mở tệp $B$, loại bỏ hoàn toàn sự phụ thuộc vào thời gian chờ cố định
- [x] T016 [US3] Thực thi `node --test tests/js/render_generation.test.mjs` và `npx playwright test tests/e2e/write.spec.ts` xác nhận tính xác định 100%

**Checkpoint**: User Story 3 hoàn tất. Cả Stage 2 Stale Guard và E2E race condition đều có bằng chứng kiểm thử thực nghiệm xác định 100%.

---

## Phase 6: User Story 4 - Ổn định hóa Kiểm thử Bảo mật XSS trên CI và Đồng bộ Tài liệu (Priority: P2)

**Goal**: Khắc phục triệt để hiện tượng `#bank-error-banner` bị ẩn trên CI khi chạy `--workers=2` do race condition với `refreshBankView()`, bảo đảm toàn bộ các job CI đều xanh.

**Independent Test**: Chạy `npx playwright test tests/e2e/bank.spec.ts --workers=2` xác nhận bài test XSS đạt 100% PASS.

### Implementation & Test cho User Story 4

- [x] T017 [P] [US4] Di chuyển lệnh `showBankErrorBanner(null)` lên đầu khối `try` của hàm `refreshBankView()` trong `webapp/js/bank.js` trước mọi điểm `await` bất đồng bộ để tránh xóa nhầm thông báo lỗi phát sinh trong thời gian chờ
- [x] T018 [US4] Cập nhật bài kiểm thử `tests/e2e/bank.spec.ts:137`: đợi `await bankModule.refreshBankView()` hoàn tất ổn định trước khi gọi `showBankErrorBanner("<b id='xss-test-payload'>...")`
- [x] T019 [US4] Chạy kiểm thử Playwright với 2 workers `npx playwright test tests/e2e/bank.spec.ts --workers=2` nhiều lần xác nhận bài test XSS đạt 100% PASS không còn flaky

**Checkpoint**: User Story 4 hoàn tất. Loại bỏ hoàn toàn nguyên nhân gây lỗi job Playwright trên CI GitHub Actions.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Đóng gói phân phối web sạch và kiểm thử hồi quy toàn diện trên toàn bộ kho mã nguồn.

- [x] T020 Đóng gói phân phối tĩnh Web Client sạch bằng `python scripts/build_web.py`
- [x] T021 [P] Chạy kiểm tra ruff lint `python -m ruff check chuviettay tests`
- [x] T022 Chạy kiểm thử đơn vị & Golden Master Node.js (`npm run test:unit`, `npm run test:browser`, `npm run test:golden`)
- [x] T023 Chạy kiểm thử hồi quy toàn diện Playwright E2E chạy song song (`npx playwright test --workers=2`) đảm bảo toàn bộ 24 bài test đạt 100% PASS
- [x] T024 [P] Chạy kiểm thử hồi quy toàn diện bộ test Python (`pytest tests/test_stable_variants.py tests/test_performance_regression.py -v`)
- [x] T025 Cập nhật bảng ghi nhận kết quả kiểm chứng thực tế trong `specs/070-render-generation-import-seed-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc — chạy đầu tiên.
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1 — khối hạ tầng bắt buộc trước khi triển khai các User Story.
- **User Story 1 (Phase 3)**: Phụ thuộc vào Phase 2 — triển khai `canExport()` kiểm tra thế hệ kết xuất và `renderedSnapshot`.
- **User Story 2 (Phase 4)**: Phụ thuộc vào Phase 2 — triển khai `currentImportGeneration` cho `handleFileImport()`.
- **User Story 3 (Phase 5)**: Phụ thuộc vào Phase 3 và Phase 4 — triển khai các hook kiểm thử xác định.
- **User Story 4 (Phase 6)**: Độc lập với tab Viết chữ — sửa race condition trong `bank.js` và `bank.spec.ts`.
- **Polish (Phase 7)**: Phụ thuộc vào việc hoàn tất toàn bộ các User Story trước đó.

### User Story Dependencies

- **User Story 1 (P1)**: Bắt đầu ngay sau Phase 2.
- **User Story 2 (P1)**: Bắt đầu ngay sau Phase 2 (có thể chạy song song với US1).
- **User Story 3 (P2)**: Bắt đầu sau khi US1 và US2 có mã nguồn cơ bản để gắn hook kiểm thử.
- **User Story 4 (P2)**: Có thể thực hiện song song với US1, US2, US3 vì nằm trên tệp `bank.js` và `bank.spec.ts`.

### Parallel Opportunities

- `T004` (Test US1), `T009` (Test US2), `T013` (Test US3), `T017` (Fix bank.js) đều được đánh dấu `[P]` và có thể tiến hành song song.
- `T021` (Ruff lint) và `T024` (Pytest) có thể chạy song song với việc đóng gói web và chạy Playwright.

---

## Parallel Example: User Story 1 & User Story 2

```bash
# Developer / Agent A: Triển khai User Story 1 (canExport & renderedSnapshot)
Task: "T004 [P] [US1] Bổ sung các ca kiểm thử đơn vị trong tests/js/render_generation.test.mjs"
Task: "T005 [US1] Triển khai lưu trữ bản chụp bất biến renderedSnapshot trong webapp/js/write.js"

# Developer / Agent B: Triển khai User Story 4 (Sửa lỗi race condition trong bank.js & bank.spec.ts)
Task: "T017 [P] [US4] Di chuyển lệnh showBankErrorBanner(null) lên đầu khối try của hàm refreshBankView() trong webapp/js/bank.js"
Task: "T018 [US4] Cập nhật bài kiểm thử tests/e2e/bank.spec.ts:137"
```

---

## Implementation Strategy

### MVP First (User Story 1 & Foundational)
1. Hoàn thành Phase 1 (Setup) và Phase 2 (Foundational: bản chụp `renderedSnapshot` và tiện ích so sánh tùy chọn).
2. Hoàn thành Phase 3 (User Story 1: khóa xuất tệp theo `renderedGeneration` và `writeOptions`).
3. Chạy `node --test tests/js/render_generation.test.mjs` nghiệm thu MVP độc lập.

### Incremental Delivery
1. Hoàn thành User Story 2: Bộ đếm thế hệ nhập tệp `currentImportGeneration` chống ghi đè khi mở nhiều tệp liên tiếp.
2. Hoàn thành User Story 3: Cung cấp hook kiểm thử xác định cho Stage 2 Stale Guard và E2E race condition.
3. Hoàn thành User Story 4: Ổn định hóa bài kiểm thử XSS trên `bank.spec.ts` chạy `--workers=2`.
4. Thực thi Phase 7: Build tĩnh sạch, kiểm thử hồi quy toàn diện (Node unit, Golden master, Playwright E2E `--workers=2`, Pytest).
