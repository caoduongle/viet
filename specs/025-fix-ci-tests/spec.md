# Feature Specification: Sửa Lỗi CI Kiểm Thử Tự Động (Playwright E2E & GUI Tkinter)

**Feature Branch**: `025-fix-ci-tests`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "áp @[local data/fix-sw-update.patch] @[local data/fix_test_gui.patch] vào để sửa các lỗi CI: Playwright sw-update test (python not found / 2 workers race) và GUI test_gui.py::test_nap_tu_thong_dung"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ổn định hóa kiểm thử cập nhật Service Worker trên đa nền tảng và đa luồng CI (Priority: P1) 🎯 MVP

Là một kỹ sư phát triển phần mềm và duy trì CI/CD, tôi muốn bộ kiểm thử Playwright E2E cho kịch bản cập nhật Service Worker (`sw-update.spec.ts`) có thể chạy độc lập, an toàn trên cả Linux (GitHub Actions CI) lẫn Windows/macOS, đồng thời tương thích hoàn hảo khi chạy song song nhiều worker (`--workers=2`), để quy trình kiểm thử tự động của dự án luôn hoàn thành nhanh chóng, xanh 100% và không bị đụng độ tài nguyên tĩnh giữa các tiến trình.

**Why this priority**: Lỗi `/bin/sh: 1: py: not found` và đụng độ ghi đè thư mục `webapp/dist` giữa các worker Playwright đang làm gãy luồng kiểm thử CI trên GitHub Actions khi chạy đa tiến trình song song.

**Independent Test**: Chạy `npx playwright test --workers=2` (hoặc lệnh tương đương) trên môi trường bất kỳ (Linux CI hoặc máy cục bộ), toàn bộ 14 test E2E vượt qua thành công, đặc biệt test `sw-update.spec.ts` không can thiệp vào `webapp/dist` dùng chung của các test khác.

**Acceptance Scenarios**:

1. **Given** Test `sw-update.spec.ts` thực thi trên môi trường Linux CI (nơi lệnh `py` của Windows không tồn tại), **When** Test gọi lệnh đóng gói `build_web.py`, **Then** Hệ thống tự động nhận diện và sử dụng interpreter Python hợp lệ (`PYTHON`, `python3`, `python` hoặc `py -3` trên Windows) thay vì cố định lệnh `py -3`, hoàn thành việc build mà không phát sinh lỗi `command not found`.
2. **Given** Playwright thực thi với 2 hoặc nhiều worker song song, **When** Test `sw-update.spec.ts` kích hoạt việc tạo bản build mới với mã băm khác để kiểm tra cache-busting, **Then** Quá trình build và web server phục vụ cho test này được cô lập hoàn toàn trong thư mục tạm (`tmpDist`) và cổng mạng riêng biệt (ví dụ port 8101), không ghi đè vào `webapp/dist` đang được các worker khác sử dụng.
3. **Given** Web server tĩnh thử nghiệm trong `scripts/serve.mjs`, **When** Nhận cấu hình qua biến môi trường (`PORT`, `DIST_DIR`), **Then** Server phục vụ đúng thư mục và cổng được chỉ định, đồng thời bảo đảm an toàn chặn các yêu cầu vượt cấp thư mục (path traversal traversal).
4. **Given** Test `sw-update.spec.ts` hoàn tất (dù thành công hay thất bại), **When** Khối dọn dẹp thực thi, **Then** Mã nguồn gốc `webapp/js/app.js` luôn được hoàn trả nguyên vẹn, server tạm thời được tắt và thư mục tạm được dọn dẹp sạch sẽ.

---

### User Story 2 - Cập nhật kiểm thử giao diện Desktop Tkinter đồng bộ với mô hình Bộ ký tự mới (Priority: P1)

Là một lập trình viên duy trì bộ test của ứng dụng Desktop, tôi muốn các bài test trong `tests/test_gui.py` phản ánh chính xác hành vi mới của nút "Bộ ký tự…" (thay thế nút "Từ thông dụng" và cơ chế bộ từ SEED cũ), để kiểm tra việc mở hộp thoại chọn bộ, nạp các ký tự còn thiếu vào hàng đợi dạy và huỷ bỏ thao tác diễn ra chuẩn xác, không còn gây lỗi gãy test `test_nap_tu_thong_dung` trên môi trường CI có Xvfb.

**Why this priority**: Tính năng chuyển đổi sang mô hình thuần ký tự (Feature 024) đã thay thế hộp thoại nhập số lượng từ của `simpledialog.askinteger` bằng cửa sổ Toplevel chọn nhóm ký tự, khiến bài test cũ bị lỗi sai khẳng định (`assert 1 == 6`).

**Independent Test**: Chạy `pytest -v tests/test_gui.py` trên môi trường có Tkinter / Xvfb, toàn bộ các test case liên quan đến tab Dạy chữ và nạp bộ ký tự đều vượt qua thành công mà không có ngoại lệ nào.

**Acceptance Scenarios**:

1. **Given** Người dùng ở tab Dạy chữ trên giao diện Tkinter, **When** Bấm nút nạp bộ ký tự và chọn "Nạp ký tự" trong hộp thoại, **Then** Toàn bộ các ký tự còn thiếu trong nhóm cơ bản (`co_ban`) được nạp vào hàng đợi dạy, không bị trùng lặp với các mục đã có sẵn trong hàng đợi và thông báo kết quả thành công.
2. **Given** Hộp thoại chọn bộ ký tự đang mở, **When** Người dùng bấm nút "Huỷ", **Then** Hàng đợi không bị biến đổi, không có thông báo lỗi hay thông báo phát sinh.

