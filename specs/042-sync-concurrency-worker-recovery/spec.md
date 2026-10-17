# Feature Specification: Hoàn thiện Kiểm soát Cạnh tranh Đa tab, Khôi phục Sự cố Worker & Nguyên tử hóa Cache Ngoại tuyến (Multi-Tab Concurrency Control, Worker Recovery & Atomic Offline Cache)

**Feature Branch**: `042-sync-concurrency-worker-recovery`

**Created**: 2026-10-17

**Status**: Draft

**Input**: User description: "Rà soát repository caoduongle/viet sau commit 42502565026c6a17e148c62c7f1c9f3e3361a874. CI hiện đã xanh nhưng cần xử lý dứt điểm các vấn đề bảo toàn dữ liệu và độ tin cậy: (1) P1 — Hoàn thiện kiểm soát cạnh tranh khi hồ sơ bị xóa hoặc tạo đồng thời (phân biệt 3 trạng thái: kỳ vọng tồn tại với phiên bản cụ thể, kỳ vọng chưa tồn tại, và ghi không kiểm soát phiên bản; ngăn tab cũ làm sống lại hồ sơ đã bị xóa ở tab khác). (2) P2 — Kiểm thử thực sự cho xung đột đồng thời khi có và không có khóa đồng bộ (hai tab đọc cùng phiên bản ban đầu rồi cùng lưu chồng lấn, kiểm tra phát hiện xung đột, thử lại, hợp nhất mẫu chữ, bảo toàn lệnh xóa ký tự không hồi sinh). (3) P2 — Hoàn thiện cơ chế phục hồi bộ xử lý nền (nút Thử lại thực sự khởi tạo lại bộ xử lý, nạp lại hồ sơ; ngăn thao tác thay đổi kho mẫu bị thực thi trùng lặp sau khi quá hạn chờ). (4) P2 — Bảo đảm tính nguyên tử khi cập nhật bộ nhớ đệm ngoại tuyến và tách tài nguyên nhập tài liệu tùy chọn khỏi danh sách bắt buộc lúc khởi tạo. (5) P3 — Chủ động hủy giao dịch khi phát sinh lỗi đồng bộ trong hàm thao tác và bổ sung kiểm thử cho lỗi giải mã thông điệp cũng như khôi phục sau khi giao diện đã khởi động."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Kiểm soát Cạnh tranh Ba Trạng thái & Ngăn Hồi sinh Hồ sơ Đã Xóa (Priority: P1) [MVP]

Người dùng mở ứng dụng trên nhiều tab trình duyệt để quản lý các hồ sơ kho mẫu chữ viết tay. Khi một tab thực hiện xóa một hồ sơ hoặc khi hai tab cùng lúc khởi tạo một hồ sơ mới, hệ thống kiểm soát phiên bản dữ liệu một cách chặt chẽ theo ba trạng thái rõ ràng: kỳ vọng hồ sơ đang tồn tại ở một mốc phiên bản cụ thể, kỳ vọng hồ sơ hoàn toàn chưa tồn tại, hoặc ghi đè chủ đích không kèm điều kiện phiên bản. Nếu một tab đang giữ bản sao cũ của hồ sơ cố gắng lưu sau khi hồ sơ đó đã bị xóa ở tab khác, hệ thống lập tức phát hiện xung đột và từ chối việc tự động tạo lại hồ sơ cũ, ngăn chặn hoàn toàn hiện tượng dữ liệu đã xóa bị làm sống lại ngoài ý muốn.

**Why this priority**: Đây là chốt chặn quan trọng nhất để bảo vệ tính toàn vẹn dữ liệu người dùng. Nếu không phân biệt được hồ sơ chưa từng tồn tại với hồ sơ đã bị xóa, hoặc bỏ qua kiểm tra khi khởi tạo mới đồng thời, người dùng có thể gặp tình trạng hồ sơ đã xóa tự động xuất hiện lại hoặc ghi đè mất dữ liệu vừa tạo ở tab bên cạnh.

**Independent Test**: Thực thi kịch bản kiểm thử độc lập mô phỏng hai phiên làm việc cùng đọc một hồ sơ, phiên thứ nhất xóa hồ sơ, sau đó phiên thứ hai thực hiện lưu bản sửa đổi cũ; xác nhận hệ thống báo xung đột phiên bản và kho lưu trữ không xuất hiện lại hồ sơ đã xóa.

