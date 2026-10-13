# Research & Technical Decisions: Củng cố và xử lý các vấn đề sau rà soát bản Web-only

**Branch**: `039-post-review-hardening` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

Tài liệu này tổng hợp các nghiên cứu kiến trúc, phân tích kỹ thuật và quyết định thiết kế nhằm xử lý triệt để 5 nhóm vấn đề được ghi nhận trong đợt rà soát commit `46467eb`.

---

## 1. Quyết định phạm vi DOCX: Web Content-First vs. Fidelity Layout (Q1: Option A)

### Bối cảnh hiện tại
- Trong các phiên bản Desktop trước đây, `chuviettay/fidelity/` cung cấp khả năng giữ nguyên bố cục Word bằng cách gọi Microsoft Word COM (PowerShell trên Windows) hoặc LibreOffice (`soffice` subprocess trên Linux/macOS) để trích xuất tọa độ bounding box (`SpatialTextExtractor`) và tạo PDF nền che chữ (`WhiteoutBackgroundGenerator`).
- Khi loại bỏ Desktop GUI/CLI ở commit `46467eb`, Web Client chạy hoàn toàn trong trình duyệt thông qua Pyodide/WebAssembly. Trong sandbox trình duyệt, việc thực thi lệnh hệ thống `subprocess` hoặc tương tác Windows COM là bất khả thi về mặt kỹ thuật.
- Script `scripts/build_web.py` đã loại bỏ `chuviettay/fidelity/` khỏi gói phân phối `chuviettay.zip`. Giao diện Web nhập tệp DOCX thông qua `BrowserBridge.import_docx()`, chuyển đổi các đoạn văn, tiêu đề, công thức và bảng thành cú pháp Markdown để đưa vào khung soạn thảo.
- Điểm bất cập: Tài liệu `README.md` vẫn mô tả module `fidelity/` là *"sẵn sàng để tích hợp lên Web"*, và giao diện Web chưa thông báo minh bạch rằng việc mở DOCX là nhập nội dung (Content-First) chứ không phải giữ nguyên tọa độ trang in (Fidelity Layout).

### Quyết định kỹ thuật
- **Quyết định**: Xác định rõ ràng phạm vi Web Client là **Content-First Import**.
  1. Cập nhật giao diện Web (`webapp/index.html` và `webapp/js/write.js`) khi người dùng tải tệp DOCX: hiển thị nhãn/tooltip rõ ràng rằng tệp được chuyển đổi cấu trúc (văn bản, bảng, công thức) sang Markdown để viết tay theo khổ giấy của ứng dụng; không áp dụng bố cục in Word cũ.
  2. Cập nhật `README.md`: loại bỏ cam kết gây hiểu lầm về việc đưa Fidelity Engine lên Web Client tĩnh. Ghi rõ `chuviettay/fidelity/` là thành phần lưu trữ (legacy/archive) của phiên bản Desktop cũ.
  3. Thêm tài liệu cảnh báo trong `chuviettay/fidelity/__init__.py` đánh dấu module là legacy code, chỉ chạy trên môi trường có Word COM / LibreOffice cục bộ và không thuộc phạm vi Web Client.
- **Lý do**:
  - Giữ vững nguyên tắc cốt lõi của dự án: Static Web App thuần túy, Zero Backend, Zero Server Cost, bảo mật tối đa cho dữ liệu người dùng (không gửi tài liệu DOCX lên bất kỳ máy chủ nào).
  - Loại bỏ hoàn toàn kỳ vọng sai lệch của người dùng về việc giữ nguyên 100% tọa độ trang Word.
- **Các phương án thay thế đã loại bỏ**:
  - *Viết lại bộ trích xuất tọa độ Word thuần JavaScript/Python trong Pyodide*: Rất phức tạp (DOCX không lưu tọa độ pixel cố định; Word dùng bộ dựng hình độc quyền DirectWrite để dàn trang), khối lượng công việc khổng lồ và không khả thi trong phạm vi hiện tại.
  - *Xây dựng máy chủ backend phụ trợ*: Vi phạm triết lý Static Web App không phụ thuộc máy chủ.

