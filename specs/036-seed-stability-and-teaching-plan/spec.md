# Feature Specification: Cải tiến Seed Stability, Phân trang Bảng và Kế hoạch Dạy chữ (Seed Stability, Table Geometry, and Teaching Plan)

**Feature Branch**: `feat/036-seed-stability`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Cải tiến 'seed' trong repo caoduongle/viet (package chuviettay) kết hợp xử lý dứt điểm các lỗi còn lại về bảng và kiểm thử: (1) Phân trang ô gộp quét source_cell_id toàn bộ bảng từ hàng 0, không ghi đè ô cùng cột; (2) Định danh ô độc lập trong layout pass không làm bẩn TableCell IR; (3) Kẹp toạ độ không làm bẹt/biến dạng nét chữ, ưu tiên co tỷ lệ/dàn trang trước khi vẽ và kiểm tra bounding box; (4) WP1 Seed minh bạch và hợp lệ trong [0, 2**32-1], WriteResult.seed_used, parseSeed web; (5) WP2 Ngẫu nhiên cục bộ trong model/rng.py neo theo token để stable_variants đúng nghĩa, viết lại test_stable_variants.py chứng minh đỏ sang xanh, giữ nguyên từng byte golden master cũ; (6) Kế hoạch dạy chữ 38 mục cốt lõi (33 chữ thường + 5 dấu thanh) mở khóa 700/700 từ SEED, gỡ nghẽn get_minimal_essentials với Bank.can(); (7) WP4 Hoàn thiện tài liệu tiếng Việt và kiểm chứng các nghi vấn kỹ thuật."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phân trang ô gộp toàn bảng, Định danh ô cô lập và Bảo toàn hình thái nét vẽ (Priority: P1)

Người dùng kết xuất bảng biểu phức tạp có ô gộp nhiều hàng (`rowspan > 1`) trải dài qua 3 hoặc nhiều trang, với các ô nằm gần mép trang in. Hệ thống bảo đảm:
1. Khi ô `rowspan` bắt đầu từ các trang trước tiếp tục tràn nội dung sang trang sau, hệ thống quét toàn bộ bảng từ hàng 0 để tìm đúng ô nguồn gốc bằng `source_cell_id`, không bao giờ ghi đè nội dung sang ô khác cùng cột.
2. Định danh ô nguồn được cấp phát tăng đơn điệu và lưu trữ độc lập trong cấu trúc tầng layout (`LaidOutCell`), tuyệt đối không sửa trực tiếp làm bẩn đối tượng `TableCell` trong Document IR.
3. Khi nội dung ô nằm sát lề dưới trang, hệ thống chủ động tính toán dàn trang lại hoặc co tỷ lệ đồng dạng trước khi vẽ; tuyệt đối không kẹp toạ độ cơ học làm dồn các điểm đáy thành các đoạn thẳng ngang bẹt dí (degenerate collinear points); kiểm tra bounding box thực tế của nét sau biến đổi cả theo phương ngang và phương dọc.

**Why this priority**: Bảo đảm tính toàn vẹn hình học và dữ liệu của engine kết xuất bảng biểu: loại bỏ hoàn toàn nguy cơ mất dòng hoặc đè dữ liệu ở các ô gộp đa trang và ngăn chặn biến dạng nét chữ viết tay.

**Independent Test**:
- Render bảng có ô `rowspan=4` chứa 80 dòng bắt đầu từ trang 1 và tiếp nối qua các trang 2, 3, 4. Xác minh toàn bộ 80 dòng hiển thị đầy đủ, đúng thứ tự tuần tự và các ô cùng cột ở các hàng kế tiếp không bị ghi đè.
- Xác minh đối tượng `TableCell` trong Document IR không có trường `source_cell_id` nào bị gán bẩn sau khi layout.
- Render phần tử sát mép trang: kiểm tra hình thái nét chữ không có các đoạn collinear bẹt dí, bounding box thực tế nằm trọn trong lề in.

**Acceptance Scenarios**:

