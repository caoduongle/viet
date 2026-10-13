# Nhật ký thay đổi

## Chưa phát hành — Hạt giống ngẫu nhiên minh bạch, biến thể chữ ổn định và tối ưu kế hoạch dạy chữ (Spec 036)

Cải tiến toàn diện cơ chế hạt giống ngẫu nhiên (seed), bộ sinh ngẫu nhiên cục bộ bảo đảm tính bất biến khi chèn sửa văn bản, và tối ưu hóa lộ trình dạy chữ:

### Hạt giống ngẫu nhiên minh bạch & kiểm chuẩn chặt chẽ (WP1)
- **Kiểm chuẩn miền giá trị seed**: `WriteOptions.validate()` kiểm tra chặt chẽ trường `seed` nằm trong khoảng $[0, 2^{32} - 1]$ hoặc `None`, ném lỗi tiếng Việt rõ ràng; loại bỏ hiện tượng trùng lặp dãy số do `Random(-5) == Random(5)` trong CPython.
- **Minh bạch hóa hạt giống hiệu dụng (`seed_used`)**: Điền đầy đủ trường `seed_used` vào `WriteResult` ở cả hai chế độ Semantic và Fidelity. CLI in thông báo hướng dẫn tái tạo khi seed tự sinh (`Seed đã dùng: N (chạy lại với --seed N để có đúng kết quả này)`).
- **Phân tích hạt giống an toàn trên Web UI**: Tách hàm thuần `parseSeed()` chấp nhận giá trị `0`, không âm thầm fallback về 42 khi nhập rỗng hoặc sai định dạng. Cầu nối `bridge.py` trả về danh sách `ignored_options` khi nhận tùy chọn lạ.

### Bộ ngẫu nhiên cục bộ & Kiểu chữ ổn định (WP2)
- **Bộ sinh ngẫu nhiên cục bộ `ScopedRNG`**: Dẫn xuất luồng con từ `(seed, *context_keys)` qua mã hóa chính tắc `hashlib.blake2b` phân tách bằng `\x00`, tự cài đặt các phân phối ngẫu nhiên trên nền `Random.random()` bảo đảm tính tất định 100% trên Python 3.10+, Python 3.14 và Pyodide.
- **Neo ngẫu nhiên theo token & dòng**: Khi bật `stable_variants=True`, toàn bộ việc chọn biến thể, jitter giữa các chữ, khoảng cách chữ số và hình học dòng được neo cục bộ theo token và vị trí xuất hiện `k`. Việc chèn thêm từ hoặc đoạn văn ở đầu tài liệu không làm đổi biến thể của các từ phía sau.
- **Chống lặp biến thể cục bộ**: Cô lập bộ đệm tránh lặp biến thể liên tiếp trong phạm vi từng token, bảo đảm từ lặp lại nhiều lần không trùng mẫu mà không ảnh hưởng tới các từ khác trong tài liệu.
- **Bảo toàn 100% đường mặc định**: Giữ nguyên từng byte mã băm SHA-256 của các ca kiểm thử Golden Master cho `stable_variants=False`.

### Kế hoạch dạy chữ tối ưu & Gỡ nghẽn hàng đợi SEED (WP3)
- **38 mục ký tự cốt lõi (`CORE_ESSENTIALS_38`)**: Xác định 33 chữ cái thường và 5 dấu thanh rời là tập ký tự tối thiểu có thể mở khóa 100% (700/700) từ trong tập từ khóa thông dụng `SEED`.
- **Đồng bộ kiểm tra khả năng viết `Bank.can()`**: Công nhận các từ nguyên khối đã được dạy trong kho `bank.words` và tên dấu thanh tiếng Việt (`dấu sắc`, `dấu huyền`...), giải phóng triệt để tình trạng từ khóa bị kẹt vĩnh viễn trong hàng đợi `missing_minimal_essentials()`.

## Chưa phát hành — Độ bền vững bố cục bảng, đồng bộ hình học và nhập DOCX (Spec 032)

Tối ưu độ ổn định của bố cục bảng biểu, phân trang an toàn, đồng bộ kích thước công thức toán học và phục hồi chính xác cấu trúc bảng DOCX:

### Phân trang bảng an toàn & kẹp lề trang (US1 - P1)
- **Hoãn nhóm ô gộp sang trang mới (`can_defer_to_next_page`)**: Khi nhóm ô gộp không vừa khoảng trống còn lại của trang hiện tại, thuật toán tự động ngắt trang thay vì cưỡng ép vẽ vượt ra ngoài lề trang.
- **Tiếp nối có kiểm soát (`is_continuation`)**: Trên trang mới, nếu nhóm ô gộp hoặc hàng đơn lẻ vượt quá chiều cao toàn trang in, hệ thống phân đoạn các hàng con vừa khít, đóng nắp đường viền và đánh dấu ô tiếp nối trên trang tiếp theo.
- **Kẹp lề tuyệt đối**: Toàn bộ nét chữ và đường viền bảng được kẹp chặt chẽ trong khoảng in được (`baseline_y <= max_page_y`), loại bỏ 100% rủi ro tràn toạ độ nét vẽ ra đáy trang giấy.

### Đồng bộ tỷ lệ số đo công thức toán học (US2 - P1)
- **Chuẩn hoá số đo `ascent`/`descent`**: Trong bộ định dạng ô bảng (`cell_inlines_formatter`), số đo công thức toán học được đồng bộ chính xác theo tỷ lệ viết tay thực tế ($S \times \text{scale\_mult}$).
- **Mở rộng chiều cao dòng động**: Chiều cao hàng tự động mở rộng theo công thức cao (phân số, căn thức, tích phân) ở mọi tỷ lệ ($S=0.5, 1.0, 1.5$) và khi bật `--auto-xh`, loại bỏ triệt để hiện tượng nét công thức đè lên đường viền ô.

### Bẻ token dài theo ký tự trong pipeline bảng (US3 - P2)
- **Bẻ nhỏ token không dấu cách theo ký tự**: Các chuỗi token quá rộng (URL dài, mã băm hex, định danh không ngắt dòng) được bẻ tự động thành các đoạn ký tự vừa khít độ rộng khả dụng (`usable_w`) ngay trong pipeline kết xuất bảng của `DocumentLayoutEngine`.
- **Bảo toàn ranh giới cột**: Khẳng định 100% toạ độ nét vẽ nằm trong giới hạn chiều rộng của cột bảng, ngăn chặn tràn mực sang các cột lân cận.