**Acceptance Scenarios**:

1. **Given** hai tab đang mở cùng một hồ sơ ở phiên bản `V1` và tab thứ nhất thực hiện xóa hoàn toàn hồ sơ đó, **When** tab thứ hai cố gắng lưu dữ liệu dựa trên kỳ vọng phiên bản `V1`, **Then** hệ thống phát hiện hồ sơ gốc không còn tồn tại, từ chối thao tác ghi với lỗi xung đột cạnh tranh và không tạo lại hồ sơ đã xóa.
2. **Given** hai tab khởi động đồng thời khi chưa có hồ sơ mặc định và cả hai cùng kỳ vọng tạo mới hồ sơ lần đầu, **When** tab thứ nhất hoàn tất tạo hồ sơ trước và tab thứ hai tiếp tục ghi xuống với kỳ vọng hồ sơ chưa tồn tại, **Then** hệ thống phát hiện xung đột tạo mới đồng thời, buộc tab thứ hai đọc lại hồ sơ vừa được tạo để hợp nhất dữ liệu thay vì ghi đè mất dữ liệu của tab thứ nhất.
3. **Given** một thao tác lưu trữ phát sinh lỗi ngoại lệ ngay trong bước chuẩn bị yêu cầu bên trong giao dịch, **When** ngoại lệ xảy ra sau khi một số lệnh ghi sơ bộ đã được xếp hàng, **Then** hệ thống chủ động hủy bỏ toàn bộ giao dịch ngay lập tức để đảm bảo không có bất kỳ thay đổi dở dang nào được lưu xuống đĩa.

---

### User Story 2 - Giải quyết Cuộc đua Ghi Đồng thời Thực sự Giữa Đa Tab (Priority: P2)

Người dùng mở hai tab trình duyệt cùng lúc (kể cả trên các trình duyệt không hỗ trợ cơ chế khóa đồng bộ cấp hệ thống) và thực hiện dạy thêm chữ mới hoặc xóa chữ cũ ở cả hai tab gần như cùng một thời điểm trước khi tab kia kịp hoàn tất lưu. Khi hai yêu cầu lưu va chạm nhau trên cùng một phiên bản nền, hệ thống tự động phát hiện xung đột, thực hiện đọc lại dữ liệu mới nhất, hợp nhất các mẫu chữ vừa dạy từ cả hai tab và tôn trọng tuyệt đối các lệnh xóa ký tự, đảm bảo không mất mẫu chữ mới và không làm sống lại ký tự vừa xóa.

**Why this priority**: Người dùng thường mở nhiều tab để vừa soạn thảo vừa dạy chữ hoặc chỉnh sửa bộ mẫu. Kiểm thử và bảo đảm an toàn cho cuộc đua ghi chồng lấn thực sự (thay vì chỉ lưu tuần tự cách quãng) là điều kiện bắt buộc để chứng minh cơ chế đồng bộ đa tab hoạt động tin cậy trong thực tế.

**Independent Test**: Khởi chạy bài kiểm thử tự động trong đó hai tab cùng đọc một phiên bản hồ sơ ban đầu và kích hoạt lưu đồng thời (chồng lấn thời gian thực thi); xác nhận xung đột được bắt và thử lại thành công, giữ đủ mẫu chữ mới của cả hai tab và không phục hồi mẫu chữ đã bị xóa.

**Acceptance Scenarios**:

1. **Given** hai tab cùng đọc hồ sơ ở phiên bản `V1` trong môi trường không có khóa đồng bộ trình duyệt, **When** tab 1 dạy ký tự `A`, tab 2 dạy ký tự `B` và cả hai phát lệnh lưu chồng lấn nhau trước khi bên nào hoàn tất, **Then** tab đến sau phát hiện xung đột phiên bản, tự động thử lại quá trình đọc-hợp nhất-lưu và kết quả cuối cùng chứa đầy đủ cả ký tự `A` lẫn `B` mà không bị nhân bản.
2. **Given** hai tab cùng đọc hồ sơ ở phiên bản `V1` có sẵn ký tự `X`, **When** tab 1 xóa ký tự `X` và lưu thành công ngay trước khi tab 2 lưu việc dạy thêm ký tự `Y` dựa trên trạng thái `V1` cũ, **Then** quá trình thử lại của tab 2 bảo toàn trạng thái đã xóa của ký tự `X` (ký tự `X` không sống lại) đồng thời lưu thành công ký tự `Y`.

