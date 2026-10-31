# Feature Specification: Chuẩn hóa script benchmark PUA và tích hợp CI smoke test

**Feature Branch**: `066-pua-benchmark-hardening`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Tôi đã kiểm tra commit mới nhất của caoduongle/viet, đối chiếu với commit a8c167d trước đó và đọc phần triển khai PUA, các bài kiểm thử mới, script benchmark cùng workflow CI. Kết luận: hai điểm còn thiếu của lần rà soát trước đã được xử lý đúng hướng. Việc kiểm tra trực tiếp tập hợp PUA và bổ sung phép đo bằng tracemalloc giúp tăng khả năng phát hiện hồi quy. Tôi chưa thấy lỗi chức năng nghiêm trọng mới trong phần diff này, nhưng còn 3 điểm P3 nên hoàn thiện: (1) P3-1. Tham số --rounds không áp dụng cho toàn bộ benchmark: Trong script, số lượt đo của bộ dữ liệu chính dùng tham số rounds, nhưng kịch bản đối kháng 100.000 ký tự PUA lại truyền cố định rounds=3. Do đó, khi chạy python scripts/benchmark_pua_memory.py --rounds 10, kịch bản chính đo 10 lượt nhưng kịch bản đối kháng vẫn đo 3 lượt. Điều này không khớp với phần trợ giúp CLI; (2) P3-2. Mô tả bộ dữ liệu benchmark chưa chính xác: Hàm make_multilingual_text() hiện tạo ký tự từ một dải CJK Unified Ideographs liên tiếp và thêm U+E000. Trong khi đó, phần báo cáo ghi dữ liệu có cả chữ Cyrillic và ký hiệu toán học; mã hiện tại không tạo những nhóm ký tự ấy. Ngoài ra, 510.001 ký tự trong mẫu chính đều thuộc các vùng mã cần 3 byte UTF-8 mỗi ký tự. Kích thước là khoảng 1,53 MB theo đơn vị thập phân, không phải khoảng 1,0 MB như báo cáo đang ghi. Cần tính kích thước bằng len(text.encode('utf-8')) và tạo mẫu thực sự gồm nhiều hệ chữ và ký hiệu toán học; (3) P3-3. Chưa có kiểm tra tự động việc chạy script trong CI: Workflow .github/workflows/ci.yml hiện chưa có bước chạy script benchmark độc lập. Thêm bước smoke test chạy python scripts/benchmark_pua_memory.py --rounds 1 --json để xác nhận script chạy thành công và xuất JSON hợp lệ, không phụ thuộc vào ngưỡng thời gian tuyệt đối."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chuẩn hóa tính nhất quán của tham số và tính chính xác của dữ liệu benchmark (Priority: P1) 🎯 MVP

Là một kỹ sư đo lường hiệu năng hoặc người đánh giá bên ngoài, tôi muốn tham số `--rounds` áp dụng nhất quán cho toàn bộ các phép đo của kịch bản benchmark, dữ liệu mẫu thực sự mang tính đa ngữ (kết hợp chữ Hán/Nôm, Cyrillic, Hy Lạp, ký hiệu toán học) và dung lượng byte được tính toán chính xác theo mã hóa UTF-8 thực tế, nhằm bảo đảm mọi con số báo cáo đều chuẩn xác, minh bạch và tin cậy tuyệt đối.

**Why this priority**: Độ chính xác và tính nhất quán của công cụ benchmark là nền tảng cho sự tín nhiệm kỹ thuật. Khi người dùng truyền `--rounds 10`, họ kỳ vọng cả kịch bản chính và đối kháng đều tuân thủ số vòng lặp tương ứng, và các thông số mô tả dữ liệu trên báo cáo phải khớp 100% với dữ liệu thực tế được nạp vào bộ nhớ.

**Independent Test**:
- Chạy `python scripts/benchmark_pua_memory.py --rounds 2 --json`: xác nhận cả kịch bản chính lẫn kịch bản đối kháng đều thực hiện đúng 2 vòng đo; dữ liệu kiểm tra chứa thực sự các ký tự Cyrillic, Hy Lạp, Toán học và CJK; dung lượng byte được tính động bằng `len(text.encode("utf-8"))` và phản ánh đúng giá trị thực tế (~1.5 MB).

