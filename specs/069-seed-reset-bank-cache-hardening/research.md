# Research & Technical Decisions: Xóa Lịch sử Hạt giống, Hoàn thiện Bộ nhớ đệm Kho mẫu và Kiểm chứng Nâng cao (seed-reset-bank-cache-hardening)

Tài liệu này tổng hợp các phân tích kỹ thuật, phương án giải quyết và lý do lựa chọn cho các yêu cầu trong tính năng `069-seed-reset-bank-cache-hardening`.

---

## Decision 1: Giao thức Xóa Lịch sử Hạt giống (Seed History Reset Protocol) xuyên suốt các lớp Web

### Ngữ cảnh & Vấn đề
Trong `AppController`, thuộc tính `_last_doc` và `_last_seed` lưu lại tài liệu của lần kết xuất gần nhất để `align_document_seeds` đối chiếu khi `opts.stable_variants == True`. Khi người dùng xóa trắng ô soạn thảo trên Web Client, `triggerPreviewImmediate()` phát hiện `!text.trim()` nên gọi `clearPreview()` và `return`, không gửi bất kỳ yêu cầu nào xuống Web Worker. Khi người dùng mở tệp mới (`handleFileImport`), nội dung mới được đưa vào `textarea` và kết xuất ngay lập tức mà không xóa `_last_doc` cũ. Kết quả: tài liệu mới bị đối chiếu nhầm với tài liệu cũ, khiến các từ trùng nhau kế thừa sai lệch chỉ số `occurrence`.

### Các phương án cân nhắc
1. **Phương án A: Gửi yêu cầu `write_text` rỗng (`text = ""`) xuống Worker**
   - *Ưu điểm*: Tận dụng nhánh `if not document.blocks: self.clear_document_history()` sẵn có trong `AppController.write_document`.
   - *Nhược điểm*: Tạo gánh nặng tính toán dư thừa (khởi tạo DocumentLayoutEngine, tạo file tạm `.xopp` trên MEMFS, đọc base64 rỗng). Hơn nữa, `clearPreview()` trên giao diện là thao tác tức thời, không nên phụ thuộc vào luồng render bất đồng bộ.
2. **Phương án B: Bổ sung thông điệp chuyên biệt `clear_document_history` đi từ Web UI $\to$ Worker $\to$ Bridge $\to$ AppController**
   - *Ưu điểm*: Cực kỳ nhẹ nhàng (lightweight), không sinh file tạm, không tốn tài nguyên CPU, phản ánh chính xác ngữ nghĩa của hành động.
   - *Nhược điểm*: Cần thêm một handler nhỏ trong `py-worker.js` và `BrowserBridge`.

### Quyết định lựa chọn: Phương án B
Triển khai thông điệp chuyên biệt `clear_document_history`:
- **`chuviettay/browser/bridge.py`**:
  ```python
  def clear_document_history(self) -> dict[str, Any]:
      """Đặt lại lịch sử tài liệu để lượt viết tiếp theo không đối chiếu hạt giống với tài liệu cũ."""
      try:
          self._ctl.clear_document_history()
          return {"ok": True}
      except Exception as e:
          return _err_res(e)
  ```
- **`webapp/js/worker/py-worker.js`**:
  ```javascript
  case "clear_document_history": {
    pyodide.runPython(`_bridge_res = _bridge.clear_document_history()`);
    const pyRes = pyodide.globals.get("_bridge_res").toJs({ dict_converter: Object.fromEntries });
    self.postMessage({ id, ...pyRes });
    break;
  }
  ```
- **`webapp/js/write.js`**:
  - Trong `triggerPreviewImmediate()`: khi `!text.trim()`, gọi `sendWorkerMessage("clear_document_history").catch(console.error)` đồng thời với `clearPreview()`.
  - Trong `handleFileImport()`: gọi `await sendWorkerMessage("clear_document_history").catch(console.error)` trước khi nạp tệp mới và gọi `triggerPreviewImmediate()`.

---

## Decision 2: Thời điểm Cam kết Bộ nhớ đệm Bản chụp Kho mẫu (Bank Snapshot Cache Commitment Timing)

### Ngữ cảnh & Vấn đề
Trong `webapp/js/bank.js`, `lastBankSnapshotCache` hiện được gán `{ epoch, revision: rev, profileId: activeProfileId }` ngay sau khi nhận phản hồi từ Worker, trước khi tổng hợp danh sách và gọi `applyFiltersAndRender()`. Nếu bước render DOM gặp ngoại lệ (ví dụ phần tử DOM chưa sẵn sàng, lỗi layout, hoặc lỗi logic), `lastBankSnapshotCache` đã ghi nhận thành công. Ở lần gọi `refreshBankView(false)` tiếp theo, hàm kiểm tra cache và thoát sớm (`return`), khiến giao diện tiếp tục hiển thị trống hoặc lỗi mà không thể tự phục hồi.