---

### User Story 3 - Khôi phục Bộ xử lý Nền Tương tác & Chống Trùng lặp Khi Quá hạn Chờ (Priority: P2)

Người dùng đang sử dụng ứng dụng đã khởi động hoàn tất để kết xuất chữ viết tay hoặc lưu mẫu chữ thì bộ xử lý nền gặp sự cố nghiêm trọng (lỗi giải mã dữ liệu, tràn bộ nhớ hoặc treo quá thời gian chờ). Thay vì bị kẹt ở màn hình lỗi hoặc buộc phải tải lại toàn bộ trang web làm mất nội dung văn bản đang soạn dở, người dùng nhìn thấy thông báo lỗi rõ ràng kèm nút hành động "Thử lại". Khi nhấn "Thử lại", hệ thống tự động dọn dẹp bộ xử lý cũ bị lỗi, khởi tạo bộ xử lý mới, nạp lại hồ sơ kho mẫu hiện hành và khôi phục trạng thái sẵn sàng làm việc. Đồng thời, nếu một thao tác thay đổi kho mẫu bị quá thời gian chờ hoặc bộ xử lý phải khởi động lại, hệ thống ngăn chặn việc áp dụng trùng lặp thao tác cũ gây sai lệch dữ liệu.

**Why this priority**: Bảo vệ trải nghiệm người dùng và văn bản đang soạn thảo khi xảy ra sự cố bộ xử lý nền, đồng thời đáp ứng đúng cam kết về khả năng tự phục hồi trên giao diện mà không gây nhân đôi dữ liệu khi thử lại.

**Independent Test**: Kích hoạt lỗi bộ xử lý nền (bao gồm lỗi thực thi và lỗi giải mã thông điệp) sau khi ứng dụng đã khởi động xong; xác nhận nút "Thử lại" xuất hiện, khi bấm vào sẽ khởi tạo lại bộ xử lý nền, nạp lại kho mẫu và tiếp tục thực hiện yêu cầu mới thành công mà không mất dữ liệu trên trang.

**Acceptance Scenarios**:

1. **Given** ứng dụng đã khởi động xong và người dùng đang soạn thảo văn bản, **When** bộ xử lý nền gặp lỗi nghiêm trọng hoặc lỗi giải mã thông điệp, **Then** mọi yêu cầu đang chờ được hủy an toàn và giao diện hiển thị thông báo lỗi kèm nút "Thử lại" có thể tương tác.
2. **Given** giao diện đang ở trạng thái báo lỗi bộ xử lý nền, **When** người dùng nhấn nút "Thử lại", **Then** hệ thống chấm dứt hẳn bộ xử lý cũ, tạo bộ xử lý mới, nạp lại hồ sơ kho mẫu đang hoạt động và đưa giao diện về trạng thái sẵn sàng mà không làm mất nội dung văn bản người dùng đã nhập.
3. **Given** một yêu cầu thay đổi hoặc đồng bộ kho mẫu bị quá hạn chờ trên giao diện trong khi bộ xử lý nền vẫn đang chạy ngầm, **When** hệ thống hủy chờ do quá hạn và người dùng thực hiện thử lại, **Then** hệ thống cách ly hoặc chấm dứt phiên xử lý bị treo trước khi thực hiện lại, đảm bảo thao tác thay đổi không bị ghi nhận hai lần.

---

### User Story 4 - Nguyên tử hóa Cập nhật Bộ nhớ Đệm Ngoại tuyến & Tách Tài nguyên Tùy chọn (Priority: P2)

