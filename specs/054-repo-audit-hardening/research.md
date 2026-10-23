# Implementation Research: Gia Cố Nền Tảng Kho Mã Nguồn Hậu Rà Soát (054-repo-audit-hardening)

**Feature**: [054-repo-audit-hardening](spec.md)  
**Date**: 2026-10-23  

---

## 1. Bộ phân tách khối công thức Markdown: Máy trạng thái một lượt và Bảo vệ khối mã

### Vấn đề
- Phương thức `_isolate_display_math_blocks` quét toàn bộ văn bản sau chuẩn hóa delimiter mà không tách biệt đoạn mã (code fence ```` ``` ````, `~~~` và inline code `` ` ``). Khi mã ví dụ chứa cú pháp `prefix:$$x=1$$`, đoạn mã bị tách thành nhiều dòng làm sai lệch nội dung.
- Quét nhìn trước lồng nhau (`for scan_idx in range(idx + 1, n)`) khi gặp dòng mở `$$` mà không đóng tạo ra độ phức tạp thời gian bậc hai $O(n^2)$. Đầu vào lớn chứa hàng nghìn dấu `$$` mở không đóng làm treo tiến trình Web Worker.

### Quyết định kỹ thuật (Decision)
- **Tách phân đoạn an toàn kết hợp máy trạng thái**:
  1. Sử dụng `_CODE_SEGMENT` để phân rã văn bản thành các phân đoạn xen kẽ (chẵn: văn bản thường; lẻ: khối mã / đoạn mã). Tuyệt đối không can thiệp vào các phân đoạn lẻ (code segments).
  2. Với các phân đoạn văn bản thường, áp dụng bộ phân tích một lượt theo dòng (line-by-line single-pass state machine) với các trạng thái: `NORMAL`, `IN_DISPLAY_MATH`.
  3. Khi gặp dòng mở `$$`, nếu không đóng trên cùng dòng, chuyển trạng thái sang `IN_DISPLAY_MATH`. Các dòng tiếp theo chỉ cần kiểm tra xem có kết thúc bằng `$$` để quay về `NORMAL`. Không quét tìm trước lặp đi lặp lại.
  4. Nếu đến cuối phân đoạn mà khối `$$` vẫn chưa đóng, coi toàn bộ như văn bản thường an toàn mà không thực hiện chèn dòng trống thừa thãi.
  5. Độ phức tạp thời gian: $O(n)$ tuyến tính với số dòng và ký tự.

### Lý do lựa chọn (Rationale)
- Tận dụng regex `_CODE_SEGMENT` sẵn có đã được kiểm chứng an toàn trong `_normalize_math_delimiters` và `_sanitize_html`.
- Máy trạng thái loại bỏ hoàn toàn các vòng lặp quét lồng nhau, bảo đảm an toàn ReDoS và chống nghẽn Web Worker.

### Các giải pháp thay thế đã cân nhắc (Alternatives Considered)
- *Phân tích toàn diện bằng AST (Full CommonMark AST AST-pass)*: Chuyển đổi toàn bộ việc cách ly sang giai đoạn AST plugin của `markdown-it-py`. Bị loại vì `markdown-it-py` đã hoàn tất tokenization trước khi plugin can thiệp, không giải quyết được việc `$$` bị nuốt vào `inline` token ngay từ pha parse block nếu thiếu dòng trống.
- *Regex Lookahead thay thế*: Dùng biểu thức chính quy phức tạp với lookaround. Bị loại vì regex phức tạp trên chuỗi dài dễ gây ra thảm họa backtracking (ReDoS) trong môi trường Python/Pyodide.

---

## 2. Bảo đảm tính bất biến của Document IR trong DocumentLayoutEngine

### Vấn đề
- Trong `chuviettay/layout/engine.py` (`_layout_inlines`), logic gộp các nút `Text` liền kề đang thực hiện phép gán đột biến trực tiếp:
  ```python
  merged_inlines[-1].text += (inl.text or "")
  ```
- Nút `Text` là dataclass có thể thay đổi (`mutable`). Khi caller gọi `write_document(doc)` nhiều lần với cùng một cây `Document`, văn bản bị nhân bản tích lũy, dẫn đến chuỗi bị nối lặp liên tục (`"Xin chào Việt Nam Việt Nam"`).

