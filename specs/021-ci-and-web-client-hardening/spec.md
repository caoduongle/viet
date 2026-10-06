# Feature Specification: 021 — Sửa lỗi CI và hoàn thiện Web Client

**Feature Branch**: `feat/021-fix-ci-and-web-client`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description:
> VAI TRÒ: Kỹ sư CI/CD + full-stack, repo ChuVietTay. Lõi Python thuần stdlib + web client tĩnh Pyodide 314.0.7 (Python 3.14) trong Web Worker. CI có 4 job: lint, test-core (3.12), web-client (Node 22 + Playwright), test-python-314.
> NGUYÊN TẮC: Chạy lại mọi lệnh kiểm chứng; mỗi Phần/mục một commit riêng; mỗi lỗi thật có test hồi quy; không đổi hành vi lõi chuviettay/, Golden Master 8/8 giữ nguyên hash; không sửa lệnh của job test-core / test-python-314.
> PHẦN A: SỬA 2 LỖI CI ĐANG ĐỎ (A1: build_web.py dist dir & an toàn; A2: test_build_web.py cách ly; A3: ci.yml; A4: dọn cấu hình).
> PHẦN B: LỖI THẬT TÌM THẤY KHI RÀ SOÁT (B1: SW không cập nhật; B2: mở .docx thiếu typing-extensions; B3: test JS ngoài CI; B4: cân bằng Node với Render; B5: độ bền cache SW; B6: hard-code version Python trong worker).
> PHẦN C: BÁO CÁO CUỐI.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sửa dứt điểm 2 lỗi CI đang đỏ để CI xanh 4/4 jobs (Priority: P1 — Phần A)

Là kỹ sư phần mềm duy trì dự án,
tôi muốn các job CI (`lint`, `test-core`, `web-client`, `test-python-314`) chạy qua 100% xanh mà không bị lỗi do thiếu `node_modules` hay xung đột phiên bản `pyinstaller` trên Python 3.14,
để mọi PR và commit mới được bảo vệ tự động bởi hệ thống kiểm thử CI.

**Why this priority**: Hai lỗi CI đang chặn toàn bộ luồng phát triển và kiểm thử tự động của repository.

**Independent Test**:
- Chạy `pip install -r requirements-dev.txt` trên môi trường Python 3.14 thành công.
- Chạy `pytest -m "not benchmark"` trong môi trường không có `node_modules/` mà không bị lỗi (các test web được skip an toàn).
- Chạy với `REQUIRE_WEB_BUILD=1` khi có `node_modules/` -> toàn bộ bài test `test_build_web.py` pass.
- Chạy `scripts/build_web.py --dist <root>` hoặc `--dist /` -> chặn đứng ngay lập tức với mã lỗi `exit != 0` và không xoá nhầm repo.

**Acceptance Scenarios**:
1. **Given** môi trường Python 3.14 sạch, **When** chạy `pip install -r requirements-dev.txt`, **Then** cài đặt thành công 100% vì không còn `pyinstaller==6.12.0`.
2. **Given** job `test-core` hoặc `test-python-314` không chạy `npm ci`, **When** chạy `pytest tests/`, **Then** các ca kiểm thử `test_build_web.py` được bỏ qua (`skipped`) sạch sẽ thay vì fail vì thiếu `node_modules/pyodide`.
3. **Given** biến môi trường `REQUIRE_WEB_BUILD=1` nhưng không có `node_modules/pyodide`, **When** chạy test, **Then** bài test phải FAIL (không được skip) để bắt lỗi trên CI job `web-client`.
4. **Given** chạy `scripts/build_web.py --dist <path>`, **When** `<path>` là gốc repo, thư mục cha của repo, filesystem root, hoặc thư mục con trong `webapp/` (ngoại trừ `webapp/dist`), **Then** script raise SystemExit ngay TRƯỚC khi rmtree và bảo vệ toàn vẹn repo.
5. **Given** `scripts/build_web.py`, **When** sinh `version.json`, **Then** trường `pyodide_version` được đọc động từ `node_modules/pyodide/package.json` thay vì chuỗi cứng.
6. **Given** tải wheels vendor từ mạng, **When** gặp lỗi mạng hoặc HTTP 5xx, **Then** tự động retry tối đa 3 lần với timeout 60s; không retry khi gặp mã lỗi HTTP 4xx.

