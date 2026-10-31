---
description: "Danh sách nhiệm vụ thực thi TDD cho tính năng 068-seed-bank-e2e-hardening"
---

# Tasks: Hoàn thiện Đối chiếu Hạt giống Đa bước, Đồng bộ Phiên bản Kho mẫu và Khắc phục Kiểm thử E2E (068-seed-bank-e2e-hardening)

**Input**: Design documents from `specs/068-seed-bank-e2e-hardening/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Organization**: Các nhiệm vụ được nhóm theo User Story để hỗ trợ thực thi và kiểm thử độc lập từng giai đoạn theo chuẩn TDD.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Có thể thực hiện song song (khác tệp tin, không phụ thuộc vào nhiệm vụ chưa hoàn tất).
- **[Story]**: Gắn với User Story tương ứng (`[US1]`, `[US2]`, `[US3]`, `[US4]`).
- Tất cả các nhiệm vụ đều chứa đường dẫn tệp tin cụ thể và hành động rõ ràng.

---

## Phase 1: Setup (Môi trường & Công cụ)

**Purpose**: Xác thực môi trường và công cụ thực thi trước khi bắt đầu triển khai code.

- [x] T001 Kiểm tra môi trường thực thi và kiểm thử hiện tại (`pytest`, `playwright`, `pyodide`) theo `specs/068-seed-bank-e2e-hardening/quickstart.md`

---

## Phase 2: Foundational (Cơ sở chung)

**Purpose**: Các thành phần hạ tầng và trạng thái cơ sở chặn trước khi triển khai các User Story.

- [x] T002 Bổ sung thuộc tính định danh thế hệ tiến trình `worker_epoch = str(uuid.uuid4())` vào phương thức khởi tạo của `BrowserBridge` trong `chuviettay/browser/bridge.py`
- [x] T003 [P] Bổ sung hai trường trạng thái `_last_doc: Document | None = None`, `_last_seed: int | None = None` và hàm `clear_document_history()` vào `AppController` trong `chuviettay/controller/app_controller.py`

**Checkpoint**: Nền tảng hạ tầng sẵn sàng — các User Story có thể bắt đầu triển khai.

---

## Phase 3: User Story 1 - Bảo toàn kiểu chữ khi sửa tài liệu có tiền tố ngắn và nhiều lượt liên tiếp (Priority: P1) 🎯 MVP

**Goal**: Khắc phục dứt điểm lỗi chồng lấn suffix lên prefix ngắn ($p < 3$) trong `align_document_seeds`, bảo toàn `token_occurrences` qua nhiều lượt chỉnh sửa liên tiếp ($D_0 \to D_1 \to D_2 \to \dots$), đồng bộ hóa `norm.split()` cho `Text` node và tích hợp vào `AppController.write_document()`.

**Independent Test**: Chạy bài test với tài liệu có tiền tố 1–2 token kèm từ lặp (`"là là đi học"` $\to$ `"là là mới là đi học"`), xác nhận 2 từ `"là"` đầu tiên giữ nguyên `occurrence = 0, 1` và từ mới nhận `occurrence = 2`; kiểm thử chuỗi 3 lượt sửa liên tiếp giữ nguyên hình thái nét chữ.

### Tests cho User Story 1 (TDD - Viết test trước, xác nhận FAIL) 🧪

- [x] T004 [P] [US1] Viết unit tests TDD cho tiền tố ngắn $p < 3$ không bị suffix overlap (`"là là đi học"` $\to$ `"là là mới là đi học"`, `"là đi học"` $\to$ `"là mới là đi học"`) trong `tests/test_stable_variants.py`
- [x] T005 [P] [US1] Viết unit tests TDD cho chuỗi nhiều lượt chỉnh sửa liên tiếp ($D_0 \to D_1 \to D_2 \to D_3$) bảo toàn `token_occurrences` và tích hợp `AppController.write_document` khi `stable_variants=True` trong `tests/test_stable_variants.py`

### Implementation cho User Story 1

- [x] T006 [US1] Sửa lỗi thuật toán cắt suffix trong `align_document_seeds` với `max_suffix = min_len - p` trong `chuviettay/document/ir.py`
- [x] T007 [US1] Cập nhật hàm `extract_doc_elements` đọc và bảo toàn `token_occurrences` trên `Text` và `occurrence` trên các node IR khác, đồng thời cập nhật `counts[key] = max(counts.get(key, 0), occ + 1)` trong `chuviettay/document/ir.py`
- [x] T008 [US1] Đồng bộ hóa việc tái tạo `node.token_occurrences` sử dụng `len(_normalize_text(node.text or "").split())` trong `chuviettay/document/ir.py`
- [x] T009 [US1] Tích hợp `align_document_seeds` vào luồng `AppController.write_document` khi `opts.stable_variants is True` và tự động gọi `clear_document_history()` trong `AppController.load_bank` hoặc khi tài liệu rỗng trong `chuviettay/controller/app_controller.py`
- [x] T010 [US1] Chạy kiểm thử xác nhận độc lập cho User Story 1 trong `tests/test_stable_variants.py`

**Checkpoint**: User Story 1 (MVP) hoàn tất độc lập và vượt qua toàn bộ các ca kiểm thử bảo toàn biến thể nét chữ.

---

## Phase 4: User Story 2 - Đồng bộ phiên bản Kho mẫu và khắc phục toàn bộ kiểm thử E2E Playwright (Priority: P1)

**Goal**: Khắc phục lỗi `ReferenceError: currentProfileId`, đồng bộ số hiệu phiên bản kho mẫu hai thành phần (`worker_epoch`, `bank_revision`) qua thao tác lưu/khởi tạo lại tiến trình, đưa 100% bài test Playwright E2E về trạng thái PASS.

**Independent Test**: Chạy `npx playwright test` xác nhận 20/20 bài test E2E vượt qua, `#bank-summary` hiển thị số lượng mẫu chữ chuẩn xác và không còn lỗi ReferenceError trong browser console.