1. **Given** một ô `rowspan > 1` bắt đầu từ một trang trước đó và tiếp tục tràn dòng ở trang hiện tại, **When** chuyển tiếp các dòng chưa vẽ sang trang kế tiếp, **Then** hệ thống tìm kiếm ô nguồn `source_cell_id` trên toàn bộ các hàng của bảng (từ hàng 0), tiếp nối chính xác vào ô gốc mà không phụ thuộc vào `curr_row_idx`.
2. **Given** các ô khác nhau nằm trên cùng một cột ở các hàng khác nhau, **When** ô gộp tiếp nối dòng, **Then** hệ thống không bao giờ ghi đè nội dung vào ô kế cận chỉ vì trùng chỉ số cột.
3. **Given** quá trình bố cục bảng (`TableLayoutEngine`), **When** tạo các ô bố cục `LaidOutCell`, **Then** mỗi ô nhận một ID duy nhất độc lập sinh từ bộ đếm của layout pass; đối tượng `TableCell` của Document IR giữ nguyên tính bất biến.
4. **Given** dòng chữ hoặc công thức nằm gần mép trang, **When** kết xuất nét, **Then** hệ thống ưu tiên co tỷ lệ đồng dạng trước khi vẽ nét, bảo đảm tỷ lệ khung hình và độ cong của nét không bị bẹt hoặc biến dạng collinear tại đường biên $y = y_{\text{max\_page\_y}}$.

---

### User Story 2 - Minh bạch hóa và kiểm chuẩn vòng đời Seed ngẫu nhiên (Priority: P1 - WP1)

Người dùng kết xuất tài liệu viết tay qua CLI, GUI hoặc Web. Hệ thống kiểm chuẩn nghiêm ngặt giá trị hạt giống đầu vào trong khoảng $[0, 2^{32}-1]$. Khi không truyền seed (`seed=None`), hệ thống sinh một seed duy nhất, sử dụng xuyên suốt toàn bộ quá trình vẽ và trả về tường minh trong kết quả (`WriteResult.seed_used`). Người dùng có thể lấy giá trị này chạy lại để tái tạo 100% kết quả ban đầu từng byte.

**Why this priority**: Hiện tại người dùng không có cách nào tái tạo lại một trang viết tay ngẫu nhiên ưng ý khi không chỉ định seed trước. Giao diện Web có lỗi ép kiểu `parseInt(...) || 42` làm mất khả năng nhập seed `0`.

**Independent Test**: Chạy kết xuất với `seed=None`. Xác minh `result.seed_used` là số nguyên trong $[0, 2^{32}-1]$. Chạy lại với `--seed <seed_used>` và xác minh XML đầu ra giống nhau từng byte. Kiểm tra hàm `parseSeed()` trên Web chấp nhận giá trị `0` và giữ nguyên seed hiện tại khi nhập rỗng/sai.

**Acceptance Scenarios**:

1. **Given** tham số `WriteOptions(seed=val)`, **When** `val` là số âm, số thực, kiểu bool hoặc vượt quá $2^{32}-1$, **Then** hệ thống ném `ValueError` với thông báo tiếng Việt rõ ràng.
2. **Given** kết xuất với `seed=None`, **When** `stable_variants=False`, **Then** sinh seed 32-bit từ `secrets.randbits(32)` một lần duy nhất tại đầu phiên và ghi nhận vào `WriteResult.seed_used` trên cả luồng semantic và fidelity.
3. **Given** kết xuất với `seed=None`, **When** `stable_variants=True`, **Then** ấn định seed mặc định là `0` và ghi nhận rõ ràng vào tài liệu và `WriteResult.seed_used`.
4. **Given** người dùng chạy CLI không truyền `--seed`, **When** kết xuất thành công, **Then** CLI in thông báo: `"Seed đã dùng: N (chạy lại với --seed N để có đúng kết quả này)"`.
5. **Given** giao diện Web `write.js`, **When** người dùng nhập seed `0`, **Then** chấp nhận `0` hợp lệ; khi ô nhập rỗng hoặc sai, giữ nguyên seed hiện tại và thông báo nhẹ, không âm thầm đổi thành 42.
6. **Given** tầng `bridge.py`, **When** nhận tùy chọn không hỗ trợ, **Then** trả về danh sách `ignored_options` thay vì âm thầm loại bỏ.
7. **Given** `chuviettay/fidelity/engine.py`, **When** khởi tạo `Writer`, **Then** truyền đầy đủ `seed`, `stable_variants`, `letter_gap`, `pen_clearance_factor`.

