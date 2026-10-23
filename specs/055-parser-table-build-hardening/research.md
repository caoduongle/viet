# Phase 0 Research: CommonMark Code Protection, GFM Compact Tables, Build Marker Exclusion, and Resilient Scalability Testing

**Feature**: `055-parser-table-build-hardening`  
**Date**: 2026-10-23  
**Status**: Completed  

---

## 1. Nghiên cứu & Quyết định Kiến trúc

### Nghiên cứu 1: Bảo vệ Khối mã (Code Fence) và Đoạn mã (Code Span) theo Chuẩn CommonMark

- **Vấn đề thực tế**:
  1. Biểu thức chính quy `_CODE_SEGMENT = re.compile(r"(`{3,}.*?(?:`{3,}|\Z)|~{3,}.*?(?:~{3,}|\Z)|`[^`\n]*`)", re.DOTALL)` sử dụng `.*?` không tham lam nối tới `(?:`{3,}|\Z)`. Khi gặp khối mã mở bằng 4 backticks ```` ```` ```` chứa một dòng bên trong có 3 backticks ```` ``` ````, regex nhận nhầm dòng 3 backticks là dấu đóng fence. Phần còn lại của khối mã (ví dụ `\[x=1\]`) rơi vào vùng văn bản thường và bị `_convert_delimited` chuyển đổi thành `$$x=1$$`.
  2. Hàm `_is_inside_code_span()` trong `_isolate_display_math_blocks` chỉ kiểm tra mẫu backtick đơn `` `[^`\n]*` ``, bỏ sót các đoạn mã nội tuyến đa ký tự backtick như ```` ``prefix:$$x=1$$`` ````.
  3. `_sanitize_html` cũng sử dụng regex `_CODE_SEGMENT` cũ.

- **Quyết định thiết kế**:
  - Xây dựng một bộ phân tích tách đoạn mã chuẩn CommonMark: `split_code_segments(text: str) -> list[tuple[str, bool]]` (hoặc `find_code_spans(text: str) -> list[tuple[int, int]]`).
  - **Quy tắc Code Fence**:
    - Dòng mở: 0-3 khoảng trắng, theo sau bởi $K \ge 3$ ký tự backtick (`` ` ``) hoặc tilde (`~`). Ghi nhận ký tự phân cách `char` và độ dài mở `k`.
    - Dòng đóng: 0-3 khoảng trắng, theo sau bởi $M \ge K$ ký tự `char` giống ký tự mở, chỉ kèm khoảng trắng phía sau. Bất kỳ dòng nào có ít hơn $K$ ký tự phân cách đều là nội dung bên trong khối mã.
    - Nếu đến cuối tài liệu (EOF) mà chưa gặp dòng đóng hợp lệ, toàn bộ phần còn lại thuộc về khối mã (unclosed fence).
  - **Quy tắc Code Span**:
    - Chuỗi $N \ge 1$ ký tự backtick liên tiếp mở một code span.
    - Code span chỉ đóng khi gặp chuỗi đúng $N$ ký tự backtick liên tiếp (không phải $N-1$ hay $N+1$).
    - Bất kỳ ký tự nào nằm giữa (kể cả ký tự toán `$$`, `\[`, `$`, `\(`) đều được coi là chuỗi ký tự nguyên bản.
  - Sử dụng hàm tách này đồng nhất trong cả `_normalize_math_delimiters()`, `_isolate_display_math_blocks()` và `_sanitize_html()`.
- **Lựa chọn thay thế đã xem xét**:
  - Dùng regex phức tạp hơn: Bị từ chối vì regex trong Python không hỗ trợ đếm số lượng ký tự backtick đóng khớp chính xác hoặc lớn hơn số lượng mở một cách linh hoạt mà không bị bùng nổ backtrack hoặc giới hạn số lượng backtick cố định. Bộ phân tích scanner một lượt hoàn toàn xác định, dễ đọc, dễ kiểm thử và đạt hiệu năng $O(n)$.

---

### Nghiên cứu 2: Bảo tồn Hàng Bảng GFM Compact Chứa Công Thức Toán

- **Vấn đề thực tế**:
  - Cú pháp GFM cho phép bảng không có thanh đứng ở hai biên ngoài:
    ```markdown
    Col | Val
    ---|---
    $$x=1$$ | 2
    ```
  - Trong `_isolate_display_math_blocks`, điều kiện:
    `if "|" in line and not stripped.startswith("$$"): continue`
    khiến dòng bắt đầu bằng `$$x=1$$` bị loại khỏi diện bảng, rơi vào nhánh phân tách toán và bị chia tách thành:
    ```markdown
    $$x=1$$

    | 2
    ```
    làm phá hủy hoàn toàn cấu trúc bảng.
  - Ngược lại, nếu chỉ kiểm tra `"|" in line`, thì dòng công thức chứa toán tử trị tuyệt đối hoặc định thức như `$$\int |x| dx = 1$$` có thể bị nhận nhầm là hàng bảng nếu không xử lý cẩn trọng.

