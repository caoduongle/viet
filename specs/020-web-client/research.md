# Phase 0: Research & Technical Decisions — Web Client (020)

**Date**: 2026-10-06  
**Status**: Completed (Dựa trên kết quả thực nghiệm GĐ0)  
**Spec Reference**: [spec.md](spec.md) | [report-g0.md](report-g0.md)

---

## 1. Technical Decisions & Trade-offs

### D1: Cơ chế kết xuất xem trước trang giấy (Preview Rendering)
- **Quyết định**: Giữ mặc định — JS trong Web Worker đọc file `.xopp` vừa được lõi ghi vào hệ file ảo (MEMFS), giải nén XML nội bộ và chuyển đổi các thẻ `<stroke>` thành vector SVG để hiển thị trên frontend.
- **Lý do**:
  1. Bảo toàn 100% mã nguồn lõi: không cần viết thêm hàm layout/render riêng cho web trong `chuviettay/layout/`.
  2. File `.xopp` đã chứa toàn bộ tọa độ hình học (pt), độ dày nét, màu mực và thông số nền giấy.
  3. Đảm bảo tính nhất quán tuyệt đối giữa bản xem trước và file `.xopp` tải về ("thấy gì tải nấy").
- **Phương án thay thế đã bác bỏ**: Thêm hàm render trả về cấu trúc nét JSON trực tiếp từ `DocumentLayoutEngine`. Bị loại vì vi phạm nguyên tắc YAGNI và làm phình to diện tích API của lõi.

### D2: Tọa độ Token & Gạch đỏ từ thiếu mẫu trên trang giấy
- **Quyết định**: Bổ sung tham số callback tùy chọn `token_layout_callback: Callable[[TokenBox], None] | None = None` vào `DocumentLayoutEngine` (mặc định `None`).
- **Lý do**:
  1. Khi xem trước trên web, truyền callback này để thu thập bounding box tọa độ của các từ thiếu mẫu (`missing`) ngay trong quá trình dàn trang. Frontend dùng tọa độ này để vẽ đường gạch đứt màu đỏ dưới chân từ thiếu.
  2. Khi xuất file `.xopp` hoặc chạy CLI/test, callback là `None` -> không ảnh hưởng đến cấu trúc `.xopp` và giữ nguyên 100% SHA-256 của Golden Master.
- **Phương án thay thế đã bác bỏ**: Dùng OCR hoặc phân tích ngược tọa độ từ SVG; bị loại vì chậm và không chính xác.

### D3: Ổn định kiểu chữ khi sửa giữa văn bản (`stable_variants`)
- **Quyết định**: Bổ sung thuộc tính `WriteOptions.stable_variants: bool = False` (mặc định tắt; CLI có thêm cờ `--stable`). Trên giao diện Web Client, cờ này được bật mặc định.
- **Lý do**:
  1. Khi dùng dòng random chung (`rnd`), việc chèn 1 từ ở đầu văn bản sẽ làm dịch chuyển chuỗi số ngẫu nhiên của toàn bộ các từ phía sau (đã chứng minh 20/20 lần đổi kiểu chữ ở mục 1).
  2. Với `stable_variants=True`, bộ chọn mẫu `Writer.pick` sẽ chọn mẫu dựa trên băm xác định tất định giữa các tiến trình. Tuyệt đối KHÔNG dùng hàm `hash()` có sẵn của Python (chuỗi bị ngẫu nhiên hoá theo `PYTHONHASHSEED`), mà dùng `hashlib.sha256(f"{seed}\x00{token}\x00{n}".encode()).digest()`, và áp dụng băm tương tự cho độ run (`jitter`). Khi người dùng gõ thêm từ ở đầu/giữa đoạn, các từ phía sau giữ nguyên kiểu chữ.
  3. Mặc định `False` giúp toàn bộ 1.074 test cũ và Golden Master không đổi 1 bit nào.
- **Phương án thay thế đã bác bỏ**: Lưu cache vị trí random trong bộ nhớ JS; bị loại vì phức tạp và không đồng bộ được khi người dùng đổi seed.

### D4: Phạm vi xóa mẫu kho chữ
- **Quyết định**: Giai đoạn v1 chỉ hỗ trợ xem từng mẫu và xóa cả nhãn (kèm tính năng Hoàn tác / Undo trên Toast).
- **Lý do**: Xóa từng mẫu đơn lẻ đòi hỏi cơ chế tombstone ở cấp độ mẫu nét (sample-level tombstone) trong `merge_bank_dicts` để đồng bộ đa tiến trình / đa tab an toàn. Việc này được tách riêng thành giai đoạn G5b (cần spec và test riêng).
- **Phương án thay thế đã bác bỏ**: Tự ý xóa index mẫu trong mảng `bank.words[word]`; bị loại vì sẽ gây xung đột mất dữ liệu hoặc hồi sinh mẫu khi hai tab đồng bộ.