### Phục hồi số cột logic DOCX & Thứ tự bảng lồng nhau (US4 - P2)
- **Ma trận chiếm chỗ 2D (Occupancy Grid)**: Chuyển đổi bảng DOCX/IR sang Markdown sử dụng lưới 2D, tính toán đúng tổng số cột logic khi có `colspan`/`rowspan` và chèn ô đệm trống chính xác vào các vị trí bị chiếm chỗ.
- **Bảo toàn thứ tự xuất hiện tài liệu**: Duyệt các phần tử con của ô bảng theo thứ tự thực tế (`c.iter_inner_content()` / `c._tc.iterchildren()`), giữ đúng thứ tự xuất hiện giữa các đoạn văn và bảng con (Đoạn A $\to$ Bảng con $\to$ Đoạn B) kèm cơ chế chặn đệ quy sâu (depth $\le 5$).

### Hỗ trợ bảng không tiêu đề trên Web UI (US5 - P3)
- **Tôn trọng checkbox "Có hàng tiêu đề"**: Modal chèn bảng Markdown trên Web UI hỗ trợ tạo bảng không tiêu đề bằng cách sinh dòng header trống `|   |   |` và dòng phân cách `:---` chuẩn CommonMark.

## Chưa phát hành — Tương thích hình học giấy và tệp .xopp chuẩn Xournal++ (Spec 031)

Hoàn thiện tính tương thích 1:1 với Xournal++ về định dạng tệp .xopp, hình học các loại nền giấy, căn dòng chữ viết tay và danh mục khổ giấy đồng bộ:

### Khắc phục tệp PDF nền XOPP (US1)
- **Chuẩn hoá chỉ số trang 1-based**: Khắc phục lỗi `pageno` từ 0-based sang 1-based (`page_index + 1`) theo đúng chuẩn `SaveHandler.cpp` của Xournal++, loại bỏ hiện tượng trang đầu bị chỉ số `-1` khiến Xournal++ không mở được file PDF nền.
- **Quy chuẩn miền domain và tên tệp trần**: Ghi `domain="absolute"` và tên file trần (`os.path.basename`) tương đối với thư mục chứa file `.xopp`, loại bỏ triệt để chuỗi `domain="relative"` trên toàn bộ mã nguồn và bộ test.

### Dựng bản xem trước SVG thống nhất trên Web (US2)
- **Hàm vẽ SVG dùng chung `getBackgroundDrawingElements`**: Thống nhất 100% logic vẽ nền cho cả `renderPageSvgString` và `renderPageSvgElement`, tránh lặp mã và lệch toạ độ.
- **Tái hiện chính xác hình học Xournal++**:
  - `ruled`/`lined`: Giới hạn dòng ngang trong `[80.0, pageHeight - 60.0]` tại $y = 80 + i \cdot r_1$; vạch kẻ lề dọc $x = m_1$ cho $m_1 > 0$ và lề phải $x = \text{pageWidth} + m_1$ cho $m_1 < 0$.
  - `graph`: Lưới bước $r_1$, lề $m_1$, làm tròn lề `rm=1`, nét đậm `blw` định kỳ `bli`.
  - `dotted`: Chấm tròn tại nút lưới bước $r_1$, đường kính 1.5pt với round cap.
  - `iso_graph` & `iso_dotted`: Bước ngang $\frac{\sqrt{3}}{2} r_1$, bước dọc $\frac{r_1}{2}$, căn giữa trang.
  - `staves`: Khuông nhạc 5 dòng, khoảng cách 5pt, khoảng cách giữa các khuông 40pt, bước dọc 62.5pt.
  - Tự động chuyển tone màu tương phản tối ưu khi nền giấy màu tối (`#1e1e1e`).

### Tự động căn dòng chữ theo dòng kẻ (US3)
- **Baseline Ruling Snapping (`snap_to_ruling = True`)**:
  - Chữ viết tay trên nền `ruled` và `lined` tự động căn đường chân chữ (baseline) khớp vào các dòng kẻ $y = 80.0 + k \cdot r_1$.
  - Bước dòng `pitch = r1 * max(1, round(line_h / r1))` chống chữ đè lên nhau khi đổi cỡ chữ.
  - Tự động ngắt trang khi baseline kế tiếp vượt quá $\text{pageHeight} - 60.0$.
  - Kẹp lề trái chữ sau vạch kẻ lề $x \ge m_1 + 8$ và kẹp lề phải trước vạch lề âm $x \le \text{pageWidth} + m_1 - 8$.
  - Bảo toàn 100% thuật toán bố cục liên tục cho nền `plain` (bảo đảm tính bất biến mã băm Golden Master `tests/test_golden_master_real_path.py`).

### Mẫu nền định sẵn & Cờ dòng lệnh CLI (US4)
- **Danh mục mẫu nền `BACKGROUND_PRESETS`**: Bổ sung đầy đủ 16 mẫu nền chuẩn theo `pagetemplates.ini.in` của Xournal++ (`plain`, `ruled`, `lined`, `lined_narrow`, `lined_college`, `lined_wide`, `lined_right`, `graph`, `graph_5mm`, `graph_grid`, `graph_border`, `graph_border_bold_5`, `dotted`, `iso_graph`, `iso_dotted`, `staves`).
- **Hỗ trợ lề dọc âm ($m_1 < 0$)**: Cập nhật `parse_length(..., allow_negative=True)`, `PageBackground.to_xml()`, và `WriteOptions.validate()`.
- **Cờ CLI mở rộng**: Bổ sung `--bg-preset`, `--bg-r1`, `--bg-m1`, `--bg-color`, `--no-snap-ruling`.

### Đồng bộ danh mục khổ giấy và giao diện (US5)
- **Hàm danh mục chuẩn `get_page_catalog()`**: Nguồn chân lý duy nhất (SSOT) cho khổ giấy, mẫu nền kèm tên song ngữ Anh/Việt và bảng tone màu.
- **Đồng bộ Desktop Tkinter & Web UI**: Dropdown khổ giấy, mẫu nền và tone màu giấy tự động nạp từ danh mục chuẩn.

## Chưa phát hành — Chuyển đổi thuần ký tự & Nạp file lưới .xopp (R1 - R4)

Chuyển đổi toàn diện hệ thống từ mô hình dạy/dùng mẫu theo TỪ sang mô hình thuần KÝ TỰ, bổ sung tính năng nạp file lưới tập viết `.xopp` trên mọi giao diện (Web, Desktop GUI, CLI) và sửa triệt để các lỗi bearing nền:

### Mô hình thuần ký tự & Tự động ghép chữ (R1, P2)
- **Luôn tự động ghép chữ (`assemble_letters = True`)**: `WriteOptions` và `Writer` mặc định luôn bật cờ ghép chữ. Văn bản viết ra luôn được ghép từ các ký tự đơn (`letters`, `digits`, `punct`, `symbols`, `marks`).
- **Ưu tiên ghép chữ cho từ vựng**: Mọi từ alphabet luôn được ghép từ chữ cái và dấu thanh.
- **Bảo toàn dữ liệu người dùng (D1)**: Trường `words` của các kho mẫu cũ được bảo lưu 100%, không bị xoá hoặc ghi đè khi lưu lại kho.
- **Kẹp trần side bearings**: Giới hạn `min(rsb, 0.3 * xh)` khi ghép chữ để các ký tự đứng cạnh nhau tự nhiên, không bị giãn cách bất thường.
- **Bảo vệ toán tử số học**: Giữ nguyên cơ chế MathLayoutEngine cho các ký tự toán tử `+-=<>/*` mà không bị đè bởi nét vector thô.

