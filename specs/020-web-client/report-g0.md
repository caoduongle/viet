# Báo cáo Khảo sát GĐ0: Nền tảng Kỹ thuật & Khả thi Pyodide Web Client

**Mã tính năng**: `020-web-client`  
**Ngày thực hiện**: 2026-10-06  
**Trạng thái**: Hoàn tất khảo sát — **CHỜ NGƯỜI DÙNG DUYỆT ĐỂ BƯỚC VÀO G1**  

---

## 1. Kết quả kiểm chứng thực nghiệm & Đo đạc Pyodide

### 1.1. Phiên bản & Môi trường
- **Pyodide**: Phiên bản ổn định mới nhất hiện tại trên npm là **`314.0.7`** (chạy Python 3.14.2 trên nền Clang/WebAssembly).
- **Node.js**: `v24.16.0`, npm `11.13.0`.
- **CPython**: `Python 3.10.11` trên môi trường máy trạm đang chạy. Lưu ý: 1.074 tests xanh trên máy này là do thư mục làm việc có sẵn file kho cá nhân `chu_cua_ban.json.gz` (bị gitignore). Trên một bản clone sạch từ git, test `test_duong_dan_mac_dinh_khi_chay_tu_ma_nguon` sẽ đỏ do thiếu file này (được xử lý dứt điểm theo D6).

### 1.2. Kiểm thử Golden Master trong Pyodide (Tiêu chí quyết định)
Toàn bộ **8/8 ca kiểm thử mẫu vàng (Golden Master)** trong `tests/test_golden_master_real_path.py` đã được chạy trực tiếp bên trong môi trường Pyodide (Node.js + MEMFS) với các thư viện pure-Python vendor (`markdown_it`, `mdit_py_plugins`, `mdurl`).

| Ca kiểm thử | Trạng thái .xopp | Mã băm SHA-256 thực tế | Khớp CPython | File _thieu.xopp | Khớp SHA-256 _thieu |
|---|---|---|---|---|---|
| `co_ban` | ✅ MATCH | `83e0967e609a5aaad50e3345ab0e19d8ae61c047c66802dfb70dd6fb153b5efe` | 100% | Có | ✅ MATCH (`000440af...`) |
| `tuy_chon` | ✅ MATCH | `190b4e1c1bf0cda0aa31d11b449d29240561a9e59b443864dbeb0f4e12b130e0` | 100% | Không | N/A |
| `nhieu_trang` | ✅ MATCH | `90a2aaf90eabae2564473afdfe10dff519866c1a3cfe4702235510c108eff40f` | 100% | Không | N/A |
| `strict_case` | ✅ MATCH | `8ae4fe97061895859183839e788139d9823a9d7d2262bb3991cd9b184fbecea8` | 100% | Có | ✅ MATCH (`ef93eae8...`) |
| **`assemble_letters`** *(mới)* | ✅ MATCH | `1d71a384018f13878f4da6abea651407b2af413b17d171c9b72ef6895a2fd589` | 100% | Không | N/A |
| `math` | ✅ MATCH | `e20f2e35fd52edf5500bfa9103b9bceab4743431d0850df10350f175b6ccd482` | 100% | Không | N/A |
| `table` | ✅ MATCH | `9239b2e3e2c825a99b4d34537170690b263ad27f93711a55a9276879054c2c82` | 100% | Không | N/A |
| `markdown_list` | ✅ MATCH | `87a0e193035427d12e2b342b23cfd8c60117a09876a991581d6474640943a4c0` | 100% | Có | ✅ MATCH (`3636548d...`) |

> **KẾT LUẬN TIÊU CHÍ CỨNG**: 8/8 ca trùng khớp 100% từng byte mã băm SHA-256 so với CPython gốc.

