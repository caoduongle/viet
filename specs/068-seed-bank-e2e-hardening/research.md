# Phase 0 Research: Hoàn thiện Đối chiếu Hạt giống Đa bước, Đồng bộ Phiên bản Kho mẫu và Khắc phục Kiểm thử E2E (068-seed-bank-e2e-hardening)

## Unknown 1: Khắc phục chồng lấn tiền tố/hậu tố trong thuật toán đối chiếu hạt giống (`align_document_seeds`)

### Vấn đề cốt lõi
Trong tệp `chuviettay/document/ir.py`, hàm `align_document_seeds(base_doc, edited_doc)` triển khai tối ưu hóa $O(N)$ bằng cách cắt bỏ tiền tố chung (`prefix`) và hậu tố chung (`suffix`) trước khi chạy `SequenceMatcher` trên phần thân giữa.
Để tránh việc các phần tử biên ngẫu nhiên trùng khớp làm cắt tham lam sai lệch, hệ thống áp dụng ngưỡng `MIN_TRIM_LEN = 3`:
```python
p = 0
while p < min_len and base_keys[p] == edited_keys[p]:
    p += 1
prefix_len = p if p >= MIN_TRIM_LEN else 0

s = 0
while (
    s < min_len - prefix_len
    and base_keys[n_base - 1 - s] == edited_keys[n_edited - 1 - s]
):
    s += 1
suffix_len = s if s >= MIN_TRIM_LEN else 0
```
Khi hai tài liệu có tiền tố chung ngắn ($p = 1$ hoặc $p = 2$), `prefix_len` bị đặt về `0`. Biểu thức `s < min_len - prefix_len` trở thành `s < min_len`. Do đó, vòng lặp tìm hậu tố `s` có thể quét ngược lên tới tận `min_len`, lấn sâu vào $p$ phần tử đầu tiên của tiền tố thực tế.
Nếu tài liệu có các từ lặp lại ở cả đầu và cuối (ví dụ tài liệu gốc: `"là là đi học"`, chỉnh sửa: `"là là mới là đi học"`), việc hậu tố quét tràn lên đầu sẽ gán nhầm các phần tử của tiền tố cho hậu tố, làm sai lệch chỉ số xuất hiện (`occurrence`) của các từ không hề thay đổi.

### Quyết định kỹ thuật
- **Quyết định**: Khống chế chặn trên của hậu tố dựa trên số lượng phần tử trùng khớp thực tế của tiền tố:
  ```python
  max_suffix = min_len - p
  s = 0
  while (
      s < max_suffix
      and base_keys[n_base - 1 - s] == edited_keys[n_edited - 1 - s]
  ):
      s += 1
  suffix_len = s if s >= MIN_TRIM_LEN else 0
  ```
- **Lý do**: Sử dụng $p$ (độ dài tiền tố trùng khớp thực tế) thay vì `prefix_len` (giá trị đã bị ép về 0 khi $p < 3$) bảo đảm bất đẳng thức:
  $$p + s \le \min(n_{base}, n_{edited})$$
  Do đó, hai vùng tiền tố và hậu tố được phân tách hoàn toàn, không bao giờ giao nhau hay chồng lấn lên nhau trong mọi trường hợp (kể cả $p = 0, 1, 2$ hoặc $\ge 3$).
- **Giải pháp thay thế bị bác bỏ**:
  - *Bỏ ngưỡng `MIN_TRIM_LEN` (chấp nhận cắt tiền tố từ 1 phần tử)*: Bị bác bỏ vì nếu một chữ đơn lẻ ngẫu nhiên trùng ở đầu câu (ví dụ liên từ "và", "là"), việc cắt cứng 1 phần tử có thể làm giảm không gian căn chỉnh toàn cục của `SequenceMatcher` ở đoạn giữa, gây lệch các cụm từ quan trọng hơn.

---

## Unknown 2: Bảo toàn chỉ số xuất hiện (`token_occurrences`) qua nhiều lượt chỉnh sửa liên tiếp (Multi-step Edits)

### Vấn đề cốt lõi
Khi người dùng thực hiện nhiều lượt chỉnh sửa nối tiếp nhau trong cùng phiên:
- Lần 1: Chỉnh sửa tài liệu gốc $D_0 \to D_1$. `align_document_seeds` gán `node.token_occurrences` cho các `Text` node và `node.occurrence` cho các `Symbol/Math/Table` node trong $D_1$.
- Lần 2: Tiếp tục chỉnh sửa $D_1 \to D_2$. `align_document_seeds` được gọi với `base_doc = D_1` và `edited_doc = D_2`.
Tuy nhiên, hàm `extract_doc_elements(doc)` hiện tại duyệt qua các node và tính:
```python
occ = counts.get((blk_prefix, tok), 0)
counts[(blk_prefix, tok)] = occ + 1
```
Hàm này đếm tuần tự từ 0 và hoàn toàn bỏ qua các giá trị `token_occurrences` hay `occurrence` đã có sẵn trên các node của `D_1`. Hệ quả là:
1. Các từ trong $D_1$ bị đánh số lại từ 0, làm mất hoàn toàn mốc căn chỉnh đã xác lập từ lượt 1.
2. Biến `curr_max_counts = dict(base_counts)` chỉ chứa số lượng đếm tuần tự, không phản ánh chỉ số `occ` tối đa thực tế. Khi chèn từ mới, từ mới có thể nhận lại chỉ số `occ` trùng với một từ đang tồn tại.