---

### User Story 3 - Ngẫu nhiên cục bộ bảo đảm kiểu chữ thực sự ổn định khi chèn sửa văn bản (Priority: P1 - WP2)

Người dùng soạn thảo tài liệu dài với chế độ kiểu chữ ổn định (`stable_variants=True`). Khi chèn thêm từ hoặc đoạn văn ở đầu trang, hoặc sửa một từ ở giữa dòng, hình thái chữ viết tay (biến thể ký tự, độ run tay, khoảng cách giữa các chữ) của các từ không bị sửa ở các dòng khác và đoạn sau giữ nguyên vẹn 100% hình thái.

**Why this priority**: Hiện tại, bộ sinh số ngẫu nhiên dùng chung một luồng tuần tự toàn cục, nên việc chèn dù chỉ một ký tự ở đầu tài liệu sẽ làm trượt toàn bộ chuỗi số ngẫu nhiên của các từ phía sau ("nhấp nháy" trên Web preview). Bài kiểm thử cũ `test_stable_variants.py` đang so sánh `None == None` tạo niềm tin sai lệch về độ ổn định.

**Independent Test**: Viết lại bộ kiểm thử `tests/test_stable_variants.py` sử dụng kho mẫu đa biến thể ($\ge 4$ biến thể/chữ). Chứng minh test thất bại (đỏ) trên mã nguồn cũ khi chèn từ "a" phía trước làm đổi hình thái từ "nay", và thành công (xanh) sau khi áp dụng luồng ngẫu nhiên cục bộ. Kiểm tra tính bất biến tịnh tiến của các đoạn văn phía sau và kiểm tra golden master của chế độ mặc định không đổi từng byte.

**Acceptance Scenarios**:

1. **Given** chế độ `stable_variants=True`, **When** tạo biến thể và nét cho một token, **Then** trạng thái ngẫu nhiên được dẫn xuất cục bộ qua hàm băm chính tắc `blake2b(seed, *khoá)` từ vị trí neo `(seed, "tok", text, k, purpose, idx)` trong đó `k` là thứ tự xuất hiện của token đó trong tài liệu.
2. **Given** module thuần `chuviettay/model/rng.py`, **When** sinh số ngẫu nhiên, **Then** chỉ dựa trên `Random.random()` và tự cài đặt `uniform`, `gauss` (Box-Muller), `randrange`, `choice`, bảo đảm kết quả băm đầu ra hoàn toàn giống nhau trên Python 3.10+, Python 3.14 và Pyodide.
3. **Given** hai lần gọi `Writer.token(t)` với cùng hạt giống và khóa token, **When** có các lệnh gọi token khác xen vào giữa, **Then** hình thái vector nét của token `t` giữ nguyên bit-exact.
4. **Given** một đoạn văn bản được chèn thêm từ mới ở đầu (không trùng từ với phần sau), **When** tài liệu được kết xuất lại, **Then** toàn bộ nét chữ của các dòng phía sau giữ nguyên hình thái (bất biến theo phép tịnh tiến trục $Y$).
5. **Given** một từ lặp lại 50 lần liên tiếp trong tài liệu, **When** kết xuất với `stable_variants=True`, **Then** hệ thống khai thác đa dạng các biến thể có sẵn trong kho mà không có hai lần xuất hiện liền kề nào bị trùng lặp biến thể.
6. **Given** chế độ mặc định `stable_variants=False`, **When** chạy lại bộ kiểm thử `tests/test_golden_master_real_path.py` và `scripts/test_golden_pyodide.mjs`, **Then** toàn bộ mã băm SHA-256 của các tệp đầu ra giữ nguyên từng byte, không có bất kỳ sai lệch nào.
7. **Given** tài liệu dài ~5.000 tokens, **When** đo thời gian kết xuất ở chế độ `stable_variants=True`, **Then** thời gian chạy không chậm hơn quá 1.5 lần so với chế độ ngẫu nhiên tuần tự.