### 1.3. Kiểm chứng `python-docx` + `lxml`
- Đã tải và nạp thành công wheel WASM chính thức: `lxml-6.1.3-cp314-cp314-pyemscripten_2026_0_wasm32.whl` (kích thước 2,14 MB).
- Module nhị phân `lxml.etree.cpython-314-wasm32-emscripten.so` khởi tạo mượt mà trong Pyodide.
- Đã chạy thử nghiệm `from chuviettay.importer.docx_importer import DocxImporter`: đọc và bóc tách tài liệu `.docx` thành công ra cây Document IR với các khối `Heading`, `Paragraph`.
- *Lưu ý quan trọng*: Để `lxml` compiled trong Pyodide không bị xung đột, gói `lxml` WASM phải nằm trong `/lib/python3.14/site-packages` của Pyodide trước đường dẫn vendor thuần Python.

### 1.4. Kích thước file phân phối thực tế (Dist sizes)
- `pyodide.asm.wasm`: 9,598,218 bytes (~9.6 MB, khi bật nén Gzip/Brotli còn ~3.4 MB).
- `python_stdlib.zip`: 2,545,637 bytes (~2.55 MB).
- `pyodide.asm.mjs`: 1,250,344 bytes (~1.25 MB).
- `lxml` wasm wheel: 2,145,850 bytes (~2.15 MB).
- Mã nguồn gói `chuviettay` (sau khi loại bỏ `view/`, `gui.py`, `cli.py`, `fidelity/`, test/docs): ~151 KB (zip).
- Gói phụ thuộc vendor (`markdown-it-py`, `mdit-py-plugins`, `mdurl`, `python-docx`): sẽ được tải chính xác theo phiên bản ghim trong `scripts/vendor_lock.json` và đo đạc kích thước thực tế khi đóng gói dist tại T027.

### 1.5. Thời gian đo đạc trên Trình duyệt thật (Chrome qua DevTools)
- **Khởi động Pyodide lần đầu**: ~4.241 ms (bao gồm fetch WASM qua HTTP nội bộ, compile WASM và nạp stdlib).
- **Phân tích kho mẫu tổng hợp (`kho_mau_tong_hop.json.gz`)**: 42.2 ms.
- *Lưu ý*: Lần nạp thứ hai đo được tại GĐ0 (~4.370 ms) do chưa có Service Worker / IndexedDB cache nhị phân WASM nên chưa phản ánh thời gian khởi động tối ưu của PWA. Con số này sẽ được đo chính xác sau khi hoàn thiện Service Worker tại G5.

---

## 2. Kết quả khảo sát hành vi mã nguồn hiện tại

### 2.1. Xử lý từ thiếu mẫu (Engine)
- Khi `writer.py` phân tích một từ không có trong kho (và không lắp ghép được từ chữ cái đơn lẻ):
  - Sinh nét `st = []` (không có nét vẽ nào).
  - Chiều rộng `w = weight(core) * b.d.get("ratio", 6.6)` -> **chừa lại một khoảng trống trắng (blank space)** có độ rộng tương xứng trên dòng giấy.
  - Từ thiếu được ghi vào từ điển `wr.missing[word]` và trả về qua `WriteResult.missing_sorted()` (sắp xếp theo số lần xuất hiện giảm dần, sau đó theo bảng chữ cái).
  - Nếu ghi file ra đĩa và có từ thiếu mẫu, ứng dụng sinh thêm file `_thieu.xopp` chứa lưới các ô luyện viết cho đúng các từ thiếu đó.

### 2.2. Cú pháp ngắt trang
- Trong hệ thống phân cấp Document IR, lớp `PageBreak(Block)` đã tồn tại ở `chuviettay/document/ir.py`, và `DocumentLayoutEngine` đã xử lý `if isinstance(block, PageBreak): self.stream.new_page()`.
- **Tuy nhiên**, trong các Importer hiện tại (`MarkdownImporter`, `TxtImporter`), chưa có cú pháp nào được dịch thành `PageBreak`. Trong `MarkdownImporter`, đường kẻ ngang `---` (`hr`) hiện bị đưa vào danh sách cảnh báo `unsupported: hr: horizontal rule`.
- **Đề xuất**: Trên thanh công cụ Markdown của Web Client, quy định nút "Ngắt trang" sẽ chèn một đoạn chuẩn (ví dụ `<!-- pagebreak -->` hoặc `\pagebreak` hoặc cấu hình MarkdownImporter nhận diện nếu được chấp thuận).