### Quyết định kỹ thuật
- **Quyết định**: Trong `extract_doc_elements(doc)`:
  1. Với `Text` node: Nếu node đã có `token_occurrences` và `tok_idx < len(token_occurrences)`, lấy `occ = inline.token_occurrences[tok_idx]`. Nếu chưa có, lấy `occ = counts.get((blk_prefix, tok), 0)`.
  2. Với `Symbol`, `MathInline`, `MathBlock`, `Table`: Tương tự, nếu `getattr(node, "occurrence", None) is not None`, ưu tiên sử dụng giá trị này.
  3. Cập nhật số đếm tối đa của khóa:
     `counts[key] = max(counts.get(key, 0), occ + 1)`
- **Lý do**:
  - Giữ vững 100% chỉ số xuất hiện của mọi phần tử đã tồn tại qua bất kỳ số lượng lượt chỉnh sửa nào ($D_0 \to D_1 \to D_2 \to \dots \to D_k$).
  - Đảm bảo `curr_max_counts[key]` luôn nghiêm ngặt lớn hơn mọi `occurrence` đã dùng cho từ khóa đó, triệt tiêu hoàn toàn nguy cơ va chạm chỉ số khi chèn từ mới.
- **Giải pháp thay thế bị bác bỏ**:
  - *Lưu lịch sử occurrences vào từ điển bên ngoài ở tầng Controller*: Bị bác bỏ vì vi phạm tính tự đóng gói (self-contained) của Document IR và làm tăng độ phức tạp khi quản lý trạng thái, dễ rò rỉ bộ nhớ hoặc lệch pha khi người dùng hoàn tác (Undo).

---

## Unknown 3: Tích hợp đối chiếu hạt giống vào luồng kết xuất thực tế (`AppController` & `BrowserBridge`)

### Vấn đề cốt lõi
Hiện tại, `align_document_seeds` chỉ được gọi độc lập trong các unit test. Trong luồng chạy thực tế của ứng dụng (`AppController.write_text`, `AppController.write_document`, và `BrowserBridge.write_text`), mỗi lần người dùng bấm kết xuất hoặc gõ phím, tài liệu mới luôn được phân tích từ đầu và chuyển thẳng cho `DocumentLayoutEngine` mà không đối chiếu với tài liệu của lượt kết xuất liền trước.

### Quyết định kỹ thuật
- **Quyết định**:
  1. Trong `AppController`: Khởi tạo hai trường trạng thái:
     ```python
     self._last_doc: Document | None = None
     self._last_seed: int | None = None
     ```
  2. Trong `AppController.write_document(document, opts, out_path, ...)`:
     - Nếu `opts.stable_variants is True`:
       - Nếu `self._last_doc is not None` và `self._last_seed == opts.seed`:
         `document = align_document_seeds(self._last_doc, document)`
       - Sau khi kết xuất thành công, cập nhật:
         `self._last_doc = document`
         `self._last_seed = opts.seed`
     - Nếu `opts.stable_variants is False` hoặc `opts.seed != self._last_seed`:
       `self._last_doc = document`
       `self._last_seed = opts.seed`
  3. Bổ sung phương thức `AppController.clear_document_history()` để hỗ trợ đặt lại lịch sử khi người dùng chủ động xóa trắng tài liệu hoặc đổi dự án.
- **Lý do**:
  - Do `BrowserBridge.write_text` ủy quyền cho `AppController.write_document` (cả nhánh Markdown và nhánh văn bản thuần), việc đặt logic tại `AppController` giúp toàn bộ các giao diện (CLI, Web Client qua Worker, desktop scripts) đều tự động có tính năng ổn định kiểu chữ mà không bị trùng lặp mã nguồn.
- **Giải pháp thay thế bị bác bỏ**:
  - *Quản lý Document IR ở tầng JavaScript Web Worker*: Bị bác bỏ vì Document IR là đối tượng Python thuần trong Pyodide; việc chuyển đổi qua lại JSON/JS Proxy vừa làm giảm hiệu năng vừa phá vỡ nguyên tắc phân tách trách nhiệm (Core Python xử lý logic tài liệu, JS chỉ làm cầu nối I/O).