Người dùng truy cập ứng dụng lần đầu hoặc khi có bản cập nhật phần mềm mới trong điều kiện mạng chập chờn. Quá trình cài đặt bản cập nhật mới chỉ nạp trước các tài nguyên cốt lõi bắt buộc vào một không gian lưu trữ có định danh phiên bản riêng biệt; nếu bất kỳ tài nguyên cốt lõi nào tải thất bại giữa chừng, không gian lưu trữ đang cài đặt dở dang được dọn sạch hoàn toàn để không làm hỏng bộ tài nguyên của phiên bản cũ đang hoạt động. Các gói thư viện mở rộng chỉ phục vụ chức năng nhập tài liệu nâng cao được tách khỏi danh sách bắt buộc lúc cài đặt ban đầu, giúp ứng dụng khởi động nhanh hơn và không bị lỗi cài đặt ngoại tuyến chỉ vì một gói mở rộng tùy chọn chưa tải được.

**Why this priority**: Đảm bảo tính năng hoạt động ngoại tuyến luôn nhất quán 100%, không bao giờ rơi vào trạng thái pha trộn nửa cũ nửa mới khi rớt mạng giữa lúc cập nhật, đồng thời tối ưu dung lượng tải bắt buộc khi khởi động.

**Independent Test**: Mô phỏng lỗi mạng ở tệp cuối cùng trong quá trình cài đặt bộ nhớ đệm ngoại tuyến mới; xác nhận quá trình cài đặt bị hủy nguyên tử, bộ nhớ đệm dở dang bị xóa bỏ và bộ nhớ đệm của phiên bản đang chạy vẫn nguyên vẹn. Xác nhận danh sách tài nguyên bắt buộc lúc cài đặt không chứa các gói thư viện nhập tài liệu tải lười.

**Acceptance Scenarios**:

1. **Given** ứng dụng đang có phiên bản bộ nhớ đệm `V1` hoạt động ổn định và phát hiện bản cập nhật `V2`, **When** quá trình tải tài nguyên cốt lõi của `V2` bị lỗi ở một tệp bất kỳ sau khi đã tải xong một số tệp trước đó, **Then** hệ thống hủy bỏ việc kích hoạt `V2`, xóa sạch bộ nhớ đệm `V2` chưa hoàn chỉnh và giữ nguyên bộ nhớ đệm `V1` không bị ghi đè.
2. **Given** người dùng mở ứng dụng để sử dụng chức năng viết chữ cơ bản, **When** trình quản lý ngoại tuyến thực hiện cài đặt bộ nhớ đệm ban đầu, **Then** chỉ các tài nguyên cốt lõi được yêu cầu tải bắt buộc, còn các gói thư viện mở rộng phục vụ nhập tài liệu chỉ được tải và lưu vào bộ nhớ đệm khi người dùng thực sự sử dụng tính năng đó.

---

### Edge Cases

