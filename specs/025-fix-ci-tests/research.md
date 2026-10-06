# Research & Decisions: 025 — Sửa lỗi CI Kiểm Thử Tự Động

## 1. Dò tìm Python Interpreter trên đa hệ điều hành cho Node.js Test Harness

### Bối cảnh & Vấn đề
Trong `tests/e2e/sw-update.spec.ts`, kịch bản cần build lại static site bằng lệnh:
```typescript
execSync("py -3 scripts/build_web.py", { encoding: "utf-8" });
```
Trên Windows, `py` là trình launcher chuẩn có sẵn. Tuy nhiên trên Linux (GitHub Actions runner `ubuntu-latest`) và macOS, tiện ích `py` không hề tồn tại trong PATH, dẫn đến lỗi:
```text
/bin/sh: 1: py: not found
```

### Quyết định kỹ thuật
Xây dựng hàm `runBuildWeb(distDir: string)` sử dụng danh sách ứng viên (candidate interpreters):
1. `process.env.PYTHON` (nếu người dùng hoặc CI chỉ định rõ).
2. `["py", ["-3"]]` (chỉ khi `process.platform === "win32"`).
3. `["python3", []]`.
4. `["python", []]`.

Hàm sử dụng `execFileSync` thay vì shell string, bắt mã lỗi `ENOENT` để thử lần lượt. Nếu xảy ra lỗi khác (ví dụ build thất bại thật sự), lập tức ném ngoại lệ lên để không nuốt lỗi.

### Giải pháp thay thế đã xem xét
- **Cố định `python3`**: Trên một số môi trường Windows cũ, `python3` không trỏ đúng vào Python 3 mà có thể mở Windows Store.
- **Dùng `npm run build:web`**: `package.json` có script `"build:web": "py -3 scripts/build_web.py"`, lệnh này vẫn bị cố định `py -3` và không truyền được tham số `--dist`.
- **Kết luận**: Thử danh sách ứng viên có lọc theo `platform` là giải pháp bền vững nhất cho mọi môi trường phát triển và CI.

---

## 2. Cách ly Tài nguyên Tĩnh cho Kịch bản Service Worker Update (Concurrency Isolation)

### Bối cảnh & Vấn đề
Khi Playwright chạy với 2 workers (`--workers=2`):
- Worker A đang chạy `sw-update.spec.ts`.
- Worker B đang chạy song song một test khác (như `write.spec.ts`, `first-run.spec.ts`, `grid-import.spec.ts`).
- Server chính đang lắng nghe ở cổng `8000` và trỏ vào thư mục `webapp/dist`.
- Khi Worker A ghi đè file nguồn `app.js` và chạy `build_web.py`, thư mục `webapp/dist` bị xoá sạch và tạo lại với hash mới.
- Hệ quả: Worker B gặp lỗi 404, file bị gián đoạn, hoặc Service Worker của Worker B tự động reload trang do phát hiện hash mới, gây lỗi `Element is intercepted` hoặc click hỏng.

### Quyết định kỹ thuật
- Nâng cấp `scripts/serve.mjs`:
  ```javascript
  const PORT = Number(process.env.PORT) || 8000;
  const DIST_DIR = path.resolve(process.env.DIST_DIR || "webapp/dist");
  ```
  Thêm xử lý `decodeURIComponent` và kiểm tra an toàn:
  ```javascript
  if (filePath !== DIST_DIR && !filePath.startsWith(DIST_DIR + path.sep)) {
    res.writeHead(403, { "Content-Type": "text/plain" });
    res.end("Forbidden");
    return;
  }
  ```
- Trong `sw-update.spec.ts`:
  - Tạo thư mục tạm thời riêng biệt: `fs.mkdtempSync(path.join(os.tmpdir(), "viet-sw-dist-"))`.
  - Chạy `build_web.py --dist <tmpDist>`.
  - Khởi động một tiến trình `serve.mjs` riêng biệt với cổng `8101` (`SW_PORT = 8101`).
  - Toàn bộ bài test chỉ tương tác với `http://localhost:8101`.
  - Thư mục `webapp/dist` và cổng `8000` hoàn toàn không bị chạm tới!

---

## 3. Tương thích Kiểm thử Tkinter GUI cho Dialog Chọn Bộ Ký tự

### Bối cảnh & Vấn đề
Trước Feature 024, tab Dạy chữ có nút "Từ thông dụng" gọi `t.add_seed()`, mở hộp thoại `simpledialog.askinteger` để hỏi số lượng từ cần nạp từ bộ 700 từ SEED.
Sau Feature 024 (R3/P4), nút này được đổi thành "Bộ ký tự…", mở hộp thoại Toplevel con cho phép người dùng chọn giữa các nhóm catalog (`co_ban`, `toan_hy_lap`, `mo_rong`, `day_du`) và bấm "Nạp ký tự" hoặc "Huỷ".
Bài test cũ `test_nap_tu_thong_dung` trong `tests/test_gui.py` vẫn mock `simpledialog.askinteger` (hàm này không còn được gọi) và mong đợi `len(t.queue) == 6`, dẫn đến lỗi `assert 1 == 6` trong CI với Xvfb.

### Quyết định kỹ thuật
Thay thế `test_nap_tu_thong_dung` bằng hai hàm test:
1. `_bam_nut_trong_hop_thoai_bo_ky_tu(t, nhan)`: Hàm trợ giúp duyệt cây widget con của tab để tìm `Toplevel` và kích hoạt nút `TButton` có nhãn mong muốn (`invoke()`).
2. `test_nap_bo_ky_tu_co_ban`:
   - Bấm `add_seed()`.
   - Tìm hộp thoại và bấm "Nạp ký tự".
   - Khẳng định `t.queue` chứa danh sách ký tự trả về từ `ctl.get_missing_chars("co_ban", exclude=["tôi"])`.
   - Khẳng định không có phần tử trùng lặp.
   - Khẳng định hiển thị thông báo `showinfo`.
3. `test_huy_bo_ky_tu_khong_them_gi`:
   - Bấm `add_seed()`.
   - Bấm "Huỷ".
   - Khẳng định `t.queue` vẫn rỗng và không có dialog nào hiện lên.
