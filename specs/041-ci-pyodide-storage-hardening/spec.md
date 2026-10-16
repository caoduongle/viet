# Feature Specification: Khắc phục CI Pyodide Golden Master, An toàn Giao dịch Lưu trữ & Cứng hóa Worker (CI Pyodide Golden Master Fix, Storage Transaction Integrity & Worker Hardening)

**Feature Branch**: `041-ci-pyodide-storage-hardening`

**Created**: 2026-10-16

**Status**: Draft

**Input**: User description: "Rà soát repository caoduongle/viet nhánh main commit 7ae70ee ngày 16/10/2026. Lỗi ưu tiên cao nhất: CI đang thất bại tại bước Verify Golden Master in Pyodide (scripts/test_golden_pyodide.mjs) ở ca markdown_list in cùng một chuỗi SHA-256 nhưng vẫn đánh dấu FAIL. Ưu tiên bảo vệ dữ liệu kho mẫu: saveProfile() chờ tx.oncomplete, sửa lệch dấu thời gian đồng bộ, kiểm soát khóa khi thiếu Web Locks. Độ tin cậy Web Worker: timeout cho sendWorkerMessage, xử lý worker.onerror/onmessageerror, không âm thầm bỏ qua lỗi tải wheel DOCX. Cứng hóa DOM: bảng ký hiệu LaTeX dùng createElement/textContent hoặc escapeHtml. Đồng bộ tài liệu và phiên bản Python."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Khôi phục và Cứng hóa Kiểm tra Golden Master trên Pyodide (Priority: P1) [MVP]

Người phát triển phần mềm và hệ thống CI chạy quy trình xác thực Golden Master trên môi trường WebAssembly (Pyodide). Khi một ca kiểm thử chạy, hệ thống đánh giá tính tương thích và tính toàn vẹn của kết quả kết xuất chữ viết tay (.xopp) và lưới luyện viết chữ phụ (_thieu.xopp) một cách minh bạch, độc lập. Trong trường hợp có bất kỳ sai khác nào, hệ thống thông báo tường minh tệp nào bị sai (tệp kết xuất chính hay tệp lưới phụ), trạng thái tồn tại của tệp, mã băm mong đợi so với mã băm nhận được kèm theo độ dài và kiểu dữ liệu, thay vì đánh tráo lỗi của tệp phụ thành lỗi không khớp mã băm của tệp chính.

**Why this priority**: Bước kiểm tra Golden Master trong Pyodide hiện đang chặn toàn bộ luồng CI của Web Client (khiến các bước kiểm thử JavaScript và Playwright phía sau không thể chạy). Việc khôi phục CI xanh với chẩn đoán chính xác là điều kiện tiên quyết để duy trì chất lượng dự án.

**Independent Test**: Chạy `node scripts/test_golden_pyodide.mjs`; xác nhận cả 8 ca kiểm thử (bao gồm `markdown_list`, `co_ban`, `strict_case`, `tuy_chon`, `nhieu_trang`, `assemble_letters`, `math`, `table`) đều vượt qua với mã thoát 0 và in thông tin chẩn đoán phân định rõ ràng giữa tệp chính và tệp lưới phụ.

**Acceptance Scenarios**:
1. **Given** ca kiểm thử `markdown_list` yêu cầu kiểm tra cả tệp `.xopp` và tệp lưới `_thieu.xopp`, **When** thực thi trong môi trường Pyodide với tùy chọn kích hoạt lưới thiếu, **Then** hệ thống so sánh mã băm của cả hai tệp độc lập và đánh dấu thành công khi cả hai khớp với chuẩn tham chiếu CPython.
2. **Given** một ca kiểm thử Golden Master gặp lỗi ở tệp lưới phụ `_thieu.xopp`, **When** ghi nhận thất bại, **Then** nhật ký hiển thị rõ ràng tệp phụ bị thiếu hoặc sai lệch mã băm nào (kèm độ dài và giá trị thực tế), không hiển thị trùng lặp mã băm tệp chính như một kết quả sai giả.

---