### Quyết định kỹ thuật (Decision)
- **Thay thế phần tử gộp bằng nút Text mới độc lập**:
  ```python
  prev = merged_inlines[-1]
  combined_text = (prev.text or "") + (inl.text or "")
  new_occ = list(t1_occ) + list(t2_occ) if (t1_occ is not None and t2_occ is not None) else None
  merged_inlines[-1] = Text(text=combined_text, token_occurrences=new_occ)
  ```
- Không bao giờ thay đổi thuộc tính `text` hay `token_occurrences` của đối tượng `prev` gốc do caller truyền vào.

### Lý do lựa chọn (Rationale)
- Sửa đổi tối thiểu, hiệu quả tuyệt đối, loại bỏ 100% tác dụng phụ (side-effect) lên cây `Document`.
- Chi phí cấp phát một đối tượng `Text` mới là không đáng kể so với quá trình dàn trang và đo đạc hình học.

### Các giải pháp thay thế đã cân nhắc (Alternatives Considered)
- *Deep copy toàn bộ Document trước khi dàn trang*: `copy.deepcopy(document)`. Bị loại vì chi phí sao chép sâu toàn bộ cây đối tượng lớn gây lãng phí bộ nhớ và CPU không cần thiết trên Pyodide.
- *Chuyển Text thành frozen dataclass*: `frozen=True`. Bị loại vì có thể phá vỡ các luồng khởi tạo linh hoạt ở các module khác trong repo mà không mang lại thêm lợi ích tương xứng.

---

## 3. Chuẩn hóa Khóa bộ nhớ đệm Service Worker định danh tài nguyên

### Vấn đề
- Hàm `generate_sw_js(dist_dir)` tính `content_hash_12` bằng cách băm chuỗi nối các mã SHA-256 của các file mà không kèm đường dẫn tương đối, đồng thời thứ tự duyệt thư mục `os.walk(dist_dir)` không được sắp xếp trước.
- Khi hai file hoán đổi nội dung hoặc một file đổi tên/đường dẫn, cache key không thay đổi. Thứ tự duyệt file khác nhau giữa các hệ điều hành (Windows NTFS vs Linux ext4) sinh ra cache key không đồng nhất.

### Quyết định kỹ thuật (Decision)
- **Chuẩn hóa danh mục (Canonical Manifest Sorting)**:
  1. Quét toàn bộ file trong `dist_dir` (trừ `sw.js`), chuẩn hóa đường dẫn tương đối theo định dạng POSIX (`rel_path = fpath.relative_to(dist_dir).as_posix()`).
  2. Sắp xếp danh sách theo thứ tự bảng chữ cái của `rel_path` trước khi băm.
  3. Dữ liệu nạp vào SHA-256 hasher cho mỗi file là: `f"{rel_path}:{file_sha}\n".encode("utf-8")`.
  4. Tạo `cache_name = f"chuviettay-cache-{hasher.hexdigest()[:12]}"`.

### Lý do lựa chọn (Rationale)
- Đảm bảo tính tái lập (reproducible build): cùng mã nguồn luôn cho ra cùng một khóa cache bất kể môi trường build.
- Phản ánh trung thực cả nội dung tệp và vị trí/tên tệp trong gói phát hành PWA.

### Các giải pháp thay thế đã cân nhắc (Alternatives Considered)
- *Sử dụng git commit hash*: Bị loại vì khi build từ archive ZIP hoặc Docker không có thư mục `.git`, commit hash không khả dụng.
- *Sử dụng timestamp hiện tại*: Bị loại vì làm mất tính tái lập (mỗi lần build đều đổi cache vô ích dù mã nguồn không đổi).

---

## 4. Bảo vệ an toàn đường dẫn và ngăn chặn xóa dữ liệu trong Build Web

### Vấn đề
- `prepare_dist_dir(dist_dir: Path)` thực hiện `shutil.rmtree(resolved_dist)` nếu thư mục tồn tại.
- Khi người dùng truyền tham số `--dist` trỏ tới một thư mục bên ngoài kho lưu trữ (như thư mục tài liệu cá nhân), hàm xóa sạch thư mục đó mà không kiểm tra.

