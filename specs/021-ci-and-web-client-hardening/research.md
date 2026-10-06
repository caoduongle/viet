# Technical Research: 021 — Sửa lỗi CI và hoàn thiện Web Client

**Date**: 2026-10-06  
**Feature**: `specs/021-ci-and-web-client-hardening/`

## Phase 0: Research Decisions & Resolution of Technical Unknowns

### 1. Build Script CLI & An Toàn File System (A1)
- **Decision**:
  - Thêm `argparse` vào `scripts/build_web.py` với cờ `--dist <path>`, mặc định là `ROOT_DIR / "webapp" / "dist"`.
  - Trong `prepare_dist_dir(dist_dir)`: Kiểm tra an toàn trước khi gọi `shutil.rmtree(dist_dir)`:
    - Chuyển `dist_dir = dist_dir.resolve()` và `ROOT_DIR = ROOT_DIR.resolve()`.
    - Kiểm tra nếu `dist_dir == ROOT_DIR`, hoặc `ROOT_DIR in dist_dir.parents` (nghĩa là dist_dir là tổ tiên của ROOT_DIR), hoặc `dist_dir.parent == dist_dir` (filesystem root như `/` hay `C:\`), hoặc nếu `dist_dir.is_relative_to(ROOT_DIR / "webapp")` và `dist_dir != ROOT_DIR / "webapp" / "dist"`: raise `SystemExit(f"Lỗi: Thư mục đích {dist_dir} không an toàn!")`.
  - Đọc `node_modules/pyodide/package.json` để trích xuất `version` gán vào `pyodide_version` trong `version.json`.
  - Hàm `ensure_vendor_wheels`: Dùng `urllib.request.urlopen(req, timeout=60)`. Bọc trong vòng lặp thử lại tối đa 3 lần cho lỗi `urllib.error.URLError`, socket timeout, hoặc `urllib.error.HTTPError` với `code >= 500`. Nếu gặp `HTTPError` 4xx, raise ngay lập tức không retry.
- **Rationale**: Ngăn chặn rủi ro vô tình xoá mất mã nguồn dự án khi truyền nhầm đường dẫn `--dist`, đảm bảo tính tất định khi tải phụ thuộc từ internet và liên kết phiên bản Pyodide động.
- **Alternatives Considered**: Sử dụng các thư viện ngoài như `requests` hay `tenacity` bị loại bỏ vì nguyên tắc Zero Dependencies cho scripts lõi (chỉ dùng Python stdlib).

---

### 2. Cách ly Test Build Web (A2)
- **Decision**:
  - Đăng ký marker `web: các kiểm thử liên quan đến web client và đóng gói build_web` trong `pytest.ini`.
  - Viết lại `tests/test_build_web.py`:
    - Fixture `built_dist(tmp_path_factory)` gọi `build_web.main(["--dist", str(tmp_dist)])`.
    - Kiểm tra `webapp/dist/version.json` mtime không đổi trước và sau khi chạy test để chứng minh `webapp/dist` hoàn toàn không bị đụng chạm.
    - Test tách nhỏ: kiểm tra metadata `version.json` khớp `package.json`, kiểm tra đủ wheels, kiểm tra lọc sạch `chuviettay.zip` (có bridge/controller/model/layout/math/importer/document, không có view/gui/cli/fidelity), kiểm tra không chứa `*.json.gz`, `tests`, `specs`, `docs`, `__pycache__`.
    - Thêm test an toàn `test_prepare_dist_dir_safety(monkeypatch, tmp_path)` kiểm tra các trường hợp đường dẫn nguy hiểm, giả lập môi trường trong thư mục tạm, tuyệt đối không trỏ vào repo thật.
    - Cấu hình `@pytest.mark.timeout(300)` và skip logic:
      ```python
      PYODIDE_EXISTS = (ROOT_DIR / "node_modules" / "pyodide" / "package.json").exists()
      REQUIRE_WEB_BUILD = os.environ.get("REQUIRE_WEB_BUILD") == "1"
      if not PYODIDE_EXISTS:
          if REQUIRE_WEB_BUILD:
              pytest.fail("REQUIRE_WEB_BUILD=1 nhưng không tìm thấy node_modules/pyodide. Hãy chạy 'npm ci'!")
          else:
              pytest.skip("Bỏ qua test build_web vì chưa cài đặt node_modules/pyodide (chạy npm ci để kích hoạt).")
      ```
- **Rationale**: Giải quyết dứt điểm Lỗi 1 của CI: các job `test-core` và `test-python-314` không chạy `npm ci` sẽ skip các test này sạch sẽ, trong khi job `web-client` với `REQUIRE_WEB_BUILD=1` bắt buộc phải pass.

---

### 3. Service Worker Dynamic Hashing & Cache Update (B1, B5)
- **Decision**:
  - Trong `scripts/build_web.py`, sau khi copy frontend và sinh tài nguyên, duyệt qua toàn bộ các tệp trong `dist_dir` (trừ `sw.js`):
    - Tính SHA-256 từng file, tổng hợp thành một hash 12 ký tự (ví dụ `cache_hash = hashlib.sha256(combined_hashes).hexdigest()[:12]`).
    - Sinh `CACHE_NAME = f"chuviettay-cache-{cache_hash}"`.
    - Sinh `PRECACHE_URLS = [...]` từ danh sách tệp thực tế trong `dist_dir` (chuẩn hoá dạng relative path `./...`), loại bỏ các file không tồn tại (như `pyodide.asm.js`).
    - Đọc template `webapp/sw.js`, thay thế `CACHE_NAME` và `PRECACHE_URLS`, sau đó ghi đè vào `dist_dir / "sw.js"`.
  - Trong `sw.js`:
    - Ở sự kiện `install`: dùng `Promise.all(PRECACHE_URLS.map(...))` sao cho nếu tải bất kỳ file core assets nào bị lỗi (HTTP != 200 hoặc network failure), `install` promise reject ngay lập tức, ngăn Service Worker kích hoạt với bộ nhớ cache thiếu hụt.
- **Rationale**: Giải quyết triệt để lỗi Service Worker không cập nhật khi deploy bản mới (B1) và lỗi cache thiếu âm thầm khi mạng chập chờn (B5).

---

### 4. Hỗ trợ Mở File Word `.docx` và Typing-Extensions trong Pyodide (B2, B6)
- **Decision**:
  - `python-docx 1.1.2` yêu cầu `typing_extensions >= 4.9.0`. Trong Pyodide 314.0.7, `typing-extensions 4.15.0` đã có sẵn trong `pyodide-lock.json` với file name `typing_extensions-4.15.0-py3-none-any.whl`, SHA-256 `4fec68770a05408e668a4fa53d6bf4f0f684b9dacf820c7c5d6e97d3ad225e29`.
  - Thêm wheel này vào `scripts/vendor_lock.json` (stage lazy).
  - Khử hard-code `/lib/python3.14/site-packages` (B6): Trong `py-worker.js`, lấy `site_packages` động bằng Python:
    ```python
    import site
    site_packages = site.getsitepackages()[0]
    ```
  - Trong nhánh `import_docx` của `py-worker.js`: Nạp `typing_extensions` TRƯỚC `python_docx`. Dùng `zipfile.ZipFile.extractall(site_packages)` (đã kiểm chứng hoạt động tốt với pure python wheels).
- **Rationale**: Đảm bảo mở tệp `.docx` không bị crash do `ImportError: No module named 'typing_extensions'`, đồng thời tương thích tương lai khi Pyodide nâng cấp phiên bản Python.

---

### 5. Chuẩn hoá Scripts Kiểm thử JS & Môi trường Render (B3, B4)
- **Decision**:
  - Sửa `tests/js/zip.test.mjs`:
    ```javascript
    const pythonCmd = process.env.PYTHON || (process.platform === "win32" ? "py -3" : "python3");
    ```
    Dùng `execSync` / `execFileSync` linh hoạt.
  - Cập nhật `package.json`:
    - `"test:unit": "node --test 'tests/js/*.test.mjs'"`
    - `"test:browser": "node tests/browser/test_bridge_no_tkinter.mjs && node tests/browser/test_bank_merge_memfs.mjs"`
  - Tích hợp 2 lệnh này vào CI job `web-client`.
  - Đối với Node version (B4): CI hiện đang dùng Node 22, Render dùng Node 24.16.0. Thử nghiệm chạy bộ test trên Node 24 cục bộ; nếu hoàn toàn tương thích, cập nhật CI sang dùng `.node-version`.