---

## 2. Chuẩn hóa Khóa RNG Hình học nét (`ScopedRNG`) theo `token_id` và Loại Nội dung (P2)

### Bối cảnh hiện tại
- Trong `chuviettay/layout/engine.py`, hàm `_render_text_line()` (dòng 244-246) đang lấy khóa cho RNG hình học như sau:
  ```python
  tok_str = item[4] if len(item) > 4 else ""
  occ = item[6] if len(item) > 6 else 0
  geom_rng = ScopedRNG(self.effective_seed, "tok", tok_str, occ, "geom")
  ```
- Nhược điểm:
  1. `item[5]` (`token_id`) đã được tạo trong `RenderItem` nhưng không được dùng làm khóa chính.
  2. Bộ đếm `block_token_counts` được khởi tạo lại thành rỗng `{}` ở mỗi lần gọi `_layout_inlines()`. Do đó, từ "ngày" ở Đoạn văn 1 có `occ=0`, và từ "ngày" ở Đoạn văn 2 cũng có `occ=0`. Cả hai từ dùng chung khóa `(effective_seed, "tok", "ngày", 0, "geom")` -> dẫn đến biến dạng jitter (scale, rotation, dy) giống hệt nhau.
  3. Một ký hiệu toán học hoặc dấu câu đứng riêng (ví dụ `+`) có `tok_str="+"`, `occ=0`, có thể trùng khóa với từ văn bản hoặc công thức toán có cùng chuỗi ký tự.

### Quyết định kỹ thuật
- **Quyết định**:
  1. **Tạo không gian tên khóa có tiền tố loại nội dung**:
     - Token văn bản thường: `token_id = f"text:{chunk}#{occ}"`
     - Ký hiệu đơn lẻ: `token_id = f"sym:{sym}#{occ}"`
     - Ô bảng: `token_id = f"cell:{r}_{c}:{chunk}#{occ}"`
  2. **Quản lý bộ đếm occurrence theo phiên xử lý khối/tài liệu**:
     - Cho phép truyền ngữ cảnh định danh khối hoặc duy trì bộ đếm token tích lũy xuyên suốt các khối văn bản của tài liệu, hoặc sử dụng định danh khối/ô (`block_id`) trong `token_id`.
  3. **Cập nhật `_render_text_line()`**:
     - Sử dụng trực tiếp `token_id` (tại `item.token_id` hoặc `item[5]`):
       ```python
       tid = item.token_id if hasattr(item, "token_id") and item.token_id else (item[5] if len(item) > 5 and item[5] else f"tok:{item[4]}#{item[6]}")
       geom_rng = ScopedRNG(self.effective_seed, "geom", tid)
       ```
- **Lý do**:
  - `ScopedRNG` băm toàn bộ payload thông qua tuple `(self.effective_seed, "geom", tid)`. Khi `tid` có tiền tố `"text:"`, `"sym:"`, `"cell:0_1:"`, việc va chạm giữa các loại phần tử khác nhau được triệt tiêu 100%.
  - Bảo đảm nguyên tắc Prepend Invariance: việc thêm từ ở đầu đoạn không làm thay đổi `token_id` của các từ không trùng chuỗi ở đoạn sau.
- **Các phương án thay thế đã loại bỏ**:
  - *Dùng tọa độ dòng (X, Y) làm khóa*: Không thể áp dụng vì khi thêm từ ở đầu tài liệu, các dòng sau bị đẩy xuống (thay đổi Y), phá vỡ hoàn toàn Prepend Invariance.

---

## 3. Khắc phục Biến thể Đơn điệu của Công thức Toán học Trùng lặp (P2)