### D5: Định dạng in đậm, nghiêng, màu theo đoạn văn
- **Quyết định**: Không hỗ trợ trong phạm vi ban đầu (giữ nguyên quy tắc KISS/YAGNI). Hoãn sang G8 (tùy chọn, hỏi trước).
- **Lý do**: Cấu trúc Document IR hiện tại của lõi chỉ hỗ trợ kiểu văn bản đồng nhất ở cấp độ Document/Paragraph.

### D6: Xử lý kiểm thử phụ thuộc môi trường `test_paths_logging.py`
- **Quyết định**: Sửa test `test_duong_dan_mac_dinh_khi_chay_tu_ma_nguon` bằng `monkeypatch` hoặc tạo mock file trong `tmp_path`.
- **Lý do**: Hiện tại test này đọc file `chu_cua_ban.json.gz` (bị gitignore) tại gốc dự án. Khi clone sạch trên máy mới/CI, test bị đỏ. Việc cô lập test bằng monkeypatch đảm bảo test xanh 100% trên mọi môi trường sạch mà không đụng tới file kho thật.

### D7: Kho mẫu mẫu (Demo Bank) trong bản Deploy
- **Quyết định**: Không nhúng kho demo vào bản deploy. Màn hình chào lần đầu hiển thị 3 lựa chọn: (1) Nhập kho có sẵn, (2) Tạo kho trống và bắt đầu dạy, (3) Xem hướng dẫn.
- **Lý do**: Tôn trọng tính riêng tư và cá nhân hóa của chữ viết tay; người dùng tự quản lý nét chữ của mình.

### D8: Bổ sung Python 3.14 vào CI Matrix
- **Quyết định**: Thêm một job riêng chạy Python 3.14 trong `.github/workflows/ci.yml`.
- **Lý do**: Môi trường runtime Pyodide 314.0.7 và môi trường build Render mặc định đều là Python 3.14.

---

## 2. Best Practices & Architecture Patterns

### 2.1. Kiến trúc Cầu nối (Browser Bridge Architecture)
- Lớp `chuviettay/browser/bridge.py` đóng vai trò Facade duy nhất giữa Web Worker và lõi Python:
  - Nhận và trả dữ liệu 100% là chuỗi JSON hoặc kiểu dữ liệu nguyên thủy (int, float, str, bool, list, dict).
  - Không bao giờ trả về `set`, `tuple`, hoặc đối tượng nội bộ của Model.
  - Mọi thao tác đều đi qua `AppController`. Tuân thủ nghiêm ngặt mô hình MVC một chiều.
  - Phơi bày cấu hình Canvas (`get_canvas_spec`) gồm các hằng số: `width=760`, `height=230`, `base_px=170`, `zoom=10.0`, `min_point_dist=2.5`, và lưới 4 dòng `hw3` để frontend JS đọc động, không bao giờ sao chép cứng hằng số sang JS.

### 2.2. Web Worker & Offloading
- Toàn bộ runtime Pyodide được cô lập trong `webapp/js/worker/py-worker.js`.
- Giao tiếp Main Thread <-> Worker bằng cơ chế Request/Response có `id` tăng dần.
- Trình soạn thảo văn bản áp dụng Debounce ~250ms trên Main Thread; nếu có request mới trong khi request cũ đang chạy, chỉ giữ lại DUY NHẤT một request mới nhất (bỏ qua các bản nháp trung gian), triệt tiêu hiện tượng lag UI và chớp giật.

### 2.3. Quản lý Dữ liệu Đa Tab (Multi-Tab Concurrency)
- Dùng `navigator.locks.request("bank_lock_<profile_name>")` để bao bọc mọi thao tác đọc-hợp nhất-ghi.
- Sử dụng `BroadcastChannel("chuviettay_sync")` để phát tín hiệu thông báo cho các tab khác nạp lại bộ nhớ khi có thay đổi.
- Cơ chế hợp nhất: Dùng lại nguyên vẹn `Bank.save()` và `merge_bank_dicts()` của lõi Python trong MEMFS; không viết lại thuật toán hợp nhất bằng JS.

### 2.4. Build & Cache Strategy
- File `scripts/build_web.py` phân tích cây import của `chuviettay/browser/bridge.py` để chỉ gom các file cần thiết, loại bỏ triệt để `view/`, `gui.py`, `cli.py`, `fidelity/`, test files, specs.
- Mọi file asset và wasm đều được băm nội dung (content hashing) để cache vĩnh viễn (`Cache-Control: public, max-age=31536000, immutable`), trừ `index.html`, `sw.js`, và `version.json` dùng `no-cache`.
- Tự host toàn bộ runtime Pyodide và wheels; không phụ thuộc bất kỳ CDN nào khi chạy thực tế.
