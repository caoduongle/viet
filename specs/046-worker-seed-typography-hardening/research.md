# Research & Technical Decisions: Worker Resilience, Seed Integrity & Typography Hardening

**Feature**: `046-worker-seed-typography-hardening`  
**Date**: 2026-10-20  
**Status**: Completed

## 1. Worker Recovery Lifecycle & Generation Resolution

### Context & Problem
Trong `webapp/js/app.js`:
- Khi Worker gửi tín hiệu `READY`, mã gọi `clearHandshakeTimer()` và bắt đầu `onWorkerReady(generation)`.
- `onWorkerReady()` thực hiện các tác vụ bất đồng bộ (`navigator.storage.persist()`, `teachController.init()`).
- Nếu trong lúc đang chờ, thế hệ Worker bị thay đổi (`workerGeneration++`), nhánh `.then()` và `.catch()` đều có điều kiện:
  ```javascript
  if (generation !== workerGeneration) {
    return;
  }
  ```
  Lệnh `return` này thoát sớm mà KHÔNG gọi `workerReadyResolve(true)` hay `workerReadyResolve(false)`.
- Khi đó, `const isReady = await readyPromise` trong `recoverWorker()` bị treo vô thời hạn (infinite hang). Khối `finally` không bao giờ được thực thi, cờ `isRecovering` giữ nguyên `true` và nút "Thử lại" bị vô hiệu hóa vĩnh viễn trong giao diện.

### Decision
1. **Quản lý phiên phục hồi theo thế hệ (Generation-Scoped Recovery Controller)**:
   - Lưu trữ trạng thái phiên phục hồi gồm: `{ generation, resolve, timer }`.
   - Khi `workerGeneration` tăng lên (bắt đầu phục hồi mới hoặc bị hủy), phiên của thế hệ cũ PHẢI lập tức được giải quyết dứt điểm:
     ```javascript
     if (activeRecoverySession && activeRecoverySession.generation !== newGen) {
       activeRecoverySession.resolve(false);
       clearTimeout(activeRecoverySession.timer);
     }
     ```
2. **Bảo vệ toàn bộ chu trình phục hồi bằng một bộ đếm thời gian hợp nhất**:
   - Bộ đếm thời gian `timeoutMs` (mặc định 10.000ms) KHÔNG bị xóa ngay khi nhận `READY`, mà tiếp tục bảo vệ giai đoạn `onWorkerReady()`. Timer chỉ được xóa khi `onWorkerReady` thực sự hoàn tất hoặc khi phiên phục hồi kết thúc.
   - Nếu `onWorkerReady` bị treo quá hạn, timer sẽ kích hoạt, giải quyết `readyPromise(false)`, chấm dứt Worker treo và hiển thị thông báo lỗi kèm nút "Thử lại".
3. **Bảo đảm khối `finally` luôn chạy**:
   - `readyPromise` luôn được bảo đảm resolve (với `true` hoặc `false`) trong mọi nhánh code, đưa `isRecovering` về `false` và mở khóa nút "Thử lại".

---

## 2. Idempotent UI Event Listeners & Teardown Mechanism

### Context & Problem
Trong `webapp/js/app.js`:
- `onWorkerReady()` gọi lần lượt `initBankTab()`, `initWriteTab()`, và `teachController.init()`.
- Nếu `teachController.init()` gặp lỗi (ví dụ Worker lỗi hoặc thiếu canvas), khối `catch` đặt `isDomListenersAttached = false`.
- Tuy nhiên, các listener đã đăng ký bên trong `initBankTab()` và `initWriteTab()` (như nút xuất file, nút chuyển trang, các input) không tự hủy.
- Khi người dùng bấm "Thử lại" và quá trình phục hồi thành công, `initBankTab()` và `initWriteTab()` được gọi lại, dẫn đến việc gắn thêm một bộ listener thứ hai vào cùng các phần tử DOM. Một lần bấm nút của người dùng sau đó sẽ kích hoạt 2 lần xuất file hoặc 2 lần render.

### Decision
1. **Sử dụng `AbortController` cho toàn bộ DOM Event Listeners trong UI**:
   - Khai báo một `uiAbortController = null` ở cấp độ module `app.js` (hoặc trong từng module tab).
   - Khi bắt đầu chu trình gắn listener: nếu `uiAbortController` đang tồn tại, gọi `uiAbortController.abort()` để tự động tháo gỡ toàn bộ các listener cũ.
   - Khởi tạo `uiAbortController = new AbortController()` và truyền `signal: uiAbortController.signal` vào các lời gọi `addEventListener` trong `bank.js`, `write.js`, `teach.js`.
