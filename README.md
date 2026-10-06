# Chữ viết tay của bạn

Gõ chữ → ra **nét viết tay của chính bạn** cho Xournal++. Có ba cách dùng, cùng chạy trên
một lõi chung:

- **Web Client (Static Web App / PWA)**: Chạy 100% trong trình duyệt qua WebAssembly (Pyodide 314.0.7) tại `webapp/` (triển khai trên Render hoặc chạy cục bộ).
- **Giao diện đồ hoạ desktop**: `python3 hw_gui.py`
- **Dòng lệnh**: `python3 hw_note.py write -f van_ban.txt -o ra.xopp`

Giao diện có ba tab chính:

| Tab | Làm gì | Có cần Xournal++ không |
|---|---|---|
| **Viết chữ** | Gõ/dán văn bản (Markdown, Math LaTeX, Bảng) → tạo file `.xopp`, ảnh PNG/SVG, in PDF | Có (khi muốn sửa tiếp trong Xournal++) hoặc tải trực tiếp ảnh/PDF |
| **Dạy chữ / Dạy từ mới** | Vẽ trực tiếp từng từ/chữ cái bằng chuột/bút cảm ứng, bấm Lưu là xong | **Không** — không cần xuất/nạp file `.xopp` nữa |
| **Kho mẫu** | Xem thống kê, tìm/xoá từ an toàn, xem thumbnail, sao lưu/nhập `.json.gz` | Xuất file xem lại vẫn qua Xournal++ (chỉ để xem, không bắt buộc) |

## Cài đặt

Cần **Python 3.10+** (đã kiểm thử liên tục trên CI với Python 3.10, 3.11, 3.12, 3.13). Lõi cơ bản không cần bất kỳ thư viện ngoài nào (Zero Core Dependencies), hoàn toàn dùng thư viện chuẩn Python. Riêng giao diện đồ hoạ cần **tkinter**:

