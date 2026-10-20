# Research & Technical Decisions: 048-worker-recovery-ui-hardening

## 1. Worker Recovery Session Isolation (User Story 1 & User Story 4)

### Problem
Trong `webapp/js/app.js`, hàm `recoverWorker()` có một race condition tinh vi trong khối `finally`:
```javascript
} finally {
  if (session) {
    if (session.timer) {
      clearTimeout(session.timer);
      session.timer = null;
    }
    if (!session.isResolved) {
      session.resolve(false);
    }
  }
  if (activeRecoverySession === session) {
    activeRecoverySession = null;
  }
  clearHandshakeTimer = null;
  if (btnRetry) {
    btnRetry.disabled = false;
    if (success) {
      btnRetry.style.display = "none";
    } else {
      btnRetry.style.display = "inline-block";
    }
  }
  isRecovering = false;
  recoveryPromise = null;
}
```
Khi phiên A đang chạy và người dùng kích hoạt phiên B (`force: true`), `activeRecoverySession` được trỏ sang B. Tuy nhiên, khi A kết thúc (dù là timeout hay reject), khối `finally` của A vẫn thực hiện:
- `isRecovering = false;`
- `recoveryPromise = null;`
- `btnRetry.disabled = false;`

Hậu quả: Ngay sau khi A kết thúc, trạng thái toàn cục báo `isRecovering = false` và nút Thử lại được mở khóa, mặc dù phiên B thực tế vẫn đang khởi tạo! Nếu có một lời gọi `recoverWorker()` thứ ba (phiên C), hệ thống sẽ coi như không có phiên nào đang chạy và khởi tạo thêm một Worker thứ 3, gây xung đột và lãng phí tài nguyên.

Tương tự, trong `attachWorkerHandlers()` khi bước khởi tạo giao diện sau tín hiệu `READY` (`initTimeout`) bị quá hạn:
```javascript
currentSession.timer = setTimeout(() => {
  if (currentSession && !currentSession.isResolved) {
    handleWorkerFatalError(`Khởi tạo giao diện sau phục hồi quá thời gian chờ (${initTimeout}ms)`);
    currentSession.resolve(false);
  }
}, initTimeout);
```
Khối này chỉ báo lỗi mà không gọi `targetWorker.terminate()`, không tăng `workerGeneration` và không xóa tham chiếu `worker = null`. Worker bị treo vẫn tiếp tục sống như một zombie worker trong nền.

### Technical Decision
1. **Cô lập khối `finally` chỉ cho phiên hiện hành**:
   ```javascript
   } finally {
     if (session) {
       if (session.timer) {
         clearTimeout(session.timer);
         session.timer = null;
       }
       if (!session.isResolved) {
         session.resolve(false);
       }
     }
     // CHỈ phiên hiện hành mới được cập nhật trạng thái toàn cục
     if (activeRecoverySession === session) {
       activeRecoverySession = null;
       clearHandshakeTimer = null;
       if (btnRetry) {
         btnRetry.disabled = false;
         if (success) {
           btnRetry.style.display = "none";
         } else {
           btnRetry.style.display = "inline-block";
         }
       }
       isRecovering = false;
       recoveryPromise = null;
     }
   }
   ```
2. **Chấm dứt vật lý Worker khi quá hạn sau `READY`**:
   ```javascript
   currentSession.timer = setTimeout(() => {
     if (currentSession && !currentSession.isResolved) {
       if (targetWorker && typeof targetWorker.terminate === "function") {
         try {
           targetWorker.terminate();
         } catch (_) {}
       }
       if (worker === targetWorker) {
         worker = null;
       }
       workerGeneration++;
       handleWorkerFatalError(`Khởi tạo giao diện sau phục hồi quá thời gian chờ (${initTimeout}ms)`);
       currentSession.resolve(false);
     }
   }, initTimeout);
   ```

### Alternatives Considered
- *Sử dụng biến đếm phiên phục hồi (`recoveryCount`)*: Bổ sung thêm biến đếm nhưng phức tạp hơn việc đối chiếu trực tiếp con trỏ đối tượng `activeRecoverySession === session`. Đối chiếu đối tượng là an toàn và đặc trưng 1-1.

---

## 2. CI Integration for Worker Resilience Tests (User Story 2)

### Problem
Trong `package.json`, script chạy unit test là:
```json
"test:unit": "node --test \"tests/js/*.test.mjs\""
```
Trước đây có 2 tệp kiểm thử Worker resilience:
1. `tests/test_worker_resilience.mjs` (nằm trực tiếp dưới `tests/`, chứa 4 test mới cho US1 và US2 nhưng không được CI chạy vì pattern `tests/js/*.test.mjs` không khớp).
2. `tests/js/worker_resilience.test.mjs` (nằm trong `tests/js/`, chứa 11 test cũ nhưng chưa có các test mới của commit `d3c93b4`).

### Technical Decision
1. **Hợp nhất toàn bộ bài test vào `tests/js/worker_resilience.test.mjs`**:
   - Di chuyển và tích hợp 4 test từ `tests/test_worker_resilience.mjs` vào `tests/js/worker_resilience.test.mjs`.
   - Bổ sung ca kiểm thử khẳng định `isRecovering` vẫn là `true` và `btnRetry.disabled === true` khi phiên cũ kết thúc trong lúc phiên mới đang chạy.
   - Bổ sung ca kiểm thử khẳng định Worker bị `terminate()` và `workerGeneration` tăng lên khi timeout sau `READY`.