2. **Thiết kế Idempotent Init Guards**:
   - Trong mỗi module tab (`bank.js`, `write.js`), lưu cờ `isInitialized` kèm hàm `teardown()` hoặc kiểm tra thuộc tính phần tử DOM (như `btn.__hasListener`) để ngăn chặn việc đăng ký lặp.
   - Khi khởi tạo thất bại, gọi hàm dọn dẹp để đưa DOM về trạng thái nguyên bản trước khi cho phép lần thử tiếp theo.

---

## 3. Seed Namespace Isolation & Consistency

### Context & Problem
1. **Heading vs Paragraph Namespace**:
   - Trong `chuviettay/document/ir.py`, hàm `align_document_seeds()` nhóm `isinstance(block, (Paragraph, Heading))` chung vào `context_prefix="text"`.
   - Trong `chuviettay/layout/engine.py`, hàm `render_paragraph_inlines()` có tham số mặc định `context_prefix="text"`. Khi kết xuất `Heading`, hàm này được gọi mà không truyền `context_prefix="heading"`.
   - Hậu quả: Một từ xuất hiện trong Tiêu đề và Đoạn văn cùng chia sẻ bộ đếm `occurrence`. Khi người dùng chèn thêm một đoạn văn bản mới vào thân bài, chỉ số `occurrence` của từ trong tiêu đề có thể bị dịch chuyển, làm nét chữ của tiêu đề bị biến dạng (vi phạm nguyên tắc cô lập seed).
2. **TableCell MathBlock Occurrence Dropping**:
   - Khi một ô bảng chứa `MathBlock`, `engine.py` chuyển đổi nó thành `MathInline`:
     `cell_inlines.append(MathInline(latex=b.latex, ast=b.ast))`
   - Các thuộc tính `occurrence` và `stable_id` đã được gán bởi `align_document_seeds()` cho `MathBlock` bị bỏ rơi, khiến công thức trong bảng không giữ được seed khi tài liệu có chỉnh sửa phía trước bảng.
3. **Chunk Sub-index in Token Geometry ID**:
   - `SeedContext.token_id` có định dạng `{content_type}:{element_id}#{occurrence}`, không chứa `sub_index`.
   - Khi một token dài bị chia thành nhiều chunk (ví dụ `chunk0`, `chunk1`), tất cả các chunk này đều nhận cùng một `token_id`.
   - Khi `_render_text_line()` dùng `item.token_id` để tạo ScopedRNG cho khoảng cách từ (`wgap`), hai chunk liên tiếp có thể nhận cùng ngữ cảnh hình học.

### Decision
1. **Phân tách rõ ràng namespace `heading`**:
   - Trong `chuviettay/document/ir.py`: Tách nhánh `isinstance(block, Heading)` dùng `context_prefix="heading"`.
   - Trong `chuviettay/layout/engine.py`: Khi kết xuất `Heading`, gọi `render_paragraph_inlines(..., context_prefix="heading")`.
2. **Chuyển tiếp đầy đủ metadata cho `MathInline` trong bảng**:
   - Trong `engine.py`: Khi chuyển đổi `MathBlock` sang `MathInline` trong ô bảng:
     `cell_inlines.append(MathInline(latex=b.latex, ast=b.ast, occurrence=getattr(b, "occurrence", None), stable_id=getattr(b, "stable_id", None)))`.
3. **Phân biệt định danh hình học của từng Chunk**:
   - Khi tạo `RenderItem` cho từng chunk của một token: gán `token_id = f"{ctx.token_id}:{chunk_idx}"` (hoặc lưu `sub_index` vào `RenderItem`), bảo đảm mỗi chunk có định danh hình học độc lập cho các bước tính khoảng cách và căn chỉnh.

---

## 4. Robust Digit Geometry, Measurement Parity & Negative Number Spacing