**Acceptance Scenarios**:
1. **Given** người dùng chạy lệnh `python scripts/benchmark_pua_memory.py --rounds N`, **When** kịch bản thực thi, **Then** cả phép đo dữ liệu chính và kịch bản đối kháng đều áp dụng nhất quán số lượt đo $N$ (hoặc được cấu hình riêng với mô tả rõ ràng).
2. **Given** hàm sinh dữ liệu đa ngữ, **When** tạo văn bản mẫu, **Then** chuỗi sinh ra chứa sự kết hợp thực sự giữa chữ Hán/Nôm (CJK), chữ Cyrillic, chữ Hy Lạp, ký hiệu toán học và ký tự PUA `\ue000`.
3. **Given** kết quả báo cáo (cả bảng văn bản lẫn JSON), **When** hiển thị kích thước văn bản, **Then** dung lượng được tính động từ kích thước byte UTF-8 thực tế, loại bỏ hoàn toàn các con số ước tính cứng không chính xác.

---

### User Story 2 - Kiểm thử tự động Smoke Test cho script benchmark (Priority: P2)

Là một lập trình viên duy trì mã nguồn, tôi muốn có một bài kiểm thử tự động (pytest) kiểm chứng khả năng thực thi từ đầu đến cuối của script benchmark với cờ `--json` và `--rounds 1`, nhằm phát hiện ngay lập tức bất kỳ lỗi cú pháp, lỗi nhập module (import error) hoặc định dạng JSON sai lệch mà không bị phụ thuộc vào ngưỡng thời gian tuyệt đối dễ dao động.

**Why this priority**: Đảm bảo script benchmark luôn hoạt động ổn định qua các lần refactor mà không bị hỏng âm thầm. Việc kiểm thử tính hợp lệ của cấu trúc dữ liệu JSON đầu ra bảo đảm công cụ luôn sẵn sàng cho các luồng tự động hóa.

**Independent Test**:
- Chạy `pytest tests/test_benchmark_pua_smoke.py`: xác nhận script benchmark chạy hoàn tất với mã thoát 0, xuất chuỗi JSON chuẩn và chứa đầy đủ tất cả các trường dữ liệu bắt buộc.

**Acceptance Scenarios**:
1. **Given** môi trường kiểm thử pytest, **When** thực thi bài kiểm thử smoke test của benchmark, **Then** kiểm thử chạy script qua subprocess hoặc hàm điều phối với `--rounds 1 --json` và hoàn thành thành công trong thời gian ngắn.
2. **Given** chuỗi đầu ra từ lệnh, **When** giải mã bằng bộ phân tích cú pháp JSON chuẩn, **Then** dữ liệu phân tích thành công thành đối tượng từ điển có đầy đủ các trường `environment`, `dataset_main`, `results_main`, `dataset_stress`, `results_stress`.
3. **Given** bài kiểm thử smoke test, **When** đánh giá kết quả, **Then** bài kiểm tra chỉ xác nhận tính đúng đắn về cấu trúc, kiểu dữ liệu và mã thoát, tuyệt đối không phụ thuộc vào ngưỡng thời gian thực thi mili-giây tuyệt đối.

---

### User Story 3 - Tích hợp Smoke Test vào Continuous Integration (CI) Workflow (Priority: P3)

Là một người quản lý dự án hoặc DevOps engineer, tôi muốn workflow GitHub Actions tự động thực thi bước kiểm tra nhanh (smoke test) của script benchmark trong mỗi lần push và pull request, bảo đảm công cụ đo lường hiệu năng luôn chạy được trên toàn bộ môi trường CI mà không làm tăng đáng kể thời gian build.

**Why this priority**: CI xanh phải thực sự đại diện cho việc toàn bộ các công cụ công khai trong repository đều hoạt động. Tích hợp trực tiếp vào `.github/workflows/ci.yml` là mắt xích cuối cùng để đảm bảo khả năng tái lập bền vững.

**Independent Test**:
- Kiểm tra file cấu hình workflow `.github/workflows/ci.yml`: có bước chạy `python scripts/benchmark_pua_memory.py --rounds 1 --json` trong các job kiểm thử cốt lõi.

**Acceptance Scenarios**:
1. **Given** cấu hình GitHub Actions trong `.github/workflows/ci.yml`, **When** rà soát các bước của job kiểm thử, **Then** tồn tại bước gọi trực tiếp `python scripts/benchmark_pua_memory.py --rounds 1 --json`.
2. **Given** bước kiểm thử benchmark trên CI, **When** chạy trên các phiên bản Python hỗ trợ (3.12, 3.13, 3.14), **Then** bước này hoàn tất trong dưới 5 giây và trả về mã thoát thành công 0.

---

### Edge Cases