### User Story 2 - Bảo vệ Tính toàn vẹn Giao dịch Lưu trữ Kho mẫu & Đồng bộ Đa tab (Priority: P1)

Người dùng thực hiện viết chữ, thêm mẫu chữ mới, đổi tên hồ sơ hoặc xóa ký tự trên một hoặc nhiều tab trình duyệt mở đồng thời. Hệ thống đảm bảo mọi thay đổi đối với kho mẫu và cài đặt người dùng chỉ được xác nhận là "Đã lưu" trên giao diện khi giao dịch cơ sở dữ liệu trình duyệt (IndexedDB) đã hoàn tất (commit) thành công ở cấp transaction. Khi có sự cố (hết dung lượng lưu trữ, giao dịch bị hủy), hệ thống bắt lỗi kịp thời và hiển thị thông báo rõ ràng cho người dùng. Dấu thời gian đồng bộ giữa các tab được cập nhật chính xác từ bản ghi đã lưu thành công, ngăn ngừa việc một tab tự coi dữ liệu của chính mình là thay đổi ngoại lai để hợp nhất thừa. Khi trình duyệt thiếu cơ chế Web Locks API, hệ thống kích hoạt cơ chế khóa tuần tự hóa dự phòng an toàn để bảo vệ kho mẫu khỏi bị ghi đè chéo.

**Why this priority**: Kho mẫu chữ viết tay là tài sản cá nhân quan trọng của người dùng. Việc xác nhận lưu trước khi transaction commit hoặc lệch dấu thời gian đồng bộ có thể dẫn đến mất dữ liệu hoặc xung đột kho mẫu khi dùng nhiều tab.

**Independent Test**: Chạy bộ kiểm thử tự động cho lớp lưu trữ: mô phỏng giao dịch bị hủy (abort), lỗi vượt dung lượng (quota exceeded), và kịch bản ghi xen kẽ giữa các tab khi tắt/bật Web Locks API; xác nhận dữ liệu kho mẫu không bao giờ bị mất hoặc rơi vào trạng thái không nhất quán.

**Acceptance Scenarios**:
1. **Given** người dùng thêm hoặc sửa mẫu chữ, **When** hệ thống ghi vào cơ sở dữ liệu lưu trữ, **Then** thao tác chỉ trả về thành công khi giao dịch hoàn tất commit ở cấp độ transaction; nếu transaction bị hủy hoặc lỗi, thao tác trả về lỗi tương ứng.
2. **Given** một tab vừa hoàn tất lưu kho mẫu và cập nhật dấu thời gian, **When** tab đó thực hiện kiểm tra đồng bộ tiếp theo, **Then** dấu thời gian cục bộ khớp với dấu thời gian trong bản ghi đã lưu, không kích hoạt quy trình hợp nhất thừa đối với chính thay đổi vừa tạo.
3. **Given** môi trường trình duyệt không hỗ trợ Web Locks API, **When** hai tab cùng thực hiện ghi kho mẫu đồng thời, **Then** hệ thống kích hoạt cơ chế tuần tự hóa dự phòng an toàn, bảo đảm các thao tác ghi được thực hiện tuần tự và không làm mất dữ liệu của nhau.

---

### User Story 3 - Cứng hóa Vòng đời Yêu cầu Web Worker & Chẩn đoán Nạp Thư viện DOCX (Priority: P2)

Người dùng thực hiện các thao tác tính toán nặng như kết xuất văn bản dài hoặc nạp tệp tài liệu Word (.docx). Giao diện gửi yêu cầu sang Web Worker (Pyodide) và duy trì cơ chế giám sát vòng đời chặt chẽ: nếu Worker gặp sự cố dừng đột ngột hoặc bị treo quá thời hạn cho phép, giao diện lập tức dọn dẹp các yêu cầu đang chờ, giải phóng tài nguyên và hiển thị trạng thái lỗi rõ ràng kèm tùy chọn "Thử lại". Khi người dùng nạp tệp Word đòi hỏi các gói thư viện bổ sung, hệ thống kiểm tra tính hợp lệ của phản hồi mạng khi tải từng gói thư viện; nếu tải thất bại (lỗi mạng hoặc HTTP 404), hệ thống dừng ngay lập tức và thông báo chính xác gói thư viện bị lỗi kèm hướng dẫn khắc phục, thay vì âm thầm bỏ qua để rồi phát sinh lỗi import khó hiểu phía sau.