### Bối cảnh hiện tại
- Trong `chuviettay/layout/engine.py`:
  - Dòng 374: `math_seed = ScopedRNG(self.effective_seed, "math", inline.latex).seed`
  - Dòng 604: `math_seed = ScopedRNG(self.effective_seed, "math", block.latex).seed`
- Khi tài liệu có 2 công thức giống nhau (ví dụ $x + 1$ ở dòng 5 và $x + 1$ ở dòng 20), cả hai đều dùng chung hạt giống `math_seed` dẫn xuất từ `(self.effective_seed, "math", "$x + 1$")`. Do đó, cả hai công thức được viết tay bởi 2 Writer độc lập nhưng có hạt giống giống hệt nhau, tạo ra các nét viết hoàn toàn trùng lặp từng điểm.

### Quyết định kỹ thuật
- **Quyết định**: Đưa bộ đếm lần xuất hiện của biểu thức toán học vào ngữ cảnh băm hạt giống:
  1. Trong `DocumentLayoutEngine`, duy trì từ điển đếm số lần xuất hiện của từng biểu thức LaTeX: `math_inline_counts: dict[str, int]` và `math_block_counts: dict[str, int]`.
  2. Khi gặp `MathInline`:
     ```python
     occ = self._math_inline_counts.get(inline.latex, 0)
     self._math_inline_counts[inline.latex] = occ + 1
     math_seed = ScopedRNG(self.effective_seed, "math", inline.latex, occ).seed
     ```
  3. Khi gặp `MathBlock`:
     ```python
     occ = self._math_block_counts.get(block.latex, 0)
     self._math_block_counts[block.latex] = occ + 1
     math_seed = ScopedRNG(self.effective_seed, "math_block", block.latex, occ).seed
     ```
- **Lý do**:
  - Lần xuất hiện đầu tiên của `$x + 1$` dùng `(effective_seed, "math", "$x + 1$", 0)`.
  - Lần xuất hiện thứ hai của `$x + 1$` dùng `(effective_seed, "math", "$x + 1$", 1)`.
  - Hai công thức có hạt giống hoàn toàn khác nhau, sinh ra các nét viết tự nhiên đa dạng, không trùng lặp.
  - Vẫn giữ nguyên tính bất biến Prepend Invariance: nếu người dùng chèn thêm văn bản thường hoặc chèn một công thức khác (ví dụ `$y = 2$`), thứ tự xuất hiện của các công thức `$x + 1$` không đổi, nên hạt giống của chúng giữ nguyên.

---

## 4. Đồng bộ hóa Metadata Phiên bản Toàn diện (Q2: Option A)

### Bối cảnh hiện tại
- Các tệp cấu hình hiện tại đang khai báo số phiên bản không đồng nhất:
  - `CHANGELOG.md`: `2.1.0`
  - `chuviettay/__init__.py`: `__version__ = "2.1.0"`
  - `pyproject.toml`: `version = "2.0.0"`
  - `package.json`: `"version": "1.0.0"`
  - `scripts/build_web.py`: dòng 269 hardcode `"version": "1.0.0"` khi sinh `version.json`.

### Quyết định kỹ thuật
- **Quyết định**: Đồng bộ hóa toàn bộ sản phẩm về một phiên bản ngữ nghĩa duy nhất: **`2.1.0`**.
  1. Nâng `pyproject.toml` lên `version = "2.1.0"`.
  2. Nâng `package.json` lên `"version": "2.1.0"`.
  3. Cập nhật hàm `generate_version_json()` trong `scripts/build_web.py` để tự động đọc phiên bản chuẩn từ `chuviettay.__version__` (hoặc `pyproject.toml`) thay vì hardcode chuỗi `"1.0.0"`.
  4. Bổ sung bài kiểm thử tự động `tests/test_version_metadata.py` kiểm tra đối chiếu:
     - `chuviettay.__version__ == pyproject.toml version`
     - `chuviettay.__version__ == package.json version`
     - Tiêu đề mới nhất trong `CHANGELOG.md` chứa `chuviettay.__version__`
     - Khi chạy `build_web.py`, tệp `dist/version.json` có trường `"version"` khớp với `chuviettay.__version__`.

