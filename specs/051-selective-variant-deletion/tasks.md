# Tasks: Chọn và Xóa Biến Thể Mẫu Nét Tùy Chọn Trong Kho Mẫu

**Input**: Design documents from `/specs/051-selective-variant-deletion/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Có thể thực hiện song song (tập tin khác nhau, không có phụ thuộc chưa hoàn thành)
- **[Story]**: Đánh dấu User Story tương ứng (`[US1]`, `[US2]`, `[US3]`) theo `spec.md`
- Mỗi tác vụ đều có đường dẫn tập tin cụ thể và có thể thực thi độc lập

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Chuẩn bị môi trường kiểm thử và cấu trúc tập tin

- [x] T001 Khởi tạo tệp kiểm thử tự động mới cho tính năng xóa biến thể tại `tests/test_bank_variant_deletion.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Triển khai hạ tầng tầng cốt lõi Python và cầu nối IPC - BẮT BUỘC hoàn thành trước khi triển khai giao diện User Stories

- [x] T002 Cài đặt phương thức `Bank.drop_samples(label, indices, category)` với thuật toán xóa chỉ số giảm dần, an toàn luồng `self._lock`, cờ dirty, generation counter, dọn dẹp nhãn rỗng và tái lập chỉ mục `tl`/`marks` trong `chuviettay/model/bank.py`
- [x] T003 [P] Cài đặt phương thức `AppController.drop_label_samples(label, indices, category)` thực thi lưu đĩa `bank.save()` và ghi log trong `chuviettay/controller/app_controller.py`
- [x] T004 [P] Cài đặt phương thức `BrowserBridge.drop_label_samples(label, indices, category)` trả về phản hồi chuẩn dạng `{"ok": True, "data": ...}` trong `chuviettay/browser/bridge.py`
- [x] T005 Khai báo message handler cho phương thức `"drop_label_samples"` trong `webapp/js/worker/py-worker.js`
- [x] T006 [P] Viết bộ kiểm thử đơn vị tự động hoàn chỉnh cho `drop_samples` trên `Bank`, `AppController` và `BrowserBridge` bao phủ các nhóm ký tự và điều kiện biên trong `tests/test_bank_variant_deletion.py`

**Checkpoint**: Tầng dữ liệu và IPC đã hoàn thiện và kiểm thử thành công — có thể bắt đầu triển khai các User Story.

---

## Phase 3: User Story 1 - Chọn và xóa nhiều biến thể mẫu nét cụ thể của một nhãn (Priority: P1) 🎯 MVP

**Goal**: Cho phép người dùng tích chọn nhiều thẻ biến thể trong modal chi tiết nhãn, hiển thị số lượng đã chọn, và xóa hàng loạt các biến thể đã chọn kèm xác nhận an toàn.

**Independent Test**: Mở modal chi tiết của một nhãn có $\ge 3$ mẫu nét, tích chọn 2 mẫu, bấm nút xóa, xác nhận, kiểm tra chỉ 2 mẫu đó bị loại bỏ, các mẫu còn lại giữ nguyên và đánh lại số thứ tự.

### Implementation for User Story 1

- [x] T007 [P] [US1] Thêm thanh công cụ thao tác hàng loạt `#modal-samples-batch-bar`, hộp kiểm `#chk-modal-select-all` và nút `#btn-label-delete-selected` vào modal chi tiết nhãn trong `webapp/index.html`
- [x] T008 [P] [US1] Bổ sung định kiểu CSS cho thẻ mẫu nét khi được chọn `.sample-item-card.selected`, hộp kiểm góc `.sample-item-checkbox` và thanh công cụ trong `webapp/css/style.css`
- [x] T009 [US1] Cài đặt quản lý tập hợp chọn `modalSelectedIndices`, sự kiện tích chọn thẻ, chọn tất cả, và hàm cập nhật thanh công cụ `updateModalBatchBar` trong `webapp/js/bank.js`
- [x] T010 [US1] Cài đặt hàm xử lý xóa hàng loạt `handleDeleteSelectedVariants` với hộp thoại xác nhận an toàn, cờ khóa in-flight guard `isDeletingVariants`, gọi IPC worker, đồng bộ `storage.syncAndSaveActiveProfile`, và cập nhật kho trong `webapp/js/bank.js`
- [x] T011 [US1] Xây dựng hàm `loadAndRenderModalSamples(label, category)` trong `webapp/js/bank.js` để nạp và kết xuất lại lưới thumbnail an toàn qua `escapeHtml()`, tự động ẩn `#modal-random-preview-box`, cập nhật số lượng mẫu và nhãn độ phủ