**Why this priority**: Web Worker chạy Pyodide WebAssembly có thể gặp trục trặc bộ nhớ hoặc treo khi tài liệu quá phức tạp. Việc thiếu timeout và bỏ qua lỗi mạng khi tải thư viện làm giảm độ tin cậy và khả năng tự phục hồi của ứng dụng web.

**Independent Test**: Gửi yêu cầu giả lập Worker bị treo hoặc tắt giữa chừng; xác nhận Promise yêu cầu bị từ chối sau thời gian timeout và giao diện hiển thị thông báo lỗi thân thiện. Mô phỏng lỗi tải gói wheel DOCX (HTTP 404 hoặc mất mạng); xác nhận hệ thống báo lỗi rõ tên gói và mã lỗi phản hồi mạng ngay tại bước tải.

**Acceptance Scenarios**:
1. **Given** một yêu cầu xử lý gửi sang Web Worker bị treo quá thời hạn quy định, **When** hết thời gian chờ, **Then** hệ thống hủy yêu cầu khỏi danh sách chờ, từ chối Promise với thông báo quá hạn, và hiển thị thông báo kèm nút cho phép người dùng thử lại.
2. **Given** Web Worker phát sinh lỗi nội bộ (`worker.onerror` hoặc `worker.onmessageerror`), **When** sự kiện kích hoạt, **Then** toàn bộ các yêu cầu đang chờ được từ chối an toàn và giao diện chuyển sang trạng thái cảnh báo phục hồi.
3. **Given** người dùng nạp tệp DOCX nhưng mạng gặp sự cố khiến một gói thư viện bổ trợ không thể tải về, **When** phản hồi HTTP trả về lỗi, **Then** quá trình dừng ngay tại gói đó, thông báo rõ ràng tên gói thư viện và trạng thái kết nối mạng, không đánh dấu gói đã cài đặt thành công.

---

### User Story 4 - Chuẩn hóa Xử lý DOM Bảng Ký hiệu & Đồng bộ Tài liệu Phiên bản (Priority: P3)

Người dùng mở bảng ký hiệu toán học / LaTeX trong trình soạn thảo để chọn và chèn các ký hiệu đặc biệt vào văn bản. Giao diện dựng các nhóm ký hiệu và hiển thị thông báo lỗi bằng các phần tử DOM có cấu trúc an toàn, tuân thủ nhất quán nguyên tắc chống tấn công tiêm mã (XSS) trên toàn bộ ứng dụng. Đồng thời, các nhà phát triển và người sử dụng tra cứu tài liệu dự án nhận được thông tin nhất quán và chính xác 100% về các phiên bản môi trường thực thi được kiểm thử và bảo đảm chính thức bởi hệ thống CI.

**Why this priority**: Củng cố tính nhất quán kiến trúc mã nguồn frontend theo nguyên tắc xử lý DOM an toàn, và duy trì độ tin cậy của tài liệu kỹ thuật dự án.

**Independent Test**: Kiểm tra mã nguồn giao diện bảng ký hiệu LaTeX không sử dụng nội suy chuỗi thô chưa qua xử lý an toàn; kiểm tra tài liệu `README.md` và tệp cấu hình dự án phản ánh chính xác ma trận phiên bản môi trường thực thi được CI kiểm tra.

**Acceptance Scenarios**:
1. **Given** bảng ký hiệu LaTeX hiển thị danh sách nhóm ký hiệu hoặc thông báo lỗi, **When** giao diện dựng các phần tử lên màn hình, **Then** tiêu đề nhóm và thông báo lỗi được gán nội dung văn bản thuần qua thuộc tính an toàn hoặc được mã hóa an toàn, không có nguy cơ phá vỡ cấu trúc DOM.
2. **Given** tệp cấu hình dự án và tài liệu hướng dẫn, **When** người đọc kiểm tra thông tin phiên bản môi trường hỗ trợ, **Then** tài liệu và cấu hình CI thống nhất chính xác về các phiên bản được hỗ trợ và kiểm thử chính thức.