---

## 5. Củng cố Hợp đồng Dữ liệu `RenderItem` (Hỗ trợ Slice Indexing)

### Bối cảnh hiện tại
- Lớp `RenderItem` trong `chuviettay/layout/engine.py` có phương thức `__getitem__(self, idx: int)`:
  - Chỉ kiểm tra `idx == 0 ... 6`, ném `IndexError` nếu `idx` không phải số nguyên trong khoảng.
  - Docstring ghi: *"Hỗ trợ giải nén tuple (unpacking: start, st, w = item[:3] hoặc a, b, c, d, e = item)"*.
  - Tuy nhiên, cú pháp `item[:3]` truyền đối tượng `slice(None, 3, None)` vào `__getitem__`, gây lỗi `IndexError` lúc chạy.
  - Các bài kiểm thử trước đây dùng `tuple(item)[:3]` nên chưa kiểm tra trực tiếp biểu thức `item[:3]`.

### Quyết định kỹ thuật
- **Quyết định**: Cập nhật `RenderItem.__getitem__()` để hỗ trợ đầy đủ đối tượng `slice` và chỉ số âm:
  ```python
  def __getitem__(self, idx: int | slice) -> Any:
      """Hỗ trợ truy cập chỉ số kiểu tuple và slice để tương thích 100% với mã nguồn cũ."""
      if isinstance(idx, slice):
          return tuple(self)[idx]
      if idx < 0:
          return tuple(self)[idx]
      if idx == 0:
          return self.start
      if idx == 1:
          return self.strokes
      if idx == 2:
          return self.width
      if idx == 3:
          return self.missing
      if idx == 4:
          return self.token
      if idx == 5:
          return self.token_id
      if idx == 6:
          return self.occurrence
      raise IndexError(f"Chỉ số RenderItem không hợp lệ: {idx}")
  ```
- **Lý do**: Phương thức `__iter__` của `RenderItem` đã sinh đầy đủ 7 trường dữ liệu. Việc ủy quyền cho `tuple(self)[idx]` khi gặp `slice` hoặc số âm vừa ngắn gọn, chuẩn xác theo quy ước Python, vừa không phát sinh chi phí tính toán khi truy cập số nguyên dương thông thường.
- Bổ sung bài kiểm thử đơn vị trong `tests/test_render_item.py` kiểm tra trực tiếp `item[:3]`, `item[1:4]`, `item[-1]`.

---

## 6. Tổng kết Ma trận Quyết định

| Vấn đề | Quyết định đã chọn | Tác động mã nguồn |
|---|---|---|
| **DOCX Fidelity vs Web** | Web Content-First Import, UI/README minh bạch, archive module fidelity | `webapp/index.html`, `webapp/js/write.js`, `README.md`, `chuviettay/fidelity/__init__.py` |
| **RNG Keying** | Thêm tiền tố loại nội dung vào `token_id`, dùng `token_id` làm khóa trong `_render_text_line` | `chuviettay/layout/engine.py` |
| **Công thức toán trùng lặp** | Đưa bộ đếm lần xuất hiện `occ` vào khóa băm `ScopedRNG` của toán học | `chuviettay/layout/engine.py` |
| **Đồng bộ phiên bản** | Thống nhất `2.1.0` trên toàn bộ dự án, cập nhật `build_web.py`, thêm test metadata | `pyproject.toml`, `package.json`, `scripts/build_web.py`, `tests/test_version_metadata.py` |
| **RenderItem Slice** | Hỗ trợ `isinstance(idx, slice)` và chỉ số âm trong `__getitem__` | `chuviettay/layout/engine.py`, `tests/test_render_item.py` |