### Nạp file lưới tập viết .xopp tạo kho ký tự (R2, F2, P1, P3, P4, P5)
- **Nạp lưới `.xopp` trên Web, Desktop GUI và CLI**:
  - Web: Nút "Nạp file lưới…" trong tab Dạy chữ và nút "Nạp lưới (.xopp)" trong tab Kho mẫu.
  - Desktop GUI: Nút "Nạp file lưới…" trong tab Dạy chữ.
  - CLI: Lệnh `hw_note.py learn --grid <file.xopp>`.
- **Sửa triệt để lỗi bearing F2**: Tính `lsb` và `rsb` trực tiếp từ khoảng cách giữa bounding box nét mực người dùng viết với đường chân chữ và biên nét thực tế, thay vì lấy toạ độ mép ô lưới gây giãn cách 10 lần.
- **Idempotent & Báo cáo kết quả (`GridImportResult`)**: Nạp lại nhiều lần an toàn, nhận diện trùng lặp, bỏ qua ô nhiều ký tự và báo cáo rõ ràng: số mẫu thêm mới, trùng lặp, bỏ qua, loại bỏ.

### Danh mục ký tự "Bộ ký tự…" thay cho bộ từ (R3, P1, P4, P5)
- **Thay thế nút "Bộ tối thiểu" và "Từ thông dụng"**: Nút "Bộ ký tự…" mở modal/hộp thoại chọn theo các nhóm ký tự: Cơ bản (85 chữ cái), Chữ hoa, Chữ thường, Chữ số, Dấu câu, Ký hiệu toán, Dấu thanh rời, Toàn bộ.
- **Xuất lưới ký tự theo nhóm**: Hỗ trợ xuất file lưới `.xopp` theo từng nhóm ký tự từ Web, GUI và CLI (`hw_note.py grid --set <nhom>`).

### Thư viện mẫu và bộ lọc Kho mẫu (P4, P5)
- **Bổ sung bộ lọc Dấu thanh (`marks`) và Ký hiệu (`symbols`)**: Hiển thị đầy đủ tất cả các danh mục ký tự trong tab Kho mẫu trên Web và Desktop.

## Chưa phát hành — Static Web Client & PWA (Spec 020)

Chuyển đổi ứng dụng thành Static Web App chạy 100% phía trình duyệt (Client-side) không cần máy chủ tính toán, bảo toàn 100% thuật toán gốc qua Pyodide 314.0.7 (WebAssembly):

### Runtime WebAssembly & Cấu trúc Client-Side
- **Pyodide 314.0.7 trong Web Worker**: Đóng gói mã nguồn `chuviettay` vào `chuviettay.zip` và nạp vào Pyodide Web Worker không chặn giao diện chính (Zero Blocking UI).
- **Zero Remote CDN**: Tự host 100% tài nguyên gồm WASM, stdlib, wheels (`markdown_it_py`, `mdit_py_plugins`) và frontend trong `webapp/dist/`.
- **Golden Master 8/8 byte-to-byte**: Xác thực mã băm SHA-256 các file `.xopp` sinh ra từ Pyodide trùng khớp từng byte với bản CPython gốc.

### Trình soạn thảo & Xuất bản (Tab Viết chữ)
- **Soạn thảo thời gian thực 2 cột**: Hỗ trợ văn bản thuần, Markdown, bảng, công thức toán học LaTeX inline `$x$` và block `$$E=mc^2$$`.
- **Xem trước Vector SVG**: Phân tích cú pháp trang giấy `paper.js` và hiển thị nét mực chân thực kèm tỷ lệ phóng thu 75% - 125%.
- **Đa định dạng xuất bản**: Xuất tệp `.xopp`, xuất ảnh PNG, vector SVG, tải nén ZIP toàn bộ trang và in trực tiếp ra giấy / lưu PDF trình duyệt.

### Dạy chữ trên Canvas (Tab Dạy chữ)
- **Pointer Events & Palm Rejection**: Hỗ trợ bút cảm ứng, màn hình cảm ứng và chuột với cơ chế chống tỳ tay và loại bỏ chạm vô tình.
- **Tương đương 100% thuật toán GUI**: Đạt 8/8 bài kiểm tra parity `tests/test_teach_parity.py` trong việc chuẩn hoá mẫu, tính toán toạ độ và phân loại nét.

### Quản lý kho mẫu & Toàn vẹn đa tab (Tab Kho mẫu)
- **Lưới mẫu & Tìm kiếm tức thì**: Lọc theo danh mục (`words`, `letters`, `digits`, `punct`, `symbols`), hiển thị hình thu nhỏ SVG và số lượng mẫu.
- **Xoá nhãn an toàn**: Xác nhận rõ ràng, hỗ trợ Hoàn tác (Undo) và cơ chế tombstone đồng bộ tránh hồi sinh.
- **Giao thức lưu 4 bước Web Locks**: Kiểm soát truy cập độc quyền kho mẫu giữa các tab, đồng bộ dữ liệu hai chiều tức thì qua BroadcastChannel và lưu vào IndexedDB.
- **Cảnh báo dung lượng & Nhắc nhở sao lưu**: Cảnh báo khi bộ nhớ trình duyệt vượt quá 80% hạn ngạch và nhắc nhở sao lưu định kỳ sau 20 mẫu dạy mới.

### PWA Offline & Triển khai đám mây
- **PWA Service Worker Cache-First**: Cài đặt ứng dụng như Native App trên máy tính và điện thoại; hoạt động hoàn toàn ngoại tuyến khi mất mạng.
- **Render Blueprint & CI**: Tích hợp `render.yaml` tự động build và triển khai lên Render Static Site với Cache-Control immutable 1 năm cho tài nguyên WASM; bổ sung CI kiểm thử Playwright E2E và Python 3.14.

---

## Chưa phát hành — Giai đoạn 1: Nền tảng (P1)

### Định dạng tài liệu & Tương thích Xournal++ (F7)
- **Chuẩn hoá định dạng kiểu nền XML XOPP (F7)**: Đối chiếu với mã nguồn gốc của Xournal++ (`PageTypeHandler::getPageTypeFormatForString`, commit `9882ffaaf2`), các kiểu nền `iso_graph`, `iso_dotted`, `music` được tuần tự hoá chính xác thành `isograph`, `isodotted`, `staves` trong XML thẻ `<background>`. Đồng thời bổ sung bộ chuẩn hoá nhận diện cả hai dạng biểu diễn ở tầng CLI và API.

