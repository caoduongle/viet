# Contract: Browser Bridge API (`chuviettay/browser/bridge.py`)

**Status**: Defined  
**Version**: 1.0.0  
**Consumer**: Web Worker (`webapp/js/worker/py-worker.js`)  
**Provider**: `chuviettay/browser/bridge.py` (chạy trong Pyodide)

---

## 1. Nguyên tắc Thiết kế
1. **Facade thuần túy**: `bridge.py` là điểm truy cập DUY NHẤT từ JavaScript vào Python. Nó CHỈ gọi các phương thức công khai của `AppController`. Tuyệt đối không import hoặc thao tác trực tiếp với các module trong `chuviettay/model/*`.
2. **Dữ liệu chuẩn hóa**: Đầu vào và đầu ra 100% là chuỗi JSON hoặc kiểu dữ liệu JSON-serializable (string, number, boolean, list, dict). Không bao giờ trả về `set`, `tuple`, hoặc đối tượng Python tùy biến. Mọi danh sách trả về đều được sắp xếp tất định.
3. **Không phụ thuộc UI Desktop**: Không import `tkinter`, `view/`, `gui.py`, `cli.py`, `fidelity/`.

---

## 2. Danh mục API

### 2.1. Quản lý Khởi tạo & Kho mẫu

#### `init_runtime() -> str`
- **Mô tả**: Khởi tạo Controller, chuẩn bị môi trường thư mục ảo `/tmp` trong MEMFS.
- **Trả về (JSON)**: `{"status": "ok", "version": "1.0.0", "python_version": "3.14.x"}`

#### `load_bank(gz_base64: str) -> str`
- **Mô tả**: Giải mã base64 của file `.json.gz`, ghi vào `/tmp/current_bank.json.gz` và gọi `controller.load_bank()`.
- **Trả về (JSON)**: Thống kê kho mẫu chi tiết:
  ```json
  {
    "status": "ok",
    "schema_version": 4,
    "xh": 7.94,
    "words_count": 1450,
    "letters_count": 66,
    "digits_count": 10,
    "punct_count": 12,
    "symbols_count": 8,
    "marks_count": 5,
    "total_samples": 4200,
    "session_scale": 1.0
  }
  ```

#### `export_bank() -> str`
- **Mô tả**: Đọc file `.json.gz` hiện tại trong MEMFS, mã hóa Base64 để JS lưu vào IndexedDB hoặc tải về máy.
- **Trả về (JSON)**: `{"status": "ok", "bank_base64": "<base64_data>"}`

#### `create_empty_bank() -> str`
- **Mô tả**: Tạo một kho mẫu trống chuẩn Schema v4 trong MEMFS và nạp vào Controller.
- **Trả về (JSON)**: Thống kê kho mẫu rỗng.

---

### 2.2. Soạn thảo & Kết xuất chữ viết tay

#### `get_write_defaults() -> str`
- **Mô tả**: Trả về các giá trị mặc định của `WriteOptions` trực tiếp từ lõi Python để frontend hiển thị làm placeholder / giá trị ban đầu, không hard-code trên JS.
- **Trả về (JSON)**:
  ```json
  {
    "scale": 1.0,
    "line": null,
    "width": null,
    "space": 1.0,
    "jitter": 1.0,
    "wscale": 1.0,
    "color": null,
    "seed": null,
    "strict_case": false,
    "paper": "a4",
    "orientation": "portrait",
    "paper_width": null,
    "paper_height": null,
    "margin_left": 36.0,
    "margin_right": 36.0,
    "margin_top": 40.0,
    "margin_bottom": 40.0,
    "background": "plain",
    "background_spacing": null,
    "background_margin": null,
    "background_color": "#ffffffff",
    "assemble_letters": false,
    "letter_gap": 1.0,
    "target_xh": 7.94,
    "auto_xh": false,
    "pen_clearance_factor": 0.8,
    "stable_variants": true
  }
  ```

#### `write_text(request_json: str) -> str`
- **Mô tả**: Nhận văn bản thô hoặc Markdown và các tùy chọn kết xuất, thực hiện dàn trang (xử lý ngắt trang `<!-- pagebreak -->` / `\pagebreak` nếu là markdown), xuất ra file `.xopp` ảo trong MEMFS, và trả về dữ liệu `.xopp` Base64 cùng danh sách từ thiếu mẫu (`missing_sorted`). Frontend JS (module `paper.js`) sẽ trực tiếp giải nén `.xopp` XML và dựng SVG trên trình duyệt (theo quyết định D1).
- **Tham số `request_json`**:
  ```json
  {
    "text": "Nội dung văn bản...",
    "mode": "markdown", // hoặc "plain"
    "options": {
      "scale": 1.0,
      "line": null,
      "width": null,
      "space": 1.0,
      "jitter": 1.0,
      "wscale": 1.0,
      "color": "#1a237e",
      "seed": 42,
      "strict_case": false,
      "paper": "a4",
      "orientation": "portrait",
      "margin_left": 36.0,
      "margin_right": 36.0,
      "margin_top": 40.0,
      "margin_bottom": 40.0,
      "background": "lined",
      "assemble_letters": true,
      "letter_gap": 1.0,
      "target_xh": 7.94,
      "auto_xh": false,
      "pen_clearance_factor": 0.8,
      "stable_variants": true
    }
  }
  ```
