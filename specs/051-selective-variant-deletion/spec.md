# Feature Specification: Chọn và Xóa Biến Thể Mẫu Nét Tùy Chọn Trong Kho Mẫu

**Feature Branch**: `051-selective-variant-deletion`

**Created**: 2026-10-20

**Status**: Ready for Planning

**Input**: User description: "tôi muốn khi xóa thì có thể chọn các biến thể muốn xóa; thay vì chỉ có lựa chọn xóa hết như trước"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chọn và xóa nhiều biến thể mẫu nét cụ thể của một nhãn (Priority: P1)

Khi người dùng mở cửa sổ xem chi tiết một nhãn ký tự trong kho mẫu nét (ví dụ chữ "Ơ" có 4 mẫu nét), người dùng có thể tích chọn một hoặc nhiều biến thể mẫu nét không ưng ý (ví dụ chọn Mẫu #2 và Mẫu #4) và nhấn lệnh xóa các biến thể đã chọn. Sau khi xác nhận, hệ thống chỉ loại bỏ đúng các biến thể đã chọn và giữ nguyên toàn bộ các biến thể còn lại (Mẫu #1 và Mẫu #3).

**Why this priority**: Hiện tại người dùng chỉ có nút "Xoá nhãn này", buộc phải xóa toàn bộ tất cả mẫu của nhãn nếu lỡ có một vài mẫu vẽ sai hoặc xấu. Việc cho phép chọn chính xác từng biến thể để xóa giúp bảo vệ công sức viết nét trước đó, tiết kiệm thời gian dạy chữ và nâng cao chất lượng kho mẫu nét.

**Independent Test**: Mở modal chi tiết của một nhãn có từ 2 mẫu nét trở lên, chọn một hoặc nhiều mẫu, thực hiện thao tác xóa và kiểm tra danh sách mẫu còn lại vẫn giữ đúng nét của các mẫu không được chọn.

**Acceptance Scenarios**:

1. **Given** một nhãn có 4 biến thể mẫu nét trong cửa sổ chi tiết, **When** người dùng tích chọn Mẫu #2 và Mẫu #4, **Then** giao diện hiển thị trạng thái đã chọn (2 biến thể) và nút xóa cập nhật thành "Xoá 2 biến thể đã chọn".
2. **Given** người dùng đã chọn ít nhất một biến thể, **When** nhấn nút "Xoá biến thể đã chọn", **Then** hệ thống hiển thị hộp thoại xác nhận nêu rõ số lượng biến thể sẽ bị xóa và cảnh báo hành động không thể hoàn tác.
3. **Given** hộp thoại xác nhận xóa biến thể đang hiển thị, **When** người dùng xác nhận đồng ý, **Then** hệ thống loại bỏ các biến thể đã chọn, giữ nguyên các biến thể còn lại, đánh lại số thứ tự mẫu hiển thị (`Mẫu #1`, `Mẫu #2`, ...) và cập nhật lại số lượng mẫu cùng trạng thái độ phủ của nhãn.
4. **Given** hộp thoại xác nhận xóa đang hiển thị, **When** người dùng bấm Hủy (Cancel), **Then** không có biến thể nào bị xóa và trạng thái lựa chọn vẫn được giữ nguyên.

---

### User Story 2 - Xóa nhanh từng biến thể mẫu nét đơn lẻ (Priority: P2)

Khi người dùng chỉ muốn loại bỏ một biến thể nét cụ thể ngay khi đang quan sát thumbnail mẫu, người dùng có thể bấm nút xóa nhanh (biểu tượng thùng rác) trên chính thẻ mẫu đó mà không cần qua nhiều bước tích chọn.

**Why this priority**: Cung cấp đường dẫn thao tác nhanh (quick-action) cho tình huống người dùng lướt qua danh sách mẫu nét và muốn loại bỏ ngay một mẫu bị lỗi nét hoặc lệch đường cơ sở.

**Independent Test**: Bấm nút xóa nhanh trên thẻ Mẫu #3, xác nhận xóa, kiểm tra chỉ riêng Mẫu #3 bị xóa khỏi danh sách.

**Acceptance Scenarios**:

1. **Given** người dùng rê chuột hoặc xem thẻ của một biến thể mẫu nét, **When** nhìn vào thẻ mẫu, **Then** hệ thống hiển thị nút xóa nhanh dành riêng cho mẫu đó.
2. **Given** người dùng bấm nút xóa nhanh trên một thẻ mẫu, **When** xác nhận xóa trong hộp thoại, **Then** chỉ riêng biến thể đó bị loại bỏ, danh sách mẫu được làm mới ngay lập tức.

---

### User Story 3 - Xử lý an toàn khi xóa toàn bộ biến thể hoặc xóa sạch nhãn (Priority: P3)

Khi người dùng chọn xóa tất cả các biến thể còn lại của một nhãn (hoặc sử dụng nút "Xoá nhãn này"), hệ thống tự động nhận diện nhãn không còn mẫu nét nào, dọn dẹp nhãn khỏi danh mục kho mẫu và đóng cửa sổ chi tiết nhãn.

**Why this priority**: Đảm bảo tính toàn vẹn dữ liệu, tránh tình trạng tồn tại các nhãn "rỗng" không có mẫu nét nào trong kho mẫu sau khi người dùng xóa hết các biến thể.

**Independent Test**: Chọn xóa tất cả các biến thể của một nhãn (hoặc xóa biến thể cuối cùng duy nhất còn lại), kiểm tra nhãn được gỡ bỏ hoàn toàn khỏi danh sách nhãn của kho mẫu.

**Acceptance Scenarios**:

1. **Given** một nhãn chỉ còn duy nhất 1 biến thể mẫu nét, **When** người dùng chọn xóa biến thể đó và xác nhận, **Then** hệ thống xóa biến thể, tự động xóa nhãn khỏi kho mẫu, đóng cửa sổ chi tiết nhãn và làm mới giao diện kho mẫu.
2. **Given** một nhãn có nhiều biến thể và người dùng chọn tất cả các biến thể để xóa, **When** người dùng xác nhận xóa, **Then** hệ thống cảnh báo đây là thao tác xóa sạch toàn bộ nhãn, sau đó tiến hành gỡ bỏ nhãn khỏi kho mẫu.
3. **Given** nút "Xoá nhãn này" hiện có trên giao diện, **When** người dùng bấm vào, **Then** hệ thống vẫn hoạt động như cũ để cung cấp lối tắt xóa toàn bộ nhãn mà không bắt buộc phải tích chọn thủ công từng biến thể.

---

### Edge Cases

- **Không chọn biến thể nào**: Khi số lượng biến thể được chọn bằng 0, nút "Xoá biến thể đã chọn" phải ở trạng thái vô hiệu hóa (disabled) hoặc ẩn, ngăn chặn thao tác xóa rỗng.
- **Biến thể cuối cùng bị xóa**: Khi xóa biến thể duy nhất còn lại của nhãn, hệ thống phải xử lý tương đương xóa nhãn hoàn toàn, đóng modal và loại bỏ nhãn khỏi danh sách hiển thị chính của kho mẫu nét.
- **Hạ mức độ phủ khi xóa biến thể**: Nếu số lượng biến thể sau khi xóa giảm từ 2 trở lên xuống dưới 2 mẫu, nhãn độ phủ phải chuyển trạng thái từ "✓ Độ phủ tốt" sang "⚠️ Độ phủ thấp (< 2 mẫu)" kèm lời khuyên dạy thêm nét.
- **Thao tác liên tục / bấm đúp**: Nút xóa phải ngăn chặn việc người dùng bấm nhiều lần liên tiếp khi tiến trình xóa đang diễn ra, tránh gửi trùng lặp yêu cầu xóa.
- **Hủy chọn hàng loạt**: Có cơ chế thuận tiện để bỏ chọn tất cả các biến thể đã chọn nếu người dùng đổi ý.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI hiển thị thành phần lựa chọn (hộp kiểm / checkbox hoặc thao tác chọn thẻ) trên từng thẻ biến thể mẫu nét trong cửa sổ chi tiết nhãn.
- **FR-002**: Hệ thống PHẢI cho phép người dùng chọn một hoặc nhiều biến thể mẫu nét cùng một lúc.
- **FR-003**: Hệ thống PHẢI cung cấp nút hành động xóa các biến thể đã chọn, thể hiện rõ số lượng biến thể đang được chọn (ví dụ: "Xoá 2 biến thể đã chọn").
- **FR-004**: Nút hành động xóa biến thể đã chọn PHẢI bị vô hiệu hóa khi chưa có biến thể nào được chọn.
- **FR-005**: Hệ thống PHẢI hiển thị hộp thoại xác nhận trước khi thực hiện xóa, thông báo rõ số lượng biến thể sẽ bị loại bỏ và cảnh báo không thể hoàn tác.
- **FR-006**: Hệ thống PHẢI giữ nguyên vẹn toàn bộ các biến thể không được chọn, bảo toàn thứ tự, tọa độ nét và chiều rộng của chúng.
- **FR-007**: Hệ thống PHẢI cập nhật lại số thứ tự mẫu hiển thị (`Mẫu #1`, `Mẫu #2`, ...), tổng số lượng biến thể và trạng thái độ phủ của nhãn ngay sau khi việc xóa thành công.
- **FR-008**: Hệ thống PHẢI cung cấp nút xóa nhanh (thùng rác) trên mỗi thẻ biến thể để hỗ trợ xóa ngay 1 mẫu mà không cần chọn checkbox trước.
- **FR-009**: Hệ thống PHẢI tự động gỡ bỏ nhãn khỏi danh mục kho mẫu và đóng cửa sổ chi tiết nhãn nếu tất cả các biến thể của nhãn đó bị xóa sạch.
- **FR-010**: Hệ thống PHẢI duy trì nút "Xoá nhãn này" hiện có như một lối tắt tiện lợi để xóa toàn bộ nhãn trong một thao tác.
- **FR-011**: Hệ thống PHẢI đồng bộ và lưu trữ ngay lập tức các thay đổi sau khi xóa vào cơ sở dữ liệu kho mẫu bền vững, đảm bảo tính nhất quán trên mọi phiên làm việc.
- **FR-012**: Tính năng chọn và xóa biến thể PHẢI hoạt động đồng nhất trên tất cả các phân loại nhãn ký tự trong kho mẫu (chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh).
- **FR-013**: Hệ thống PHẢI vô hiệu hóa các nút xóa và hiển thị trạng thái đang xử lý khi tiến trình xóa đang diễn ra nhằm ngăn chặn xung đột hoặc gửi trùng lặp yêu cầu xóa (in-flight request guard).
- **FR-014**: Hệ thống PHẢI đóng hoặc làm mới khung xem thử ngẫu nhiên (`#modal-random-preview-box`) khi có biến thể bị xóa để tránh hiển thị kết quả dựa trên các mẫu nét cũ đã bị loại bỏ.
- **FR-015**: Hệ thống PHẢI áp dụng cơ chế thoát chuỗi an toàn (`escapeHtml`) khi hiển thị thông tin nhãn hoặc thông báo lỗi trên giao diện DOM, loại bỏ nguy cơ lỗ hổng DOM-based XSS.

### Key Entities

- **Nhãn ký tự (Character Label)**: Thực thể đại diện cho một ký tự, từ hoặc ký hiệu trong kho mẫu, bao gồm tên nhãn (ví dụ "Ơ", "hoa", ","), phân loại (letters, words, digits, punct, symbols, marks), và danh sách các biến thể mẫu nét tương ứng.
- **Biến thể mẫu nét (Stroke Variant / Sample)**: Thực thể đại diện cho một lần người dùng dạy nét viết cho nhãn, bao gồm danh sách các nét vẽ (tọa độ điểm), chiều rộng nét tính bằng điểm (pt), và thứ tự hiển thị trong danh sách biến thể của nhãn.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng có thể tích chọn và hoàn tất xóa một hoặc nhiều biến thể mẫu nét tùy ý trong vòng dưới 5 giây.
- **SC-002**: 100% các biến thể không được chọn được bảo toàn nguyên vẹn về chất lượng nét và kích thước, không xảy ra mất mát dữ liệu ngoài ý muốn.
- **SC-003**: Giao diện danh sách biến thể, số lượng mẫu và thông tin độ phủ cập nhật trực quan ngay lập tức (dưới 500ms) sau khi xác nhận xóa.
- **SC-004**: Tất cả các kịch bản kiểm thử tự động cho việc xóa 1 biến thể, xóa nhiều biến thể, và xóa biến thể cuối cùng đạt tỷ lệ vượt qua (pass rate) 100%.

## Assumptions

- Người dùng thao tác quản lý kho mẫu nét trên trình duyệt máy tính hoặc thiết bị cảm ứng thông qua giao diện đồ họa trực quan.
- Khi người dùng xóa hết toàn bộ biến thể của một nhãn, việc tự động xóa nhãn đó khỏi kho mẫu là hành vi mặc định mong muốn (vì một nhãn rỗng không thể dùng để tạo chữ viết tay).
- Thao tác xóa biến thể là vĩnh viễn và không hỗ trợ hoàn tác tự động, do đó luôn cần có bước xác nhận rõ ràng trước khi thực thi.
- Cơ chế xóa biến thể áp dụng thống nhất cho tất cả các nhóm ký tự được quản lý trong kho mẫu nét.