### Vị trí kho mẫu và cấu hình môi trường (F4)
- **Đường dẫn chuẩn hoá theo hệ điều hành (F4)**: Chuyển vị trí kho mẫu mặc định từ thư mục package sang thư mục dữ liệu người dùng chuẩn (`%APPDATA%`, `~/Library/Application Support`, `$XDG_DATA_HOME`), bảo đảm hoạt động đúng sau khi cài bằng `pip`.

### Lưới tập viết & Tập ký tự ngoại lai (F3)
- **Bổ sung f, j, w, z vào lưới hw3 (F3)**: Mở rộng lưới từ 77 lên 85 ô, hỗ trợ các từ mượn và tên riêng tiếng Latinh; bảo toàn tương thích ngược với tờ lưới 77 ô cũ và ngăn ngừa việc đưa chữ số, dấu câu vào kho chữ cái `bank.letters`.

### Kho chữ tổng hợp & Kiểm thử nghiệm thu định lượng (Q4)
- **Bộ sinh kho mẫu tất định (Q4)**: Cung cấp hàm `build_synthetic_letter_bank()` sinh đầy đủ 66 chữ cái, 5 dấu thanh rời, 10 chữ số, dấu câu và ký hiệu cho kiểm thử tự động với các chỉ số đo lường mực viết khách quan.

### Đồng bộ tài liệu và Schema v4 (Q3)
- **Nguồn sự thật Schema v4 (Q3)**: Đồng bộ mã nguồn, docstring, script và tài liệu hướng dẫn về Schema v4; chuẩn hoá thông tin lưới 85 ô.

## Chưa phát hành — Lưới an toàn & vá lỗi toàn vẹn dữ liệu (P0)

### Toàn vẹn dữ liệu kho mẫu & Nâng cấp Schema v4 (D1, D2, D5)
- **Phân tách không gian tên tombstone (D1)**: Định dạng tombstone được mở rộng thành `<category>:<label>` (ví dụ `letters:a`, `words:a`, `symbols:π`). Khắc phục lỗi `drop_letter("a")` làm mất từ `"a"` trong kho khi đồng bộ merge. Hỗ trợ tương thích ngược: các tombstone cũ không có tiền tố danh mục vẫn được tôn trọng xóa trên mọi danh mục.
- **Nâng cấp Schema v4 (`CURRENT_VERSION = 4`)**: Bổ sung bộ chuyển đổi di trú tự động `_migrate_v3_to_v4` khi nạp kho v3 lên v4, đảm bảo cấu trúc kho và từ điển `tombstones` luôn nhất quán.
- **Gỡ tombstone khi dạy lại ký hiệu (D2)**: `add_symbol_sample` nay xóa bỏ đúng tombstone tương ứng khi thêm mẫu mới, khắc phục lỗi ký hiệu bị mất mẫu sau khi xóa rồi dạy lại và merge kho.
- **Chống đua luồng khi lưu hoãn & tăng tốc serialize (D5)**: Bổ sung `RLock` bảo vệ trạng thái kho mẫu và chuỗi đột biến `_mutation_seq`. Chuyển sang serialize `json.dumps()` nguyên tử trước khi nén gzip, đưa I/O đĩa ra ngoài khóa; tăng tốc độ ghi đĩa gấp 5x và loại bỏ hoàn toàn ngoại lệ `RuntimeError: dictionary changed size during iteration`.

### Sửa lỗi dàn trang và học mẫu (D3, D4)
- **Học mẫu tất định & khử trùng ô (D3)**: Hàm `learn_from_files` giải nén gzip trước khi băm SHA-256 XML để tránh phụ thuộc vào header timestamp của gzip. Thêm cơ chế kiểm tra trùng lặp tọa độ nét để loại bỏ các ô trùng lặp.
- **Tôn trọng cờ missing_grid & bảo vệ nét người dùng (D4)**: Hỗ trợ cờ `--no-missing-grid` trên CLI và hộp kiểm trên GUI; không tự động ghi đè file `_thieu.xopp` nếu phát hiện có nét vẽ của người dùng.

## Chưa phát hành — Sửa & cải tiến cơ chế ghép chữ viết tay (spec 017)

Khắc phục triệt để hiện tượng chữ dính/nhoè ("cục mực"), khôi phục khả năng ghép chữ tiếng Việt có dấu thanh từ kho mẫu ký tự đơn, chuẩn hoá tỉ lệ nét/cỡ chữ tương đồng với chữ viết tay thực tế trong sổ ghi chú, và bổ sung định dạng lưới tập viết 4 dòng kẻ `hw3`.

### Sửa lỗi & Cải tiến chất lượng ghép chữ
- **Khắc phục dính/nhoè nét (cục mực)**: Thay thế công thức tiến con trỏ cũ `advance = max(0.2*xh, w - overlap)` bằng cơ chế tiến con trỏ tự nhiên theo cặp đường bao biên (contour pair gap) và lsb/rsb. Bổ sung sàn khe hở tối thiểu `pen_clearance_factor * pen_thickness` (mặc định 0,8x nét bút), triệt tiêu hoàn toàn hiện tượng mép chữ sau đè lên nét chữ trước (chồng bbox giảm từ 51,7% - 74,5% về 0,0%).
- **Ghép chữ có dấu thanh (Dual-Path Assembly)**: Giải quyết dứt điểm lỗi kho mẫu chữ cái đơn không ghép được từ có dấu khiến các từ như "Lời", "Bài", "Chạy", "Phần", "giải", "Điều kiện"... bị bỏ trống. Ưu tiên 1 sử dụng trực tiếp mẫu nguyên âm có sẵn dấu trong `bank.letters`/`bank.words`; Ưu tiên 2 ghép nguyên âm cơ sở với dấu thanh trong `bank.marks`.
- **Tự động tránh va chạm dấu & triệt tiêu chấm `i`/`j`**: Tự động tính trọng tâm nguyên âm để đặt dấu thanh cân đối; phát hiện và né tránh va chạm với nét vươn cao (ascender); tự động ẩn chấm chữ `i`/`j` khi có dấu thanh phía trên bằng ngưỡng tỉ lệ bounding box.
- **Hỗ trợ định danh kỹ thuật & ký tự hỗn hợp**: Token kỹ thuật chứa dấu gạch dưới (`bill_length_mm`), ngoặc đơn, toán tử (`>=`, `<=`, `<`, `>`, `=`) và đường phân cách (`---`) tự động bóc tách và tra cứu qua `letters` -> `words` -> `digits` -> `punct` -> `symbols` -> nét vector dự phòng.
- **Chuẩn hoá x-height & tỉ lệ nét mực**: Bổ sung tuỳ chọn `--auto-xh` (tự động chuẩn hoá cỡ chữ trong kho về x-height mục tiêu 7,94 pt của sổ tay) và `--target-xh <pt>`, đưa tỉ lệ nét bút / x-height từ 36,6% về 18,0% (chuẩn ghi chú 17,8%).

