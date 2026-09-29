# Nhật ký thay đổi

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

### Mới
- Bộ kiểm thử hơn 370 ca (`pytest`), gồm test giao diện thật chạy dưới màn hình ảo, golden-master so với bản
  gốc, test bộ nạp tài liệu và test kiến trúc. Xem README → "Kiểm thử".
- Tham số `--bank` cho `hw_gui.py`; cờ `-v` cho cả hai.