---

### User Story 4 - Chuẩn hóa Kế hoạch Dạy chữ và Gỡ nghẽn Hàng đợi SEED (Priority: P2 - Teaching Plan)

Người dùng bắt đầu dạy chữ viết tay cho hệ thống bằng bộ từ khóa tối thiểu `SEED`. Hệ thống ưu tiên gợi ý các ký tự cốt lõi (33 chữ cái thường và 5 dấu thanh rời) để người dùng chỉ cần dạy 38 mục là có thể ghép và viết được 100% trong số 700 từ thông dụng. Khi người dùng hoàn thành một từ trong danh sách tối thiểu thông qua `teach_char()`, hệ thống nhận diện chính xác độ phủ ký tự của từ đó và gỡ bỏ khỏi hàng đợi cần dạy, không để từ bị kẹt vĩnh viễn trong hàng đợi.

**Why this priority**: Hiện tại, `get_minimal_essentials(60)` trả về các từ đa ký tự như "tôi", "không". Khi người dùng dạy từ "tôi", hàm `teach_char()` lưu vào `bank.words`, nhưng hàm kiểm tra khả năng viết `Bank.can()` hoạt động theo chuẩn char-first chỉ kiểm tra `letters` và `marks`, dẫn đến `Bank.can("tôi")` trả về `False` và mục này kẹt lại hàng đợi mãi mãi. Đồng thời, 5 dấu thanh đang bị xếp ở vị trí 100-104 trong lưới cơ bản khiến việc dạy 33 chữ cái đầu chỉ viết được 185/700 từ.

**Independent Test**: Nạp kho mẫu chứa 33 chữ thường và 5 dấu thanh. Xác minh rằng hệ thống tính toán có thể viết được 700/700 từ trong tập `SEED`. Dạy thử một từ trong hàng đợi `get_minimal_essentials` và xác minh từ đó được giải phóng khỏi hàng đợi cần học mà không bị tắc nghẽn.

**Acceptance Scenarios**:

1. **Given** danh sách từ khóa tối thiểu trong kế hoạch dạy chữ, **When** phân tích cấu trúc ký tự tiếng Việt, **Then** hệ thống ưu tiên tối đa 33 chữ cái thường cơ bản và 5 dấu thanh rời (tổng cộng 38 mục cốt lõi) trước các từ ghép đa ký tự.
2. **Given** người dùng thực hiện dạy một từ hoặc ký tự trong hàng đợi thông qua `teach_char()`, **When** kiểm tra điều kiện hoàn thành với `Bank.can()`, **Then** hàng đợi phản ánh trung thực tiến độ học, gỡ bỏ các mục đã thỏa mãn điều kiện kết xuất.
3. **Given** kho mẫu chỉ mới học các ký tự cấu thành mà chưa lưu mẫu nguyên khối của từ trong `bank.words`, **When** `Bank.can(word)` được gọi, **Then** hàm trả về `True` nếu tất cả chữ cái và dấu thanh cấu thành đã có trong kho.

---

### User Story 5 - Hoàn thiện tài liệu, Parity CLI/GUI/Web và Xác minh Nghi vấn (Priority: P3 - WP4)

Người dùng và nhà phát triển tra cứu tài liệu hướng dẫn về seed và tính ổn định. README, CHANGELOG và tài liệu kỹ thuật được cập nhật chi tiết bằng tiếng Việt chuẩn mực, hướng dẫn rõ ràng cách sử dụng `--seed` để tái tạo kết quả. Toàn bộ các nghi vấn kỹ thuật được kiểm chứng độc lập bằng test tự động.

**Why this priority**: Bảo đảm tính toàn vẹn của tài liệu dự án, giúp người dùng hiểu rõ cơ chế hoạt động của hạt giống ngẫu nhiên và hỗ trợ kiểm thử hồi quy lâu dài.

