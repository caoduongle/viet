# Feature Specification: Xóa Hàng Loạt Kho Mẫu và Chuyển Đổi Giao Diện Sáng / Tối

**Feature Branch**: `specs/027-batch-delete-and-theme-toggle`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "thêm nút xóa hàng loạt ở kho mẫu cùng nút chỉnh giao diện sáng tối"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xóa hàng loạt ký tự trong kho mẫu (Priority: P1) 🎯 MVP

Là người dùng quản lý kho mẫu chữ viết tay, tôi muốn có khả năng chọn nhiều ký tự hoặc tất cả các ký tự đang lọc và thực hiện xóa hàng loạt cùng lúc, kèm hộp thoại xác nhận rõ ràng về số lượng mẫu sẽ bị xóa, thay vì phải bấm xóa thủ công từng ký tự một.

**Why this priority**: Giúp tiết kiệm thời gian và nâng cao trải nghiệm khi người dùng muốn dọn dẹp kho mẫu, xóa các bộ ký tự lỗi, hoặc thiết lập lại một danh mục ký tự cụ thể mà không phải lặp lại thao tác xóa hàng chục/hàng trăm lần.

**Independent Test**: Mở tab Kho mẫu trên Web Client hoặc Desktop GUI; chọn nhiều ký tự (qua hộp kiểm hoặc chọn nhiều dòng); nhấn nút "Xóa đã chọn"; hộp thoại xác nhận hiển thị tổng số ký tự và số mẫu sẽ bị xóa; sau khi đồng ý, tất cả các ký tự được chọn biến mất khỏi danh sách và dữ liệu được lưu xuống đĩa.

**Acceptance Scenarios**:

1. **Given** Người dùng đang ở tab Kho mẫu (cả Web Client và Desktop GUI) với danh sách ký tự đang hiển thị, **When** Người dùng chọn nhiều ký tự (hoặc bấm nút "Chọn tất cả" / "Bỏ chọn tất cả"), **Then** Giao diện kích hoạt nút "Xóa đã chọn" và hiển thị số lượng mục đang được chọn.
2. **Given** Người dùng đã chọn một hoặc nhiều ký tự và bấm nút "Xóa đã chọn", **When** Hộp thoại xác nhận xuất hiện, **Then** Hộp thoại nêu rõ danh sách/số lượng ký tự và tổng số mẫu nét sắp bị xóa, yêu cầu xác nhận dứt khoát trước khi tiến hành.
3. **Given** Người dùng xác nhận xóa trong hộp thoại, **When** Lệnh xóa hàng loạt thực thi, **Then** Toàn bộ các ký tự đã chọn bị xóa khỏi kho, hệ thống ghi nhận tombstone tương ứng, lưu kho an toàn xuống đĩa, và danh sách hiển thị cập nhật ngay lập tức.
4. **Given** Người dùng hủy bỏ hoặc đóng hộp thoại xác nhận, **When** Thao tác kết thúc, **Then** Không có bất kỳ ký tự nào bị xóa và trạng thái lựa chọn được giữ nguyên.

---

### User Story 2 - Chuyển đổi giao diện Sáng / Tối (Theme Toggle) (Priority: P2)

Là người dùng ứng dụng ChuVietTay, tôi muốn có nút chuyển đổi giao diện sáng (Light Mode) và tối (Dark Mode) trên cả Web Client và Desktop GUI để thuận tiện làm việc trong các điều kiện ánh sáng khác nhau mà không bị mỏi mắt.

**Why this priority**: Cải thiện trực tiếp sự thoải mái về thị giác, hiện đại hóa trải nghiệm người dùng, đáp ứng tiêu chuẩn giao diện người dùng hiện đại trên cả trình duyệt và ứng dụng máy tính.

**Independent Test**: Nhấn nút chuyển đổi chủ đề (icon mặt trời ☀️ / mặt trăng 🌙) ở góc giao diện; toàn bộ màu nền, văn bản, thanh điều hướng, các nút bấm và khung canvas chuyển đổi tức thì sang giao diện tối; tải lại trang hoặc khởi động lại ứng dụng, giao diện vẫn duy trì chế độ tối đã lưu.

**Acceptance Scenarios**:

1. **Given** Người dùng mở ứng dụng lần đầu, **When** Chưa có tùy chọn chủ đề nào được lưu, **Then** Ứng dụng tự động phát hiện và áp dụng chủ đề mặc định theo cấu hình hệ điều hành / trình duyệt (`prefers-color-scheme`).
2. **Given** Người dùng đang ở chế độ Sáng (Light Mode), **When** Nhấn nút chuyển đổi chủ đề (Theme Toggle), **Then** Toàn bộ giao diện (thanh công cụ, các tab, bảng danh sách, khung vẽ, hộp thoại) chuyển sang chế độ Tối (Dark Mode) với độ tương phản cao, dịu mắt và dễ đọc.
3. **Given** Người dùng đang ở chế độ Tối (Dark Mode), **When** Nhấn nút chuyển đổi chủ đề, **Then** Giao diện chuyển ngược lại chế độ Sáng (Light Mode).
4. **Given** Người dùng đã chọn một chủ đề nhất định, **When** Người dùng làm mới trang Web hoặc khởi động lại Desktop GUI, **Then** Tùy chọn chủ đề đã lưu được tự động phục hồi mà không bị chớp nháy giao diện.