### Mới
- **Tờ lưới tập viết 4 dòng kẻ (`hw3`)**:
  - Lệnh CLI `python3 hw_note.py grid -o luoi.xopp` xuất tờ lưới mẫu 4 dòng kẻ (chân chữ, x-height, ascender, descender) kèm 2 vạch lề biên độ rộng và hướng dẫn viết tay bằng tiếng Việt rõ ràng.
  - Bổ sung 14 cụm phụ âm/nguyên âm đôi tiếng Việt thông dụng (`ng, nh, ch, tr, ph, th, kh, gi, qu, ươ, ưa, uy, ay, oa`) giúp thu thập nét nối liền tự nhiên.
  - Bộ nạp `learn` tự động nhận diện thẻ `hw3`, lọc màu nét kẻ mẫu và trích xuất khoảng đệm biên `lsb`/`rsb` vào `bank.letters`.
- **Công cụ di trú kho mẫu (`scripts/migrate_letter_bank.py`)**:
  - Tự động di trú kho mẫu từ `words` sang `letters` (chuẩn schema v4), chuẩn hoá toạ độ baseline, phân tách dấu thanh rời thông minh, trích xuất `lsb`/`rsb` và tính đường bao biên dạng hình học.
- **Bộ công cụ đo lường & kiểm thử**:
  - `tools/measure_ink.py`: Đo đạc định lượng khách quan (x-height thực tế, tỉ lệ nét/xh, khoảng cách trong từ, khoảng cách giữa các từ, độ chồng bbox, khe hở nét nhỏ nhất, độ lệch chuẩn xh).
  - `tools/render_xopp.py`: Kết xuất trực tiếp các trang của tệp `.xopp` ra ảnh PNG không phụ thuộc Xournal++.

## Chưa phát hành — Sửa lỗi và mở rộng xử lý công thức toán (LaTeX / OMML / MathType)

Kiểm chứng trên bài giải thật (`loi-giai-phan-A.md`, `loi-giai-phan-B.md`, 2 file `.docx`) bằng cách chạy đủ
đường nạp → dàn trang → `.xopp`. Danh sách "ký hiệu thiếu mẫu" trước đây chứa các mục sai như `\dfrac`,
`\\`, `\quad`, `\bar`, `\ngtr`, `body\_mass\_g`; nay chỉ còn ký hiệu thật sự thiếu mẫu.

### Lỗi đã sửa
- **MathType bị bỏ im lặng**: đối tượng OLE (`w:object`, ProgID `Equation.*`/`DSMT*`) trước đây biến mất không cảnh báo
  (đoạn chỉ chứa công thức bị mất hẳn). Nay luôn thay bằng ô vuông `□` kèm cảnh báo có số lượng và hướng xử lý. Trường
  `EQ` cũ của Word cũng được báo. *Chưa* đọc được nội dung MathType (xem README).
- **OMML**: chuỗi `2x+3=0` trong một `m:r` từng thành MỘT ký hiệu (ô trống); dấu trừ U+2212 của Word không có trong
  kho; `m:d` chỉ lấy phần tử đầu (`[a;b]` thành `[a]`); `m:nary` mất ∑/∫; `m:limLow` mất `x→0`; `m:acc` (vectơ) rơi mất;
  `m:eqArr` (hệ phương trình) và `m:m` (ma trận) bị dàn thành một hàng; `m:oMathPara` nhiều dòng bị gộp.
- **Parser LaTeX**: `]` ở ngoài cùng bị bỏ (`[0,1]` thành `[0,1`); `xy^2` hiểu là (xy)²; `x^23` mũ 23; `\frac12` hỏng;
  thiếu `\sin \lim \log…`, `\{ \}`, `\%`, `\\`, `\mathbb`, `\dfrac`, `\binom`, vectơ/góc, môi trường `cases/aligned/matrix`;
  `\left\{` hỏng; `\text{body\_mass\_g}` rò rỉ ký tự LaTeX; `^\circ` dùng ∘ thay vì °; `}` thừa bị nuốt không báo.
- **Markdown**: `\(…\)`, `\[…\]` và `\begin{align}` trần bị coi là chữ thường; `$$…$$` trong mục danh sách bị bỏ;
  `a<b và c>d` ngoài `$` bị bộ lọc HTML xoá thành `ad`; `5$ rồi 10$` bị nhận nhầm là công thức.
- **Dàn trang**: danh sách lồng nhau bị **bỏ hoàn toàn** (mất nội dung); công thức trong mục danh sách bị bỏ; công thức
  display/inline dài tràn khỏi trang; công thức cao không được tính vào chiều cao dòng; công thức trong ô bảng tràn ô.
- **Fidelity**: bản làm trắng chỉ đổi màu `w:r`, không đụng tới công thức OMML (`m:r`, `m:ctrlPr`) nên công thức in vẫn
  đen dưới chữ viết tay (đã tái hiện: dựng PDF bằng LibreOffice, công thức giữ nguyên 267 điểm ảnh đen sau khi "làm trắng").
  Nay đặt màu trắng đúng lược đồ OOXML (`m:r/w:rPr/w:color`, `m:*Pr/m:ctrlPr/w:rPr`), giữ đúng thứ tự phần tử. Mới kiểm
  chứng ở mức XML; xem "Giới hạn đã biết" về LibreOffice.

### Mới
- AST: `Delimited`, `NAry`, `OverUnder`, `Accent`, `Matrix`, `Boxed`, `SpaceNode`; `TextNode.kind`, `Fraction.bar`.
- Dàn trang: khoảng cách giữa ký hiệu theo bảng của TeX (quan hệ/toán tử/dấu phẩy…), ngoặc co giãn, ∑ ∏ ∫ cỡ lớn, cận
  trên/dưới ở công thức display, ma trận/`cases`/`aligned` thẳng cột, vectơ/góc/gạch ngang, ngắt dòng công thức dài.
- Ký hiệu chưa có mẫu viết tay được vẽ tạm bằng nét vector (vẫn được báo là thiếu để dạy thêm); chữ cái biến và tên hàm
  tự ghép từ `letters` khi kho chưa có mẫu nguyên từ.
- Mô-đun `importer/omml.py` (README đã nhắc từ trước nhưng chưa tồn tại), `math/latex_writer.py` (AST → LaTeX).

### Kiểm thử
- Thêm hơn 550 test: hồi quy parser, vòng AST → LaTeX → AST trên 184 công thức (141 lấy từ bài giải thật), hình học dàn
  trang, bộ chuyển OMML, nạp `.docx`/MathType/Markdown, tích hợp dàn trang, làm trắng Fidelity.
