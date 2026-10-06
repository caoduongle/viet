# Phase 0: Research & Key Design Decisions

**Feature**: Chuyển đổi mô hình mẫu chữ sang thuần Ký Tự và Nạp lưới tạo kho mẫu (`specs/024-kho-ky-tu`)  
**Context**: Kiến trúc MVC hiện tại của repo `chuviettay`, Python lõi + Web Client (Pyodide Worker) + Desktop GUI (Tkinter) + CLI.

---

## 1. Technical Context & Resolved Clarifications

| Unknown / Item | Resolution / Decision | Rationale | Alternatives Considered |
|---|---|---|---|
| **D1: Phạm vi kho mẫu & tương thích kho cũ** | Kho chỉ lưu và dùng các phân loại ký tự đơn: `letters`, `digits`, `punct`, `symbols`, `marks`. Bỏ mục `words` trong UI/teaching/assembly. Khi load kho cũ có `words`, `Bank` vẫn giữ trong dict nội bộ để khi save không làm mất dữ liệu người dùng. | Bảo vệ dữ liệu người dùng (Hiến pháp I & IV), không gây breaking change với các file kho cá nhân cũ. | Xóa sạch `words` khi save (bị cấm theo R4/D1); Migrate biến `words` thành ký tự (không khả thi vì từ gồm nhiều ký tự dính nhau). |
| **D2: Danh mục một nguồn (`char_catalog.py`)** | Tạo module mới `chuviettay/model/char_catalog.py` chứa các bộ ký tự chuẩn (`co_ban`, `toan_hy_lap`, `mo_rong`, `day_du`). Cả `tao_luoi_day_du.py` (CLI `grid`), Desktop GUI, Web Client đều dùng chung nguồn này. | Tránh lệch bộ ký tự giữa các nền tảng (Single Source of Truth). | Giữ danh sách riêng trong `tao_luoi_day_du.py` và hardcode trong frontend JS (dễ lệch nhau). |
| **D3: Phân loại ký tự chuẩn (`classify_char`)** | Hàm `text_utils.classify_char(label) -> Literal['letters', 'digits', 'punct', 'symbols', 'marks']`. Kiểm tra theo Unicode categories kết hợp danh mục thanh dấu rời (`\u0300`, `\u0301`, `\u0303`, `\u0309`, `\u0323` hoặc các dấu thanh riêng biệt). | Thống nhất phân loại giữa nạp lưới, dạy tay, bridge và UI. | Cho người dùng tự chọn loại ký tự bằng tay trong UI (dễ sai sót). |
| **D4: Bearing chuẩn (LSB/RSB) & Chống giãn chữ (F2)** | Nạp lưới và dạy tay tính `lsb/rsb` theo bounding box nét chữ hoặc giá trị mặc định theo contour; không lấy khoảng cách tới mép ô lưới hw3 (F2). Thêm guard trong `Writer.assemble_word`: `lsb = min(lsb, 0.3 * xh)`, `rsb = min(rsb, 0.3 * xh)` nếu giá trị dương lớn bất thường. | Sửa dứt điểm lỗi chữ bị giãn 10 lần khi nạp lưới. | Bỏ hoàn toàn bearing (chữ dính sát nhau không tự nhiên). |
| **D5: Hiệu chỉnh cỡ tay bằng ký tự mốc (`pick_calib_char`)** | Thêm hàm `calibration.pick_calib_char(bank)` ưu tiên tìm các ký tự chuẩn đo x-height ('n', 'o', 'a', 'm', 'u') thay vì tìm từ trong `bank.words`. | Khi bỏ `bank.words`, tính năng tính tỷ lệ co giãn mẫu tay vẫn hoạt động chuẩn xác 100%. | Hardcode lấy ký tự bất kỳ (nếu lấy phải chữ có nét đuôi g/y sẽ sai x-height). |
| **D6: API Dạy mẫu thống nhất** | Thay `teach_word` + `teach_letter` bằng một phương thức duy nhất: `AppController.teach_char(label, strokes, bbox)`. | Tinh gọn controller, áp dụng KISS/YAGNI. | Giữ nguyên `teach_letter` và để `teach_word` rỗng (thừa mã nguồn chết). |
| **D7: Cập nhật x-height kho sau nạp lưới** | Nếu kho rỗng (`xh == 0` hoặc mặc định), nạp lưới sẽ tính trung vị chiều cao các chữ cái chuẩn x-height và gán cho `bank.xh`. Nếu kho đã có xh, chỉ cập nhật nếu độ lệch > 3% có cảnh báo. | Giúp văn bản sinh ra có tỷ lệ chính xác ngay sau khi nạp lưới mà không cần thao tác phụ. | Luôn ghi đè `bank.xh` (làm mất cấu hình tùy chỉnh của người dùng). |
| **D8: Kết quả nạp lưới `GridImportResult`** | Trả về dataclass chứa: `total_cells`, `cells_with_ink`, `added_samples`, `duplicate_samples`, `empty_cells`, `skipped_multi_char`, `rejected_cells`. | Báo cáo minh bạch trên cả CLI, GUI Tkinter và Web modal. | Chỉ trả về số nguyên `count` đơn giản (người dùng không biết vì sao một số ô không được nhận). |

---

## 2. Component Architecture & Integration Points

```mermaid
flowchart TD
    subgraph Model Layer [chuviettay/model]
        CC[char_catalog.py] --> GI[xopp.py: import_char_grid]
        TU[text_utils.py: classify_char] --> GI
        GI --> BK[bank.py: Bank]
        CAL[calibration.py: pick_calib_char] --> BK
        WR[writer.py: Writer (Luôn assemble_word)] --> BK
    end

    subgraph Controller Layer [chuviettay/controller]
        AC[app_controller.py: AppController] --> BK
        AC --> WR
        AC --> GI
        AC --> CC
    end

    subgraph Adapters & Interfaces
        CLI[cli.py] --> AC
        BR[browser/bridge.py] --> AC
        GUI[view/ tkinter tabs] --> AC
        WEB[webapp / py-worker.js] --> BR
    end
```

---

## 3. Best Practices & Risk Mitigation

1. **Test-Driven Refactoring (Đỏ trước - Xanh sau)**:
   - Viết test tái hiện F2 (bearing lệch), F3 (thiếu char_catalog), F4 (classify_char), F7 (thiếu calib_char) ngay trong P0.
   - Chạy test suite sau mỗi pha và chỉ commit khi 100% test pass.
2. **Backward Compatibility**:
   - Kho JSON cũ có trường `words` vẫn load thành công, không văng ngoại lệ.
   - File lưới `.xopp` cũ chứa 343 cụm ghép chữ (khi sinh bằng `--with-clusters`) sẽ được importer nhận diện và bỏ qua an toàn, ghi nhận vào `skipped_multi_char`.
3. **Web Worker Performance**:
   - `bridge.py` serialize `GridImportResult` sang dict JSON thuần túy để truyền qua `postMessage` giữa Pyodide worker và UI thread không bị nghẽn.
