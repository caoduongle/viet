# Data Model & Entity Specifications: Post-Review Hardening

**Branch**: `039-post-review-hardening` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

Tài liệu này mô tả chi tiết các thực thể dữ liệu, cấu trúc khóa băm và hợp đồng trường dữ liệu phục vụ việc củng cố hệ thống sau rà soát.

---

## 1. Thực thể `RenderItem` (Hiển thị & Bố cục dòng)

`RenderItem` là cấu trúc dữ liệu mang thông tin của một mục hiển thị trên dòng chữ hoặc trong ô bảng.

### Cấu trúc trường dữ liệu
```python
@dataclass(slots=True)
class RenderItem:
    start: float                          # Vị trí X tương đối trong dòng (điểm bắt đầu vẽ)
    strokes: list[Stroke]                 # Danh sách các nét chữ (mỗi Stroke là list các điểm (x, y))
    width: float                          # Chiều rộng hiển thị của mục (đã nhân hệ số co giãn)
    missing: list[str] = field(default_factory=list)  # Danh sách ký tự thiếu mẫu
    token: str = ""                       # Chuỗi ký tự gốc (ví dụ: "chữ", "+", "E=mc^2")
    token_id: str = ""                    # Định danh duy nhất kèm phân loại nội dung (ví dụ: "text:chữ#0")
    occurrence: int = 0                   # Thứ tự xuất hiện trong phạm vi ngữ cảnh
```

### Hợp đồng Sequence & Indexing
- **Giải nén tuần tự (`__iter__`)**: Sinh lần lượt 7 giá trị theo thứ tự:
  `[start, strokes, width, missing, token, token_id, occurrence]`.
- **Độ dài (`__len__`)**: Luôn trả về giá trị `7`.
- **Truy cập chỉ số nguyên (`item[i]`)**:
  - `item[0]`: `start`
  - `item[1]`: `strokes`
  - `item[2]`: `width`
  - `item[3]`: `missing`
  - `item[4]`: `token`
  - `item[5]`: `token_id`
  - `item[6]`: `occurrence`
  - `item[-1]`: `occurrence` (hỗ trợ chỉ số âm)
  - `i >= 7` hoặc `i < -7`: ném ngoại lệ `IndexError`.
- **Cắt lát (`item[start:stop:step]`)**:
  - Trả về tuple con các phần tử tương ứng: `tuple(self)[idx]`.
  - Ví dụ: `item[:3]` trả về `(start, strokes, width)`.
  - `item[1:4]` trả về `(strokes, width, missing)`.

---

## 2. Quy ước Không gian Tên Khóa Ngẫu nhiên (`ScopedRNG Payload Schema`)

Hệ thống dẫn xuất hạt giống và bộ sinh ngẫu nhiên `ScopedRNG` sử dụng các tuple phân cấp rõ ràng để ngăn chặn triệt để hiện tượng va chạm giữa các thành phần khác bản chất:

### 2.1 Khóa Hình học Nét chữ (`geom_rng`)
- **Mục đích**: Tính toán các biến dạng vi mô của nét viết (độ co giãn `s`, độ nghiêng `rot`, độ lệch dọc `dy`, biến thiên độ dày nét `wscale_mult`) trong hàm `_render_text_line()`.
- **Cấu trúc Payload**: `(effective_seed, "geom", token_id)`
- **Định dạng `token_id` theo loại đối tượng**:
  | Loại nội dung | Định dạng `token_id` | Ví dụ |
  |---|---|---|
  | **Văn bản thường** | `text:<chunk>#<occ>` | `text:nghiên#0`, `text:cứu#0` |
  | **Ký hiệu đơn lẻ** | `sym:<symbol>#<occ>` | `sym:+#0`, `sym:α#0` |
  | **Ô bảng** | `cell:<row>_<col>:<chunk>#<occ>` | `cell:0_1:tên#0`, `cell:1_1:Lê#0` |
  | **Toán học inline** | `math_tok:<chunk>#<occ>` | `math_tok:x#0`, `math_tok:+#0` |

### 2.2 Khóa Hạt giống Biểu thức Toán học (`math_seed`)
- **Mục đích**: Cấp phát hạt giống độc lập cho từng công thức toán học, đảm bảo công thức lặp lại có nét tự nhiên khác nhau.
- **Cấu trúc Payload**:
  - **Công thức Inline**: `(effective_seed, "math", latex_str, occurrence)`
  - **Công thức Display Block**: `(effective_seed, "math_block", latex_str, occurrence)`
- **Quy tắc bộ đếm**:
  - `occurrence` bắt đầu từ `0` cho lần xuất hiện đầu tiên của chuỗi `latex_str`.
  - Mỗi lần lặp lại của cùng chuỗi `latex_str` trong tài liệu sẽ tăng `occurrence` lên `1`.

---

## 3. Thực thể Metadata Phiên bản (`ReleaseMetadata`)

Mô hình cấu trúc phiên bản sản phẩm thống nhất toàn diện:

### Cấu trúc dữ liệu
```json
{
  "version": "2.1.0",
  "name": "chuviettay-web",
  "single_source_of_truth": "chuviettay/__init__.__version__",
  "files": {
    "python_package": "chuviettay/__init__.py",
    "pyproject_toml": "pyproject.toml",
    "package_json": "package.json",
    "changelog": "CHANGELOG.md",
    "dist_version_json": "webapp/dist/version.json"
  }
}
```

### Quy tắc bất biến (Invariants)
1. Số phiên bản trên tất cả các tệp phải là chuỗi SemVer hợp lệ `MAJOR.MINOR.PATCH` và bằng chính xác `"2.1.0"`.
2. Hàm `build_web.py::generate_version_json()` không được phép hardcode phiên bản mà phải nạp động từ `chuviettay.__version__`.
3. Kiểm thử `tests/test_version_metadata.py` đóng vai trò là Quality Gate tự động bắt buộc trong CI.

---

## 4. Thực thể Báo cáo Nhập DOCX (`DocxImportState`)

Mô tả trạng thái và hợp đồng dữ liệu khi Web Client xử lý tệp DOCX:

### Cấu trúc dữ liệu
```typescript
interface DocxImportResult {
  markdown_text: string;     // Toàn bộ nội dung trích xuất dạng Markdown
  n_paragraphs: number;      // Số đoạn văn bản
  n_tables: number;          // Số bảng biểu trích xuất
  n_equations: number;       // Số công thức toán học trích xuất
  warnings: string[];        // Các cảnh báo về thành phần giản lược (ví dụ: SmartArt, WordArt)
  fidelity_notice: string;   // Thông báo: "Chế độ nhập nội dung sang Markdown (không giữ nguyên toạ độ in Word)"
}
```