- **Quyết định thiết kế**:
  - Nhận diện một dòng là hàng bảng khi dòng đó chứa ký tự phân cách cột `|` nằm **BÊN NGOÀI** các khối/đoạn công thức toán hoàn chỉnh và ngoài code span.
  - Cụ thể: Khi kiểm tra một dòng có chứa `|`:
    1. Nếu dòng đang trong trạng thái `in_display_math` nhiều dòng: đã được bảo vệ bởi nhánh C.
    2. Đối với dòng độc lập: Nếu ta ẩn/bỏ qua các cặp công thức hoàn chỉnh (`\$\$.*?\$\$` và `\$[^\s$].*?\$`) và các code span:
       - Nếu phần còn lại của dòng VẪN CHỨA ký tự `|` (không bị thoát `\|`): Dòng này chắc chắn chứa ký tự phân cách cột của bảng (ví dụ: `$$x=1$$ | 2` có ` | 2` nằm ngoài công thức). Do đó, dòng này là hàng bảng và được giữ nguyên.
       - Nếu phần còn lại của dòng KHÔNG chứa `|` (ví dụ: `$$|x| = 1$$` có `|` nằm hoàn toàn bên trong cặp `$$`), dòng này không phải là hàng bảng mà là khối công thức display độc lập.
- **Lựa chọn thay thế đã xem xét**:
  - Dùng bộ nhớ đệm kiểm tra dòng trước có phải `---|---`: Bị từ chối vì hàng đầu tiên của bảng (`Col | Val`) nằm trước đường phân cách, và kiểm tra `|` ngoài công thức bao quát được cả hàng tiêu đề, hàng phân cách và hàng dữ liệu compact.

---

### Nghiên cứu 3: Loại trừ Tệp Marker Khỏi Precache và Gói Phân Phối Web

- **Vấn đề thực tế**:
  - Tệp `.chuviettay_build_dist` được tạo trong thư mục `dist` bởi `prepare_dist_dir` để nhận diện thư mục build hợp lệ cho các lần build sau.
  - Trong `generate_sw_js()`, vòng lặp `for root, _, files in os.walk(dist_dir)` thu thập mọi tệp (chỉ trừ `sw.js`). Do đó `.chuviettay_build_dist` bị nạp vào `raw_files`, được băm vào `CACHE_NAME` và đưa vào `PRECACHE_URLS`.
  - Trên máy chủ web chặn tệp ẩn (dotfiles), việc Service Worker cố gắng tải `./.chuviettay_build_dist` sẽ nhận mã lỗi 404/403, khiến cài đặt Service Worker bị thất bại.

- **Quyết định thiết kế**:
  - Trong `generate_sw_js(dist_dir)` của `scripts/build_web.py`:
    Thêm điều kiện bỏ qua: `if f == "sw.js" or f.startswith(".") or f == BUILD_MARKER_NAME: continue`.
  - Bảo đảm danh sách `raw_files`, `files_to_cache`, băm tổng hợp `CACHE_NAME` và mảng `precache_list` hoàn toàn sạch, không chứa bất kỳ tệp ẩn nào.
  - Tệp marker tiếp tục tồn tại trên đĩa trong thư mục `dist_dir` để phục vụ xác thực an toàn cho các lần build tiếp theo.
- **Lựa chọn thay thế đã xem xét**:
  - Xóa marker ở cuối script build: Bị từ chối vì nếu xóa đi, lần chạy build tiếp theo vào cùng thư mục ngoài đó sẽ thấy thư mục không rỗng và không có marker, dẫn tới bị chặn an toàn trừ khi người dùng nhớ truyền `--force-clean`.

---

### Nghiên cứu 4: Đo Tỷ lệ Mở rộng Tuyến tính Bền bỉ Trên CI

- **Vấn đề thực tế**:
  - `test_linear_scalability_unclosed_display_math` đo thời gian xử lý với 5.000 dòng và áp ngưỡng cứng: `assert elapsed < 0.25`.
  - Trên runner CI dùng chung (GitHub Actions free runner), tải CPU có thể biến động lớn đột ngột, làm thời gian thực thi tăng lên $0.28$s hoặc $0.35$s dù thuật toán là $O(n)$ tuyến tính thuần túy.

- **Quyết định thiết kế**:
  - Chuyển sang kiểm tra tỷ lệ mở rộng tương đối (relative scaling ratio):
    - Đo thời gian xử lý với kích thước $N = 2,500$ cặp dòng ($5,000$ dòng) là $T_1$.
    - Đo thời gian xử lý với kích thước $2N = 5,000$ cặp dòng ($10,000$ dòng) là $T_2$.
    - Đối với thuật toán tuyến tính $O(n)$, kỳ vọng $T_2 / T_1 \approx 2.0$.
    - Đối với thuật toán bậc hai $O(n^2)$, tỷ lệ sẽ là $T_2 / T_1 \approx 4.0$.
    - Kiểm tra: `assert (T2 / T1) <= 3.5` (hoặc nếu $T_2 < 0.15$s thì coi như đạt ngay vì quá nhanh).
    - Đồng thời giữ một ngưỡng trần bảo vệ rộng rãi (ví dụ: $T_2 < 2.0$s) để phát hiện sự cố treo luồng mà không gây báo lỗi giả trên CI.
- **Lựa chọn thay thế đã xem xét**:
  - Tăng ngưỡng cứng lên 1.0s: Chấp nhận được nhưng không phản ánh bản chất toán học của độ phức tạp thuật toán; phương pháp tỷ lệ $T(2N)/T(N) \le 3.5$ vừa bảo đảm tính toán học vừa độc lập với tốc độ xung nhịp CPU.

---

## 2. Kết luận Nghiên cứu

Tất cả các câu hỏi kỹ thuật và phương án xử lý đã được làm rõ đầy đủ và xác minh qua nguyên mẫu thử nghiệm. Không có điểm nào cần làm rõ thêm (`NEEDS CLARIFICATION: 0`). Đủ điều kiện chuyển sang Phase 1.
