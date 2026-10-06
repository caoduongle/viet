# Contract: Teach Queue & Character Learning API

**Modules**: `chuviettay.view.teach_tab`, `webapp/js/teach.js`, `chuviettay.browser.bridge`
**Feature**: `026-remove-whole-words`
**Date**: 2026-10-06

## 1. Hành vi Ô Nhập Thêm Hàng Đợi (`add_from_text`)

### Quy tắc xử lý
Khi người dùng nhập văn bản $T$ vào ô thêm (ví dụ `"học tiếng Việt"`):
1. Chuẩn hóa $T$ bằng `unicodedata.normalize('NFC', T.strip())`.
2. Trích xuất danh sách ký tự đơn lẻ phân biệt:
   - Loại bỏ khoảng trắng (` `), xuống dòng (`\n`), và ký tự tab.
   - Duyệt từng ký tự $c \in T$.
3. Với mỗi ký tự $c$:
   - Kiểm tra xem ký tự này đã có mẫu trong kho chưa (`bank.letters`, `bank.digits`, `bank.punct`, `bank.symbols`, `bank.marks`).
   - Nếu chưa có đủ số lượng mẫu khuyến nghị (ví dụ $< 3$ mẫu) và chưa có trong hàng đợi hiện tại $\rightarrow$ Thêm $c$ vào hàng đợi.
4. Giao diện hiển thị danh sách các ký tự đơn lẻ trong hàng đợi.

---

## 2. Thao tác Lưu Nét Vẽ (`save_current`)

### Desktop GUI (`TeachTab.save_word`)
1. Lấy ký tự hiện tại `label = self.current`.
2. Chuyển đổi nét vẽ trên canvas sang đơn vị kho mẫu.
3. Nếu đang trong chế độ hiệu chỉnh cỡ tay (`_calib_pending`):
   - Tính hệ số `session_scale` mới dựa trên các mẫu có sẵn của `label` trong `bank.letters`.
   - Cập nhật `session_scale`.
4. Gọi `ctl.teach_char(label, rel, width)` (lưu vào `letters`, `digits`, `punct`, `symbols`, hoặc `marks`).
5. Không gọi `ctl.teach_word()` trong bất kỳ trường hợp nào.

### Web Client (`TeachManager.saveChar` trong `teach.js`)
1. Gửi request tới Worker:
   ```javascript
   const res = await this.worker.request("teach_char", {
       label: this.current,
       pixel_strokes: pixelStrokes,
       calibrating: this.isCalibrating,
       deferred_save: true,
   });
   ```
2. Worker nhận và gọi `_bridge.teach_char(...)`.
3. Không gửi yêu cầu dạng `teach_sample` với phân loại `words`.