- **Trả về (JSON)**:
  ```json
  {
    "status": "ok",
    "xopp_base64": "<base64_data>",
    "total_pages": 2,
    "total_words": 150,
    "total_chars": 820,
    "covered_words_count": 142,
    "missing_sorted": [
      ["blockchain", 5],
      ["quantum", 3]
    ],
    "missing_boxes": [
      {"page": 0, "token": "blockchain", "x": 120.5, "y": 240.0, "w": 45.2, "h": 12.0}
    ],
    "warnings": []
  }
  ```

#### `import_docx(docx_base64: str) -> str`
- **Mô tả**: Tải lười `lxml` + `python-docx` (nếu chưa nạp), nạp file `.docx` sang Document IR và trả về text Markdown đại diện để hiển thị lên trình soạn thảo.
- **Trả về (JSON)**: `{"status": "ok", "markdown_text": "...", "warnings": []}`

---

### 2.3. Vùng vẽ & Dạy mẫu chữ

#### `get_canvas_spec(label: str) -> str`
- **Mô tả**: Cung cấp đặc tả hình học chuẩn cho Canvas vẽ tay. JS TUYỆT ĐỐI KHÔNG tự định nghĩa các hằng số này.
- **Trả về (JSON)**:
  ```json
  {
    "status": "ok",
    "width": 760,
    "height": 230,
    "base_px": 170,
    "zoom": 10.0,
    "min_point_dist": 2.5,
    "xh": 7.94,
    "guidelines": {
      "baseline": 170.0,
      "xh_line": 90.6,
      "hw3_lines": {
        "top": 30.0,
        "mean": 90.6,
        "base": 170.0,
        "bottom": 210.0
      }
    }
  }
  ```

#### `teach_sample(request_json: str) -> str`
- **Mô tả**: Nhận danh sách các nét vẽ pixel logic `[[[x, y], ...]]` từ Canvas JS. Lớp cầu nối gọi hàm quy đổi hình học chuẩn (`strokes_to_bank_units`) rồi route sang `ctl.teach_letter` hoặc `ctl.teach_word`.
- **Tham số `request_json`**:
  ```json
  {
    "label": "bà",
    "pixel_strokes": [[[150, 170], [152, 160], [155, 120]]],
    "is_calibrating": false
  }
  ```
- **Trả về (JSON)**:
  ```json
  {
    "status": "ok",
    "label": "bà",
    "category": "words",
    "sample_index": 3,
    "session_scale": 1.0,
    "recalibrated": false,
    "total_samples": 4
  }
  ```

#### `drop_label(label: str, category: str) -> str`
- **Mô tả**: Xóa toàn bộ nhãn khỏi kho và ghi nhận tombstone an toàn.
- **Trả về (JSON)**: `{"status": "ok", "label": "...", "dropped_count": 3}`

#### `list_label_samples(label: str, category: str) -> str`
- **Mô tả**: Liệt kê tất cả các biến thể mẫu nét của một nhãn cụ thể để hiển thị thư viện so sánh.
- **Trả về (JSON)**: Danh sách các mẫu nét kèm hình thu nhỏ SVG.

---

### 2.4. Trợ giúp & Tra cứu

#### `get_latex_symbols() -> str`
- **Mô tả**: Lấy toàn bộ danh sách ký hiệu LaTeX từ `chuviettay/math/symbols.py`, phân nhóm theo loại (quan hệ, toán tử, chữ cái Hy Lạp, dấu mũi tên, v.v.).
- **Trả về (JSON)**: Cấu trúc từ điển phân nhóm ký hiệu để render bảng bấm chèn.

#### `get_missing_queue(kind: str, limit: int = 50) -> str`
- **Mô tả**: Lấy danh sách từ thông dụng còn thiếu (`missing_seed_words`) hoặc danh mục tối thiểu (`missing_minimal_essentials`).
- **Trả về (JSON)**: `{"status": "ok", "tokens": ["0", "1", "2", "!", "?"]}`