### Tests cho User Story 2 (TDD - Viết test trước) 🧪

- [x] T011 [P] [US2] Viết kiểm thử đơn vị cho việc tăng `bank_revision` khi gọi `sync_save` và kiểm tra trường `worker_epoch` trong `tests/test_bridge.py`

### Implementation cho User Story 2

- [x] T012 [US2] Sửa lỗi tham chiếu hồ sơ an toàn bằng `const activeProfileId = (await storage.getSetting("active_profile_id", "default_profile")) || "default_profile"` trong `webapp/js/bank.js`
- [x] T013 [US2] Cập nhật đối tượng bộ nhớ đệm `lastBankSnapshotCache` kiểm tra cả 3 yếu tố `{ epoch, revision, profileId }` trong `webapp/js/bank.js`
- [x] T014 [US2] Cập nhật nhánh `sync_save` trong `webapp/js/worker/py-worker.js` nạp lại kho mẫu nếu có `diskGzBytes` và luôn kích hoạt `_bridge.bank_revision += 1`
- [x] T015 [US2] Chạy xác nhận bộ kiểm thử E2E Playwright (`tests/e2e/bank.spec.ts`, `tests/e2e/grid-import.spec.ts`, `tests/e2e/multitab.spec.ts`, `tests/e2e/offline.spec.ts`)

**Checkpoint**: User Story 2 hoàn tất độc lập, tab Kho mẫu đồng bộ mượt mà và toàn bộ các kịch bản kiểm thử E2E trên trình duyệt đều xanh.

---

## Phase 5: User Story 3 - Đảm bảo tính nguyên tử của bản chụp Kho mẫu và hiển thị lỗi an toàn (Priority: P2)

**Goal**: Đảm bảo `BrowserBridge.get_bank_snapshot` kiểm tra trạng thái của tất cả các danh mục con (nguyên tử), và tái cấu trúc `showBankErrorBanner` sang DOM API an toàn triệt tiêu nguy cơ HTML Injection.

**Independent Test**: Giả lập lỗi truy vấn con trong `get_bank_snapshot` xác nhận trả về `ok: False` kèm thông điệp lỗi; truyền chuỗi chứa mã HTML vào `showBankErrorBanner` xác nhận hiển thị dạng text thuần không thực thi script.

### Tests cho User Story 3 (TDD - Viết test trước) 🧪

- [x] T016 [P] [US3] Viết unit test cho tính nguyên tử của `get_bank_snapshot` khi một truy vấn danh mục con thất bại trong `tests/test_bridge.py`
- [x] T017 [P] [US3] Viết E2E test xác nhận `showBankErrorBanner` hiển thị an toàn với thông điệp chứa thẻ HTML trong `tests/e2e/bank.spec.ts`

### Implementation cho User Story 3

- [x] T018 [US3] Cập nhật `get_bank_snapshot` trong `chuviettay/browser/bridge.py` kiểm tra tuần tự trạng thái `.ok` của `letters_res`, `symbols_res`, `marks_res` và bổ sung trường `worker_epoch`
- [x] T019 [US3] Tái cấu trúc hàm `showBankErrorBanner` trong `webapp/js/bank.js` sử dụng DOM API thuần (`replaceChildren`, `createElement`, `textContent`) thay thế `innerHTML`

**Checkpoint**: User Story 3 hoàn tất, tính nguyên tử dữ liệu kho mẫu và an toàn bảo mật giao diện được củng cố.

