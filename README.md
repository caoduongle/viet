# Chữ viết tay của bạn

Gõ chữ → ra **nét viết tay của chính bạn** cho Xournal++. Có hai cách dùng, cùng chạy trên
một lõi chung:

- **Giao diện đồ hoạ**: `python3 hw_gui.py`
- **Dòng lệnh**: `python3 hw_note.py write -f van_ban.txt -o ra.xopp`

Giao diện có ba tab:

| Tab | Làm gì | Có cần Xournal++ không |
|---|---|---|
| **Viết chữ** | Gõ/dán văn bản → tạo file `.xopp` bằng nét viết tay của bạn | Có — mở file `.xopp` ra, Ctrl+A, Ctrl+C, dán vào sổ như trước giờ |
| **Dạy từ mới** | Vẽ trực tiếp từng từ bằng chuột/bút cảm ứng, bấm Lưu là xong | **Không** — không cần xuất/nạp file `.xopp` nữa |
| **Kho mẫu** | Xem thống kê, tìm/xoá từ, xuất file xem lại toàn bộ kho | Xuất file xem lại vẫn qua Xournal++ (chỉ để xem, không bắt buộc) |

## Cài đặt

Cần **Python 3.10+** (đã kiểm thử liên tục trên CI với Python 3.10, 3.11, 3.12, 3.13). Không cần cài thư viện ngoài nào khi chạy ứng dụng — hoàn toàn dùng thư viện chuẩn Python (zero external runtime dependencies). Riêng giao diện cần **tkinter**:

- **Ubuntu/Debian**: `sudo apt install python3-tk`
- **Windows / macOS**: bản Python tải từ [python.org](https://www.python.org/) đã có sẵn tkinter.

## Chạy

Giữ nguyên cấu trúc thư mục này (thư mục `chuviettay/` phải nằm **cạnh** hai file `hw_*.py`):

```
hw_note.py
hw_gui.py
chuviettay/            ← toàn bộ mã nguồn
chu_cua_ban.json.gz    ← kho mẫu chữ viết tay của bạn
```

```bash
python3 hw_gui.py                 # mở giao diện
python3 hw_gui.py --bank D:\kho_khac.json.gz   # mở thẳng một kho mẫu khác
python3 hw_note.py stats          # dòng lệnh: thống kê kho mẫu
```

Cửa sổ tự tìm `chu_cua_ban.json.gz` cùng thư mục. Muốn dùng kho mẫu khác thì bấm **"Chọn kho
mẫu khác..."** ở góc trên; muốn bắt đầu một kho **trống** để dạy từ đầu thì bấm **"Tạo kho
mẫu mới..."** (chọn file đã có thì app chỉ mở nó ra, **không bao giờ ghi đè**).

## Dạy từ mới — lưu ý khi vẽ

- Có 2 đường kẻ mờ làm mốc: đường **dưới** là dòng kẻ chính (đặt chân chữ lên đó), đường ngắn
  **phía trên bên trái** là mốc chiều cao chữ thường (như "a", "o", "c").
- Viết dấu thanh (sắc, huyền, hỏi, ngã, nặng) như **một nét riêng**, đừng nối liền với thân chữ —
  app cần nét riêng để nhận ra đó là dấu.
- Muốn dạy một **cụm nhiều từ dính nhau** (ví dụ "cà phê" viết liền một nét), gõ nguyên cụm đó
  vào ô "Thêm từ vào hàng đợi" — app không tự tách theo khoảng trắng.
- **Hiệu chỉnh cỡ tay**: nếu tay bạn vẽ bằng chuột to/nhỏ khác với chữ đã học trước đó, bấm "Hiệu
  chỉnh cỡ tay" một lần đầu buổi — app đưa ra một từ đã có sẵn nhiều mẫu, bạn viết lại đúng từ đó
  tự nhiên, app tự tính hệ số và áp dụng cho các từ dạy sau trong phiên này (giống cơ chế "ô đo
  cỡ tay" của lệnh `learn`). Bấm "Bỏ qua" hoặc "Xoá hàng đợi" khi đang ở từ mốc là huỷ việc
  hiệu chỉnh.
- Mỗi từ lưu xuống kho mẫu ngay lập tức (không cần bấm "Save" riêng ở đâu khác).
- Kho mẫu hỗ trợ an toàn liên tiến trình hoàn toàn (cross-process file lock, tự động hợp nhất mẫu và bảo vệ deletion tombstones), cho phép GUI và CLI chạy đồng thời mà không bị mất dữ liệu hay hồi sinh từ đã xoá. Tab Viết chữ luôn tự động tải bản kho mới nhất.

## Tương đương lệnh dòng lệnh

| Lệnh CLI | Chỗ tương ứng trong app |
|---|---|
| `write -f/-t ... -o ra.xopp` | Tab **Viết chữ** |
| `learn ra_thieu.xopp` | Tab **Dạy từ mới** (vẽ trực tiếp, không cần file trung gian) |
| `seed 200` | Nút **"Nạp từ thông dụng còn thiếu..."** trong tab Dạy từ mới |
| `check` | Nút **"Xuất file kiểm tra lại (.xopp)..."** trong tab Kho mẫu |
| `drop từ` | Chọn từ trong tab Kho mẫu → **"Xoá từ đã chọn"** |
| `stats` | Ô thống kê ở đầu tab Kho mẫu |

Xem `python3 hw_note.py --help` (và `python3 hw_note.py write --help`) để biết đủ tuỳ chọn:
`--scale`, `--line`, `--width`, `--space`, `--jitter`, `--wscale`, `--color`, `--seed`, `--strict-case`.

---

# Dành cho người phát triển

## Kiến trúc (MVC)

Mọi mã nằm trong package `chuviettay/`, chia ba lớp với **luật phụ thuộc một chiều**:

```
   cli.py           gui.py + view/
  (dòng lệnh)      (giao diện Tkinter)
       │                  │
       └────────┬─────────┘        mũi tên = "được phép gọi xuống"
                ▼
      controller/app_controller.py     ← điểm vào DUY NHẤT cho mọi thao tác nghiệp vụ
                │
                ▼
      model/   (Bank, Writer, composer, learning, xopp, ...)   ← dữ liệu + thuật toán thuần
```

| Lớp | Được làm | Không được làm |
|---|---|---|
| **model/** | Dữ liệu + thuật toán thuần Python | import tkinter/argparse/controller/view · `print` · `sys.exit` |
| **controller/** | Điều phối, giữ trạng thái (kho đang mở, hệ số cỡ tay), ghi log, trả `dataclass` | import tkinter/argparse/view/cli · `print` |
| **view/** (+ `gui.py`) | Dựng widget, bắt sự kiện, gọi Controller, hiển thị kết quả | đụng thẳng vào `Bank`/`Writer`/`model/*` |
| **cli.py** | Đọc tham số, gọi Controller, `print` kết quả | đụng thẳng vào `model/*` |

Các luật này **được kiểm tra tự động** (`tests/test_architecture.py`): vi phạm là test đỏ, chỉ rõ file và dòng.

```
hw_note.py, hw_gui.py     lối vào mỏng (giữ nguyên tên + cách gọi như trước)
chu_cua_ban.json.gz       kho mẫu của bạn — DỮ LIỆU, không phải mã nguồn
chuviettay/
├── config.py             hằng số dùng chung (lưới ô, ngưỡng...) — xem cảnh báo bên dưới
├── paths.py              tìm kho mẫu mặc định (kể cả khi đã đóng gói thành .exe)
├── logging_setup.py      ghi log ra chuviettay.log
├── formatting.py         câu chữ báo cáo dùng chung cho CLI và GUI
├── cli.py                dòng lệnh (argparse) → gọi Controller
├── gui.py                dựng Controller + MainWindow, chạy mainloop
├── model/
│   ├── text_utils.py     hàm thuần: dấu thanh, độ rộng chữ, hình học nét, chuẩn hoá văn bản
│   ├── xopp.py           đọc/ghi .xopp, sinh/đọc file lưới ô
│   ├── calibration.py    công thức hiệu chỉnh cỡ tay (MỘT chỗ duy nhất)
│   ├── bank.py           Bank: nạp/lưu/tạo mới/thêm mẫu/xoá từ/chỉ mục tra cứu
│   ├── writer.py         Writer: ghép một token (từ/số/dấu câu) thành nét
│   ├── composer.py       dàn dòng + chia trang + "run tay" + xuất .xopp (WriteOptions, WriteResult)
│   ├── learning.py       học mẫu từ file .xopp đã viết tay
│   └── seed_words.py     700 từ thông dụng (dữ liệu tĩnh)
├── controller/
│   ├── app_controller.py AppController — write_text, teach_word, learn_from_files, drop_words, ...
│   └── results.py        các dataclass kết quả
└── view/                 ← chỗ DUY NHẤT được import tkinter
    ├── app_window.py     MainWindow: trung gian giữa các tab, chọn/tạo kho, bắt lỗi bất ngờ
    ├── write_tab.py · teach_tab.py · bank_tab.py
    ├── word_canvas.py    ô vẽ + quy đổi pixel → đơn vị kho mẫu (hàm thuần, test được)
    └── dialogs.py        báo lỗi: ghi traceback vào log rồi mới hiện hộp thoại
```

> ⚠️ **Đừng đổi `config.py` và các ngưỡng trong `text_utils.find_tone` nếu không cố ý.** Kho mẫu
> hiện có được sinh ra dựa trên đúng các con số đó (kích thước ô lưới, cách nhận nét dấu thanh...).
> Đổi chúng là làm lệch cách đọc mọi mẫu chữ đã học.

## Tìm lỗi (debug)

- **Log**: mọi lỗi đều được ghi kèm traceback đầy đủ vào **`chuviettay.log`** (cạnh chương trình,
  tự xoay vòng ~1MB × 3 file). Hộp thoại báo lỗi có in sẵn đường dẫn file này. Khi nhờ ai đó xem lỗi,
  chỉ cần gửi file này — kể cả với bản `.exe` không có cửa sổ console.
- **Chế độ chi tiết**: `python3 hw_note.py -v write ...` hoặc `python3 hw_gui.py -v` ghi thêm log mức
  DEBUG và in ra màn hình. (`-v` đặt **trước** tên lệnh.)
- **Tái tạo đúng một kết quả**: `write ... --seed 7` cho ra đúng cùng file mỗi lần (mặc định mỗi lần
  một khác vì có "run tay" ngẫu nhiên).
- **Thử lõi mà không cần giao diện**:

  ```python
  from chuviettay.controller.app_controller import AppController
  from chuviettay.controller.results import WriteOptions
  ctl = AppController(); ctl.load_bank()
  r = ctl.write_text("Xin chào", WriteOptions(seed=1), "thu.xopp")
  print(r)                 # WriteResult(n_lines=..., missing={...}, ...)
  ```

Gặp triệu chứng nào thì mở file nào trước:

| Triệu chứng | Xem |
|---|---|
| Chữ ghép sai, dấu thanh lệch/thiếu | `model/writer.py` (`substitute`), `model/bank.py` (`rebuild`, `_harvest`) |
| Xuống dòng/sang trang sai, khoảng cách lạ | `model/composer.py` |
| Học từ file `.xopp` nhầm ô / sai cỡ | `model/xopp.py` (`parse_learn_file`), `model/calibration.py` |
| Hiệu chỉnh cỡ tay trong app ra cỡ lạ | `controller/app_controller.py` (`teach_word`), `view/word_canvas.py` |
| Nút bấm không phản hồi / hiển thị sai | `view/*_tab.py` |
| Lệnh CLI in sai câu chữ | `cli.py`, `formatting.py` |

## Kiểm thử

```bash
pip install -r requirements-dev.txt
python3 -m pytest                  # chạy tất cả (test giao diện tự bỏ qua nếu không có màn hình)
xvfb-run -a python3 -m pytest      # Linux không màn hình: chạy cả test giao diện thật
```

Hơn 210 ca kiểm thử tự động, chia nhóm:

- **Đơn vị** cho từng hàm/lớp Model (`test_text_utils`, `test_bank`, `test_writer`, `test_xopp`, ...) và
  cho `AppController`; kho mẫu thử là một kho **nhỏ tự dựng** (`tests/conftest.py`) nên tự tính tay được đáp án.
- **Giao diện thật** (`test_gui.py`): dựng `MainWindow`, điều khiển như người dùng (gõ, vẽ, bấm nút), hộp
  thoại được giả lập.
- **Golden-master** (`test_golden_master.py`): mã băm SHA-256 của file `.xopp` sinh ra **bởi bản gốc trước
  khi tái cấu trúc** — đầu ra thuật toán phải khớp từng byte. Sửa thuật toán làm đổi nét vẽ thì test này
  đỏ; nếu là cố ý, kiểm tra bằng mắt trong Xournal++ rồi cập nhật hằng số.
- **Kiến trúc** (`test_architecture.py`): giữ các luật MVC ở trên.

Test **không bao giờ** đọc hay ghi `chu_cua_ban.json.gz` của bạn: chúng dùng một **bản chụp cố định** trong
`tests/data/` (và luôn làm việc trên bản sao trong thư mục tạm), nên kết quả không đổi khi bạn dạy thêm từ mới.

## Mở rộng — làm theo công thức

**Thêm một tuỳ chọn cho `write`** (ví dụ `--indent`):
1. Thêm trường vào `WriteOptions` (`model/composer.py`) và dùng nó trong `compose_document`.
2. CLI: thêm cờ trong `cli.build_parser` và truyền vào `WriteOptions(...)` ở `_cmd_write`.
3. GUI: thêm ô nhập ở `WriteTab._build_options` và đọc nó ở `WriteTab.read_options`.
4. Thêm test ở `tests/test_composer.py`.

**Thêm một lệnh mới** (ví dụ `export`):
1. Viết phần nghiệp vụ thuần ở `model/`, kèm test.
2. Thêm phương thức vào `AppController` (+ dataclass kết quả ở `controller/results.py` nếu cần).
3. CLI: hàm `_cmd_export` + subparser. GUI: nút trong tab phù hợp. **Cả hai chỉ gọi Controller.**

**Thêm một tab mới**: tạo `view/xxx_tab.py` nhận `ctl: AppController`, đăng ký trong
`MainWindow._build_tabs`. Cần nói chuyện với tab khác thì truyền callback từ `MainWindow`
(các tab không gọi nhau trực tiếp).

## Đóng gói ứng dụng (hoặc tải từ GitHub Releases)

Người dùng cuối có thể tải các bản đóng gói chạy ngay (standalone binaries) từ mục **GitHub Releases** của repository (bao gồm `hw_gui-windows.zip` cho Windows và `hw_gui-linux.tar.gz` cho Linux x86_64).

Nếu tự đóng gói từ mã nguồn:

**Windows** — build trên máy Windows:

1. Cài Python từ [python.org](https://www.python.org/) (tick **"Add python.exe to PATH"**).
2. Chạy `pip install -r requirements-dev.txt`.
3. Bấm đúp `build_windows.bat` (hoặc chạy trong PowerShell/cmd) → tạo `hw_gui.exe` trong thư mục `dist/`.
4. Copy `hw_gui.exe` ra một thư mục riêng, để **cạnh nó** file `chu_cua_ban.json.gz` rồi bấm đúp là chạy.
   Kho mẫu và file log luôn nằm **cạnh file `.exe`** (không nằm trong thư mục tạm của PyInstaller).

**Linux / macOS**:
1. Cài `requirements-dev.txt`.
2. Chạy `./build_linux_mac.sh` (macOS phải build trên máy Mac) → tạo binary trong `dist/`.

Lưu ý: file binary độc lập nặng (~15–25MB) vì gói kèm môi trường Python; Windows có thể cảnh báo "Windows protected your PC" vì chưa có chữ ký số — chọn **More info → Run anyway**.

Xem `CHANGELOG.md` để biết chi tiết những gì đã thay đổi so với bản một-file trước đây.