- **Ubuntu/Debian**: `sudo apt install python3-tk`
- **Windows / macOS**: bản Python tải từ [python.org](https://www.python.org/) đã có sẵn tkinter.

### Mở rộng hỗ trợ Markdown (.md) và Word (.docx)
Để mở và chuyển đổi trực tiếp các file tài liệu định dạng Markdown hoặc Word kèm bảng biểu và công thức toán học:

```bash
pip install "chuviettay[docs]"
# hoặc trong thư mục mã nguồn:
pip install ".[docs]"
```

Gói `docs` bao gồm `markdown-it-py`, `mdit-py-plugins` và `python-docx`. Nếu không cài gói này, ứng dụng vẫn hoạt động 100% với văn bản thuần `.txt` mà không phát sinh lỗi.

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

## Web Client (Ứng dụng web chạy trong trình duyệt)

Web Client là phiên bản tĩnh 100% client-side (SPA / PWA) chạy Python qua **Pyodide 314.0.7** (WASM) trong Web Worker, dữ liệu kho mẫu lưu trữ an toàn trong IndexedDB của trình duyệt mà không cần máy chủ backend.

### Chạy thử cục bộ (Local Development)

```bash
# 1. Đóng gói mã nguồn và dependencies vào webapp/dist/
python3 scripts/build_web.py

# 2. Khởi chạy HTTP Server hỗ trợ Web Worker & Cache headers
node scripts/serve.mjs
# Mở trình duyệt tại http://localhost:8080
```

### Triển khai lên Render (Static Site)

Dự án đã cấu hình sẵn Blueprint [`render.yaml`](render.yaml):
1. Đẩy mã nguồn lên repository GitHub/GitLab.
2. Trên [Render Dashboard](https://dashboard.render.com/), chọn **New +** → **Blueprint** và chọn repo này.
3. Render tự động chạy `python scripts/build_web.py` và triển khai thư mục `webapp/dist/` dưới dạng Static Site.
4. Tệp Blueprint đã tích hợp sẵn:
   - Header bảo mật CSP (`Content-Security-Policy`), chống sniff MIME (`X-Content-Type-Options: nosniff`), Web Locks & Service Worker hỗ trợ.
   - Header bộ đệm dài hạn `Cache-Control: public, max-age=31536000, immutable` cho các file tĩnh và tài nguyên WASM / wheels.

---

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
- Kho mẫu hỗ trợ an toàn liên tiến trình hoàn toàn (khóa file nguyên tử cross-process, tự động hợp nhất mẫu và bảo vệ deletion tombstones với nhãn thời gian), cho phép GUI và CLI chạy đồng thời mà không bị mất dữ liệu hay hồi sinh từ đã xoá. Tab Viết chữ luôn tự động tải bản kho mới nhất.

## Tương đương lệnh dòng lệnh

| Lệnh CLI | Chỗ tương ứng trong app |
|---|---|
| `write -f/-t ... -o ra.xopp` | Tab **Viết chữ** |
| `learn ra_thieu.xopp` | Tab **Dạy từ mới** (vẽ trực tiếp, không cần file trung gian) |
| `grid -o luoi.xopp` | Xuất tờ lưới tập viết ký tự 4 dòng kẻ (`hw3`) |
| `seed 200` | Nút **"Nạp từ thông dụng còn thiếu..."** trong tab Dạy từ mới |
| `check` | Nút **"Xuất file kiểm tra lại (.xopp)..."** trong tab Kho mẫu |
| `drop từ` | Chọn từ trong tab Kho mẫu → **"Xoá từ đã chọn"** |
| `stats` | Ô thống kê ở đầu tab Kho mẫu |

Xem `python3 hw_note.py --help` (và `python3 hw_note.py write --help`) để biết đủ tuỳ chọn:
`--format {auto,txt,md,docx}`, `--scale`, `--line`, `--width`, `--space`, `--jitter`, `--wscale`, `--color`, `--seed`, `--strict-case`, `--assemble`, `--auto-xh`, `--target-xh`, `--letter-gap`, `--pen-clearance`.

### Cơ chế ghép chữ từ ký tự đơn (`--assemble`)

Khi bật cờ `--assemble`, các từ chưa có mẫu nguyên từ trong kho sẽ được tự động ghép từ các ký tự đơn (`letters`), chữ số (`digits`), dấu câu (`punct`) và ký hiệu (`symbols`):
- **Khoảng cách tự nhiên & chống dính chữ**: Sử dụng đường bao biên hình học (contour pair gap) và khoảng đệm biên `lsb`/`rsb` thay cho việc chồng nét cứng. Sàn khe hở tối thiểu `--pen-clearance 0.8` (mặc định 0,8 lần nét bút) đảm bảo các chữ cái liền kề không bao giờ bị bết mực vào nhau.
- **Ghép chữ có dấu thanh (Dual-Path Assembly)**: Ưu tiên sử dụng trực tiếp mẫu nguyên âm có sẵn dấu tiếng Việt trong kho; tự động fallback ghép nguyên âm cơ sở với dấu thanh trong `bank.marks` kèm thuật toán đặt dấu theo trọng tâm và né tránh nét vươn cao (ascender).
- **Chuẩn hoá cỡ chữ (`--auto-xh`)**: Tự động chuẩn hoá các ký tự trong kho về cùng cỡ x-height chuẩn (mặc định 7,94 pt, có thể tinh chỉnh bằng `--target-xh`) giúp nét bút thanh mảnh tự nhiên và đúng tỉ lệ ghi chú thực tế.
- **Hỗ trợ từ mã / kỹ thuật**: Tự động nhận diện và ghép các token chứa dấu gạch dưới (`body_mass_g`), ngoặc và toán tử (`>=`, `<=`, `<`, `>`, `=`).

### Xuất tờ lưới tập viết ký tự 4 dòng kẻ (`hw3`)

```bash
python3 hw_note.py grid -o luoi_ky_tu.xopp
```
Tờ lưới `hw3` gồm 4 dòng kẻ mốc (chân chữ baseline, x-height, ascender, descender) kèm vạch lề trái/phải và hướng dẫn viết tay chi tiết bằng tiếng Việt. Lưới tạo 85 ô (29 chữ cái tiếng Việt + 4 chữ cái Latin mượn f, j, w, z × hoa/thường = 66 ô, 14 cụm phụ âm/nguyên âm đôi thông dụng `ng, nh, ch, tr, ph, th, kh, gi, qu, ươ, ưa, uy, ay, oa`, và 5 ô dấu thanh rời) và hoàn toàn không chứa chữ số. Chữ số và dấu câu được dạy thông qua "bộ tối thiểu" (`model/seed_words.MINIMAL_DIGITS`, `MINIMAL_PUNCT` qua nút ở tab Dạy hoặc lệnh `seed`). Nạp tờ lưới đã viết bằng lệnh `python3 hw_note.py learn luoi_ky_tu.xopp`.

### Di trú kho mẫu ký tự (`scripts/migrate_letter_bank.py`)

Nếu bạn có kho mẫu ký tự đơn cũ (chỉ chứa các ký tự trong `words` dạng v3):
```bash
python3 scripts/migrate_letter_bank.py --in kho_mau_cu.json.gz --out kho_mau_moi.json.gz
```
Công cụ sẽ tự động chuẩn hoá toạ độ chân chữ baseline, bóc tách dấu thanh rời chính xác, tính toán khoảng đệm `lsb`/`rsb` và đưa về chuẩn `letters` (schema v4) với đầy đủ siêu dữ liệu x-height thực nghiệm.

Định dạng đầu vào tự động nhận diện theo đuôi mở rộng (`.txt`, `.md`, `.markdown`, `.docx`), hỗ trợ bảng dữ liệu (GFM / Word) và công thức toán học (LaTeX / OMML) căn chỉnh theo baseline nét viết tay.

#### Công thức toán học

| Nguồn | Hỗ trợ |
|---|---|
| Markdown | `$…$`, `$$…$$`, `\(…\)`, `\[…\]`, môi trường `\begin{align}…\end{align}` (kể cả trong mục danh sách và ô bảng). Tiền (`5$ rồi 10$`) không bị nhận nhầm là công thức. |
| LaTeX | Phân số (`\frac \dfrac \binom`), căn, chỉ số/số mũ (kể cả `x^2`, `f'`), ngoặc co giãn `\left…\right`, `\sum \int \lim` có cận, tên hàm (`\sin \log …`), vectơ/góc/gạch ngang (`\overrightarrow \widehat \overline …`), `\mathbb \mathcal \text \mathrm`, ma trận / `cases` / `aligned` / `array`, khoảng trắng và hơn 200 ký hiệu. |
| Word (.docx) | Công thức Office Math (OMML): phân số, chỉ số, căn, ngoặc nhiều phần tử, toán tử lớn, giới hạn, hàm, dấu trang trí, hệ phương trình, ma trận, khung. Công thức nhập trong cùng một run (`2x+3=0`) được tách đúng thành số/biến/toán tử. |
| MathType | **Chưa đọc được** nội dung đối tượng OLE của MathType / Equation Editor. Ứng dụng phát hiện và thay bằng ô vuông trống `□`, kèm cảnh báo có số lượng (không bao giờ im lặng bỏ mất). Cách xử lý: trong Word dùng *Convert Equations* của MathType để đổi sang công thức gốc của Word rồi lưu lại, hoặc chép công thức sang Markdown/LaTeX. |

Quy ước: dấu phẩy trần trong `$0,1$` là dấu ngăn cách (như TeX); dấu phẩy thập phân kiểu Việt Nam viết là `$0{,}1$`.
Ký hiệu chưa có mẫu viết tay trong kho được vẽ tạm bằng nét vector và vẫn nằm trong danh sách "Ký hiệu thiếu mẫu" để bạn dạy thêm.
Công thức quá rộng được thu nhỏ vừa dòng/ô bảng, hoặc ngắt dòng sau dấu quan hệ/toán tử; công thức cao làm tăng chiều cao dòng.

> **Fidelity và công thức:** bản làm trắng có đặt màu trắng cho công thức OMML (theo lược đồ OOXML). LibreOffice bỏ qua màu chữ trong công thức, nên khi chuyển đổi Fidelity qua LibreOffice, công thức in có thể vẫn hiện màu đen dưới chữ viết tay; chế độ Semantic không bị ảnh hưởng.

### Chế độ xử lý tài liệu Word (.docx)

Ứng dụng hỗ trợ 2 chế độ chuyển đổi tài liệu `.docx` sang chữ viết tay:

| Chế độ | Mô tả | Hỗ trợ nền tảng | Công cụ yêu cầu |
|---|---|---|---|
| **Semantic Mode** (`--mode semantic`) | Trích xuất nội dung ngữ nghĩa (đoạn văn, bảng biểu, công thức toán) và tự động căn chỉnh, xuống dòng, ngắt trang linh hoạt theo các tùy chọn khổ giấy (A3, A4, A5, Letter) và nền giấy (ô li, dòng kẻ, chấm). | **Đa nền tảng 100%** (Windows, Linux, macOS) | Python thuần (`python-docx`, `markdown-it-py`) |
| **Fidelity Mode** (`--mode fidelity`) | Khóa cố định 100% bố cục, vị trí dòng kẻ, hình ảnh và bảng biểu gốc của tài liệu. Chỉ thay thế chữ in bằng chữ viết tay đúng tại tọa độ gốc. | **Windows** (toàn diện)<br>**Linux/macOS** (hỗ trợ PDF nền) | Trích xuất tọa độ không gian yêu cầu **Microsoft Word COM** trên Windows.<br>Tạo PDF nền hỗ trợ Microsoft Word COM hoặc **LibreOffice**. |

> **Ghi chú**: Trên Linux/macOS hoặc máy chủ CI không cài đặt Microsoft Word, vui lòng chọn chế độ **Semantic Mode** (`--mode semantic` trên CLI hoặc chọn *Tự do (Semantic)* trên GUI) để ứng dụng tự động dàn trang tối ưu.

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
├── document/
│   ├── ir.py             Document Intermediate Representation (Paragraph, Heading, Table, MathBlock...)
│   └── page_format.py    Quy chuẩn khổ giấy, hướng giấy, lề trang và nền giấy (.xopp)
├── importer/
│   ├── base.py           BaseImporter trừu tượng và factory
│   ├── txt_importer.py   Nạp tệp văn bản thuần (.txt)
│   ├── markdown_importer.py Nạp tệp Markdown (.md) kèm bảng và công thức
│   ├── docx_importer.py  Nạp tệp Word (.docx) kèm bảng phức tạp và định dạng
│   └── omml.py           Chuyển công thức Office Math (OMML) của Word sang cây cú pháp toán học
├── layout/
│   ├── engine.py         DocumentLayoutEngine: dàn trang tự do theo cấu trúc ngữ nghĩa
│   ├── math_layout.py    Dàn công thức toán học theo baseline nét viết tay (khoảng cách kiểu TeX, ngoặc co giãn, ma trận...)
│   ├── vector_glyphs.py  Nét vector dự phòng cho ký hiệu chưa có mẫu viết tay
│   └── table_layout.py   Dàn bảng biểu, đo độ rộng ô theo nét thật và viền bảng
├── math/
│   ├── ast.py            Cấu trúc cây cú pháp toán học (MathRow, Fraction, Delimited, NAry, Matrix, Accent...)
│   ├── symbols.py        Bảng ký hiệu, phân lớp kiểu TeX, chuẩn hoá Unicode
│   ├── parser.py         Bộ phân tích biểu thức LaTeX sang cây cú pháp
│   ├── latex_writer.py   Chuyển cây cú pháp ngược lại thành LaTeX
│   └── build.py          Hàm dựng nút dùng chung giữa bộ phân tích LaTeX và OMML
├── fidelity/
│   ├── converter.py      FidelityConverter: chuyển đổi PDF nền và trích xuất tọa độ cố định
│   ├── extractor.py      SpatialTextExtractor: trích xuất dòng văn bản và hình học không gian
│   ├── background.py     WhiteoutBackgroundGenerator: làm trắng chữ in giữ nguyên ảnh/bảng
│   ├── engine.py         FidelityLayoutEngine: đặt nét viết tay vào đúng bounding box gốc
│   └── fixed_model.py    Mô hình dữ liệu không gian FixedDocument, TextBox, ImageBox
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

## Cơ chế đồng thời và an toàn dữ liệu (Concurrency & Data Integrity)

Kho mẫu (`Bank`) sử dụng kiến trúc lai kết hợp các cơ chế sau để bảo đảm tính toàn vẹn dữ liệu:
1. **Khóa file nguyên tử cấp hệ điều hành (`FileLock`)**: Sử dụng file khóa `.lock` để tuần tự hoá các thao tác ghi và nạp lại kho mẫu giữa các tiến trình GUI và CLI chạy song song, ngăn chặn tuyệt đối tình trạng race condition và can thiệp đồng thời vào tệp đĩa.
2. **Dọn dẹp và chống hồi sinh từ bằng Deletion Tombstones có nhãn thời gian**: Khi xoá từ bằng `Bank.drop()`, hệ thống ghi nhận tombstone mang nhãn thời gian `deleted_at`. Thuật toán `merge_bank_dicts()` đối chiếu timestamp này với `readded_at` và thời điểm nạp snapshot của tiến trình khác để loại bỏ các mẫu cũ từ snapshot trước thời điểm xoá, ngăn ngừa tình trạng snapshot cũ hồi sinh từ đã xoá mà vẫn bảo đảm người dùng có thể chủ động dạy lại từ sau khi xoá. Thao tác gọi `drop()` trên từ không tồn tại sẽ an toàn trả về 0 mà không tạo tombstone dư thừa.
3. **Bộ đếm thế hệ tăng đơn điệu (`_generation`)**: Đóng vai trò chuỗi định danh đột biến nội bộ phiên làm việc phục vụ ghi log kiểm toán (audit log) và xác thực tính tuần tự của các lần ghi nhớ.
4. **Ghi đĩa nguyên tử và bảo vệ file hỏng**: Ghi dữ liệu ra tệp tạm `.tmp` rồi đổi tên đè (`os.replace`) dưới khóa file. Nếu tệp trên đĩa bị hỏng hoặc không giải mã được trong quá trình hợp nhất, thao tác `save()` sẽ lập tức huỷ bỏ và ném lỗi thay vì vô tình ghi đè phá huỷ dữ liệu đĩa.

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
python3 -m pytest -vv -s --timeout=30             # chạy tất cả kèm watchdog timeout
xvfb-run -a python3 -m pytest -vv -s --timeout=30 # Linux không màn hình: chạy cả test giao diện thật
```

Hơn 1.020 ca kiểm thử tự động, chia nhóm:

- **Đơn vị** cho từng hàm/lớp Model (`test_text_utils`, `test_bank`, `test_writer`, `test_xopp`, ...) và
  cho `AppController`; kho mẫu thử là một kho **nhỏ tự dựng** (`tests/conftest.py`) nên tự tính tay được đáp án.
- **Giao diện thật** (`test_gui.py`): dựng `MainWindow`, điều khiển như người dùng (gõ, vẽ, bấm nút), hộp
  thoại được giả lập.
- **Golden-master** (`test_golden_master_real_path.py`): mã băm SHA-256 của file `.xopp` sinh ra **bởi bản gốc trước
  khi tái cấu trúc** — đầu ra thuật toán phải khớp từng byte (bao gồm cả 8 ca kiểm thử tương thích trong Pyodide 314.0.7 qua `node scripts/test_golden_pyodide.mjs`). Sửa thuật toán làm đổi nét vẽ thì test này
  đỏ; nếu là cố ý, kiểm tra bằng mắt trong Xournal++ rồi cập nhật hằng số.
- **Kiến trúc** (`test_architecture.py`): giữ các luật MVC ở trên.

Test **không bao giờ** đọc hay ghi `chu_cua_ban.json.gz` của bạn: chúng dùng một **bản chụp cố định** trong
`tests/data/` (và luôn làm việc trên bản sao trong thư mục tạm), nên kết quả không đổi khi bạn dạy thêm từ mới.

### Về dữ liệu cá nhân và lịch sử Git

Repository đã được rà soát và làm sạch hoàn toàn các blob dữ liệu cá nhân (`chu_cua_ban.json.gz` và `kho_mau_chup_lai.json.gz`) khỏi toàn bộ lịch sử commit của các nhánh và thẻ bằng `git-filter-repo` (xem `scripts/purge_git_history.ps1` hoặc `scripts/purge_git_history.sh`).

> [!NOTE]
> **Lưu ý về lưu trữ đối tượng phía máy chủ (GitHub):** Việc viết lại lịch sử nhánh (`git push --force --mirror`) đảm bảo 100% các nhánh và thẻ công khai không còn tham chiếu tới dữ liệu cũ. Tuy nhiên, các nền tảng máy chủ từ xa như GitHub có thể lưu trữ tạm thời các commit object mồ côi (unreachable objects) trong bộ nhớ đệm máy chủ nếu truy cập trực tiếp bằng mã SHA commit cũ, cho đến khi chu kỳ dọn rác (Garbage Collection) của máy chủ chạy hoặc theo yêu cầu thu hồi bộ nhớ gửi tới GitHub Support.

## Mở rộng — làm theo công thức

**Thêm một tuỳ chọn cho `write`** (ví dụ `--indent`):
1. Thêm trường vào `WriteOptions` (`model/composer.py`) và dùng nó trong `DocumentLayoutEngine` (`layout/engine.py`).
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