- Test đối chiếu: cùng một công thức đi qua LaTeX và qua OMML thật do pandoc sinh phải ra cùng AST (tự bỏ qua nếu thiếu pandoc).
- `tests/test_docx_omml_diagnostics.py`: cập nhật vì `m:nary`/`m:m` không còn là "chưa hỗ trợ".

### Giới hạn đã biết
- Chưa đọc nội dung MathType; chưa đọc nội dung trường `EQ` cũ (chỉ báo cáo).
- Làm trắng công thức trong Fidelity chỉ có tác dụng với Word: LibreOffice bỏ qua màu chữ trong công thức OMML (đã thử
  bằng màu đỏ: màu không đổi), nên nếu chuyển đổi Fidelity qua LibreOffice thì công thức in vẫn đen dưới chữ viết tay.
  Phía Word chưa kiểm chứng được vì cần Windows + Word COM.
- Code block và `---` trong Markdown vẫn chỉ được báo "chưa hỗ trợ" (đúng hợp đồng IR của spec 014).
- Hai test Fidelity cần Word COM trên Windows (`test_cli_write_mode_fidelity_and_semantic`,
  `test_controller_write_docx_fidelity_api`) thất bại trên Linux, cả ở bản gốc.

## 2.0.0 — Tái cấu trúc sang MVC

**Mục tiêu:** dễ debug, dễ nâng cấp, tách lớp MVC, dễ bảo trì — **không đổi cách dùng và không đổi
kết quả**. `hw_note.py` và `hw_gui.py` vẫn chạy y như trước; kho mẫu `chu_cua_ban.json.gz` dùng nguyên
(không cần chuyển đổi).

### Cách kiểm chứng "không đổi kết quả"
Chạy song song **bản gốc** và **bản mới** trên kho mẫu thật (362 từ):
- Dòng lệnh: 8 kiểu chạy `write` (nhiều bộ tuỳ chọn, nhiều trang, strict-case, đọc từ stdin và `-t`),
  `stats`, `seed`, `check`, `learn` (có và không có ô đo cỡ tay), `drop`, và trường hợp thiếu kho mẫu →
  **stdout, mọi file `.xopp` (so từng byte) và kho mẫu sau khi học/xoá đều giống hệt**.
- Giao diện: tab **Viết chữ** trên kho mẫu thật, cùng đầu vào → file `.xopp`, nội dung ô "Kết quả" và danh
  sách "từ còn thiếu" giống hệt giao diện bản gốc (và giống hệt đầu ra dòng lệnh bản gốc).

Kết quả đó được giữ thành test vĩnh viễn: `tests/test_golden_master.py` (mã băm SHA-256 sinh từ **bản gốc**,
không phải tự so với chính mình).

### Cấu trúc
- Hai file ~1340 dòng → package `chuviettay/` gồm `model/`, `controller/`, `view/` + `cli.py`, `gui.py`.
- `hw_note.py`, `hw_gui.py` còn là lối vào mỏng, giữ nguyên tên và cách gọi.
- Luật phụ thuộc một chiều (`view`/`cli` → `controller` → `model`) được kiểm tra tự động.

### Bỏ trùng lặp giữa dòng lệnh và giao diện
- Công thức hiệu chỉnh cỡ tay có ở 2 nơi (`cmd_learn`, `TeachTab.save_word`) → một hàm `calibration.compute_scale`.
- Logic "thêm một mẫu vào kho" và "xoá từ" lặp ở CLI và GUI → `Bank.add_sample()` / `Bank.drop()`.
- Thống kê kho, xuất file kiểm tra, danh sách từ thông dụng còn thiếu: mỗi thứ viết 2 lần → một phương thức
  `AppController` dùng chung.
- GUI không còn giả lập `argparse.Namespace` + `redirect_stdout` để gọi `cmd_write`; nhận `WriteResult`
  (dữ liệu thuần), câu chữ báo cáo dựng ở một chỗ (`formatting.py`).
- `Bank` không còn tự `sys.exit()` khi thiếu file (ném `BankNotFoundError`; CLI/GUI tự quyết cách báo).

### Dễ debug
- **Log ra file** `chuviettay.log` (xoay vòng) với traceback đầy đủ — bản `.exe` không có console vẫn có
  chỗ để xem lỗi. Cờ `-v/--verbose` cho cả CLI và GUI.
- Mọi hộp thoại lỗi ghi traceback vào log trước khi hiện (bản gốc chỉ còn `str(e)` một dòng).
  `MainWindow.report_callback_exception` bắt cả lỗi bất ngờ trong sự kiện giao diện.
- CLI: lỗi bất ngờ → thông báo gọn + trỏ tới file log (thay vì traceback dài); `-v` để xem đầy đủ.

### Lỗi đã sửa (phát hiện khi gộp phần trùng lặp và khi đọc lại bản gốc)
1. **"Từ còn thiếu mẫu" trong tab Viết chữ bỏ qua tuỳ chọn strict-case.** GUI tính lại danh sách bằng hàm
   `missing_words()` riêng, luôn tạo `Writer` với strict-case = tắt, nên khi bạn bật strict-case, các từ
   viết hoa đầu từ thực sự đang bị để trống trên trang lại không có trong danh sách để dạy. Giờ danh sách
   lấy từ chính lần viết đó.
2. **Cờ "đang hiệu chỉnh cỡ tay" không được tắt khi bỏ qua từ mốc / xoá hàng đợi.** Chỉ `save_word` mới tắt
   cờ, nên lần lưu kế tiếp bị coi nhầm là hiệu chỉnh nếu từ đó đã có mẫu sẵn trong kho. Giờ tắt đúng lúc.
3. **Không mở được kho mẫu lúc khởi động** (file hỏng, đường dẫn sai...): bản gốc chỉ bắt `SystemExit`, mọi
   lỗi khác làm chương trình văng ngay lúc khởi động (traceback chỉ hiện ở console; bản `.exe` không console
   thì không có chỗ nào để xem). Nhánh "chưa có kho" của bản gốc, nếu có chạy tới, cũng không bao giờ dựng
   lại các tab sau khi bạn chọn được kho hợp lệ. Giờ cửa sổ luôn mở, báo rõ lý do (kèm đường dẫn file log),
   và dựng đủ các tab ngay khi có kho hợp lệ.
4. **README bản gốc hứa** "trỏ tới file chưa tồn tại thì app tự tạo kho trống", nhưng hộp thoại *Mở file* của
   Tk không cho chọn file chưa có ("File ... does not exist"). Thêm nút **"Tạo kho mẫu mới..."** (không bao giờ
   ghi đè file có sẵn — chọn file đã có thì chỉ mở nó ra).
5. **Mất trắng kho mẫu nếu bị ngắt giữa lúc lưu.** `Bank.save()` bản gốc ghi thẳng đè lên file thật; mất điện /
   đầy đĩa / tắt máy đúng lúc đó là hỏng cả kho (hàng giờ viết tay). Giờ ghi ra file tạm rồi đổi tên đè
   (thao tác nguyên tử): bị ngắt giữa chừng thì kho cũ vẫn còn nguyên.
