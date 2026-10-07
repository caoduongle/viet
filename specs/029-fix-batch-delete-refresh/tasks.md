# Tasks: Khắc Phục Lỗi Làm Mới Khi Xóa Hàng Loạt Trên Web Client

**Input**: Design documents from `specs/029-fix-batch-delete-refresh/`
**Feature Name**: `029-fix-batch-delete-refresh`

---

## Phase 1: Setup

**Purpose**: Định vị và chuẩn bị các tệp nguồn cần sửa đổi

- [X] T001 Khảo sát và định vị toàn bộ các vị trí chứa lời gọi `refreshBankTab` trong `webapp/js/bank.js` và `webapp/dist/js/bank.js`

---

## Phase 2: Foundational

**Purpose**: Xác thực hợp đồng định danh và cơ chế làm mới tab Kho mẫu

- [X] T002 Xác thực hợp đồng định danh `refreshBankView()` trong `webapp/js/bank.js` theo `specs/029-fix-batch-delete-refresh/contracts/batch-delete-ui-contract.md`

---

## Phase 3: User Story 1 - Xóa hàng loạt ký tự trong Kho mẫu Web (Priority: P1) 🎯 MVP

**Goal**: Người dùng thực hiện thao tác "Xoá đã chọn" trên Web Client thành công và giao diện được làm mới ngay lập tức mà không có lỗi `refreshBankTab is not defined`.

**Independent Test**: Mở Web Client tại tab Kho mẫu, chọn một số ký tự, bấm nút "Xoá đã chọn", chấp nhận confirm; không có alert báo lỗi và các thẻ đã chọn biến mất khỏi giao diện.

### Implementation for User Story 1

- [X] T003 [US1] Thay thế lời gọi không tồn tại `await refreshBankTab()` bằng `await refreshBankView()` trong hàm `handleDeleteSelected()` tại `webapp/js/bank.js`
- [X] T004 [US1] Đảm bảo làm sạch `selectedLabels.clear()` và gọi cập nhật thanh công cụ chọn hàng loạt sau khi xóa trong `webapp/js/bank.js`
- [X] T005 [US1] Chạy kiểm tra đơn vị JS với `npm run test:unit` xác nhận cú pháp và các mô-đun Web Client tải bình thường

**Checkpoint**: User Story 1 hoàn tất - lỗi `ReferenceError` khi xóa hàng loạt được giải quyết triệt để trên mã nguồn phát triển.

---

## Phase 4: User Story 2 - Đồng bộ Bản phân phối & Kiểm thử E2E (Priority: P2)

**Goal**: Đồng bộ hóa bản build phân phối `webapp/dist/` và bổ sung kiểm thử tự động Playwright E2E chống hồi quy.

**Independent Test**: Chạy `npx playwright test tests/e2e/bank.spec.ts` kiểm chứng toàn diện luồng chọn nhiều nhãn $\to$ bấm xóa $\to$ xác nhận không có dialog lỗi.

### Implementation for User Story 2

- [X] T006 [P] [US2] Cập nhật đồng bộ lời gọi `refreshBankView()` trong tệp phân phối `webapp/dist/js/bank.js`
- [X] T007 [US2] Chạy script đóng gói web `py -3.12 scripts/build_web.py` để cập nhật toàn bộ thư mục `webapp/dist/` và làm mới hash cache-busting
- [X] T008 [US2] Bổ sung kịch bản kiểm thử E2E thao tác chọn và xóa hàng loạt thẻ ký tự trong `tests/e2e/bank.spec.ts`
- [X] T009 [US2] Chạy kiểm thử Playwright `npx playwright test tests/e2e/bank.spec.ts` để xác thực luồng xóa hàng loạt hoạt động hoàn hảo

**Checkpoint**: Toàn bộ bản phân phối và kiểm thử E2E hoàn tất, khẳng định không còn lỗi trên môi trường triển khai thực tế.

---

## Phase 5: Polish & CI Verification

**Purpose**: Rà soát chất lượng mã nguồn và đảm bảo toàn bộ pipeline CI xanh 100%

- [X] T010 [P] Chạy kiểm tra linter với `ruff check .`
- [X] T011 Chạy toàn diện bộ kiểm thử `npm run test:unit` và `npx playwright test tests/e2e/bank.spec.ts` xác nhận đạt trạng thái 100% PASS

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Thực hiện đầu tiên để định vị phạm vi.
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1 - Xác nhận hợp đồng hàm.
- **User Story 1 (Phase 3 - MVP)**: Phụ thuộc vào Phase 2 - Sửa lỗi cốt lõi trên mã nguồn JS.
- **User Story 2 (Phase 4)**: Phụ thuộc vào Phase 3 - Đóng gói dist và viết kiểm thử E2E.
- **Polish (Phase 5)**: Phụ thuộc vào việc hoàn thành User Story 1 và 2.

### Parallel Opportunities

- `T006` có thể chuẩn bị song song với `T003`.
- `T010` (ruff lint) có thể chạy song song trong pha Polish.

---

## Implementation Strategy

### MVP First (User Story 1)
1. Khắc phục ngay lỗi typo tại `webapp/js/bank.js:392` (`refreshBankTab` $\to$ `refreshBankView`).
2. Xác nhận luồng chạy trực tiếp không còn văng ReferenceError.

### Incremental Delivery
1. Đóng gói lại `webapp/dist/` bằng `scripts/build_web.py`.
2. Bổ sung test E2E Playwright để khóa chặt hành vi, không bao giờ để lỗi tái diễn.