**Checkpoint**: User Story 1 (MVP) hoàn chỉnh và có thể kiểm thử độc lập trên trình duyệt.

---

## Phase 4: User Story 2 - Xóa nhanh từng biến thể mẫu nét đơn lẻ (Priority: P2)

**Goal**: Cung cấp nút biểu tượng thùng rác trên từng thẻ mẫu nét để xóa ngay 1 biến thể bị lỗi mà không cần qua nhiều bước tích chọn.

**Independent Test**: Bấm biểu tượng thùng rác trên thẻ Mẫu #2, xác nhận trong hộp thoại, kiểm tra chỉ duy nhất Mẫu #2 bị loại bỏ và danh sách mẫu được đánh lại số thứ tự ngay lập tức.

### Implementation for User Story 2

- [x] T012 [P] [US2] Thêm nút xóa nhanh `.sample-item-delete-btn` vào cấu trúc HTML của thẻ mẫu nét khi render và bổ sung CSS hover/focus trong `webapp/js/bank.js` và `webapp/css/style.css`
- [x] T013 [US2] Cài đặt hàm xử lý xóa nhanh `handleQuickDeleteVariant` với hộp thoại xác nhận riêng lẻ, kiểm soát cờ `isDeletingVariants`, gửi IPC worker với `indices: [idx]`, đồng bộ hồ sơ và nạp lại lưới mẫu trong `webapp/js/bank.js`

**Checkpoint**: Cả User Story 1 và User Story 2 đều hoạt động độc lập và bổ trợ lẫn nhau.

---

## Phase 5: User Story 3 - Xử lý an toàn khi xóa toàn bộ biến thể hoặc xóa sạch nhãn (Priority: P3)

**Goal**: Hệ thống tự động phát hiện khi tất cả các biến thể của nhãn bị xóa sạch (hoặc xóa biến thể cuối cùng), dọn dẹp nhãn khỏi kho, ghi nhận tombstone đồng bộ đa tab, đóng modal chi tiết và làm mới danh sách kho mẫu bên ngoài.

**Independent Test**: Xóa biến thể cuối cùng còn lại của một nhãn (hoặc tích chọn tất cả các mẫu rồi xóa), xác nhận cảnh báo xóa toàn bộ nhãn, kiểm tra modal tự đóng và nhãn biến mất khỏi giao diện kho mẫu nét.

### Implementation for User Story 3

- [x] T014 [US3] Hoàn thiện logic dọn dẹp nhãn rỗng trong `Bank.drop_samples` khi `remaining_count == 0`: loại bỏ nhãn khỏi từ điển mục tiêu, ghi nhận tombstone `{cat}:{label}` vào `_tombstones` và `_deleted_words`, dọn dẹp `tl`/`marks` và trả về `label_deleted: True` trong `chuviettay/model/bank.py`
- [x] T015 [US3] Cài đặt xử lý phản hồi `label_deleted: true` trong `webapp/js/bank.js` để tự động đóng modal `#modal-label-detail`, xóa rỗng `currentDetailLabel`, gọi đồng bộ lưu trữ và làm mới danh sách nhãn qua `refreshBankView()`