---

### User Story 2 - Khắc phục các lỗi ngầm trong Service Worker, định dạng .docx và hạ tầng JS (Priority: P2 — Phần B)

Là người dùng Web Client và lập trình viên,
tôi muốn:
1. Trình duyệt tự động cập nhật Service Worker và nạp phiên bản web mới nhất khi có bản dựng mới;
2. Mở tài liệu `.docx` thành công trên web mà không gặp lỗi thiếu `typing_extensions`;
3. Tất cả các bộ unit test JS (`tests/js/`, `tests/browser/`) được thực thi trên CI;
4. Service Worker cài đặt an toàn (fail nếu thiếu core assets);
5. Không hard-code đường dẫn Python 3.14 trong worker script.

**Why this priority**: Đây là các lỗi chức năng thực tế ngoài thực địa làm trải nghiệm người dùng bị đóng băng ở bản cũ, gãy tính năng mở file `.docx`, và thiếu vắng kiểm thử JS trên CI.

**Independent Test**:
- Playwright E2E: Deploy bản v1 -> chờ SW active -> đổi nội dung app.js và build lại bản v2 -> reload -> xác nhận app hiển thị nội dung v2.
- Playwright E2E: Mở file Word mẫu qua `#input-open-file` -> văn bản hiển thị đầy đủ trong textarea soạn thảo.
- Chạy `npm run test:unit` và `npm run test:browser` -> 100% test JS và bridge browser pass độc lập trên Windows và Linux.

**Acceptance Scenarios**:
1. **Given** `scripts/build_web.py` thực hiện build, **When** ghi `dist/sw.js`, **Then** `CACHE_NAME` được sinh động theo mã băm nội dung của `dist` và `PRECACHE_URLS` được lập động từ danh sách tệp thực tế trong `dist`.
2. **Given** file `.docx` được tải lên giao diện web, **When** worker xử lý nạp module `docx`, **Then** wheel `typing_extensions` đã được giải nén sẵn trong `site-packages` trước `python_docx`, tài liệu được chuyển đổi thành công.
3. **Given** script `tests/js/zip.test.mjs`, **When** chạy trên Linux/macOS hoặc Windows, **Then** tự động xác định đúng binary Python (`python3` hoặc `py -3`) và pass.
4. **Given** quá trình cài đặt Service Worker (`sw.js install`), **When** tải các tài nguyên cốt lõi (wasm, stdlib, chuviettay.zip, wheels), **Then** nếu bất kỳ tài nguyên nào bị lỗi tải, quá trình cài đặt phải reject để không đưa SW vào trạng thái nửa vời.
5. **Given** Web Worker `worker.js` và kịch bản test, **When** xác định đường dẫn `site-packages`, **Then** đường dẫn được trích xuất động từ Python runtime (qua `sysconfig` / `site`) thay vì ghim cứng `/lib/python3.14/site-packages`.

---

