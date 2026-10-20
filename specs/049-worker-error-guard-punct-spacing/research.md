# Research & Technical Decisions: 049-worker-error-guard-punct-spacing

## 1. Late Worker Error Isolation (User Story 1 & FR-001)

### Problem Analysis
Trong `webapp/js/app.js`, hàm `attachWorkerHandlers(targetWorker, generation = workerGeneration, timeoutMs = 10000, session = null)` đăng ký 3 callback chính trên đối tượng Worker:
- `targetWorker.onmessage`
- `targetWorker.onerror`
- `targetWorker.onmessageerror`

Ở commit `95c21bfd`, `onmessage` đã có bộ lọc thế hệ ở đầu hàm:
```javascript
targetWorker.onmessage = (e) => {
  if (generation !== workerGeneration) {
    if (boundSession && !boundSession.isResolved) {
      boundSession.resolve(false);
    }
    return;
  }
  // ...
};
```
Tuy nhiên, cả `targetWorker.onerror` và `targetWorker.onmessageerror` lại thiếu bước kiểm tra này:
```javascript
targetWorker.onerror = (e) => {
  const currentSession = boundSession || activeRecoverySession;
  if (currentSession && currentSession.generation === generation) {
    if (currentSession.timer) {
      clearTimeout(currentSession.timer);
      currentSession.timer = null;
    }
    handleWorkerFatalError(e.message || "Lỗi runtime trong Web Worker");
    currentSession.resolve(false);
  } else if (generation === workerGeneration) {
    handleWorkerFatalError(e.message || "Lỗi runtime trong Web Worker");
  }
};
```
`boundSession` là tham chiếu session thế hệ `generation` được lưu lại trong closure của `attachWorkerHandlers`. Khi Worker A (thế hệ `gen A`) đã bị thay thế bởi Worker B (thế hệ `gen B`), `boundSession` của Worker A vẫn mang `boundSession.generation === generation` (đều là `gen A`).
Nếu Worker A phát sinh một lỗi runtime hoặc lỗi giải mã thông điệp muộn sau khi Worker B đã hoạt động:
1. Biểu thức `currentSession && currentSession.generation === generation` đánh giá thành `true`.
2. `handleWorkerFatalError()` được gọi ngay lập tức!
3. Toàn bộ `pendingRequests` của Worker B bị từ chối (`req.reject(...)`).
4. Giao diện người dùng bị chuyển sang trạng thái lỗi (`status_error`) và hiện nút "Thử lại".
5. Worker B đang thực hiện tác vụ hợp lệ bị hủy ngang một cách oan uổng.

### Technical Decision
Đặt guard chặn ngay đầu cả hai hàm `targetWorker.onerror` và `targetWorker.onmessageerror`:
```javascript
targetWorker.onerror = (e) => {
  if (generation !== workerGeneration) {
    if (boundSession && !boundSession.isResolved) {
      boundSession.resolve(false);
    }
    return;
  }
  // Xử lý lỗi bình thường cho thế hệ hiện hành
  const currentSession = boundSession || activeRecoverySession;
  if (currentSession && currentSession.generation === generation) {
    if (currentSession.timer) {
      clearTimeout(currentSession.timer);
      currentSession.timer = null;
    }
    currentSession.resolve(false);
  }
  handleWorkerFatalError(e.message || "Lỗi runtime trong Web Worker");
};
```
Tương tự cho `targetWorker.onmessageerror`:
```javascript
targetWorker.onmessageerror = () => {
  if (generation !== workerGeneration) {
    if (boundSession && !boundSession.isResolved) {
      boundSession.resolve(false);
    }
    return;
  }
  const currentSession = boundSession || activeRecoverySession;
  if (currentSession && currentSession.generation === generation) {
    if (currentSession.timer) {
      clearTimeout(currentSession.timer);
      currentSession.timer = null;
    }
    currentSession.resolve(false);
  }
  handleWorkerFatalError("Lỗi giải mã thông điệp (message deserialization error)");
};
```
Điều này đảm bảo:
- Nếu Worker cũ gửi lỗi muộn (`generation !== workerGeneration`), sự kiện bị triệt tiêu ngay lập tức mà không gây tác dụng phụ lên Worker mới hoặc giao diện.
- `boundSession` cũ (nếu chưa giải quyết) được đóng với `false` để tránh rò rỉ bộ nhớ promise.
- Nếu là Worker hiện hành (`generation === workerGeneration`), lỗi được báo và xử lý nghiêm ngặt như thiết kế.

---

## 2. Multi-Session Worker Lifecycle Regression Tests (User Story 2 & FR-002)