### Các phương án cân nhắc
1. **Phương án A: Bỏ hoàn toàn cache, luôn render lại**
   - *Nhược điểm*: Lãng phí tài nguyên render DOM thẻ chữ (hàng trăm thẻ SVG) mỗi khi người dùng chuyển qua lại giữa các tab hoặc khi nhận tín hiệu đồng bộ nhẹ.
2. **Phương án B: Cam kết có điều kiện (Two-Phase Cache Commit)**
   - Lưu trữ khóa phiên bản mới vào biến tạm `pendingCacheKey`.
   - Thực thi `applyFiltersAndRender()`.
   - Chỉ khi `applyFiltersAndRender()` kết thúc thành công 100%: gán `lastBankSnapshotCache = pendingCacheKey`.
   - Nếu xảy ra lỗi: đặt lại `lastBankSnapshotCache = { epoch: null, revision: null, profileId: null }` để vô hiệu hóa hoàn toàn cache.

### Quyết định lựa chọn: Phương án B
Đảm bảo tính trọn vẹn và tự phục hồi (resilience) của giao diện kho mẫu.

---

## Decision 3: Đo kiểm Hình thái Nét Toàn diện (Full Stroke Geometry Parity)

### Ngữ cảnh & Vấn đề
Trong bài kiểm thử `test_app_controller_stable_variants_workflow` (`tests/test_stable_variants.py`), mã nguồn hiện mới chỉ so sánh `strokes1[0] == strokes2[0]`. Điều này chỉ chứng minh nét đầu tiên của từ đầu tiên không đổi, chưa bao quát toàn bộ các nét của các từ khác được giữ lại sau thao tác chèn từ vào giữa câu.

### Giải pháp kỹ thuật
- Trích xuất toàn bộ danh sách chuỗi nét vẽ (`strokes`) từ cả hai tệp XOPP kết xuất.
- Đối chiếu toàn bộ mảng nét vẽ của từ `"xin"` đầu tiên (`doc1` vs `doc2`).
- Đối chiếu toàn bộ mảng nét vẽ của từ `"chào"` đầu tiên (`doc1` vs `doc2`).
- Đối chiếu toàn bộ mảng nét vẽ của từ `"ba"` cuối câu (`doc1` vs `doc2`).
- Trong `test_align_document_seeds_multi_step_consecutive_edits`, bổ sung dòng kiểm tra tường minh: `assert occs_d3[3] == 1, f"Token 'học' mới chèn phải nhận occ=1, nhận {occs_d3[3]}"`.

---

## Decision 4: Đo kiểm Hiệu năng Kho mẫu Đa biến thể Quy mô lớn (Multi-Variant Bank Benchmark)

### Ngữ cảnh & Vấn đề
Bài kiểm thử `test_bank_snapshot_large_scale_performance` trong `tests/test_performance_regression.py` hiện sinh 1.030 nhãn nhưng mỗi nhãn chỉ có duy nhất 1 mẫu nét (`sample`). Trong thực tế, kho mẫu phong phú sẽ có từ 3 đến 5 biến thể trên mỗi chữ để tạo hiệu ứng viết tay tự nhiên không trùng lặp.

### Giải pháp kỹ thuật
- Nâng cấp dữ liệu sinh trong bài benchmark:
  - 700 từ ngữ (`word_0` $\to$ `word_699`): mỗi từ có 3 biến thể nét $\to$ 2.100 samples.
  - 300 chữ cái (`ch_0` $\to$ `ch_299`): mỗi chữ có 4 biến thể nét $\to$ 1.200 samples.
  - 20 ký hiệu và 30 dấu thanh: mỗi nhãn có 2 biến thể nét $\to$ 100 samples.
  - Tổng số mẫu nét: **3.400+ samples** trên 1.050 nhãn.
- Kiểm tra tính đúng đắn của dữ liệu trả về từ `get_bank_snapshot()`:
  - `stats["n_letters"] >= 300`
  - `stats["n_samples"] >= 3400`
  - Thời gian thực thi $t < 200$ ms.

---

## Decision 5: Đồng bộ hóa Tài liệu Kỹ thuật và Báo cáo Kiểm toán

### Giải pháp kỹ thuật
- Chuẩn hóa đường dẫn: Cập nhật mọi tham chiếu từ `tests/test_browser_bridge.py` về tệp hiện hữu `tests/test_bridge.py`.
- Đồng bộ số lượng E2E test: Cập nhật tài liệu phản ánh chính xác **20/20 bài kiểm thử Playwright E2E** đã vượt qua trên CI Run #71.
- Minh bạch số liệu kiểm thử Python:
  - Môi trường CI (Python 3.12 / 3.13 trên Linux runner): `1.405 passed · 14 skipped · 7 deselected` (do bỏ qua các kiểm thử phụ thuộc Word COM / GUI Tkinter của máy cục bộ).
  - Môi trường phát triển cục bộ (Windows): `1.426 passed`.