### Context & Problem
1. **Mẫu chữ số dị biệt cực đoan**:
   - Hàm `_normalize_digit_sample()` co giãn theo tỷ lệ `scale_y = clamp(target_h / sample_h, 0.35, 1.85)`.
   - Nếu một kho mẫu có nét vẽ lỗi (ví dụ chỉ là một dấu chấm cao `0.1 * xh`, hoặc nét vẽ quá khổ `4.0 * xh`), sau khi nhân hệ số bị kẹp trong `[0.35, 1.85]`, chữ số vẫn bị quá nhỏ (`0.185 * xh`) hoặc quá lớn (`1.40 * xh`), không đạt chuẩn `1.20 * xh`.
2. **Lệch khoảng cách giữa `measure_text_width()` và `number()`**:
   - Trong `number()`: Khoảng cách trước dấu phẩy là `0.08 * xh`, khoảng cách sau dấu phẩy là `0.10 * xh`, khoảng cách giữa các chữ số là `dgap` (`0.10 * xh .. 0.18 * xh`).
   - Trong `measure_text_width()`: Nhánh số lại cộng cố định `cw + 0.18 * xh` cho dấu phẩy và `0.12 * xh` cho chữ số, dẫn đến sự chênh lệch tích lũy độ rộng. Bộ ngắt dòng có thể phán đoán sai rằng dòng đã đầy và ngắt dòng số thập phân không cần thiết.
3. **Khoảng cách sau dấu âm ở đầu số**:
   - Trong `_resolve_dgap(first, is_hyphen, ...)`: Khi `first=True`, hàm trả về `0.0`.
   - Với số `-25`: Ký tự `-` có `first=True` (gap = 0). Đến chữ số `2`, `first=False` nhưng `ch == "2"` nên `is_hyphen=False`.
   - Kết quả: Khoảng cách giữa dấu trừ và chữ số đầu tiên bị tính bằng full `dgap` thông thường (`1.43` pt), trong khi typographic chuẩn đòi hỏi dấu âm phải đứng sát chữ số đầu tiên (`0.05 * xh .. 0.10 * xh`).

### Decision
1. **Chính sách xử lý mẫu số cực đoan (Adaptive Scaling Policy)**:
   - Vì hàm `get_vector_glyph_fallback` trong kho mã hiện chỉ hỗ trợ ký hiệu toán/lập trình và không có định nghĩa nét cho chữ số `'0'`-`'9'`, ta áp dụng chính sách co giãn thích ứng trực tiếp trên mẫu thực tế của người dùng:
     - Với mọi mẫu có chiều cao hữu hiệu (`sample_h > 1e-4`): Tính toán tỷ lệ `scale_y = target_h / sample_h` với dải kẹp mở rộng `clamp(scale_y, 0.10, 15.0)`, và `scale_x = clamp(scale_y ** 0.5, 0.40, 2.50)`.
     - Chính sách này bảo đảm 100% mẫu dị biệt (dù bị vẽ quá bé `0.10 * xh` hay quá lớn `4.0 * xh`) đều được co giãn chuẩn xác về đúng chiều cao chuẩn `target_h = 1.20 * xh` (`[1.05 * xh, 1.30 * xh]`).
     - Với mẫu suy biến rỗng hoặc không có nét (`sample_h <= 1e-4`): Trả về nét rỗng an toàn và độ rộng `0.6 * xh` mà không gây lỗi chia cho 0.
2. **Đồng bộ hóa 100% giữa `measure_text_width()` và `number()`**:
   - Chuẩn hóa quy tắc tính toán độ rộng tiến của số trong `measure_text_width()` bám sát từng bước của `number()`: khoảng hở trước dấu phẩy `0.08 * xh` (nếu không phải ký tự đầu tiên), sau dấu phẩy `0.10 * xh`, khoảng cách giữa các chữ số lấy theo `_resolve_dgap` hoặc `default_dgap = 0.12 * xh`, và nén `0.5 * gap` đối với chữ số đứng liền kề dấu trừ.
3. **Thu hẹp khoảng cách sau dấu âm ở đầu số**:
   - Trong `Writer.number(s)`: Nhận diện liên kết dấu âm bằng cách truyền cờ `is_hyphen=(ch == "-" or (d_idx > 0 and s[d_idx - 1] == "-"))` vào `_resolve_dgap()`.
   - Khi ký tự liền trước là `-`, khoảng cách đến chữ số tiếp theo được thu hẹp còn `0.5 * dgap` (khoảng `0.05 * xh .. 0.09 * xh`), mang lại diện mạo số âm liền lạc và tự nhiên.