---

### Edge Cases

- **Môi trường thiếu interpreter `py`**: Trên Linux/macOS, `py` không tồn tại; helper tìm kiếm Python phải lần lượt thử các biến thể (`process.env.PYTHON`, `python3`, `python`) và chỉ báo lỗi nếu thực sự không tìm thấy bất kỳ interpreter nào.
- **Lỗi trong quá trình chạy test E2E**: Nếu test gặp lỗi giữa chừng, `finally` block phải đảm bảo khôi phục lại file gốc `webapp/js/app.js` và giải phóng cổng mạng / tiến trình server con để không làm ảnh hưởng các lần chạy sau.
- **Ký tự trong URL trên server tĩnh**: `scripts/serve.mjs` phải giải mã an toàn `decodeURIComponent(url)` và bắt lỗi `URIError` (trả về HTTP 400 Bad Request) thay vì làm sập tiến trình node.
- **Tấn công duyệt thư mục**: Yêu cầu chứa `../` thoát khỏi `DIST_DIR` trên `scripts/serve.mjs` phải bị chặn với mã HTTP 403 Forbidden.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống kiểm thử E2E MUST tự động phát hiện trình thông dịch Python thích hợp trên từng hệ điều hành (`process.env.PYTHON`, `py -3` trên win32, `python3`, `python`) khi thực thi lệnh đóng gói `build_web.py`.
- **FR-002**: Kịch bản kiểm thử `sw-update.spec.ts` MUST xây dựng và phục vụ bản build thử nghiệm trong một thư mục tạm độc lập (`tmpDist`) và một cổng mạng riêng (`SW_PORT = 8101`), không can thiệp vào `webapp/dist` hoặc server chính ở cổng 8000.
- **FR-003**: Máy chủ tĩnh `scripts/serve.mjs` MUST hỗ trợ cấu hình cổng qua biến môi trường `PORT` và thư mục phục vụ qua biến môi trường `DIST_DIR`.
- **FR-004**: Máy chủ tĩnh `scripts/serve.mjs` MUST kiểm tra đường dẫn an toàn, từ chối các yêu cầu có nguy cơ path traversal nằm ngoài `DIST_DIR` với mã trạng thái 403.
- **FR-005**: Kịch bản `sw-update.spec.ts` MUST có cơ chế dọn dẹp độc lập trong khối `finally` để phục hồi tệp `webapp/js/app.js`, tắt tiến trình server tạm và xóa thư mục tạm.
- **FR-006**: Bài kiểm thử GUI trong `tests/test_gui.py` MUST thay thế bài test cũ `test_nap_tu_thong_dung` bằng hai bài kiểm thử `test_nap_bo_ky_tu_co_ban` và `test_huy_bo_ky_tu_khong_them_gi` tương ứng với hộp thoại chọn bộ ký tự Toplevel mới.
- **FR-007**: Bài kiểm thử `test_nap_bo_ky_tu_co_ban` MUST kiểm tra chính xác danh sách ký tự được thêm vào hàng đợi khớp với danh sách ký tự thiếu được trả về từ `AppController.get_missing_chars("co_ban")` và không nhân bản mục đã có sẵn.

### Key Entities

- **Isolated Test Environment (E2E)**: Môi trường đóng gói và phục vụ web tạm thời gồm `tmpDist` (thư mục tạm trên OS), tiến trình con `scripts/serve.mjs` trên cổng `8101`, và file nguồn cần mô phỏng thay đổi hash.
- **Character Catalog Dialog (GUI)**: Cửa sổ con Toplevel chứa giao diện chọn nhóm ký tự (`co_ban`, `toan_hy_lap`, ...) và các nút hành động "Nạp ký tự" / "Huỷ".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Bộ kiểm thử Playwright chạy thành công 100% với cấu hình 2 worker song song (`npx playwright test --workers=2`), hoàn thành trong dưới 3 phút mà không có bất kỳ worker nào bị lỗi đụng độ file hoặc thiếu lệnh python.
- **SC-002**: Toàn bộ các kiểm thử GUI trong `tests/test_gui.py` vượt qua 100% khi chạy trên môi trường có Tkinter / Xvfb (`xvfb-run -a pytest tests/test_gui.py`), không còn lỗi `AssertionError` ở bài test nạp bộ ký tự.
- **SC-003**: Không có mã nguồn nào vi phạm quy tắc linter (`ruff check` 0 errors) hoặc phá vỡ các ràng buộc kiến trúc MVC của dự án (`tests/test_architecture.py` 17 passed).

## Assumptions

- Môi trường CI trên Linux có cài đặt sẵn Python (thông qua lệnh `python` hoặc `python3`).
- Môi trường CI có đủ quyền tạo và xóa các thư mục tạm trong `os.tmpdir()`.
- Cổng 8101 khả dụng trên môi trường chạy test E2E để khởi chạy server tạm thời cho `sw-update.spec.ts`.
- Hành vi của nút "Bộ ký tự…" trên giao diện Tkinter mở ra một Toplevel window với các nút "Nạp ký tự" và "Huỷ" như đã triển khai ở Feature 024.