### Quyết định kỹ thuật (Decision)
- **Quy tắc bảo vệ 4 tầng**:
  1. Nếu `resolved_dist == DEFAULT_DIST_DIR.resolve()` (`webapp/dist`): Cho phép tự động xóa và tái tạo (hành vi mặc định an toàn).
  2. Nếu `resolved_dist` nằm bên trong repo nhưng ngoài `webapp/dist`: Đã bị chặn bởi các kiểm tra hiện tại.
  3. Nếu `resolved_dist` nằm ngoài repo hoặc là thư mục tùy ý:
     - Nếu thư mục chưa tồn tại hoặc là thư mục rỗng: Cho phép tạo/dọn dẹp.
     - Nếu thư mục đã tồn tại và không rỗng: Chỉ cho phép xóa khi có tệp chữ ký build `.chuviettay_build_dist` HOẶC người dùng truyền cờ `--force-clean`.
     - Nếu không thỏa mãn các điều kiện trên: Dừng chương trình với thông báo lỗi rõ ràng, bảo toàn nguyên vẹn thư mục.
  4. Sau khi dọn dẹp và tạo lại thư mục, ghi tệp đánh dấu `.chuviettay_build_dist` vào thư mục đích.

### Lý do lựa chọn (Rationale)
- Tránh thảm họa mất dữ liệu do gõ nhầm đường dẫn trong dòng lệnh.
- Vẫn hỗ trợ trơn tru các kịch bản build vào thư mục tạm (như trong các bài kiểm thử `test_build_web.py`).

---

## 5. Đồng bộ hóa Preview và Kho mẫu theo Phiên bản tăng đơn điệu

### Vấn đề
- Trong `webapp/js/write.js`, `isBankDirty` bị gán về `false` khi `res && res.ok` của tác vụ render hiện hành.
- Nếu người dùng dạy chữ trong lúc render $A$ đang chạy, `notifyBankUpdated` đặt `isBankDirty = true`. Khi render $A$ kết thúc, nó xóa `isBankDirty = false`. Nếu render $B$ (cho kho mới) sau đó bị lỗi hoặc bị hủy, giao diện hiển thị preview của kho cũ nhưng trạng thái lại báo là đã đồng bộ.

### Quyết định kỹ thuật (Decision)
- **Cơ chế số hiệu phiên bản kho mẫu (Monotonic Bank Revision)**:
  1. Khởi tạo `bankRevision = 1` và `lastRenderedRevision = 0`.
  2. Mỗi khi `notifyBankUpdated()` được kích hoạt, tăng `bankRevision++` và đặt `isBankDirty = true`.
  3. Khi `requestRender()` khởi chạy, lưu lại `const requestBankRevision = bankRevision`.
  4. Khi nhận kết quả thành công từ Worker:
     - Lưu `lastRenderedRevision = requestBankRevision`.
     - Chỉ đặt `isBankDirty = false` nếu `requestBankRevision === bankRevision`.
     - Nếu `bankRevision > requestBankRevision` (có thay đổi mới phát sinh trong lúc đang render), giữ nguyên `isBankDirty = true`.
  5. Khi render thất bại hoặc ném ngoại lệ: Giữ nguyên `isBankDirty = true`.

### Lý do lựa chọn (Rationale)
- Đơn giản, tự nhiên, không cần khóa phức tạp mà vẫn giải quyết triệt để race condition.
- Trạng thái bẩn của kho mẫu luôn phản ánh chính xác sự thật giữa bản vẽ trên màn hình và dữ liệu trong Worker.

---

## 6. Hợp đồng nhập liệu DOCX Content-First và Báo cáo cảnh báo

### Vấn đề
- Người dùng có thể kỳ vọng `DocxImporter` tái tạo nguyên vẹn bố cục đồ họa của Word (hình ảnh, bảng lồng nhau). Trong thực tế, importer được thiết kế theo triết lý Content-First để trích xuất văn bản và công thức sang chữ viết tay.

### Quyết định kỹ thuật (Decision)
- Ghi nhận rõ ràng trong tài liệu hợp đồng và danh sách `warnings` của `ImportResult` khi phát hiện:
  1. Hình ảnh hoặc đối tượng đồ họa (`drawing`/`pict`): ghi cảnh báo về việc ảnh không được hiển thị trong luồng viết tay.
  2. Bảng lồng nhau (`nested table`): ghi cảnh báo về việc bảng con được tóm tắt thành văn bản bên trong ô cha.
- Không thay đổi cấu trúc bảng hay parser nếu chưa có mô hình IR bảng lồng nhau tương ứng.
