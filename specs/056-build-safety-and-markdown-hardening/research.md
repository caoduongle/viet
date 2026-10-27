# Phase 0 Research: External Build Safety, CommonMark Nested Code & Contextual GFM Tables

**Feature**: `056-build-safety-and-markdown-hardening`  
**Date**: 2026-10-23  
**Status**: Completed  

---

## 1. Nghiên cứu & Quyết định Kiến trúc

### Nghiên cứu 1: An toàn Tuyệt đối cho Thư mục Build Ngoài Repo (`prepare_dist_dir`)

- **Vấn đề thực tế**:
  - `prepare_dist_dir()` cho phép `shutil.rmtree(resolved_dist)` khi `has_marker` là `True` (tệp `.chuviettay_build_dist` tồn tại).
  - Nếu người dùng từng chỉ định `--dist /path/to/my_folder --force-clean`, sau đó người dùng thêm các tệp tài liệu riêng vào `my_folder`, rồi chạy lại lệnh build không kèm `--force-clean`, marker cũ khiến toàn bộ thư mục bị xóa sạch, làm mất dữ liệu người dùng.
- **Quyết định thiết kế**:
  - Thư mục mặc định `webapp/dist` là thư mục nội bộ thuần túy của dự án, được phép tự động làm sạch.
  - Đối với MỌI thư mục ngoài `webapp/dist`:
    - Nếu thư mục rỗng (`not any(resolved_dist.iterdir())`): cho phép ghi trực tiếp.
    - Nếu thư mục KHÔNG rỗng: BẮT BUỘC phải có cờ `--force-clean` tại chính lần chạy đó. Nếu không có `--force-clean`, script dừng ngay lập tức với lỗi `SystemExit` bảo vệ an toàn.
    - Sự tồn tại của marker nội bộ cũ KHÔNG BAO GIỜ được coi là quyền xóa dữ liệu người dùng.
  - Loại bỏ hoàn toàn việc sinh marker `.chuviettay_build_dist` vào thư mục xuất xưởng `dist_dir`. Thư mục `dist` thành phẩm hoàn toàn sạch sẽ, không có bất kỳ tệp nội bộ nào.
- **Lựa chọn thay thế đã xem xét**:
  - Dùng manifest tệp để xóa từng tệp: Bị từ chối vì nếu người dùng ghi đè hoặc hoán đổi tệp trùng tên, việc xóa một phần có thể để lại trạng thái thư mục nửa vời không nhất quán. Yêu cầu `--force-clean` tường minh là giải pháp an toàn, minh bạch và dứt khoát nhất.

---

### Nghiên cứu 2: Bảo vệ Khối mã CommonMark trong Blockquote, Indented Code và Escaped Backtick

- **Vấn đề thực tế**:
  1. Khối mã fence lồng trong blockquote (`> ~~~latex\n> \\[x=1\\]\n> ~~~`): Dòng bắt đầu bằng ký tự `>`, regex đầu dòng trước đó bỏ qua khiến `\[x=1\]` bị chuyển đổi thành `$$x=1$$`.
  2. Khối mã thụt lề 4 khoảng trắng (Indented Code Block) theo CommonMark chưa được bảo vệ.
  3. Dấu backtick bị thoát bởi dấu gạch ngược (`\``) bị nhận nhầm là dấu phân cách inline code.
- **Quyết định thiết kế**:
  - Cải tiến bộ tách mã một lượt `_split_code_segments(text: str)`:
    - Nhận diện tiền tố blockquote `^[ ]{0,3}(>[ ]?)+` ở đầu dòng. Nếu có tiền tố blockquote, kiểm tra code fence ngay sau tiền tố đó. Khối mã blockquote được theo dõi và chỉ đóng khi gặp dòng đóng có cùng tiền tố trích dẫn và $M \ge K$ ký tự phân cách tương ứng.
    - Nhận diện Indented Code Block: các dòng liên tiếp có thụt lề $\ge 4$ spaces (hoặc tab) ở cấp độ gốc (không có tiền tố trích dẫn) được đánh dấu là `is_code = True`.
    - Nhận diện Escaped Backtick: kiểm tra số lượng dấu `\` đứng liền trước. Nếu là số lẻ (1, 3, ...), backtick là ký tự dữ liệu thoát, không mở hoặc đóng inline code span.
- **Lựa chọn thay thế đã xem xét**:
  - Chờ thư viện `markdown-it` phân tích block trước: Bị từ chối vì `markdown-it` CommonMark nuốt dấu `\` trong `\[` và `\(` trước khi plugin toán học hoạt động, do đó bước tiền xử lý chuẩn hóa công thức là bắt buộc phải chạy trước.

---

### Nghiên cứu 3: Nhận diện Ngữ cảnh Bảng GFM Chặt chẽ và Bảo toàn Giá trị Ô

- **Vấn đề thực tế**:
  - Hàm `_is_table_line()` trước đây coi bất kỳ dòng nào chứa `|` ngoài math là hàng bảng. Một dòng đơn độc lập `$$x=1$$ | 2` bị bỏ qua bước tách math display, khiến nó thành văn bản nội tuyến trong đoạn văn thay vì một `MathBlock`.
- **Quyết định thiết kế**:
  - Một dòng chỉ được coi là hàng bảng khi nó nằm trong một khối bảng GFM hợp lệ. Khối bảng hợp lệ là một nhóm các dòng liên tiếp không rỗng có chứa ít nhất một hàng phân cách cột (`---|---`, `:---:|:---:`).
  - Thuật toán tiền quét (pre-scan) xác định tập hợp các chỉ số dòng `table_line_indices` thuộc về khối bảng có hàng phân cách.
  - Khi phân tách công thức display: chỉ các dòng thuộc `table_line_indices` mới được xem là hàng bảng. Dòng đơn lẻ `$$x=1$$ | 2` không có hàng phân cách sẽ được phân tách thành `MathBlock` và `Paragraph` bình thường.
  - Bổ sung kiểm thử xác nhận chi tiết từng ô trong Document IR của bảng compact (ô 1 là Math, ô 2 là Text("2")).
- **Lựa chọn thay thế đã xem xét**:
  - Chỉ kiểm tra dòng liền trước: Bị từ chối vì hàng tiêu đề của bảng compact nằm trước dòng phân cách, cần kiểm tra toàn bộ khối liên tục.

---

### Nghiên cứu 4: Làm sạch Thư mục Xuất xưởng và Lọc Thư mục Ẩn trong Service Worker

- **Vấn đề thực tế**:
  - `.chuviettay_build_dist` không được phép tồn tại trong thư mục phân phối `webapp/dist`.
  - Vòng lặp `os.walk(dist_dir)` chưa loại trừ thư mục ẩn in-place (`dirs[:] = [...]`), có nguy cơ duyệt vào `.internal/` hoặc `.git/`.
- **Quyết định thiết kế**:
  - Bỏ hoàn toàn việc tạo `.chuviettay_build_dist` trong `prepare_dist_dir`.
  - Trong `generate_sw_js`: cập nhật `dirs[:] = [d for d in dirs if not d.startswith(".")]`.
- **Lựa chọn thay thế đã xem xét**:
  - Xóa marker ở cuối script: Không cần thiết vì ta đã loại bỏ sự phụ thuộc vào marker ở Nghiên cứu 1.

---

## 2. Kết luận Nghiên cứu

Tất cả các giải pháp kỹ thuật đã được nguyên mẫu hóa và kiểm chứng thành công. Không có điểm nào cần làm rõ thêm (`NEEDS CLARIFICATION: 0`). Đủ điều kiện chuyển sang Phase 1.
