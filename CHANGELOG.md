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

### Còn tồn tại từ bản gốc (chưa sửa, cần lưu ý)
- App giữ kho mẫu trong bộ nhớ và **ghi đè cả file** mỗi lần dạy/xoá từ. Nếu trong lúc cửa sổ đang mở bạn chạy
  `hw_note.py learn/drop` ở dòng lệnh rồi lại **dạy tiếp trong cửa sổ**, phần dòng lệnh vừa thêm có thể bị ghi
  đè. Tab Viết chữ thì luôn nạp lại kho mới nhất từ đĩa trước mỗi lần viết (giống bản gốc).

### Mới
- Bộ kiểm thử hơn 160 ca (`pytest`), gồm test giao diện thật chạy dưới màn hình ảo, golden-master so với bản
  gốc, và test kiến trúc. Xem README → "Kiểm thử".
- Tham số `--bank` cho `hw_gui.py`; cờ `-v` cho cả hai.