2. **Xóa tệp dư thừa `tests/test_worker_resilience.mjs`** để tránh nhầm lẫn và trùng lặp mã nguồn.
3. Giữ nguyên script `package.json` hoặc mở rộng đảm bảo mọi tệp `.test.mjs` trong `tests/js/` đều được thực thi tự động.

---

## 3. Full UI Event Listener Rollback & Observer Teardown (User Story 3)

### Problem
1. **`TeachController`**: Phương thức `_bindEvents()` đăng ký các sự kiện trực tiếp trên các nút DOM và sự kiện `keydown` trên `document` mà không nhận `AbortSignal` hay có phương thức `destroy()`. Khi `onWorkerReady()` chạy lại, một thể hiện `TeachController` mới được tạo và đăng ký chồng thêm listener trên `document`.
2. **`setupPreviewNavigation`** trong `write.js`: Khởi tạo `ResizeObserver` theo dõi `#preview-stage` nhưng không lưu lại tham chiếu để `disconnect()` và không lắng nghe sự kiện `abort` từ `options.signal`.
3. **`initQuotaAndBackupReminders`** trong `app.js`: Đăng ký sự kiện click trên `#btn-quota-backup`, `#btn-toast-dismiss`, `#btn-toast-backup` mỗi khi `initUI()` chạy mà không kiểm tra cờ đánh dấu đã gắn.

### Technical Decision
1. **`TeachController` hỗ trợ `signal` và `destroy()`**:
   - Nhận `options.signal` trong `constructor` hoặc `init({ signal })`.
   - Tất cả các sự kiện (kể cả trên `document`) được gắn với `{ signal: this.signal }` hoặc lưu lại hàm xử lý để `destroy()` có thể `removeEventListener`.
   - Nếu `TeachController.init()` được gọi lại trên cùng một thể hiện hoặc một thể hiện mới, thể hiện cũ được giải phóng sạch sẽ.
2. **`ResizeObserver` gắn với `signal`**:
   - Lưu trữ biến module-level `activePreviewResizeObserver`.
   - Nếu `activePreviewResizeObserver` đã tồn tại, gọi `disconnect()` trước khi tạo observer mới.
   - Nếu `options.signal` được cung cấp, đăng ký `options.signal.addEventListener("abort", () => observer.disconnect(), { once: true })`.
3. **Lũy đẳng cho `initQuotaAndBackupReminders`**:
   - Gắn cờ thuộc tính trên phần tử (ví dụ `btn.__hasBackupListener`) hoặc sử dụng `AbortSignal` chuyển từ `uiAbortController`.

---

## 4. Extreme Digit Geometry Sanitization & Multi-Variant Width Parity (User Story 5)

### Problem
1. **Mẫu chữ số suy biến**: Trong `chuviettay/model/writer.py`, phương thức `_normalize_digit_sample(inst, ch, xh)`:
   - Nếu mẫu chữ số có `sample_h <= 1e-3` (ví dụ một chấm điểm hoặc nét phẳng nằm ngang), thuật toán rơi vào nhánh `scale_x, scale_y = 1.0, 1.0` và `adv_w` có thể bằng 0.0 nếu `raw_max_x - raw_min_x <= 1e-3`. Nếu `raw_w` cũng không có, mẫu trở nên tàng hình và gây sai lệch độ rộng.
2. **Độ rộng trong kho mẫu đa biến thể**:
   - `measure_text_width()` đo chữ số dựa vào `get_char_advance_width(ch)`, vốn luôn lấy biến thể đầu tiên `sample = b.digits[char][0]`.
   - `Writer.number()` sử dụng `self.pick(lib, "d" + ch)` dựa trên seed / ScopedRNG.
   - Khi kho mẫu có nhiều biến thể chữ số với độ rộng khác nhau, `measure_text_width()` và `number()` có thể lệch nhau quá $0.05 \times x_h$.
   - Tương tự, `_resolve_dgap()` dùng ScopedRNG để chọn trong danh sách `dgaps`, trong khi `measure_text_width()` dùng trung bình cộng `avg_g`.

### Technical Decision
1. **Khử suy biến trong `_normalize_digit_sample`**:
   - Nếu `sample_h <= 1e-3` hoặc `bbox_w <= 1e-3`, áp dụng kích thước dự phòng chuẩn:
     `adv_w = max(raw_w, 0.60 * eff_xh)` và tạo nét dự phòng chuẩn tắc từ `get_vector_glyph_fallback(ch, xh=eff_xh)` nếu danh sách nét rỗng hoặc suy biến.
2. **Đồng bộ `measure_text_width` với `number`**:
   - Với chuỗi số (`NUMRE.match(nfc_text)`), khi `self.stable_variants=True`:
     Để độ rộng dự đoán khớp hoàn hảo với `number()`, `measure_text_width()` mô phỏng đúng bước chọn biến thể và `_resolve_dgap` theo ngữ cảnh của chuỗi số mà không làm biến đổi `self.last` hay `self.counts`.
   - Hoặc với chế độ đo nhanh không context, kiểm tra tính toán dgap và advance width sao cho sai lệch cực đại $\le 0.05 \times x_h$.
3. **Thắt chặt assertion trong kiểm thử**:
   - Sửa các assert trong `test_system_hardening_feature_046.py` và `test_number_fraction_typography.py` để kiểm tra trực tiếp bounding box thực tế của các nét vẽ sau khi kết xuất.