- **Tab giữ hồ sơ cũ cố lưu sau khi hồ sơ bị xóa hoàn toàn**: Khi tất cả các lần thử lại đều phát hiện hồ sơ mục tiêu không còn tồn tại trong kho lưu trữ sau khi đã từng được đồng bộ trước đó, hệ thống phải dừng thử lại và thông báo rõ cho người dùng rằng hồ sơ đã bị xóa ở một tab khác thay vì tự ý tái tạo hồ sơ cũ.
- **Lỗi đồng bộ xảy ra ngay trong callback giao dịch sau khi đã phát lệnh ghi**: Giao dịch cơ sở dữ liệu phải được gọi lệnh hủy chủ động ngay trong khối bắt lỗi để ngăn trình duyệt tự động cam kết các lệnh ghi đã xếp hàng trước thời điểm ném lỗi.
- **Yêu cầu thay đổi dữ liệu bị hết thời gian chờ (timeout)**: Khi một yêu cầu gửi tới bộ xử lý nền bị quá hạn chờ, bộ xử lý đó có thể vẫn đang chạy ngầm và làm biến đổi trạng thái nội bộ; hệ thống phải đánh dấu bộ xử lý ở trạng thái cần tái khởi tạo hoặc chấm dứt nó để ngăn phản hồi muộn hoặc trạng thái dở dang gây nhiễm bẩn cho lần thử lại tiếp theo.
- **Người dùng nhấn nút "Thử lại" liên tiếp nhiều lần khi khôi phục bộ xử lý nền**: Hệ thống phải khóa nút hoặc gom yêu cầu khôi phục để đảm bảo chỉ có duy nhất một tiến trình khởi tạo lại bộ xử lý nền chạy tại một thời điểm.
- **Mất mạng ngay khi đang tải tệp cốt lõi cuối cùng trong quá trình cài đặt ngoại tuyến**: Bộ nhớ đệm tạm thời của phiên bản mới phải được dọn dẹp triệt để trong nhánh xử lý lỗi trước khi kết thúc sự kiện cài đặt, và tiến trình mới không được chiếm quyền điều khiển phiên bản đang chạy.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cơ chế lưu hồ sơ kho mẫu MUST hỗ trợ kiểm soát cạnh tranh ba trạng thái rõ rệt: (a) kỳ vọng hồ sơ đã tồn tại với dấu thời gian phiên bản cụ thể, (b) kỳ vọng hồ sơ chưa tồn tại (khởi tạo mới lần đầu), và (c) ghi không điều kiện khi được chỉ định tường minh.
- **FR-002**: Khi lưu hồ sơ với kỳ vọng phiên bản cụ thể nhưng hồ sơ trong kho lưu trữ đã bị xóa (không còn tồn tại), hệ thống MUST phát sinh lỗi xung đột cạnh tranh và hủy bỏ giao dịch, tuyệt đối không ghi đè để làm sống lại hồ sơ đã xóa.
- **FR-003**: Khi lưu hồ sơ với kỳ vọng chưa tồn tại nhưng một phiên làm việc khác đã tạo hồ sơ đó trước, hệ thống MUST phát sinh lỗi xung đột cạnh tranh để kích hoạt luồng đọc lại và hợp nhất dữ liệu.
- **FR-004**: Trong trình quản lý giao dịch cơ sở dữ liệu, nếu hàm thao tác phát sinh ngoại lệ đồng bộ, hệ thống MUST chủ động gọi lệnh hủy giao dịch trước khi từ chối kết quả để ngăn chặn việc tự động cam kết các thao tác đã xếp hàng trước đó.
- **FR-005**: Quy trình đồng bộ và lưu hồ sơ đang hoạt động MUST xử lý an toàn các cuộc đua ghi đồng thời thực sự giữa nhiều tab (cả khi có và không có khóa hệ thống): tự động phát hiện xung đột, đọc lại dữ liệu mới nhất, hợp nhất mẫu chữ từ các bên và bảo toàn trạng thái đã xóa của ký tự mà không làm mất hay nhân đôi mẫu chữ.
- **FR-006**: Khi bộ xử lý nền gặp sự cố thực thi, lỗi giải mã thông điệp hoặc treo quá thời hạn chờ (kể cả sau khi ứng dụng đã khởi động thành công), giao diện MUST cung cấp hành động "Thử lại" trực tiếp cho phép chấm dứt bộ xử lý lỗi, khởi tạo bộ xử lý mới, nạp lại hồ sơ hiện hành và khôi phục hoạt động mà không cần tải lại trang.
- **FR-007**: Khi một yêu cầu sang bộ xử lý nền bị quá thời gian chờ, hệ thống MUST chấm dứt hoặc vô hiệu hóa phiên bộ xử lý bị treo đó để đảm bảo công việc đang chạy ngầm không thể tiếp tục thay đổi trạng thái hoặc gây thực thi trùng lặp khi người dùng thử lại.
- **FR-008**: Trình quản lý bộ nhớ đệm ngoại tuyến MUST sử dụng định danh phiên bản riêng biệt cho mỗi bản phát hành và đảm bảo tính nguyên tử khi cài đặt: chỉ kích hoạt phiên bản mới sau khi toàn bộ tài nguyên cốt lõi đã được tải và xác thực thành công; nếu bất kỳ tài nguyên cốt lõi nào lỗi, phải xóa bỏ bộ nhớ đệm đang cài đặt dở dang.
- **FR-009**: Danh sách tài nguyên nạp trước bắt buộc lúc cài đặt ngoại tuyến MUST chỉ bao gồm các tài nguyên cốt lõi phục vụ khởi động và viết chữ; các gói thư viện mở rộng phục vụ nhập tài liệu nâng cao phải được tách sang cơ chế nạp và lưu đệm theo nhu cầu sử dụng.
- **FR-010**: Bộ kiểm thử tự động MUST bao phủ đầy đủ các kịch bản: từ chối ghi lại hồ sơ đã xóa, xung đột tạo mới đồng thời, cuộc đua lưu chồng lấn thực sự giữa hai tab không có khóa hệ thống, hủy giao dịch khi lỗi đồng bộ, lỗi giải mã thông điệp bộ xử lý nền, khôi phục bộ xử lý nền bằng nút "Thử lại" sau khi ứng dụng đã chạy, và tính nguyên tử của bộ nhớ đệm ngoại tuyến.