**Independent Test**: Chạy toàn bộ test suite, kiểm tra CLI `--help` hiển thị mô tả cho cờ `--seed`, kiểm tra tài liệu README có mục "Tái tạo đúng một kết quả", và chạy test xác minh các nghi vấn kỹ thuật (`Random(-5)` vs `Random(5)`, `MathLayoutEngine._scratch`, `Writer.measure_text_width`).

**Acceptance Scenarios**:

1. **Given** giao diện dòng lệnh `hw-note --help`, **When** xem mô tả các tùy chọn, **Then** cờ `--seed` có thông tin hướng dẫn rõ ràng về giá trị số nguyên không âm và ý nghĩa tái tạo kết quả.
2. **Given** tài liệu README và CHANGELOG của dự án, **When** tra cứu phiên bản mới, **Then** các mục thay đổi được ghi nhận đầy đủ bằng tiếng Việt theo phong cách hiện có của kho mã.
3. **Given** nghi vấn kỹ thuật về `Random(-5)` và `Random(5)`, **When** chạy kiểm thử phân tích, **Then** hệ thống có test chứng minh sự trùng lặp hoặc khác biệt giữa hai giá trị hạt giống để làm căn cứ cho việc giới hạn miền giá trị.
4. **Given** cờ `assemble_letters` không còn được `Writer` sử dụng trực tiếp trong luồng mới, **When** hoàn thiện rà soát, **Then** lập báo cáo kỹ thuật rõ ràng về hiện trạng của cờ này và checkbox tương ứng trên GUI mà không gây xáo trộn ngoài phạm vi.

---

### Edge Cases

- Điều gì xảy ra khi người dùng nhập `seed=0` trên Web hoặc CLI?
  Hệ thống coi `0` là một seed hoàn toàn hợp lệ, không bị ghi đè bởi giá trị mặc định 42.
- Điều gì xảy ra khi một từ xuất hiện nhiều lần ở các câu khác nhau trong tài liệu dài?
  Khóa neo cục bộ sử dụng số thứ tự xuất hiện của từ đó (`k`), giúp các lần xuất hiện khác nhau nhận các biến thể phong phú nhưng vẫn hoàn toàn tất định khi chèn sửa các đoạn văn khác.
- Điều gì xảy ra khi người dùng chèn thêm một từ trùng lặp với từ đã có trong tài liệu?
  Từ được chèn mới sẽ làm tăng chỉ số xuất hiện của chính từ đó ở các đoạn sau, trong khi các từ khác xung quanh vẫn giữ nguyên hình thái nét chữ.
- Điều gì xảy ra khi kho mẫu chỉ có 1 biến thể duy nhất cho mỗi chữ cái?
  Bộ ngẫu nhiên cục bộ chọn biến thể duy nhất đó một cách nhất quán, không gây lỗi chia cho 0 hay tràn mảng.
- Điều gì xảy ra khi ô `rowspan=5` bắt đầu từ trang 1 và kéo dài qua trang 2, trang 3 và trang 4?
  Toàn bộ các lát cắt tìm kiếm ô gốc trên toàn bộ các hàng từ hàng 0, định tuyến chính xác 100% dòng dữ liệu không bị rơi rụng.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI tìm kiếm `source_cell_id` trên toàn bộ các hàng của bảng (từ hàng 0) khi tiếp nối dòng ô gộp qua các trang, và KHÔNG ĐƯỢC ghi đè nội dung sang ô khác chỉ vì cùng cột.
- **FR-002**: `TableLayoutEngine` PHẢI sinh mã định danh ô tăng đơn điệu độc lập trong layout pass, lưu trong `LaidOutCell` và TUYỆT ĐỐI KHÔNG sửa trực tiếp đối tượng `TableCell` trong Document IR.
- **FR-003**: Khi kết xuất dòng chữ sát mép trang, hệ thống PHẢI ưu tiên co tỷ lệ hoặc dàn trang trước khi vẽ, bảo đảm tỷ lệ khung hình và độ cong của nét không bị bẹt thành các đoạn collinear degenerate tại mép trang.
- **FR-004**: `WriteOptions.validate()` PHẢI kiểm tra trường `seed`: chỉ chấp nhận `None` hoặc số nguyên `int` (không phải `bool`) nằm trong khoảng $[0, 2^{32}-1]$; ném `ValueError` với thông báo tiếng Việt nếu vi phạm.
- **FR-005**: Hệ thống PHẢI xác định hạt giống hiệu dụng (`seed_used`) một lần duy nhất ở đầu mỗi lượt kết xuất:
  - Nếu người dùng cung cấp seed hợp lệ: sử dụng nguyên giá trị đó.
  - Nếu `seed=None` và `stable_variants=False`: tự sinh bằng `secrets.randbits(32)`.
  - Nếu `seed=None` và `stable_variants=True`: ấn định giá trị `0` cố định.