### 2.3. Báo lỗi LaTeX trong Importer / Parser
- `MarkdownImporter` chỉ bóc tách chuỗi thô giữa các dấu `$...$` và `$$...$$` đưa vào `MathInline(latex=...)` hoặc `MathBlock(latex=...)`. Quá trình import **không** kiểm tra cú pháp LaTeX nên `ImportResult.warnings` không có lỗi toán học.
- `LatexMathParser` khi gặp macro lạ hoặc cú pháp không hợp lệ: **nuốt lỗi im lặng**, chỉ ghi log cảnh báo (`_log.warning`) và đưa ký hiệu đó thành `SymbolNode(symbol=cmd)`.
- Khi dàn trang toán qua `MathLayoutEngine`, các `SymbolNode` không tìm thấy mẫu sẽ rơi vào `missing_symbols` và được cộng vào danh sách thiếu.
- **Kết luận**: Đúng như người dùng lưu ý trong prompt, parser nuốt lỗi im lặng và chuyển thành ký hiệu thiếu mẫu. Web Client sẽ giữ nguyên hành vi này, không can thiệp sửa parser.

### 2.4. Phát hiện thay đổi file bằng `mtime` trên hệ file ảo (MEMFS)
- Đã kiểm chứng thực nghiệm bằng `test_bank_mtime_pyodide.js`:
  - `os.stat(bank_path).st_mtime_ns` trên MEMFS của Emscripten thay đổi chính xác khi có hành vi ghi đè file.
  - Nhánh phát hiện `needs_merge = True` trong `Bank.save()` hoạt động bình thường, gọi `load_and_validate()` và `merge_bank_dicts()`.
  - Kết quả kiểm tra: Hai đối tượng Bank độc lập cùng ghi và hợp nhất vào file ảo thành công, bảo toàn đầy đủ các từ mà không bị mất dữ liệu.
- Trong kiến trúc đa tab Web Client: Mỗi tab có một Web Worker với MEMFS riêng. Việc đồng bộ dữ liệu giữa các tab sẽ được quản trị thông qua Web Locks + IndexedDB + BroadcastChannel (như thiết kế ở mục 6).

### 2.5. Phân loại nhãn của Tab Dạy Tkinter
- Khảo sát `view/teach_tab.py` cho thấy quy trình dạy phân định rõ:
  - Nếu nhãn là chữ cái đơn lẻ hoặc dấu thanh (`is_letter_token`): gọi `ctl.teach_letter()` -> đưa vào `bank.letters` hoặc `bank.marks`.
  - Nếu nhãn là từ, cụm từ, chữ số, dấu câu, ký hiệu toán: gọi `ctl.teach_word()` -> qua `bank.add_sample_incremental()` -> tự động phân loại bằng `classify_token`:
    - Chữ số -> `bank.digits`
    - Dấu câu -> `bank.punct`
    - Ký hiệu -> `bank.symbols`
    - Từ/cụm từ -> `bank.words`
- **Kết luận**: `AppController` và `Bank` **đã phủ 100% mọi loại nhãn** mà giao diện desktop dạy. Không có loại nhãn nào bị thiếu ở tầng controller.

---

## 3. Môi trường triển khai Render Static Site
- Người dùng đã kết nối repository thành công với Render Dashboard (ngày 2026-10-06).
- Theo tài liệu chính thức của Render, môi trường build Linux của Static Site hỗ trợ Python và Node.js.
- Phiên bản Python được ghim qua `PYTHON_VERSION` (ví dụ `3.13.5`), Node.js qua `NODE_VERSION` (ví dụ `24.16.0`).
- Lệnh build trong `render.yaml`:
  ```yaml
  buildCommand: "python scripts/build_web.py"
  staticPublishPath: "./webapp/dist"
  ```
- Render hỗ trợ rewrite routes và tùy biến HTTP headers (MIME wasm, CSP, Cache-Control).

