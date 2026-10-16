# Implementation Plan: Khắc phục CI Pyodide Golden Master, An toàn Giao dịch Lưu trữ & Cứng hóa Worker

**Branch**: `041-ci-pyodide-storage-hardening` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/041-ci-pyodide-storage-hardening/spec.md`

---

## Summary

Dự án hiện có một lỗi CI đã được xác nhận tại bước "Verify Golden Master in Pyodide" (`scripts/test_golden_pyodide.mjs`) ở ca kiểm thử `markdown_list`. Nguyên nhân do ca kiểm thử không truyền tùy chọn `missing_grid=True` (vốn đã được chuyển sang mặc định `False` từ Feature 040), dẫn đến tệp lưới phụ `_thieu.xopp` không được tạo, đồng thời đoạn mã chẩn đoán gom chung lỗi tệp phụ vào mã băm tệp chính khiến console in ra hai chuỗi SHA giống hệt nhau nhưng vẫn báo `FAIL`. 

Kế hoạch này giải quyết dứt điểm lỗi CI trên, đồng thời hoàn thiện 3 nhóm kiến trúc trọng yếu theo rà soát kỹ thuật độc lập:
1. **Lớp lưu trữ (`storage.js`)**: Chuyển giao các thao tác ghi dữ liệu sang chờ xác nhận `tx.oncomplete` ở cấp transaction, xử lý `tx.onerror` và `tx.onabort` (bắt lỗi `QuotaExceededError`), triệt tiêu độ lệch timestamp đồng bộ đa tab, và cung cấp cơ chế tuần tự hóa dự phòng an toàn khi trình duyệt thiếu `navigator.locks`.
2. **Vòng đời Worker (`app.js`, `py-worker.js`)**: Bổ sung timeout cho `sendWorkerMessage`, lắng nghe `worker.onerror` và `worker.onmessageerror` để dọn dẹp các yêu cầu treo và hỗ trợ thử lại, kiểm tra nghiêm ngặt mã trạng thái HTTP (`resp.ok`) khi tải wheel DOCX tải lười để dừng ngay khi có lỗi mạng thay vì âm thầm bỏ qua.
3. **An toàn DOM & Thống nhất tài liệu**: Chuẩn hóa việc dựng DOM trong modal ký hiệu LaTeX (`write.js`) bằng `document.createElement`/`textContent`, và đồng bộ hóa tài liệu `README.md` với ma trận kiểm thử CI thực tế (Python 3.12, 3.13, 3.14).

---

## Technical Context

**Language/Version**: Python >=3.10 (ma trận CI chính thức: 3.12, 3.13, 3.14), JavaScript ES Modules (ES2022+), WebAssembly (Pyodide 314.0.7), Node.js >= 20.x  
**Primary Dependencies**: Pyodide 314.0.7, Playwright, pytest, ruff  
**Storage**: IndexedDB (`chuviettay_web`, stores: `profiles`, `app_settings`), MEMFS ảo trong Pyodide WebAssembly  
**Testing**: `scripts/test_golden_pyodide.mjs` (Pyodide Node.js test runner), `pytest` (Python 1235+ tests), `npm run test:unit`, `npm run test:browser`, Playwright E2E (`multitab.spec.ts`, `e2e.spec.ts`)  
**Target Platform**: Trình duyệt hiện đại (Chrome, Edge, Firefox, Safari), Linux CI runner (Ubuntu)  
**Project Type**: Headless Python Engine + Client-side Web SPA (WASM/Pyodide)  
**Performance Goals**: Pyodide Golden Master 8/8 tests pass trong < 15s; thao tác commit transaction IndexedDB < 50ms; Worker RPC round-trip thông thường < 50ms  
**Constraints**: 
- Duy trì cố định phiên bản Pyodide `"314.0.7"` trong `package.json`.
- Tuyệt đối không can thiệp hoặc thay đổi mã băm tham chiếu một cách cơ học khi chưa xác định đúng nguyên tắc kết xuất.
- Tuân thủ nguyên tắc Loose Coupling, High Cohesion và Zero-GUI dependencies của kiến trúc lõi.  
**Scale/Scope**: 642 tệp mã nguồn, trọng tâm tác động tập trung vào 5 tệp: `scripts/test_golden_pyodide.mjs`, `webapp/js/storage.js`, `webapp/js/app.js`, `webapp/js/worker/py-worker.js`, `webapp/js/write.js`, cùng tài liệu `README.md`.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá | Ghi chú tuân thủ |
| :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | **PASS** | Tách bạch rõ ràng logic xác thực tệp chính và tệp lưới phụ trong Golden Master; chuẩn hóa wrapper transaction dùng chung trong `storage.js`; mã nguồn tự tài liệu hóa với chú thích tường minh. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Sử dụng wrapper transaction chuẩn của IndexedDB, Promise timeout đơn giản, và fallback lease lock tối giản; không đưa thêm thư viện bên ngoài hoặc trừu tượng hóa quá mức. |
| **III. Comprehensive Automated Testing** | **PASS** | Tái hiện và kiểm chứng trực tiếp bằng `node scripts/test_golden_pyodide.mjs` và các test suite đơn vị `npm run test:unit`, `npm run test:browser`, `pytest`. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Giữ nguyên hợp đồng giao tiếp giữa main thread và Worker qua message passing; module lưu trữ đóng gói toàn bộ logic transaction trong `storage.js`. |
| **Quality Gates & CI Verification** | **PASS** | Mọi thay đổi đều được kiểm tra qua Ruff lint, compileall, pytest core, web dist build, Pyodide golden master, JS unit/browser tests. |

---

## Project Structure

### Documentation (this feature)

```text
specs/041-ci-pyodide-storage-hardening/
├── plan.md              # Kế hoạch thực thi (/speckit-plan)
├── research.md          # Phân tích nguyên nhân và quyết định kỹ thuật (Phase 0)
├── data-model.md        # Thực thể và mô hình trạng thái (Phase 1)
├── quickstart.md        # Hướng dẫn chạy và kiểm chứng kịch bản (Phase 1)
├── contracts/           # Các giao ước giao diện kỹ thuật (Phase 1)
│   ├── golden-test-contract.md
│   ├── storage-transaction-contract.md
│   └── worker-lifecycle-contract.md
├── checklists/
│   └── requirements.md  # Checklist yêu cầu kỹ thuật
└── tasks.md             # Danh sách tác vụ cụ thể (/speckit-tasks)
```

### Source Code Layout (affected components)

```text
d:\viet\app\
├── scripts/
│   ├── test_golden_pyodide.mjs         # [AFFECTED] Sửa WriteOptions(missing_grid=True) & tái cấu trúc chẩn đoán
│   └── build_web.py                    # Build dist web client
├── webapp/
│   └── js/
│       ├── storage.js                  # [AFFECTED] tx.oncomplete wrapper, timestamp sync fix, locks fallback
│       ├── app.js                      # [AFFECTED] sendWorkerMessage timeout, worker.onerror/messageerror
│       ├── write.js                    # [AFFECTED] LaTeX symbols DOM safety (createElement/textContent)
│       └── worker/
│           └── py-worker.js            # [AFFECTED] Fail-fast fetch for lazy DOCX wheels
├── tests/
│   ├── test_golden_master_real_path.py # Đối chiếu CPython Golden Master
│   ├── js/                             # Kiểm thử đơn vị lưu trữ & worker (Node --test)
│   └── e2e/multitab.spec.ts            # Kiểm thử E2E đa tab (Web Locks & No Locks)
├── README.md                           # [AFFECTED] Đồng bộ ma trận phiên bản Python CI
└── pyproject.toml                      # Khai báo cấu hình dự án
```

**Structure Decision**: Cấu trúc module hoá hiện tại của ứng dụng được giữ nguyên vẹn. Các cải tiến được áp dụng trực tiếp tại các điểm tiếp giáp thành phần (boundaries) mà không gây biến động cấu trúc thư mục dự án.

---

## Complexity Tracking

*Không phát sinh vi phạm nguyên tắc thiết kế.* Không cần bảng ngoại lệ phức tạp.

---

## Implementation Phases & Strategy

### Phase 1: Khắc phục CI Pyodide Golden Master (US1 - P1)
1. Trong `scripts/test_golden_pyodide.mjs`:
   - Bổ sung `missing_grid=True` vào lời gọi `ctl_l.write_document(doc_l, WriteOptions(seed=19, missing_grid=True), out_l)`.
   - Tách bạch cấu trúc kết quả kiểm tra `test_results` để lưu độc lập thông tin tệp chính `.xopp` và tệp lưới `_thieu.xopp`.
   - Nâng cấp vòng lặp báo cáo kết quả JavaScript để in thông tin chẩn đoán chuẩn hóa theo `golden-test-contract.md` (bao gồm trạng thái tồn tại, kích thước byte, mã băm mong đợi so với mã băm nhận được).
2. Kiểm chứng tức thì: chạy `node scripts/test_golden_pyodide.mjs` và xác nhận 8/8 ca kiểm thử vượt qua.

### Phase 2: An toàn Giao dịch Lưu trữ & Khóa Đa tab (US2 - P1)
1. Trong `webapp/js/storage.js`:
   - Viết hàm dùng chung `executeTransaction(db, storeNames, mode, operationFn)` lắng nghe `tx.oncomplete`, `tx.onerror`, và `tx.onabort` (bảo toàn `QuotaExceededError` từ `lastRequestError`).
   - Chuyển đổi `saveProfile`, `setSetting`, và `deleteProfile` sang dùng transaction wrapper, bảo đảm Promise chỉ `resolve()` sau khi commit thành công.
   - Sửa hàm `saveProfile` để trả về đúng bản ghi có `updated_at` cuối cùng; trong `syncAndSaveActiveProfile`, gán `localSyncedTimestamp = savedProfile.updated_at` để triệt tiêu hiện tượng lệch dấu thời gian.
   - Bổ sung cơ chế khóa dự phòng trong `requestProfileLock` kết hợp in-memory Promise queue nội bộ tab và Optimistic Concurrency Control (OCC qua kiểm tra `expectedUpdatedAt`) khi thiếu `navigator.locks`.
2. Kiểm chứng với `npm run test:unit` (`tests/js/storage.test.mjs`) và kiểm thử đa tab `npx playwright test tests/e2e/multitab.spec.ts`.

### Phase 3: Cứng hóa Vòng đời Worker & Nạp Wheel DOCX (US3 - P2)
1. Trong `webapp/js/app.js`:
   - Bổ sung tham số `timeoutMs` (mặc định 60.000ms) vào `sendWorkerMessage`, cài đặt timer tự động dọn dẹp `pendingRequests` và reject Promise khi quá hạn.
   - Thêm `worker.onerror` và `worker.onmessageerror` trong `initWorker()`, kích hoạt quy trình dọn dẹp và thông báo lỗi có khả năng phục hồi.
2. Trong `webapp/js/worker/py-worker.js`:
   - Thêm kiểm tra `resp.ok` khi fetch từng wheel DOCX; nếu thất bại hoặc có lỗi kết nối, lập tức throw `Error` rõ tên gói và mã HTTP, không ghi nhận gói vào `loadedWheels`.
3. Kiểm chứng các luồng lỗi và timeout.

### Phase 4: An toàn DOM Bảng Ký hiệu & Đồng bộ Tài liệu (US4 - P3)
1. Trong `webapp/js/write.js`:
   - Tái cấu trúc `loadLatexSymbols()` để sử dụng `document.createElement()`, `textContent`, và `container.replaceChildren()`, loại bỏ toàn bộ việc nội suy biến thô vào `innerHTML`.
2. Trong `README.md`:
   - Điều chỉnh mô tả ma trận kiểm thử CI để thống nhất chuẩn xác với `.github/workflows/ci.yml` (Python 3.12, 3.13 và 3.14 future-proofing).
3. Kiểm thử toàn diện: chạy lại toàn bộ quy trình CI cục bộ (Ruff, compileall, pytest, build_web, test_golden_pyodide, test:unit, test:browser).