### Edge Cases
- **Mạng chập chờn khi build**: Hàm tải wheel có retry 3 lần, timeout 60s, không retry 404/403.
- **Thư mục dist tuỳ biến**: Đảm bảo dọn dẹp an toàn tuyệt đối, không xoá nhầm bất kỳ thư mục mã nguồn nào.
- **Node version chênh lệch**: CI kiểm tra khớp `.node-version` (Node 24.16.0). Nếu có xung đột thư viện giữa Node 22 và Node 24, phải báo cáo trung thực.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `scripts/build_web.py` MUST hỗ trợ tham số dòng lệnh `--dist <thư mục>` với giá trị mặc định là `webapp/dist`.
- **FR-002**: `prepare_dist_dir()` trong `scripts/build_web.py` MUST kiểm tra và từ chối thực thi (raise `SystemExit`) TRƯỚC khi gọi `rmtree` nếu đường dẫn là `ROOT_DIR`, tổ tiên của `ROOT_DIR`, gốc hệ thống tập tin, hoặc nằm trong `webapp/` (trừ `webapp/dist`).
- **FR-003**: `scripts/build_web.py` MUST gọi `require_pyodide_runtime()` kiểm tra sự tồn tại của `node_modules/pyodide` TRƯỚC khi xoá thư mục dist cũ.
- **FR-004**: `version.json` MUST đọc trường `version` từ `node_modules/pyodide/package.json` để gán cho `pyodide_version`.
- **FR-005**: Hàm tải wheel trong `scripts/build_web.py` MUST đặt timeout 60 giây và thử lại tối đa 3 lần đối với lỗi kết nối hoặc HTTP 5xx; không thử lại khi gặp HTTP 4xx.
- **FR-006**: `pytest.ini` MUST đăng ký marker `web`. `tests/test_build_web.py` MUST sử dụng marker `web`, timeout 300s, và build vào thư mục tạm `tmp_path` mà không đụng tới `webapp/dist`.
- **FR-007**: `tests/test_build_web.py` MUST skip nếu thiếu `node_modules/pyodide`, TRỪ KHI biến môi trường `REQUIRE_WEB_BUILD=="1"` (khi đó bắt buộc phải fail).
- **FR-008**: `requirements-dev.txt` MUST loại bỏ `pyinstaller==6.12.0` và để lại ghi chú giải thích; `requirements-build.txt` giữ nguyên cho việc đóng gói binary.
- **FR-009**: `.github/workflows/ci.yml` job `web-client` MUST cài `pytest pytest-timeout` và chạy `tests/test_build_web.py` với `REQUIRE_WEB_BUILD: '1'` trước bước build dist chính. Job `test-python-314` đổi target sang `'3.14'`.
- **FR-010**: `pyproject.toml` MUST loại bỏ khối `[tool.pytest.ini_options]` trùng lặp để tránh cảnh báo của pytest.
- **FR-011**: `scripts/build_web.py` MUST tính mã băm SHA-256 các file trong dist và ghi `CACHE_NAME` cùng `PRECACHE_URLS` động vào `dist/sw.js`.
- **FR-012**: `scripts/vendor_lock.json` MUST bổ sung wheel `typing_extensions-4.15.0-py3-none-any.whl`, được worker nạp trước `python_docx`.
- **FR-013**: `package.json` MUST bổ sung các scripts `test:unit` và `test:browser`. Kịch bản `tests/js/zip.test.mjs` MUST chạy được trên cả Windows và POSIX.
- **FR-014**: Service Worker `install` event MUST reject nếu bất kỳ asset cốt lõi nào tải thất bại.
- **FR-015**: Worker script và test runner MUST xác định đường dẫn `site-packages` động thay vì hard-code `/lib/python3.14/site-packages`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 4/4 jobs CI trên GitHub Actions (`lint`, `test-core`, `web-client`, `test-python-314`) chạy qua thành công 100%.
- **SC-002**: Đạt 8/8 Golden Master Pyodide 314.0.7 trùng khớp từng byte SHA-256 (`node scripts/test_golden_pyodide.mjs`).
- **SC-003**: Đạt 100% tests Playwright E2E gồm cả test cập nhật SW và test upload mở file `.docx`.
- **SC-004**: Đạt 100% unit tests JS (`npm run test:unit`) và browser tests (`npm run test:browser`).
- **SC-005**: 1.116/1.116 unit tests CPython của repo tiếp tục pass sạch sẽ mà không có bất kỳ thay đổi nào làm gãy mã nguồn lõi `chuviettay/`.

---

## Assumptions

- Môi trường CI GitHub Actions có kết nối mạng bình thường để cài đặt dependencies npm/pip.
- `requirements-build.txt` phục vụ riêng cho các lập trình viên cần đóng gói desktop exe trên Python <3.14 và không can thiệp vào CI web.
- Phiên bản Pyodide hiện tại ghim trong package.json là 314.0.7 tương ứng với CPython 3.14.