**Checkpoint**: Toàn bộ luồng xóa biến thể và xóa sạch nhãn hoạt động an toàn và đồng bộ đa tab.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm thử bảo mật DOM, đóng gói bản phát hành web và nghiệm thu toàn diện

- [x] T016 [P] Bổ sung ca kiểm thử an toàn DOM trong `tests/js/bank_safety.test.mjs` xác minh các phần tử `#btn-label-delete-selected`, `.sample-item-checkbox`, `.sample-item-delete-btn` và hợp đồng `escapeHtml()`
- [x] T017 Chạy script đóng gói web `python scripts/build_web.py` để đóng gói lại `chuviettay.zip` và cập nhật các tệp web sang `webapp/dist/`
- [x] T018 Chạy kiểm thử toàn vẹn bản đóng gói web qua `pytest tests/test_build_web.py`
- [x] T019 Thực hiện kiểm chứng nghiệm thu thủ công E2E theo hướng dẫn trong `specs/051-selective-variant-deletion/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc — có thể bắt đầu ngay
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1 — CHẶN (BLOCK) toàn bộ các User Story
- **User Story 1 (Phase 3)**: Phụ thuộc vào Phase 2 hoàn thành — Là MVP cốt lõi
- **User Story 2 (Phase 4)**: Phụ thuộc vào Phase 2 và tích hợp với hàm render của Phase 3
- **User Story 3 (Phase 5)**: Phụ thuộc vào Phase 2 và liên kết với luồng kết thúc của Phase 3/Phase 4
- **Polish (Phase 6)**: Phụ thuộc vào việc hoàn tất các User Story

### User Story Dependencies

- **User Story 1 (P1)**: Có thể triển khai ngay sau Phase 2, cung cấp tính năng chọn và xóa nhiều biến thể hoàn chỉnh.
- **User Story 2 (P2)**: Tái sử dụng hàm `loadAndRenderModalSamples` từ US1, gắn thêm nút xóa nhanh 1 click trên mỗi thẻ.
- **User Story 3 (P3)**: Tích hợp nhánh kiểm tra `label_deleted` vào callback của cả US1 và US2.

### Cơ hội chạy Song song (Parallel Opportunities)

- Trong Phase 2: `T003` (`app_controller.py`), `T004` (`bridge.py`) và `T006` (`tests/`) có thể viết song song.
- Trong Phase 3 (US1): `T007` (`index.html`) và `T008` (`style.css`) có thể thực hiện song song trước khi hoàn thiện `T009` và `T010` (`bank.js`).
- Trong Phase 6: `T016` (`bank_safety.test.mjs`) có thể chạy song song với việc đóng gói web `T017`.

---

## Parallel Example: User Story 1

```bash
# Thực hiện song song phần giao diện HTML và CSS:
Task T007: Thêm thanh công cụ batch delete vào webapp/index.html
Task T008: Bổ sung CSS cho .sample-item-card.selected và checkbox vào webapp/css/style.css
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Hoàn thành Phase 1 & Phase 2 (Cốt lõi Python + IPC bridge + Unit tests).
2. Hoàn thành Phase 3 (User Story 1: Tích chọn nhiều biến thể và xóa hàng loạt).
3. **Dừng và Kiểm chứng**: Chạy `pytest tests/test_bank_variant_deletion.py` và kiểm tra trên giao diện web. Đạt MVP!

### Incremental Delivery

1. Phase 1 + Phase 2 → Nền tảng cốt lõi sẵn sàng
2. Phase 3 (US1) → Đạt MVP: Xóa nhiều biến thể đã chọn
3. Phase 4 (US2) → Tiện ích mở rộng: Nút xóa nhanh 1-click trên thẻ
4. Phase 5 (US3) → Toàn vẹn dữ liệu: Xử lý xóa cạn kiệt và dọn dẹp nhãn
5. Phase 6 → Kiểm thử bảo mật DOM, đóng gói `scripts/build_web.py` và E2E