### Test Suite Structure
File kiểm thử `tests/js/worker_resilience.test.mjs` hiện đã nằm trong thư mục `tests/js/*.test.mjs` được quét bởi `npm run test:unit`. Tuy nhiên, cần bổ sung các kịch bản kiểm thử hồi quy cụ thể:
1. **Late `onerror` Isolation**:
   - Khởi tạo Worker A (thế hệ 1).
   - Kích hoạt phục hồi cưỡng chế sang Worker B (thế hệ 2, `force: true`).
   - Worker B hoàn tất READY và tiếp nhận yêu cầu `render`.
   - Worker A kích hoạt sự kiện `onerror`.
   - Khẳng định: yêu cầu trên Worker B hoàn tất thành công, `getPendingRequestsCount()` trở về 0, không có `handleWorkerFatalError`, giao diện không chuyển sang lỗi.
2. **Late `onmessageerror` Isolation**:
   - Tương tự kịch bản trên nhưng Worker A kích hoạt `onmessageerror`.
   - Khẳng định: Worker B không bị ảnh hưởng.
3. **Current Generation Error Handling**:
   - Worker B (thế hệ hiện hành) kích hoạt `onerror` hoặc `onmessageerror`.
   - Khẳng định: yêu cầu trên Worker B bị reject với thông báo lỗi phù hợp, nút "Thử lại" mở khóa.

---

## 3. Context-Aware Number Measurement (User Story 3 & FR-003, FR-004)

### Problem Analysis
Trong `chuviettay/model/writer.py`, hàm `measure_text_width(self, text: str, scale: float = 1.0)` đo trước độ rộng của token để bộ bố cục `DocumentLayoutEngine._layout_inlines()` quyết định ngắt dòng hoặc phân mảnh token dài (`_partition_long_token_linear`).
Khi gặp chuỗi số (`NUMRE.match(nfc_text)`), `measure_text_width` mô phỏng cuộc gọi `self.number(nfc_text, k=k_idx)`.
Tuy nhiên:
1. `measure_text_width` không nhận tham số `context: SeedContext | None = None`.
2. Do đó, `number(nfc_text, k=k_idx)` luôn chạy với ngữ cảnh mặc định (`content_type="text"`).
3. Trong khi đó, tại thời điểm kết xuất thực tế:
   - Trong tiêu đề, `context_prefix = "heading"` và `tok_occ` lấy từ hạt giống tiêu đề.
   - Trong ô bảng, `context_prefix = "cell"` và `tok_occ` lấy từ ô bảng.
4. Khi kho mẫu có nhiều biến thể chữ số có bề rộng khác nhau (ví dụ chữ số `1` mảnh rộng 3.0pt nhưng biến thể viết nghiêng rộng 4.5pt), hạt giống khác nhau sẽ chọn biến thể khác nhau!
5. Hệ quả: Bề rộng ước lượng khi bố cục khác với bề rộng thực tế khi vẽ, dẫn đến tràn lề hoặc ngắt dòng sớm/muộn không mong muốn.

### Technical Decision
1. Mở rộng chữ ký hàm trong `chuviettay/model/writer.py`:
   ```python
   def measure_text_width(
       self,
       text: str,
       scale: float = 1.0,
       context: SeedContext | None = None,
   ) -> float:
   ```
2. Trong nhánh `NUMRE.match(nfc_text)` của `measure_text_width`:
   ```python
   if self.stable_variants:
       saved_counts = dict(self._token_counts)
       saved_last = dict(self.last)
       saved_token_last = dict(self._token_last)
       saved_ctx = (
           getattr(self, "_current_ctx_type", "text"),
           getattr(self, "_current_tok", ""),
           getattr(self, "_current_k", 0),
           getattr(self, "_char_idx", 0),
           getattr(self, "_current_context", None),
       )
       try:
           k_idx = self._token_counts.get(nfc_text, 0)
           _, rend_w, _ = self.number(nfc_text, k=k_idx, context=context)
           return rend_w * scale
       finally:
           self._token_counts = saved_counts
           self.last = saved_last
           self._token_last = saved_token_last
           (
               self._current_ctx_type,
               self._current_tok,
               self._current_k,
               self._char_idx,
               self._current_context,
           ) = saved_ctx
   ```
3. Trong `DocumentLayoutEngine._layout_inlines()` (`chuviettay/layout/engine.py`):
   Xác định `tok_occ` trước khi đo độ rộng và tạo `SeedContext`:
   ```python
   if getattr(inline, "token_occurrences", None) is not None and inline_tok_idx < len(inline.token_occurrences):
       tok_occ = inline.token_occurrences[inline_tok_idx]
   else:
       tok_occ = self._doc_token_counts.get((context_prefix, tok), 0)

   from chuviettay.model.rng import SeedContext
   ctx = SeedContext(
       content_type=context_prefix,
       element_id=tok,
       occurrence=tok_occ,
       sub_index=0,
   )
   est_w = self.wr.measure_text_width(tok, context=ctx) * self.S * scale_mult
   ```
   Điều này đảm bảo phép đo độ rộng dùng đúng 100% biến thể chữ số sẽ được vẽ.

---

## 4. Optical Punctuation, Decimal, and Math Delimiter Spacing (User Story 4 & FR-005, FR-006, FR-007, FR-008)