- **FR-006**: Cấu trúc kết quả `WriteResult` PHẢI bổ sung trường `seed_used: int | None = None` và được điền đầy đủ ở cả luồng kết xuất ngữ nghĩa (`DocumentLayoutEngine`) và luồng fidelity (`FidelityLayoutEngine`).
- **FR-007**: Giao diện dòng lệnh CLI PHẢI in thông báo hướng dẫn tái tạo khi seed được tự sinh: `"Seed đã dùng: N (chạy lại với --seed N để có đúng kết quả này)"`.
- **FR-008**: Giao diện Web (`write.js`) PHẢI tách hàm thuần `parseSeed(val, currentSeed)` có thể kiểm thử bằng `node --test`: chấp nhận giá trị `0`; giữ nguyên seed hiện tại và thông báo nếu nhập rỗng hoặc sai định dạng; loại bỏ hoàn toàn biểu thức `parseInt(...) || 42`.
- **FR-009**: Tầng `chuviettay/browser/bridge.py` PHẢI trả về danh sách `ignored_options` khi nhận được khóa lạ thay vì âm thầm loại bỏ.
- **FR-010**: `chuviettay/fidelity/engine.py` PHẢI truyền đầy đủ các tham số `seed`, `stable_variants`, `letter_gap`, `pen_clearance_factor` vào `Writer`.
- **FR-011**: Hệ thống PHẢI xây dựng module thuần túy `chuviettay/model/rng.py` cung cấp bộ sinh số ngẫu nhiên cục bộ dẫn xuất qua `hashlib.blake2b` trên mã hóa chính tắc phân tách bằng byte `\x00`. Module này chỉ dựa trên `Random.random()` và tự cài đặt `uniform`, `gauss` (Box-Muller), `randrange`, `choice` để bảo đảm tính tất định 100% trên Python 3.10+, Python 3.14 và Pyodide.
- **FR-012**: Khi `stable_variants=True`, toàn bộ các vị trí tiêu thụ ngẫu nhiên (chọn biến thể, jitter giữa chữ, dgap, độ dày/xoay/co giãn nét, đường lượn sóng của dòng, viền bảng, công thức toán) PHẢI lấy từ luồng ngẫu nhiên cục bộ được neo theo khóa ngữ cảnh thay vì luồng tuần tự toàn cục.
- **FR-013**: Chế độ mặc định `stable_variants=False` PHẢI giữ nguyên 100% luồng sinh ngẫu nhiên cũ, bảo đảm mã băm SHA-256 trong `tests/test_golden_master_real_path.py` và `scripts/test_golden_pyodide.mjs` không đổi từng byte.
- **FR-014**: Bộ kiểm thử `tests/test_stable_variants.py` PHẢI được viết lại hoàn toàn, kiểm tra trực tiếp các tag biến thể và toạ độ vector nét vẽ, chứng minh đỏ trên mã nguồn cũ và xanh trên mã nguồn mới.
- **FR-015**: Bổ sung ca kiểm thử golden master riêng biệt cho chế độ `stable_variants=True` trên cả pytest và Pyodide.
- **FR-016**: Kế hoạch dạy chữ PHẢI ưu tiên 38 mục ký tự cốt lõi (33 chữ cái thường và 5 dấu thanh rời) để bảo đảm đủ mẫu ghép được 700/700 từ khóa `SEED`.
- **FR-017**: Khi người dùng dạy từ thông qua `teach_char()`, hàng đợi gợi ý học PHẢI đồng bộ với `Bank.can()` để gỡ bỏ chính xác các mục đã có đủ điều kiện ghép chữ, không để từ khóa bị kẹt vĩnh viễn trong hàng đợi.