---

## Unknown 4: Khắc phục lỗi E2E `currentProfileId` và đồng bộ phiên bản kho mẫu hai thành phần (`worker_epoch`, `bank_revision`)

### Vấn đề cốt lõi
1. **Lỗi E2E ReferenceError**: Trong `webapp/js/bank.js:194`, dòng mã:
   `const activeProfileId = currentProfileId || "default";`
   gây lỗi `ReferenceError: currentProfileId is not defined` do biến này không được khai báo trong scope của `bank.js`. Lỗi này làm dừng toàn bộ hàm `refreshBankView()`, khiến tab Kho mẫu kẹt ở trạng thái đang tải và làm hỏng 6 bài kiểm thử Playwright E2E.
2. **Lỗi đồng bộ Revision**: Khi Worker gặp sự cố và khởi động lại, `bank_revision` trong Python bắt đầu lại từ `1`. Nếu giao diện đang lưu cache với `revision: 1`, giao diện sẽ không nhận biết dữ liệu trong Worker mới đã khác và dùng lại cache cũ. Đồng thời, thao tác `sync_save` trong `py-worker.js` khi nhận dữ liệu cập nhật từ tab khác chưa kích hoạt tăng `bank_revision`.

### Quyết định kỹ thuật
1. **Sửa biến Profile an toàn**:
   Trong `webapp/js/bank.js`:
   `const activeProfileId = (await storage.getSetting("active_profile_id", "default_profile")) || "default_profile";`
2. **Thế hệ phiên xử lý (`worker_epoch`)**:
   Trong `chuviettay/browser/bridge.py`:
   - Khi khởi tạo `BrowserBridge`, sinh một UUID duy nhất:
     `self.worker_epoch = str(uuid.uuid4())`
   - Trong `get_bank_snapshot()`, trả về cả `revision` và `worker_epoch`.
3. **Đồng bộ `sync_save`**:
   Trong `webapp/js/worker/py-worker.js`:
   Khi nhận `sync_save`, nếu có `diskGzBytes`, gọi nạp lại kho mẫu vào bridge và luôn tăng `_bridge.bank_revision += 1`.
4. **Kiểm tra bộ nhớ đệm đa yếu tố**:
   Trong `bank.js`: Cache được kiểm tra theo bộ 3 giá trị:
   ```javascript
   if (
     !force &&
     lastBankSnapshotCache.epoch === snapshot.worker_epoch &&
     lastBankSnapshotCache.revision === snapshot.revision &&
     lastBankSnapshotCache.profileId === activeProfileId
   ) {
     return;
   }
   ```
- **Lý do**: Loại bỏ hoàn toàn lỗi ReferenceError, đồng thời vô hiệu hóa chính xác cache khi Worker crash hoặc nạp lại hồ sơ mới.
- **Giải pháp thay thế bị bác bỏ**:
  - *Dùng `Date.now()` làm số phiên bản*: Bị bác bỏ vì độ phân giải mili-giây có thể gặp race condition khi có nhiều thao tác ghi liên tiếp trong cùng một chu kỳ tick.

---

## Unknown 5: Tính nguyên tử của bản chụp kho mẫu (`get_bank_snapshot`) và an toàn DOM chống mã độc

### Vấn đề cốt lõi
1. Trong `BrowserBridge.get_bank_snapshot()`: Phương thức chỉ kiểm tra `stats_res.get("ok")` nhưng không kiểm tra trạng thái của `letters_res`, `symbols_res`, `marks_res`. Nếu một truy vấn thành phần thất bại, phương thức vẫn trả về `{"ok": True, "data": {"letters": [], ...}}`. Người dùng sẽ thấy danh sách chữ bị rỗng giả tạo.
2. Trong `webapp/js/bank.js:180`: Hàm `showBankErrorBanner(message)` sử dụng `banner.innerHTML = ... ${message} ...`. Nếu thông điệp lỗi chứa dữ liệu do người dùng nhập từ bên ngoài (như tên file hoặc nhãn độc hại), trình duyệt có nguy cơ bị tấn công XSS.

### Quyết định kỹ thuật
1. **Kiểm tra toàn diện tính nguyên tử**:
   Trong `get_bank_snapshot()`:
   ```python
   for res in (letters_res, symbols_res, marks_res):
       if not res.get("ok"):
           return res
   ```