6. Lời nhắc trong file `check` do GUI xuất thiếu câu gợi ý lệnh `drop` so với bản CLI → thống nhất.
7. Nhập sai ô số trong tab Viết chữ: thay vì thông báo thô của Python ("could not convert string to float"),
   giờ nói rõ ô nào sai và bạn đã nhập gì.

### Khác biệt nhỏ cần biết
- Hiệu chỉnh cỡ tay trong app dùng chung một hàm với `learn`, nên ngưỡng "đo quá nhỏ thì không tin" giờ tính
  trên độ rộng **thô** (trước khi nhân hệ số cũ) thay vì độ rộng đã nhân. Chỉ khác khi hiệu chỉnh **nhiều
  lần trong một phiên** với hệ số đã lệch xa 1.0; lần đầu trong phiên (trường hợp thường gặp) hoàn toàn như cũ.
- Đổi sang kho mẫu khác giữa chừng thì hệ số cỡ tay của phiên được đặt lại 1.0 và đường kẻ mốc vẽ lại theo
  kho mới (trước đây giữ nguyên hệ số của kho cũ, vốn không còn ý nghĩa).
- Xoá từ trong tab Kho mẫu không còn "đọc ngược" nhãn từ chuỗi hiển thị `"từ  (3 mẫu)"` (độ bền, chưa từng
  gây lỗi thực tế).
- File `hw_gui-linux` kèm sẵn được build lại từ mã nguồn mới (bản cũ build từ mã cũ).

### Nếu bạn có script riêng đang `import hw_note`
`hw_note.py` giờ chỉ là lối vào dòng lệnh (`python hw_note.py ...` vẫn chạy y như cũ), nên `import hw_note` để
lấy hàm/lớp bên trong sẽ không còn dùng được. Đổi sang:

| Bản gốc (`hw_note.`) | Bản mới |
|---|---|
| `Bank` | `chuviettay.model.bank.Bank` |
| `Writer` | `chuviettay.model.writer.Writer` |
| `cmd_write(ns)` | `AppController.write_text(text, WriteOptions(...), out)` hoặc `chuviettay.model.composer.write_document` |
| `make_grid`, `pick_calib_word`, `read_xopp`, `save_xopp`, `cell_xy` | `chuviettay.model.xopp` |
| `tone_info`, `strip_tone`, `find_tone`, `normalize_text`, `weight`, `clamp`, `fmt`, ... | `chuviettay.model.text_utils` |
| `SEED` | `chuviettay.model.seed_words.SEED` |
| `BANK_PATH` | `chuviettay.paths.default_bank_path()` |

### An toàn đa tiến trình & Đồng bộ đồng thời (Đã giải quyết)
- Hệ thống hỗ trợ hoàn toàn an toàn đa tiến trình (cross-process concurrency) giữa GUI và CLI thông qua `FileLock` (khóa file cấp hệ điều hành), kiểm tra cache `mtime_ns`/`size` và thuật toán hợp nhất `merge_bank_dicts()` nguyên tử.
- Xung đột xóa và dạy từ được giải quyết thông qua cơ chế Deletion Tombstones có ghi nhận nhãn thời gian (`deleted_at`, `readded_at`), ngăn ngừa tuyệt đối tình trạng snapshot cũ hồi sinh từ đã xoá trong khi vẫn hỗ trợ người dùng chủ động dạy lại từ sau khi xoá.
- Bộ đếm thế hệ tăng đơn điệu (`_generation`) phục vụ kiểm toán (audit log) và truy vết chuỗi đột biến nội bộ phiên làm việc.
- Thao tác `Bank.drop(word)` được tinh chỉnh: nếu từ không tồn tại trong kho, phương thức an toàn trả về 0 ngay lập tức mà không tăng `_generation` và không sinh tombstone rác trong siêu dữ liệu.
- `Bank.save()` tự động huỷ bỏ và bảo vệ file gốc nguyên vẹn nếu phát hiện file trên đĩa bị hỏng trong quá trình hợp nhất, chống mất dữ liệu ngoài ý muốn.
- Thắt chặt kiểm tra lược đồ `pen.color` bằng `re.fullmatch()`, từ chối các chuỗi mã màu chứa ký tự rác ở đuôi.

