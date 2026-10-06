# Tasks: Sửa kích thước xem trước giấy và hình học xem trước tab Viết chữ

**Feature**: `specs/023-write-preview-paper-geometry`
**Date**: 2026-10-06
**Status**: Hoàn thành (Completed)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Chuẩn bị cấu trúc môi trường thử nghiệm và tài liệu

- [X] T001 [P] Cập nhật hướng dẫn cổng chạy máy chủ phát triển từ 8080 thành 8000 trong README.md
- [X] T002 Chuẩn bị file kịch bản kiểm thử Playwright E2E mới trong tests/e2e/paper-geometry.spec.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nền tảng tính toán kích thước hình học giấy theo đơn vị pixel CSS ($px = pt \times \frac{96}{72} \times zoom$)

- [X] T003 Cập nhật hàm tính toán kích thước pixel và render SVG theo kích thước thật trong webapp/js/paper.js
- [X] T004 Cập nhật kiểu dáng CSS cho khung giấy `.paper-frame` và vùng chứa cuộn `#preview-stage` trong webapp/css/style.css

**Checkpoint**: Nền tảng hình học pixel hoàn tất - các user story có thể triển khai tiếp

---

## Phase 3: User Story 1 - Kích thước giấy thật hiển thị chuẩn màn hình (Priority: P1) 🎯 MVP

**Goal**: Hiển thị trang giấy ở mức zoom 100% với kích thước thật (A4 dọc ~794 px thay vì bị co rút về 300 px) và giữ đúng tỷ lệ mọi khổ giấy.

**Independent Test**: Nạp kho mẫu thử `tests/data/kho_mau_tong_hop.json.gz`, gõ văn bản và đo kích thước phần tử SVG trên DOM ở zoom 100% đạt $\ge 700\text{ px}$.

### Tests for User Story 1
- [X] T005 [US1] Viết kịch bản kiểm thử Playwright đo kích thước thật của trang giấy ở 1920×1020 và 1366×768 trong tests/e2e/paper-geometry.spec.ts

### Implementation for User Story 1
- [X] T006 [US1] Áp dụng kích thước pixel layout cụ thể cho `.paper-frame` khi render nhiều trang trong webapp/js/write.js
- [X] T007 [US1] Đảm bảo tỷ lệ khung hình chuẩn khi đổi khổ giấy A4, A5, Letter và hướng xoay trang trong webapp/js/paper.js

**Checkpoint**: User Story 1 hoàn thành - Giấy hiển thị rõ ràng, nét chữ to tự nhiên, không còn chữ li ti.

---

## Phase 4: User Story 2 - Bộ điều khiển Zoom và chế độ Fit tự động (Priority: P1)

**Goal**: Thêm các nút bấm điều khiển zoom trực quan (`−`, `+`, `Fit`, `% display`), loại bỏ zoom bằng CSS transform để thanh cuộn trình duyệt hoạt động chính xác khi zoom lớn, và tự động căn vừa khi resize viewport.

**Independent Test**: Bấm `+` và `−` thay đổi zoom 50%–300%, bấm `Fit` giấy vừa khít khung xem trước không có thanh cuộn ngang, resize màn hình giấy tự động co giãn.

### Tests for User Story 2
- [X] T008 [US2] Viết kiểm thử Playwright cho chế độ Fit (không cuộn ngang) và phản hồi khi resize viewport trong tests/e2e/paper-geometry.spec.ts

### Implementation for User Story 2
- [X] T009 [P] [US2] Thêm giao diện HTML các nút điều khiển zoom (`btn-zoom-out`, `zoom-percent-display`, `btn-zoom-in`, `btn-zoom-fit`) trong webapp/index.html
- [X] T010 [P] [US2] Thêm kiểu dáng CSS cho bộ nút zoom trong webapp/css/style.css
- [X] T011 [US2] Triển khai logic điều khiển zoom layout thật, dải 50%–300%, tính toán Fit và lắng nghe ResizeObserver trong webapp/js/write.js

**Checkpoint**: User Story 2 hoàn thành - Điều khiển zoom mượt mà, cuộn tự nhiên, Fit tự thích ứng.

---

## Phase 5: User Story 3 - Chuẩn hóa kiểu giấy nền theo Xournal++ (Priority: P2)

**Goal**: Sửa đảo ngược quy ước giữa `lined` và `ruled` theo chuẩn Xournal++ v1.2.6 (`lined` = dòng kẻ + lề đỏ; `ruled` = chỉ dòng kẻ), cập nhật nhãn tiếng Việt trên UI và đặt mặc định là `lined`.

**Independent Test**: Chọn kiểu giấy `lined` thấy vạch lề đỏ bên trái; chọn `ruled` chỉ thấy dòng ngang; xuất `.xopp` bảo toàn định dạng.

### Tests for User Story 3
- [X] T012 [US3] Viết kiểm thử Playwright xác minh hiển thị đường kẻ và về lề đỏ cho `lined` và `ruled` trong tests/e2e/paper-geometry.spec.ts

### Implementation for User Story 3
- [X] T013 [P] [US3] Sửa điều kiện vẽ vạch lề đỏ cho `lined` thay vì `ruled` trong webapp/js/paper.js
- [X] T014 [P] [US3] Cập nhật danh sách tùy chọn `#opt-background` và đặt mặc định `lined` trong webapp/index.html
- [X] T015 [US3] Cập nhật giá trị mặc định của `writeOptions.background` thành `"lined"` trong webapp/js/write.js

**Checkpoint**: User Story 3 hoàn thành - Nền giấy khớp chuẩn Xournal++, nhãn giao diện rõ ràng chính xác.

---

## Phase 6: Polish & Verification

**Purpose**: Rà soát hồi quy, chạy toàn bộ bộ test và ghi nhận kết quả đo lường

- [X] T016 Rà soát và cập nhật các test cũ nếu phụ thuộc kích thước 300px hoặc nhãn `lined`/`ruled` cũ trong tests/e2e/ và tests/js/
- [X] T017 Chạy kiểm thử hồi quy toàn diện: `pytest -m "not benchmark"` và `npm run test:e2e`
- [X] T018 Thu thập số đo kích thước trước/sau và chụp ảnh màn hình nghiệm thu

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)** & **Phase 2 (Foundational)**: Thực hiện trước tiên.
- **Phase 3 (User Story 1 - Kích thước thật)**: Thực hiện ngay sau Phase 2 (MVP).
- **Phase 4 (User Story 2 - Bộ điều khiển Zoom)**: Tiếp nối sau Phase 3.
- **Phase 5 (User Story 3 - Chuẩn hóa Xournal++)**: Có thể thực hiện song song hoặc nối tiếp Phase 4.
- **Phase 6 (Polish & Verification)**: Chạy sau khi hoàn thành toàn bộ các user stories.