---

## Phase 6: User Story 4 - Đo kiểm hiệu năng bản chụp Kho mẫu quy mô lớn (Priority: P3)

**Goal**: Xây dựng kịch bản kiểm thử hồi quy hiệu năng tự động cho `get_bank_snapshot` trên kho mẫu lớn (1.000+ nhãn) với ngưỡng hoàn tất dưới 200ms.

**Independent Test**: Chạy `pytest tests/test_performance_regression.py -k "bank_snapshot_large_scale" -v` xác nhận $t < 200$ ms.

### Implementation & Test cho User Story 4

- [x] T020 [P] [US4] Bổ sung hàm đo kiểm hiệu năng `test_bank_snapshot_large_scale_performance` trên kho mẫu 1.000+ nhãn đa dạng trong `tests/test_performance_regression.py`
- [x] T021 [US4] Chạy và xác thực ngưỡng thời gian thực thi của bài đo kiểm hiệu năng snapshot trong `tests/test_performance_regression.py`

**Checkpoint**: User Story 4 hoàn tất, xác nhận hệ thống duy trì hiệu năng cao trên dữ liệu lớn.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm thử hồi quy toàn diện trên toàn bộ kho mã nguồn và đóng gói tài liệu.

- [x] T022 Chạy kiểm thử hồi quy toàn diện bộ test Python (`pytest`) đảm bảo hơn 1.410 bài test đạt 100% PASS
- [x] T023 Chạy kiểm thử hồi quy toàn diện bộ test Playwright E2E (`npx playwright test`) đảm bảo 20/20 bài test đạt 100% PASS
- [x] T024 [P] Cập nhật tài liệu kiểm chứng trong `specs/068-seed-bank-e2e-hardening/quickstart.md` với kết quả chạy thực tế

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc — chạy đầu tiên.
- **Foundational (Phase 2)**: Phụ thuộc vào Setup — **CHẶN** tất cả các User Stories.
- **User Stories (Phase 3+)**: Phụ thuộc vào hoàn tất Phase 2.
  - Có thể thực thi tuần tự theo mức độ ưu tiên: US1 (P1 - MVP) $\to$ US2 (P1) $\to$ US3 (P2) $\to$ US4 (P3).
- **Polish (Phase 7)**: Phụ thuộc vào toàn bộ 4 User Stories đã hoàn thành.

### User Story Dependencies

- **User Story 1 (P1)**: Phụ thuộc Phase 2 (T003). Độc lập với US2, US3, US4.
- **User Story 2 (P1)**: Phụ thuộc Phase 2 (T002). Độc lập với US1, US3, US4.
- **User Story 3 (P2)**: Phụ thuộc Phase 2 (T002) và US2 (T012).
- **User Story 4 (P3)**: Phụ thuộc Phase 2 (T002) và US3 (T018).

### Within Each User Story

- Viết test trước, chạy test xác nhận thất bại (TDD).
- Sửa logic thuật toán / dữ liệu cốt lõi trước.
- Tích hợp controller / worker / bridge tiếp theo.
- Chạy kiểm thử xác nhận thành công trước khi chuyển sang story tiếp theo.

---

## Parallel Opportunities

- **Setup & Foundational**: T002 và T003 có thể chạy song song (2 tệp khác nhau: `bridge.py` và `app_controller.py`).
- **User Story 1**: T004 và T005 có thể viết song song; T006, T007, T008 có thể triển khai liên tục trên `ir.py`.
- **User Story 2**: T011 có thể chạy song song với việc chuẩn bị `bank.js` và `py-worker.js`.
- **User Story 3 & 4**: T016, T017 và T020 có thể viết test song song.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Hoàn thành Phase 1 (Setup) & Phase 2 (Foundational).
2. Viết test TDD cho User Story 1 (T004, T005).
3. Triển khai T006, T007, T008 trong `chuviettay/document/ir.py`.
4. Triển khai T009 trong `chuviettay/controller/app_controller.py`.
5. **DỪNG LẠI & XÁC THỰC**: Chạy T010 để kiểm chứng độc lập User Story 1.

### Incremental Delivery
1. Sau khi MVP (US1) xanh $\to$ Chuyển sang User Story 2 (Khắc phục E2E Playwright và đồng bộ revision).
2. Sau khi US2 xanh (20/20 E2E pass) $\to$ Chuyển sang User Story 3 (Tính nguyên tử snapshot & an toàn DOM).
3. Sau khi US3 xanh $\to$ Chuyển sang User Story 4 (Đo kiểm hiệu năng snapshot 1.000+ nhãn).
4. Thực thi Phase 7 (Polish & Cross-cutting verification).