---

### Edge Cases

- **Tệp lưới phụ không tồn tại khi kiểm tra Golden Master**: Hệ thống phải báo rõ `missing_grid_path` là rỗng/không tìm thấy, thay vì so sánh chuỗi mã băm rỗng hoặc lấy mã băm của tệp chính thế vào.
- **Trình duyệt từ chối cấp quyền Web Locks hoặc ở chế độ ẩn danh (Private Browsing)**: Cơ chế khóa tuần tự hóa dự phòng qua cơ sở dữ liệu IndexedDB phải kích hoạt tự động mà không ném ngoại lệ làm sập ứng dụng.
- **Dung lượng lưu trữ trình duyệt bị cạn kiệt trong lúc đang commit transaction**: Giao dịch bị hủy (`tx.onabort`), hệ thống bắt đúng `QuotaExceededError` và hiển thị cảnh báo giải phóng dung lượng cho người dùng mà không làm hỏng kho mẫu hiện có.
- **Yêu cầu sang Worker bị timeout đúng lúc Worker vừa gửi kết quả về**: Tránh xử lý hai lần hoặc gây race condition; yêu cầu đã timeout bị hủy bỏ và kết quả muộn bị loại bỏ an toàn.
- **Tệp wheel tải về bị gián đoạn giữa chừng**: Kiểm tra mã trạng thái phản hồi HTTP và độ dài nội dung tải về trước khi chuyển sang hệ thống tệp ảo của Pyodide.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Kịch bản kiểm tra `test_golden_pyodide.mjs` MUST phân định rạch ròi kết quả xác thực giữa tệp kết xuất chính `.xopp` và tệp lưới ô phụ `_thieu.xopp`, in đầy đủ mã băm thực tế, mã băm mong đợi, trạng thái tệp và độ dài khi có sai lệch.
- **FR-002**: Kịch bản `test_golden_pyodide.mjs` MUST chạy ca `markdown_list` (và các ca kiểm thử lưới ô nếu có) với tùy chọn kích hoạt lưới thiếu (`missing_grid: True`) đồng bộ với cấu hình kiểm thử CPython để kiểm tra trọn vẹn cả tệp chính và tệp phụ.
- **FR-003**: Trong module `webapp/js/storage.js`, các hàm ghi dữ liệu (`saveProfile`, `setSetting`, `deleteProfile`) MUST chỉ giải quyết (resolve) Promise khi sự kiện `tx.oncomplete` của transaction được kích hoạt; bắt buộc lắng nghe `tx.onerror` và `tx.onabort` để từ chối (reject) Promise kèm lỗi chi tiết.
- **FR-004**: Hàm `syncAndSaveActiveProfile` trong `webapp/js/storage.js` MUST cập nhật biến dấu thời gian cục bộ `localSyncedTimestamp` bằng chính dấu thời gian `updated_at` của hồ sơ thực sự được lưu thành công từ `saveProfile`.
- **FR-005**: Hàm `requestProfileLock` trong `webapp/js/storage.js` MUST cung cấp cơ chế tuần tự hóa dự phòng an toàn (dựa trên IndexedDB transaction hoặc cờ kiểm soát phiên bản) khi trình duyệt không hỗ trợ `navigator.locks`, ngăn chặn việc bỏ qua khóa gây xung đột ghi đè dữ liệu.
- **FR-006**: Hàm `sendWorkerMessage` trong `webapp/js/app.js` MUST hỗ trợ cơ chế giới hạn thời gian chờ (timeout); tự động dọn dẹp danh sách yêu cầu chờ `pendingRequests` và reject Promise khi hết hạn.
- **FR-007**: Hệ thống Web Client MUST thiết lập trình lắng nghe sự kiện lỗi Worker (`worker.onerror`, `worker.onmessageerror`), tự động từ chối toàn bộ các yêu cầu đang chờ và chuyển giao diện sang trạng thái thông báo lỗi có khả năng phục hồi / thử lại.
- **FR-008**: Quá trình nạp wheel lười trong `webapp/js/worker/py-worker.js` MUST kiểm tra trạng thái phản hồi HTTP (`resp.ok`); nếu thất bại, phải dừng ngay lập tức, trả về thông báo lỗi chi tiết chứa tên gói và mã trạng thái HTTP, và không thêm gói vào danh sách đã nạp thành công.
- **FR-009**: Giao diện hiển thị bảng ký hiệu LaTeX trong `webapp/js/write.js` MUST sử dụng các phương thức xử lý DOM an toàn (`createElement`, `textContent` hoặc `escapeHtml`) cho tên danh mục ký hiệu và thông báo lỗi, loại bỏ việc nội suy trực tiếp chuỗi chưa qua xử lý vào `innerHTML`.
- **FR-010**: Tài liệu kỹ thuật (`README.md`, `pyproject.toml`) và cấu hình CI (`.github/workflows/ci.yml`) MUST được rà soát và đồng bộ hóa chuẩn xác về các phiên bản môi trường thực thi được kiểm thử và hỗ trợ chính thức.