---

## 4. Đề xuất trả lời các Quyết định D1 – D8

| Mã | Nội dung | Mặc định | Đề xuất của AI | Lý do kỹ thuật |
|---|---|---|---|---|
| **D1** | **Dữ liệu xem trước trang giấy** | JS đọc lại file `.xopp` vừa ghi trong MEMFS và trích xuất SVG | **GIỮ MẶC ĐỊNH** | Không sửa đổi gì vào lõi Python; `.xopp` đã chứa toàn bộ tọa độ nét và trang; JS parser SVG viết gọn nhẹ và độc lập. |
| **D2** | **Tọa độ token (gạch đỏ từ thiếu mẫu trên trang giấy)** | Chỉ có bảng từ thiếu | **ĐỒNG Ý (Opt-in callback)** | Thêm callback tùy chọn `token_layout_callback` trong engine (mặc định `None`). Khi xem trước web thì truyền để lấy bounding box gạch đỏ; khi xuất file thì `None` nên không ảnh hưởng golden master. |
| **D3** | **Kiểu chữ ổn định khi sửa giữa văn bản (`stable_variants`)** | Tắt (dòng random chung) | **ĐỒNG Ý (Opt-in cờ)** | Thêm `WriteOptions.stable_variants = False` (CLI thêm `--stable`). Trên web bật `True` để người dùng gõ văn bản không bị "nhảy" kiểu chữ của các từ phía sau con trỏ. Khi tắt, byte-identical 100%. |
| **D4** | **Phạm vi xóa mẫu** | Xem từng mẫu + xóa cả nhãn (có Undo) | **GIỮ MẶC ĐỊNH CHO V1** | Xóa từng mẫu cần thiết kế tombstone cấp mẫu trong `merge_bank_dicts`. Tách thành giai đoạn riêng G5b để đảm bảo an toàn dữ liệu. |
| **D5** | **Định dạng theo đoạn chữ (đậm/nghiêng/màu)** | Không hỗ trợ | **GIỮ MẶC ĐỊNH (KHÔNG)** | Lõi IR Text và layout chưa có cấu trúc phân đoạn kiểu này; giữ đúng nguyên tắc KISS/YAGNI, hoãn sang G8. |
| **D6** | **Sửa test phụ thuộc kho cá nhân `test_paths_logging.py`** | Ghi nhận test đỏ | **ĐỒNG Ý SỬA TEST** | Dùng `monkeypatch` hoặc tạo mock trong thư mục tạm khi chạy test đó để toàn bộ test xanh 100% trên clone sạch mà không tạo file rác ở gốc repo. |
| **D7** | **Kho mẫu demo trong bản deploy** | Không | **GIỮ MẶC ĐỊNH (KHÔNG)** | Bảo vệ quyền riêng tư tuyệt đối, tránh nhầm lẫn bản quyền nét vẽ. Lần đầu mở hiện màn hình chào 3 lựa chọn rõ ràng. |
| **D8** | **Bổ sung Python 3.14 vào CI** | Không | **ĐỒNG Ý** | Render và Pyodide 314 đều dùng Python 3.14. Thêm 1 job riêng cho 3.14 trong CI workflow để kiểm soát tính tương thích lâu dài. |

---

## 5. Danh mục dọn dẹp sau GĐ0
- Các file script khảo sát tạm thời (`run_golden_in_pyodide.js`, `test_docx_lxml.js`, `test_bank_mtime_pyodide.js`, `benchmark_all.py`, `test_browser.html`) đã hoàn thành sứ mệnh kiểm chứng.
- Code kiểm thử golden trong Pyodide (`run_golden_in_pyodide.js`) sẽ được quy hoạch thành script chính thức `scripts/test_golden_pyodide.js` trong G1 để chạy tự động trong CI.

---

**BƯỚC TIẾP THEO**: Kính mời bạn xem xét báo cáo và cho ý kiến duyệt các đề xuất D1–D8 để tiến hành `/speckit-plan` cho Giai đoạn 1 (Nền tảng).