2. **Dựng DOM an toàn bằng API chuẩn**:
   Trong `showBankErrorBanner()`:
   ```javascript
   banner.replaceChildren();
   const span = document.createElement("span");
   span.textContent = `⚠️ ${message}`;
   const closeBtn = document.createElement("button");
   closeBtn.className = "btn btn-sm btn-link";
   closeBtn.style.cssText = "color: inherit; text-decoration: underline; background: none; border: none; cursor: pointer;";
   closeBtn.textContent = "Đóng";
   closeBtn.onclick = () => { banner.style.display = "none"; };
   banner.append(span, closeBtn);
   banner.style.display = "flex";
   ```
- **Lý do**: Tuân thủ tuyệt đối chuẩn an toàn giao diện web, ngăn chặn hoàn toàn HTML/Script injection và đảm bảo tính nhất quán của dữ liệu kho mẫu.

---

## Unknown 6: Đo kiểm hiệu năng bản chụp kho mẫu quy mô lớn (Benchmark 1.000+ nhãn)

### Vấn đề cốt lõi
Cần bổ sung một bài kiểm thử hiệu năng hồi quy tự động nhằm xác nhận rằng với một kho mẫu thực tế quy mô lớn (1.000 nhãn từ/ký tự trở lên, kèm nhiều biến thể nét), cơ chế bản chụp một lượt (`get_bank_snapshot`) duy trì thời gian phản hồi dưới 200ms.

### Quyết định kỹ thuật
- **Quyết định**: Bổ sung kiểm thử vào `tests/test_performance_regression.py`:
  - Tạo một kho mẫu thử nghiệm với 1.000 ký tự đa dạng (chữ cái Latinh/Việt, chữ số, ký hiệu toán học, dấu thanh, từ vựng).
  - Khởi tạo `BrowserBridge` gắn với kho mẫu này.
  - Đo thời gian thực thi `get_bank_snapshot()`.
  - Khẳng định: `res["ok"] is True`, số lượng nhãn trích xuất $\ge 1.000$, và thời gian thực thi $t < 200$ ms.
- **Lý do**: Bảo đảm không phát sinh suy giảm hiệu năng khi người dùng tích lũy dữ liệu học chữ lớn theo thời gian.

---

## Unknown 7: Đồng bộ hóa chuẩn hóa văn bản `norm.split()` khi tái tạo `token_occurrences` trên `Text` node

### Vấn đề cốt lõi
Tại dòng 322 của `chuviettay/document/ir.py`:
`node.token_occurrences = [token_map.get(i, i) for i in range(len(node.text.split()))]`
Trong khi đó, ở hàm trích xuất `extract_doc_elements` (dòng 180) và hàm bố cục `DocumentLayoutEngine` (`chuviettay/layout/engine.py:332`), các token được tách dựa trên chuỗi đã chuẩn hóa:
`norm = _normalize_text(inline.text or "")`
`for tok_idx, tok in enumerate(norm.split()):`
Nếu `node.text` chứa các ký tự như khoảng trắng không ngắt (`\u00a0`), tab (`\t`) hoặc ký tự điều khiển định dạng, độ dài của `node.text.split()` có thể lệch so với `norm.split()`. Khi `DocumentLayoutEngine` truy cập `inline.token_occurrences[inline_tok_idx]`, sự lệch độ dài này có thể gây lỗi hoặc làm mất đồng bộ chỉ số xuất hiện của các token cuối đoạn.

### Quyết định kỹ thuật
- **Quyết định**: Khi tái tạo `node.token_occurrences` trong `align_document_seeds`:
  ```python
  norm = _normalize_text(node.text or "")
  node.token_occurrences = [
      token_map.get(i, i) for i in range(len(norm.split()))
  ]
  ```
- **Lý do**: Đảm bảo 100% tính nhất quán về kích thước mảng token giữa `ir.py` và `engine.py`.

---

## Unknown 8: Vòng đời và điểm đặt lại của `_last_doc` trong `AppController`

### Vấn đề cốt lõi
Nếu người dùng nạp một tệp kho mẫu mới (`load_bank`) hoặc xóa trắng tài liệu, cây `_last_doc` của lượt trước vẫn đang mang ngữ cảnh biến thể nét chữ của kho mẫu cũ. Nếu tiếp tục đối chiếu với `_last_doc` cũ, các biến thể nét chữ gán cho tài liệu mới có thể bị lệch hoặc tham chiếu tới các mẫu không còn tồn tại trong kho mới.

### Quyết định kỹ thuật
- **Quyết định**:
  1. Trong `AppController.load_bank(...)`: Tự động gọi `self.clear_document_history()`.
  2. Trong `AppController.write_document(...)`: Nếu tài liệu đầu vào rỗng (không có block nào hoặc toàn bộ text rỗng), tự động gọi `self.clear_document_history()`.
- **Lý do**: Ngăn ngừa ô nhiễm trạng thái chéo giữa các kho mẫu khác nhau và bảo đảm tài liệu mới bắt đầu từ kho mới hoàn toàn độc lập.