### Key Entities *(include if feature involves data)*

- **StorageTransaction**: Đối tượng giao dịch cơ sở dữ liệu trình duyệt quản lý tính nguyên tử (atomic) của các thao tác đọc/ghi hồ sơ kho mẫu và cài đặt ứng dụng.
- **SyncProfileRecord**: Bản ghi hồ sơ kho mẫu chứa định danh `id`, tên `name`, khối nhị phân dữ liệu `data`, số mẫu đã dạy `teach_count_since_backup`, và dấu thời gian cập nhật chính xác `updated_at`.
- **WorkerRequest**: Đối tượng yêu cầu gửi từ luồng chính sang Web Worker, bao gồm mã định danh `id`, phương thức gọi `method`, tham số `params`, thời hạn chờ `timeout`, cùng các bộ xử lý `resolve`/`reject`.
- **GoldenResult**: Đối tượng kết quả kiểm thử Golden Master trong Pyodide bao gồm tên ca kiểm thử, kết quả tệp chính, kết quả tệp lưới phụ, mã băm thực tế và mã băm mong đợi của từng tệp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các ca kiểm thử Golden Master trong `scripts/test_golden_pyodide.mjs` (8/8 ca) chạy thành công trên Pyodide với mã thoát 0; lỗi báo cáo sai giả giữa tệp chính và tệp phụ được triệt tiêu hoàn toàn.
- **SC-002**: 100% các thao tác ghi dữ liệu kho mẫu trong `storage.js` được bảo đảm tính nguyên tử qua transaction commit; 0 trường hợp báo "Đã lưu" khi transaction thất bại hoặc bị hủy.
- **SC-003**: Độ lệch dấu thời gian đồng bộ đa tab được triệt tiêu (0% trường hợp tab tự hợp nhất thừa thay đổi của chính mình).
- **SC-004**: 100% các yêu cầu gửi sang Web Worker bị treo hoặc lỗi mạng khi tải wheel DOCX đều được bắt lỗi trong thời gian quy định với thông báo chính xác và có nút thử lại.
- **SC-005**: 100% các điểm dựng DOM trong bảng ký hiệu LaTeX đạt tiêu chuẩn an toàn DOM (0 cảnh báo nội suy thô); toàn bộ các job CI (Lint, Test Core, Web Client, Python 3.14) chạy thành công với mã thoát 0 trên commit mới.

## Assumptions

- Môi trường CI sử dụng Node.js hiện đại hỗ trợ Pyodide v314.0.7 và Playwright Chromium.
- Các tài nguyên tĩnh và wheel tải lười của DOCX được lưu trữ tại đường dẫn hợp lệ trong gói phát hành Web Client hoặc môi trường mạng kiểm thử.
- Trình duyệt mục tiêu của người dùng hỗ trợ IndexedDB v2.