### Key Entities *(include if feature involves data)*

- **ConcurrencyExpectation**: Trạng thái kỳ vọng phiên bản khi ghi hồ sơ, bao gồm ba chế độ: yêu cầu khớp dấu thời gian cụ thể (hồ sơ phải tồn tại), yêu cầu hồ sơ chưa tồn tại (khởi tạo mới), hoặc không kiểm tra phiên bản (ghi cưỡng bức).
- **WorkerSession**: Phiên làm việc của bộ xử lý nền gắn với mã thế hệ (epoch/generation), trạng thái sẵn sàng, danh sách yêu cầu đang chờ và quy trình chấm dứt/tái khởi tạo sạch khi gặp sự cố hoặc quá hạn chờ.
- **OfflineCacheRelease**: Phiên bản bộ nhớ đệm ngoại tuyến có định danh gắn với bản dựng, tách biệt nhóm tài nguyên cốt lõi bắt buộc (nạp nguyên tử lúc cài đặt) và nhóm tài nguyên mở rộng tùy chọn (nạp và lưu đệm khi gọi tính năng).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các thao tác lưu từ tab giữ phiên bản cũ sau khi hồ sơ đã bị xóa ở tab khác đều bị chặn lại bởi cơ chế kiểm soát cạnh tranh (0 trường hợp hồ sơ đã xóa tự động sống lại).
- **SC-002**: 100% các cuộc đua ghi đồng thời chồng lấn giữa hai tab (cả khi bật và tắt khóa đồng bộ trình duyệt) đều hội tụ chính xác sau khi tự động thử lại: giữ đủ 100% mẫu chữ mới của cả hai bên và 0% ký tự đã xóa bị hồi sinh.
- **SC-003**: Người dùng có thể khôi phục bộ xử lý nền bị lỗi hoặc bị treo ngay trên giao diện chỉ với 1 thao tác nhấn "Thử lại" (hoàn tất tái khởi tạo và nạp lại hồ sơ trong dưới 15 giây trên môi trường tiêu chuẩn) mà không mất nội dung văn bản đang soạn thảo và không bị nhân đôi dữ liệu kho mẫu.
- **SC-004**: 100% các lần cài đặt hoặc cập nhật bộ nhớ đệm ngoại tuyến bị gián đoạn giữa chừng đều giữ nguyên vẹn bộ nhớ đệm của phiên bản đang hoạt động (0 tài nguyên bị ghi đè một phần) và giảm số lượng tệp bắt buộc tải lúc cài đặt nhờ tách riêng các gói thư viện nhập tài liệu tùy chọn.
- **SC-005**: Toàn bộ chuỗi kiểm định chất lượng (kiểm tra quy chuẩn mã nguồn, kiểm thử đơn vị, kiểm thử cầu nối trình duyệt, kiểm thử chuẩn đầu ra và kiểm thử đầu-cuối đa tab) đạt tỷ lệ vượt qua 100%.

## Assumptions

- Khi một hồ sơ đang mở bị xóa hoàn toàn bởi một tab khác, việc từ chối lưu bản sửa đổi cũ và thông báo xung đột cho người dùng là hành vi an toàn ưu tiên hơn việc âm thầm tạo lại hồ sơ đã xóa.
- Khi một yêu cầu gửi tới bộ xử lý nền bị quá thời hạn chờ (mặc định 60 giây), bộ xử lý đó được xem là đã rơi vào trạng thái không xác định và việc chấm dứt để khởi tạo lại bộ xử lý mới là cách duy nhất đảm bảo tính toàn vẹn tuyệt đối cho kho mẫu trong bộ nhớ.
- Các gói thư viện mở rộng phục vụ nhập tài liệu Word vẫn được đóng gói sẵn trong thư mục phân phối của ứng dụng web để có thể tải nội bộ bất cứ lúc nào và được lưu vào bộ nhớ đệm ngay trong lần đầu người dùng sử dụng tính năng nhập tài liệu.