### Problem Analysis & Visual Proof
Từ hình ảnh người dùng tải lên (`media_1792488673943_817ed8ee.png`), xuất hiện 3 điểm nghẽn thị giác dính nét:
1. **Dấu ngoặc toán học chạm chữ số/biến số**:
   Trong biểu thức `F_X(1)` và `P(2 <= X <= 5)`, dấu ngoặc mở `(` và đóng `)` được phân tích cú pháp thành `SymbolNode('(')` và `SymbolNode(')')` trong `MathRow`.
   Trong `MathLayoutEngine._row_gaps()`, khoảng cách giữa ký hiệu mở/đóng và ký tự thông thường (`ord` / `num`) được gán:
   `gap = em * _HUG` với `_HUG = 0.02`.
   Với `em = 7.0 * 1.6 = 11.2pt`, khoảng cách này chỉ bằng `0.22pt` (~0.08mm)!
   Trong khi độ dày nét bút là 0.35mm - 0.50mm, khoảng hở nhỏ hơn bề dày nét bút khiến chữ số `1` hoặc `4` đè sát hoặc dính chập vào nét vòng cung của dấu `)`.
2. **Dấu phẩy/chấm thập phân trong chuỗi số**:
   Trong `Writer.number()`, khi gặp dấu phẩy `,` giữa hai chữ số (ví dụ `0,39`, `0,19`, `0,20`):
   - Dấu phẩy được đặt tại `x + p_gap` với `p_gap = 0.08 * xh`.
   - Chữ số tiếp theo được đặt tại `x += p_gap + p_w + 0.10 * xh` và `gap = 0.0`.
   - Khi nét của chữ số `0` vươn về bên phải hoặc dấu phẩy có đuôi móc vươn về bên phải, khoảng cách hình học này biến thành va chạm nét mực.
3. **Dấu câu sau từ trong văn bản thường**:
   Trong `Writer.token()`, khi kết xuất cụm `ta có:`, phần thân `có` có dấu sắc `\u0301`. Nếu dấu câu đi kèm (`:`, `,`, `;`) được đặt căn cứ vào advance width danh nghĩa thay vì biên phải nét vẽ cực đại (`core_max_x`), dấu câu có nguy cơ chạm vào nét đuôi của chữ hoặc dấu thanh.

### Technical Decision
1. **Trong `MathLayoutEngine._row_gaps` và `_m_Delimited`**:
   - Tăng `_HUG` từ `0.02` lên `0.08` (đạt khoảng cách quang học `~0.90pt` đến `1.1pt`, tương đương `>= 0.12 * xh`).
   - Trong `_m_MathRow`, bổ sung kiểm tra sàn khoảng hở quang học thực tế giữa biên phải của glyph trước và biên trái của glyph sau:
     Nếu `item[i]` là `SymbolNode('(')` hoặc `item[i+1]` là `SymbolNode(')')`, khoảng cách biên hình học tối thiểu giữa chúng được bảo đảm:
     `clearance = max(0.12 * self.xh * eff, 0.85 * pen_w)`.
   - Trong `_m_Delimited`, `pad = max(1.2 * eff, 0.14 * self.xh * eff)`.
2. **Trong `Writer.number()`**:
   - Khi đặt dấu `,` hoặc `.`:
     Tính `prev_ink_max_x = max((pt for s_ in out for pt in s_[0::2]), default=x)`.
     Sàn khoảng hở trước dấu phẩy: `p_gap = max(p_gap, (prev_ink_max_x + max(0.10 * xh, 0.8 * pen_w)) - x)`.
     Tính `comma_ink_max_x = max((pt for s_ in p_st for pt in s_[0::2]), default=p_w) + (x + p_gap)`.
     Sàn khoảng hở sau dấu phẩy: `x = max(x + p_gap + p_w + 0.10 * xh, comma_ink_max_x + max(0.10 * xh, 0.75 * pen_w))`.
   - Cơ chế này tự động bảo toàn 100% Golden Master trên `tiny_bank` vì `tiny_bank` có advance width rộng sẵn (`x` danh nghĩa đã vượt quá ngưỡng sàn), nhưng trên kho mẫu thật hoặc chữ viết tay dày nét, sàn quang học sẽ tự kích hoạt đẩy dạt ra, ngăn ngừa dính nét hoàn toàn.
3. **Trong `Writer.token()`**:
   - Tính toán biên trái thực tế của dấu câu: `p_min_x = min((pt for s_ in p_st for pt in s_[0::2]), default=0.0)`.
   - Vị trí đặt dấu câu: `place_x = x - p_min_x if p_min_x < 0 else x`.
   - Bảo đảm khoảng hở giữa các dấu `trail` liên tiếp tối thiểu `max(0.60 * pen_w, 0.14 * xh)`.
   - Bổ sung vector fallback cho `:` và `;` trong `get_vector_glyph_fallback` nếu kho mẫu chưa dạy các ký hiệu này.