### Độ tin cậy kiểm thử, Thẩm tra Tk/Tcl & Vệ sinh Git History
- **Thu hẹp phạm vi ngoại lệ kiểm thử GUI**: Chỉ bắt `tkinter.TclError` khi khởi tạo `MainWindow` trong `tests/test_gui.py` và fixture `app` (loại bỏ `except Exception`), bảo đảm các lỗi logic nghiệp vụ của Controller và Model gây lỗi kiểm thử lập tức thay vì bị che giấu thành trạng thái bỏ qua (`SKIPPED`).
- **Khớp hợp đồng thẩm tra Tk/Tcl runtime**: Bổ sung kiểm tra tường minh tệp thư viện cốt lõi `$tcl_library/init.tcl` song song với `$tk_library/{tk.tcl, listbox.tcl, button.tcl, entry.tcl}` trong `tests/conftest.py`.
- **Minh bạch hóa bộ nhớ đệm máy chủ Git**: Làm rõ cơ chế lưu trữ commit object của GitHub trong tài liệu và script bảo trì (`scripts/purge_git_history.*`), phân biệt rõ ràng giữa việc làm sạch 100% lịch sử nhánh/thẻ với việc máy chủ từ xa lưu tạm các commit mồ côi theo mã SHA cho tới kỳ GC.
- **Nâng cấp CI & Đồng bộ tài liệu**: Nâng cấp và rà soát các action GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`), chuẩn hóa số liệu kiểm thử (>240 ca) và đồng bộ mã kịch bản nghiệm thu.

### Phòng chống Treo/Deadlock CI, Kiểm thử Chẩn đoán Timeout & An toàn Bộ nạp Tài liệu (Feature 008)
- **Cấu hình Timeout & Tự động hủy job cũ trên CI**: Bổ sung `timeout-minutes: 10` cho test job, `timeout-minutes: 5` cho lint job; kích hoạt `concurrency.cancel-in-progress: true` vô điều kiện để giải phóng runner ngay khi có commit mới.
- **Tích hợp Watchdog Timeout (`pytest-timeout`)**: Kiểm soát từng ca kiểm thử với ngưỡng 30s (`--timeout=30`), tự động ngắt và in traceback call-stack chi tiết nếu test bị kẹt; gắn `@pytest.mark.timeout(120)` cho benchmark lớn.
- **Bảo vệ an toàn pha thu thập kiểm thử (Collection Phase Safety)**: Sử dụng `pytest.importorskip` cho tất cả các kiểm thử tài liệu mở rộng (`python-docx`, `markdown-it-py`), triệt tiêu hoàn toàn lỗi crash `ModuleNotFoundError` khi chạy trong môi trường tối giản.
- **Mock tự động hộp thoại Tkinter trong kiểm thử không đầu**: Thêm fixture autouse `_safe_gui_dialogs` trong `tests/conftest.py` và hoàn thiện mocking trong `tests/test_gui_document.py`, ngăn chặn vĩnh viễn tình trạng mở popup modal chờ người dùng bấm trên môi trường Linux `xvfb`.
- **Hiển thị tiến trình trực tiếp (Streaming Logs)**: Đổi cờ pytest trên CI từ `-q` sang `-vv -s` để theo dõi tiến trình chạy và log từng ca kiểm thử theo thời gian thực.

### Khắc phục Lỗi Nhân đôi Nét Căn thức, Lưới Chiếm dụng Ô Bảng Gộp & Hợp nhất Pipeline (Feature 009)
- **Khắc phục triệt để lỗi nhân đôi nét/glyph căn thức (P0)**: Trong `chuviettay/layout/math_layout.py`, hàm bố trí `Root` đã được tái cấu trúc: khởi tạo danh sách glyph và stroke trống (`glyphs = []`, `strokes = []`), tính toán độ dời `sign_w` của dấu căn bậc n / căn bậc 2 và chỉ thêm các nét/glyph của radicand một lần duy nhất với tọa độ dịch chuyển chính xác. Hỗ trợ hiển thị số mũ căn bậc `degree` (ví dụ $\sqrt[3]{x}$) đặt phía trên móc căn.
- **Bố trí ô gộp nhiều hàng bằng Lưới chiếm dụng 2 chiều (Table Rowspan Occupancy Grid - P0)**: Bổ sung thuật toán `_resolve_occupancy()` trong `chuviettay/layout/table_layout.py` sử dụng ma trận chiếm dụng 2 chiều `grid[row][col]`. Khi một ô có `rowspan > 1` hoặc `colspan > 1`, toàn bộ các ô con trong vùng chữ nhật $[r, r + rs) \times [c, c + cs)$ được đánh dấu đã chiếm dụng. Các ô tiếp theo trên cùng hàng hoặc các hàng bên dưới tự động tìm ô trống đầu tiên mà không bị va chạm tọa độ hoặc đè lên nhau.
- **Tính toán bề rộng cột và đệm hàng rỗng chính xác**: Cập nhật `compute_column_widths()` và `pad_jagged_rows()` dựa trên kết quả giải quyết lưới chiếm dụng, ngăn ngừa việc chèn ô rỗng giả vào các vị trí đã được ô `rowspan` chiếm dụng từ hàng trước.
- **Thống nhất luồng bố trí bảng một nguồn sự thật duy nhất (Single Source of Truth - P1)**: Loại bỏ toàn bộ logic tính toán lại tọa độ, ngắt dòng văn bản và kẻ đường viền bảng phân tán trong `DocumentLayoutEngine.render()`. Giờ đây `DocumentLayoutEngine` ủy quyền toàn bộ cho `TableLayoutEngine.layout_table()` và nhận về `TableLayoutData` hoàn chỉnh.
- **Cắt trang bảng gắn kết nhóm hàng (Table Pagination Group Cohesion - P1)**: Bổ sung phương thức `TableLayoutData.slice_page()` với cơ chế gắn kết nhóm hàng đang chịu ảnh hưởng của ô gộp nhiều hàng (`rowspan`), bảo đảm các hàng liên kết không bị xé vụn qua ranh giới ngắt trang trừ phi kích thước khối ô vượt quá sức chứa một trang.
- **Triệt tiêu đường kẻ nội bộ trong vùng ô gộp**: Phương thức `generate_border_strokes()` trong `TableLayoutEngine` kiểm tra tọa độ hình học thực tế của các ô gộp, loại bỏ hoàn toàn các nét kẻ ngang/dọc bên trong vùng merged cell.
- **Kiểm thử hồi quy nghiêm ngặt (Strict Regression Testing)**:
  - Bổ sung kiểm thử khẳng định các ký hiệu và chữ số toán học ($x^2+1, \sqrt{x}, \sqrt{x^2+1}, \frac{x+1}{2}, x_i^2$) sinh ra nét viết tay vector thật (`total_glyph_strokes > 0`).
  - Bổ sung kiểm thử ma trận chiếm dụng ô gộp `colspan=2`, `rowspan=2` và ô gộp phức hợp $2 \times 2$.
  - Bảo vệ an toàn pha import Tkinter trong `tests/test_gui_document.py` khi chạy trên môi trường headless không có display/Tkinter.
  - Kiểm thử đầu cuối (E2E) chuyển đổi bộ tệp mẫu thực tế `sample.txt`, `sample.md`, `sample.docx` ra `.xopp`.

### Bảo Toàn Số Bắt Đầu Danh Sách Có Thứ Tự Trong Markdown Importer (Feature 010)
- **Bảo toàn số thứ tự (`start`) khi danh sách bị ngắt quãng**: Bổ sung phương thức `_extract_list_start()` trong `MarkdownImporter` (`chuviettay/importer/markdown_importer.py`), trích xuất an toàn thuộc tính `start` từ token `ordered_list_open` và truyền vào `ListBlock(ordered=True, items=items, start=start)`.
- **Khắc phục lỗi reset số thứ tự sau bảng biểu**: Khi một danh sách có thứ tự bị ngắt quãng bởi khối không thụt lề (bảng biểu GFM, đoạn văn) hoặc khi người dùng bắt đầu từ một số khác 1 (ví dụ `4. ... 5. ...`), hệ thống giữ nguyên đúng số đánh dấu gốc thay vì reset về `1. ... 2. ...`.
- **Phân giải thuộc tính bền bỉ (Resilient Parsing)**: Hỗ trợ linh hoạt cả `tok.attrGet("start")`, dict `tok.attrs`, list `tok.attrs`, và tự động fallback về `1` an toàn nếu thuộc tính bị khuyết hoặc mang giá trị phi số.
- **Kiểm thử tích hợp & đầu cuối**: Bổ sung unit tests cho danh sách ngắt quãng bởi bảng trong `tests/test_importer_markdown.py`, kiểm thử pipeline render trong `tests/test_document_pipeline.py` và kiểm thử CLI chuyển đổi ra `.xopp` trong `tests/test_cli_format.py`.

### Mới
- Bộ kiểm thử hơn 370 ca (`pytest`), gồm test giao diện thật chạy dưới màn hình ảo, golden-master so với bản
  gốc, test bộ nạp tài liệu và test kiến trúc. Xem README → "Kiểm thử".
- Tham số `--bank` cho `hw_gui.py`; cờ `-v` cho cả hai.


