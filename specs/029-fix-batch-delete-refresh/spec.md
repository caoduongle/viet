# Feature Specification: Khắc Phục Lỗi Làm Mới Khi Xóa Hàng Loạt Trên Web Client

**Feature Branch**: `specs/029-fix-batch-delete-refresh`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "tôi gặp lỗi này khi xóa hàng loạt: Lỗi khi xoá hàng loạt: refreshBankTab is not defined kèm ảnh chụp màn hình tab Quản lý kho mẫu chữ"

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xóa hàng loạt ký tự đã chọn trong Kho mẫu Web Client (Priority: P1) 🎯 MVP

Người dùng trên Web Client chọn một hoặc nhiều nhãn mẫu chữ trong tab "Quản lý kho mẫu chữ" (hoặc bấm "Chọn tất cả hiển thị"), sau đó nhấn nút "Xoá đã chọn". Hệ thống hiển thị hộp thoại xác nhận số lượng ký tự và số mẫu nét sẽ bị xóa. Khi người dùng đồng ý, hệ thống tiến hành xóa hàng loạt thành công, tự động lưu xuống bộ nhớ cục bộ, đồng bộ đa tab và làm mới lại toàn bộ danh sách thẻ ký tự trên giao diện mà không gặp bất kỳ lỗi tham chiếu script nào (như `refreshBankTab is not defined`).

**Why this priority**: Lỗi `refreshBankTab is not defined` làm gián đoạn hoàn toàn luồng trải nghiệm của người dùng khi xóa hàng loạt mẫu chữ trên Web Client, gây cảnh báo lỗi đỏ và khiến giao diện không thể tự động cập nhật danh sách thẻ sau khi xóa.

**Independent Test**:
1. Mở Web Client tại tab "Quản lý kho mẫu chữ".
2. Chọn nhiều nhãn thẻ (ví dụ 3 nhãn bất kỳ hoặc chọn tất cả).
3. Bấm nút "Xoá đã chọn (N)", xác nhận trên hộp thoại confirm.
4. Kiểm tra không có bất kỳ alert lỗi nào xuất hiện; danh sách thẻ được làm mới tức thì và các nhãn đã chọn biến mất khỏi giao diện cũng như khỏi kho mẫu.

**Acceptance Scenarios**:
1. **Given** người dùng đang ở tab Quản lý kho mẫu chữ và đã tick chọn ít nhất một nhãn, **When** người dùng bấm nút "Xoá đã chọn" và xác nhận đồng ý, **Then** hệ thống thực hiện lệnh xóa hàng loạt, đồng bộ lưu trữ và gọi đúng hàm cập nhật giao diện `refreshBankView()`, loại bỏ hoàn toàn lỗi `ReferenceError: refreshBankTab is not defined`.
2. **Given** sau khi thao tác xóa hàng loạt hoàn tất, **When** giao diện được làm mới, **Then** thanh chọn hàng loạt được đặt lại trạng thái ban đầu (bỏ tick chọn tất cả, số lượng đã chọn trở về 0, nút xóa bị vô hiệu hóa).
3. **Given** người dùng mở ứng dụng trên môi trường web deploy thực tế (bao gồm các bản build trong `webapp/dist/`), **When** thực hiện xóa hàng loạt, **Then** hành vi diễn ra trơn tru và đồng nhất giữa mã nguồn phát triển và bản build phân phối.

---

### User Story 2 - Đảm bảo Đồng bộ và Tái xây dựng Bản phân phối Web (Priority: P2)

Nhà phát triển và hệ thống triển khai tự động (CI/CD) có thể build lại toàn bộ gói Web Client sang thư mục phân phối `webapp/dist/` đảm bảo mã nguồn JavaScript bundle luôn đồng bộ 100% với mã nguồn gốc, không còn tàn dư của các tham chiếu hàm không tồn tại.

**Why this priority**: Dự án duy trì cả hai thư mục `webapp/js/` và `webapp/dist/js/`. Bất kỳ sửa đổi nào trên mã nguồn chính cần được phản ánh vào bản build để môi trường chạy thực tế (Render/PWA) không sử dụng mã cũ.