### Key Entities

- **Định danh ô bố cục (`LaidOutCellId`)**: Giá trị nguyên tăng dần duy nhất gán cho từng ô trong một lượt bố cục, tồn tại độc lập với mô hình tài liệu Document IR.
- **Hạt giống ngẫu nhiên hiệu dụng (`seed_used`)**: Giá trị số nguyên 32-bit duy nhất đại diện cho toàn bộ yếu tố ngẫu nhiên của một lượt kết xuất tài liệu, cho phép tái hiện kết quả bất biến khi cung cấp lại.
- **Luồng ngẫu nhiên cục bộ (`ScopedRNG`)**: Trình sinh ngẫu nhiên tất định được dẫn xuất độc lập cho từng đơn vị ngữ cảnh (token, dòng, bảng, công thức) từ hạt giống gốc và khóa định danh.
- **Khóa định danh ngữ cảnh (`ContextKey`)**: Chuỗi tuple định danh vị trí tương đối và thứ tự xuất hiện của phần tử văn bản trong tài liệu, bảo đảm tính bất biến khi dịch chuyển ngữ cảnh xung quanh.
- **Tập ký tự tối thiểu (`MinimalEssentials`)**: Danh sách ưu tiên gồm 10 chữ số, 11 dấu câu thông dụng, 33 chữ cái thường và 5 dấu thanh rời phục vụ việc dạy chữ tối ưu nhất.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các dòng văn bản của ô gộp nhiều hàng bắt đầu từ các trang trước được bảo tồn tuần tự nguyên vẹn qua 3+ trang, với 0 dòng bị mất và 0 ô lân cận bị ghi đè.
- **SC-002**: Document IR structures (`TableCell`) giữ nguyên tính bất biến 100%, có 0 trường layout state bị chèn vào đối tượng IR.
- **SC-003**: 100% các giá trị seed đầu vào được kiểm chuẩn chặt chẽ trong $[0, 2^{32}-1]$, loại bỏ hoàn toàn các lỗi tiềm ẩn do seed âm hoặc sai kiểu dữ liệu.
- **SC-004**: Khi chạy kết xuất với `seed=None`, 100% kết quả trả về trường `seed_used` hợp lệ và khi chạy lại với seed đó sẽ tạo ra tệp đầu ra giống nhau từng byte.
- **SC-005**: Khi chèn thêm đoạn văn mới vào đầu tài liệu ở chế độ `stable_variants=True`, tỉ lệ nét chữ của các đoạn văn phía sau giữ nguyên hình thái đạt $\ge 95\%$ (bất biến theo phép tịnh tiến trục $Y$).
- **SC-006**: 100% các bài kiểm thử golden master hiện tại (`stable_variants=False`) giữ nguyên mã băm SHA-256 trên cả Python chuẩn và Pyodide.
- **SC-007**: Người dùng hoàn thành 38 mục ký tự cốt lõi (33 chữ thường + 5 dấu thanh) có thể viết thành công 700/700 từ khóa trong tập `SEED`.
- **SC-008**: Toàn bộ test suite ($\ge 1269$ tests) vượt qua thành công, ruff sạch 100%, không phát sinh cảnh báo mới.
- **SC-009**: Thời gian kết xuất tài liệu văn bản ~5.000 tokens ở chế độ `stable_variants=True` không chậm hơn quá 1.5 lần so với chế độ ngẫu nhiên tuần tự.

## Assumptions

- Thuật toán ghép chữ và khoảng cách nối nét (`Writer.assemble_word`) được giữ nguyên vẹn.
- Bảng mã `CO_BAN_CHARS` và cấu trúc tệp kho mẫu `.json.gz` không bị thay đổi định dạng schema.
- Thư viện chuẩn `hashlib.blake2b` và `random.Random` của Python có sẵn trên mọi nền tảng hỗ trợ (bao gồm Pyodide).
- Người dùng ưu tiên việc tái hiện chính xác kết quả viết tay hơn là hành vi ngẫu nhiên không kiểm soát được.