---

### Edge Cases

- **Xóa rỗng hoặc không chọn mục nào**: Nút "Xóa đã chọn" bị vô hiệu hóa (disabled) khi số lượng mục chọn bằng 0.
- **Xóa khi đang lọc tìm kiếm**: Thao tác "Chọn tất cả" chỉ áp dụng cho các mục đang hiển thị theo bộ lọc tìm kiếm hiện tại, không vô tình chọn các mục đang bị ẩn.
- **Vẽ nét trên Canvas trong chế độ Tối**: Nền canvas tập viết và đường kẻ mốc (baseline, ascender, descender, x-height) phải tự động đảo màu tương phản thích hợp để nét mực (đen/xanh hoặc màu tương phản) hiển thị rõ ràng, không bị chìm vào nền tối.
- **Mất mạng hoặc ngắt tiến trình khi đang xóa hàng loạt**: Thao tác xóa hàng loạt phải được thực hiện theo cơ chế giao dịch/an toàn (batch mutation trong lock) và chỉ lưu đĩa một lần khi hoàn tất, tránh trạng thái dữ liệu dở dang.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI cung cấp cơ chế chọn nhiều ký tự trong tab Kho mẫu trên cả Desktop GUI (`BankTab`) và Web Client (`bank.js`).
- **FR-002**: Hệ thống PHẢI cung cấp tùy chọn "Chọn tất cả" / "Bỏ chọn tất cả" cho danh sách ký tự đang hiển thị theo bộ lọc hiện tại.
- **FR-003**: Hệ thống PHẢI có nút "Xóa đã chọn" hiển thị số lượng mục được chọn (ví dụ: `Xóa (5)`), chỉ kích hoạt khi có ít nhất 1 mục được chọn.
- **FR-004**: Khi nhấn "Xóa đã chọn", hệ thống PHẢI hiển thị hộp thoại cảnh báo xác nhận chi tiết về số lượng ký tự và tổng số mẫu nét sẽ bị xóa.
- **FR-005**: `AppController` và `BrowserBridge` PHẢI cung cấp phương thức xóa hàng loạt (`drop_chars(chars: list[str])`) để thực hiện xóa tập trung trong một lần khóa (`_lock`) và lưu đĩa một lần duy nhất (`save()`).
- **FR-006**: Hệ thống PHẢI tích hợp nút chuyển đổi giao diện Sáng / Tối (Theme Toggle) ở vị trí dễ quan sát trên thanh tiêu đề/thanh công cụ chính của cả Web Client và Desktop GUI.
- **FR-007**: Hệ thống PHẢI lưu trữ trạng thái chủ đề được chọn (Light / Dark) vào bộ nhớ cục bộ (`localStorage` trên Web Client và tệp cấu hình người dùng trên Desktop GUI) để duy trì trạng thái qua các phiên làm việc.
- **FR-008**: Bảng màu chế độ Tối (Dark Theme) PHẢI đảm bảo độ tương phản đáp ứng chuẩn trợ năng WCAG AA cho văn bản, biểu tượng, đường kẻ lưới ô và nét vẽ chữ viết tay.

### Key Entities

- **SelectedCharItem**: Danh sách các nhãn ký tự được người dùng tích chọn để thao tác hàng loạt, bao gồm nhãn (`char`) và nhóm danh mục (`category`).
- **ThemePreference**: Tùy chọn giao diện người dùng với các giá trị hợp lệ: `'light'` (Sáng), `'dark'` (Tối), hoặc `'system'` (Theo hệ điều hành).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng có thể xóa 50 ký tự trong kho mẫu chỉ với 2 thao tác (Chọn tất cả -> Xác nhận xóa) trong thời gian dưới 3 giây, thay vì phải thực hiện 50 lần thao tác xóa đơn lẻ.
- **SC-002**: 100% các ký tự được chọn để xóa bị loại bỏ hoàn toàn khỏi kho mẫu và bộ nhớ đệm, với tombstone được ghi nhận đúng danh mục.
- **SC-003**: Thời gian chuyển đổi giữa chủ đề Sáng và Tối diễn ra tức thì (dưới 100ms) trên cả Web Client và Desktop GUI, không gây hiện tượng giật lag hoặc chớp màn hình.
- **SC-004**: Tùy chọn chủ đề được bảo lưu 100% qua các lần tải lại trang hoặc đóng mở ứng dụng.

## Assumptions

- Người dùng Desktop GUI có thư viện Tkinter hỗ trợ cấu hình kiểu dáng ttk/tcl (hỗ trợ chủ đề tối qua cấu hình màu style hoặc theme ttk).
- Trình duyệt Web của người dùng hỗ trợ CSS Variables và `localStorage` (đáp ứng 100% các trình duyệt hiện đại).
- Thao tác xóa hàng loạt là có chủ đích của người dùng sau khi đã qua bước xác nhận cảnh báo.
