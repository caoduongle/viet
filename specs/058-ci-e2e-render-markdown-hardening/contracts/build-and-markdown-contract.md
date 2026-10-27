# Contracts: Build Safety, Render Config & Markdown Preprocessing

**Feature**: `058-ci-e2e-render-markdown-hardening`  
**Date**: 2026-10-27

---

## 1. CLI & E2E Build Safety Contract (`scripts/build_web.py` & `tests/e2e/sw-update.spec.ts`)

1. **Bất biến bảo vệ của `prepare_dist_dir(dist_dir: Path, force_clean: bool = False)`**:
   - Nếu `dist_dir.resolve() != DEFAULT_DIST_DIR.resolve()` và thư mục đích đã tồn tại, có chứa ít nhất một mục bên trong (`any(dist_dir.iterdir())`) và `force_clean == False`, hàm **bắt buộc** ném `RuntimeError` và không xóa bất kỳ dữ liệu nào.
2. **Hợp đồng gọi build trong `tests/e2e/sw-update.spec.ts`**:
   - `runBuildWeb(distDir: string, forceClean = false): void`
   - Lần build khởi tạo trên thư mục tạm mới tạo `tmpDist`: gọi `runBuildWeb(tmpDist)` (`forceClean = false`).
   - Lần build cập nhật thứ hai trên cùng thư mục tạm `tmpDist`: gọi `runBuildWeb(tmpDist, true)` (`forceClean = true`).

---

## 2. Render & CI Python Version Contract (`.python-version` & `render.yaml`)

1. **Tệp `.python-version`**:
   - Tồn tại ở thư mục gốc của dự án và có giá trị sau khi strip khớp chính xác `3.13` (định dạng `^\d+\.\d+$`).
2. **Tệp `render.yaml`**:
   - Không được khai báo biến môi trường `PYTHON_VERSION` mang giá trị rút gọn `Major.Minor` (vì Render yêu cầu biến môi trường `PYTHON_VERSION` phải là bản đầy đủ `Major.Minor.Patch`, trong khi `.python-version` hỗ trợ `Major.Minor`).
   - Mặc định chuẩn của dự án: Không khai báo `PYTHON_VERSION` trong `render.yaml` để ủy quyền hoàn toàn cho tệp `.python-version`.

---

## 3. Markdown Importer Preprocessing Contract (`chuviettay/importer/markdown_importer.py`)

1. **Bảo toàn khối mã thụt lề (Indented Code Block)**:
   - Mọi khối mã thụt lề hợp lệ theo CommonMark 4.4 (bắt đầu sau dòng trống hoặc đầu văn bản, thụt $\ge 4$ khoảng trắng hoặc `\t`) phải được bảo toàn nguyên vẹn từng ký tự qua cả 3 bước:
     - `_normalize_math_delimiters(text)`
     - `_isolate_display_math_blocks(seg)`
     - `_sanitize_html(text)`
   - Kể cả khi bên trong khối mã thụt lề có chứa `prefix:$$x=1$$`, `$$y=2$$`, `\[z=3\]`, `\(w=4\)`, hoặc các chuỗi giống thẻ HTML như `<b>tag</b>`, `<script>alert(1)</script>`, nội dung không bị biến đổi và không sinh `MathBlock` giả.
   - Dòng thụt lề $\ge 4$ khoảng trắng nằm ngay sau một dòng văn bản thường (không có dòng trống ngăn cách — lazy paragraph continuation) không phải là khối mã thụt lề.

2. **Nhận diện ngữ cảnh bảng GFM**:
   - Chỉ đánh dấu các dòng thuộc bảng GFM khi có dòng tiêu đề `h` đứng ngay trước dòng phân cách `d` (`h = d - 1`), cả hai dòng có cùng số lượng cột ($C_{\text{header}} == C_{\text{delim}} \ge 1$), và theo sau bởi các dòng dữ liệu liên tiếp chứa ký tự `|` phân cách cột bên ngoài công thức/code span.
   - Đoạn văn chứa ký tự `|` và công thức `$$...$$` đứng trước dòng tiêu đề `h` (trong cùng nhóm dòng không trống) hoặc đứng trước một dòng giả phân cách không khớp số cột vẫn được tách thành `MathBlock` như văn bản thường.

3. **Bảo toàn kết quả & Độ phức tạp tuyến tính $O(n)$**:
   - `_split_code_segments(text)` và `_find_code_spans(text)` không cắt lát phần đuôi chuỗi `text[i:]` ở mỗi đầu dòng và không quét lặp lại bậc hai trên các dấu backtick mở không có dấu đóng.
   - Khi kích thước đầu vào bất lợi tăng gấp 4 lần ($N \to 4N$), thời gian thực thi tiền xử lý tăng không quá 6 lần ($T(4N) / T(N) \le 6.0$).