- **Người dùng truyền `--rounds 0` hoặc số âm**: Script tự động điều chỉnh về giá trị tối thiểu là 1 vòng lặp để tránh lỗi chia cho 0 (`ZeroDivisionError`).
- **Môi trường CI không có thông tin processor chi tiết**: Script xử lý an toàn bằng fallback `"Unknown CPU"`, không làm sập tiến trình.
- **Dữ liệu đa ngữ chứa các ký tự Unicode có độ dài UTF-8 biến thiên (1 đến 3 byte)**: Phép tính dung lượng sử dụng `len(text.encode("utf-8"))` phản ánh chính xác 100% dung lượng thực tế.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Kịch bản `scripts/benchmark_pua_memory.py` PHẢI áp dụng nhất quán tham số `--rounds` cho cả kịch bản kiểm thử dữ liệu chính lẫn kịch bản đối kháng lặp lại 100.000 ký tự PUA.
- **FR-002**: Dữ liệu kiểm thử chính trong `scripts/benchmark_pua_memory.py` PHẢI chứa hỗn hợp thực tế gồm ít nhất 4 họ ký tự Unicode khác nhau (CJK/Hán Nôm, Cyrillic, Hy Lạp, Ký hiệu toán học) kèm điểm mã PUA `\ue000`.
- **FR-003**: Kịch bản benchmark PHẢI tính toán kích thước văn bản thử nghiệm một cách động dựa trên kích thước byte mã hóa UTF-8 thực tế (`len(text.encode("utf-8"))`) và hiển thị chính xác theo đơn vị phù hợp (MB/KB) trong cả bảng văn bản và JSON.
- **FR-004**: Repository PHẢI cung cấp một bài kiểm thử tự động (pytest) kiểm chứng khả năng chạy thành công và tính hợp lệ của cấu trúc JSON xuất ra từ `scripts/benchmark_pua_memory.py --rounds 1 --json`.
- **FR-005**: File workflow CI `.github/workflows/ci.yml` PHẢI bổ sung bước thực thi tự động lệnh `python scripts/benchmark_pua_memory.py --rounds 1 --json` trong các job kiểm thử Python.

---

### Key Entities *(include if feature involves data)*

- **Multilingual Benchmark Corpus**: Chuỗi văn bản thử nghiệm được tổng hợp từ 4 dải Unicode phân biệt:
  - CJK Unified Ideographs (`U+4E00..U+5200`): đại diện cho chữ Hán, chữ Nôm (3 bytes/char).
  - Cyrillic (`U+0410..U+044F`): đại diện cho bảng chữ cái Slap (2 bytes/char).
  - Greek & Coptic (`U+0391..U+03C9`): đại diện cho chữ cái Hy Lạp dùng trong toán học (2 bytes/char).
  - Mathematical Operators (`U+2200..U+2280`): đại diện cho các toán tử toán học (3 bytes/char).
  - Private Use Area (`U+E000`): ký tự giữ chỗ va chạm (3 bytes/char).
- **Benchmark JSON Output Schema**: Cấu trúc từ điển JSON gồm các khóa: `environment` (thông tin máy chủ/runtime), `dataset_main` (thông số tập dữ liệu chính gồm cả `text_bytes`), `results_main` (danh sách kết quả 3 phương pháp), `dataset_stress` (thông số kịch bản đối kháng), `results_stress` (kết quả kịch bản đối kháng).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Lệnh `python scripts/benchmark_pua_memory.py --rounds 1 --json` hoàn tất trong dưới 5 giây, xuất ra chuỗi JSON chuẩn và thoát với mã 0.
- **SC-002**: Kích thước byte UTF-8 hiển thị trong báo cáo khớp chính xác 100% với `len(text.encode("utf-8"))`.
- **SC-003**: 100% các bài kiểm thử tự động (bao gồm smoke test mới của benchmark) vượt qua thành công trên pytest.
- **SC-004**: Workflow `.github/workflows/ci.yml` thực thi thành công bước smoke test của script trên tất cả các matrix Python mà không phát sinh lỗi dao động (flakiness).

---

## Assumptions

- Việc thêm bước smoke test benchmark trong CI chỉ tốn thêm 1-2 giây trên mỗi job, không gây ảnh hưởng đến giới hạn thời gian chạy của GitHub Actions (timeout 10 phút).
- Bài kiểm thử smoke test chỉ tập trung xác nhận tính toàn vẹn của tiến trình và định dạng dữ liệu (structural integrity), không đặt bất kỳ giả định nào về tốc độ phần cứng máy chạy CI.