**Independent Test**:
Chạy kịch bản kiểm thử E2E Playwright mô phỏng hành vi chọn và xóa hàng loạt trên Web Client, khẳng định 100% không phát sinh lỗi console `ReferenceError`.

**Acceptance Scenarios**:
1. **Given** mã nguồn `webapp/js/bank.js` đã được sửa gọi `refreshBankView()`, **When** chạy script build web (`scripts/build_web.py`), **Then** tệp `webapp/dist/js/bank.js` được cập nhật đồng bộ.
2. **Given** kịch bản Playwright kiểm thử giao diện kho mẫu, **When** thực hiện thao tác xóa hàng loạt, **Then** kiểm thử hoàn tất thành công mà không có lỗi dialog alert thông báo `refreshBankTab is not defined`.

---

### Edge Cases

- **Xóa toàn bộ các thẻ hiển thị khi đang tìm kiếm/lọc**: Sau khi xóa hàng loạt, bộ lọc hiện tại vẫn giữ nguyên, lưới thẻ hiển thị thông báo trống phù hợp nếu không còn kết quả nào khớp bộ lọc.
- **Hủy thao tác xóa trên hộp thoại confirm**: Nếu người dùng bấm "Cancel", hệ thống không gọi API xóa và danh sách chọn vẫn được giữ nguyên.
- **Lỗi từ backend worker khi xóa**: Nếu worker gặp sự cố (ví dụ kho bị khóa), hệ thống hiển thị thông báo lỗi thân thiện thay vì làm đơ giao diện.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống Web Client MUST gọi chính xác hàm làm mới giao diện kho mẫu `refreshBankView()` sau khi hoàn tất thao tác xóa hàng loạt trong `handleDeleteSelected()`.
- **FR-002**: Hệ thống MUST KHÔNG chứa bất kỳ tham chiếu nào tới định danh hàm không tồn tại `refreshBankTab` trong toàn bộ mã nguồn `webapp/js/` và `webapp/dist/js/`.
- **FR-003**: Sau khi xóa hàng loạt thành công, tập hợp các nhãn đã chọn (`selectedLabels`) MUST được làm sạch và thanh điều khiển hàng loạt (`updateBatchBar`) MUST được cập nhật lại trạng thái (ẩn nút xóa hoặc hiển thị số lượng 0).
- **FR-004**: Mã nguồn phân phối `webapp/dist/js/bank.js` MUST được tái đồng bộ và nhất quán hoàn toàn với mã nguồn `webapp/js/bank.js`.
- **FR-005**: Bộ kiểm thử Playwright E2E MUST bổ sung hoặc xác nhận kịch bản chọn hàng loạt và xóa hàng loạt không làm phát sinh dialog alert lỗi.

---

### Key Entities

- **BatchDeleteAction**: Thao tác xóa nhiều ký tự được chọn cùng lúc, bao gồm danh sách nhãn (`labelsToDelete`), tổng số mẫu nét ảnh hưởng và việc kích hoạt làm mới giao diện.
- **BankViewRefresh**: Cơ chế tải lại danh sách thẻ từ kho mẫu và vẽ lại giao diện kho chữ (`refreshBankView`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0% xuất hiện lỗi `ReferenceError: refreshBankTab is not defined` khi người dùng bấm nút xóa hàng loạt trên Web Client.
- **SC-002**: 100% các ký tự được chọn bị xóa khỏi kho mẫu và biến mất khỏi lưới thẻ giao diện ngay sau khi xác nhận.
- **SC-003**: 100% các bài kiểm thử Playwright E2E và bộ kiểm thử đơn vị web vượt qua thành công (0 failures).

---

## Assumptions

- Hàm làm mới tab kho mẫu chuẩn đã được export và sử dụng xuyên suốt trong `webapp/js/bank.js` là `refreshBankView()`.
- Người dùng thực hiện thao tác xóa hàng loạt trên trình duyệt hiện đại hỗ trợ ES Modules và các API DOM tiêu chuẩn.
- Thao tác xóa hàng loạt không ảnh hưởng đến các phân loại khác không được chọn.
