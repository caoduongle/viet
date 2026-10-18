# Implementation Plan: Feature 043 — Khôi phục Worker Tin cậy và Ổn định Ngữ cảnh Seed Kết xuất

**Branch**: `043-worker-recovery-seed-stability` | **Date**: 2026-10-18 | **Spec**: [spec.md](file:///d:/viet/app/specs/043-worker-recovery-seed-stability/spec.md)

**Input**: Feature specification from `specs/043-worker-recovery-seed-stability/spec.md`

---

## Summary

Feature 043 giải quyết hai trụ cột cốt lõi theo trình tự 4 giai đoạn có kiểm soát:
1. **Giai đoạn 1 (Web Worker Recovery & Storage Hardening - P1/P2)**:
   - Sửa lỗi `recoverWorker()` trong [`webapp/js/app.js`](file:///d:/viet/app/webapp/js/app.js) báo thành công giả: chỉ trả về `true` và ẩn `#btn-worker-retry` sau khi nhận `READY` và hoàn tất toàn bộ `onWorkerReady()` (bao gồm `load_bank`).
   - Áp dụng timeout 10s (`WORKER_INIT_TIMEOUT_MS = 10000`) cho bước chờ sẵn sàng; xử lý đầy đủ `ERROR`, `onerror`, `onmessageerror`, lỗi `onWorkerReady()` và lỗi khởi tạo đồng bộ.
   - Chuyển `incrementTeachCount()` và `resetTeachCount()` trong [`webapp/js/storage.js`](file:///d:/viet/app/webapp/js/storage.js) sang giao dịch `readwrite` nguyên tử, chống hồi sinh hồ sơ đã xóa và đồng bộ `localSyncedTimestamp`.
2. **Giai đoạn 2 (Chuẩn hóa `SeedContext` & Cam kết Bất biến Chỉnh sửa - P1)**:
   - Thiết lập `SeedContext` thống nhất trong [`chuviettay/model/rng.py`](file:///d:/viet/app/chuviettay/model/rng.py) và truyền xuyên suốt từ [`DocumentLayoutEngine`](file:///d:/viet/app/chuviettay/layout/engine.py) / [`FidelityLayoutEngine`](file:///d:/viet/app/chuviettay/fidelity/engine.py) tới [`Writer`](file:///d:/viet/app/chuviettay/model/writer.py).
   - Khắc phục 3 lỗi rò rỉ ngữ cảnh trong `Writer`: cô lập `_token_last` theo `(content_type, element_id, tag)`, bảo toàn ngữ cảnh token cha khi `Writer.token()` gọi `Writer.number()`, và cố định chỉ số `jitter` trong `Writer.assemble_word()`.
   - Triển khai `align_document_seeds(base_doc, edited_doc)` (dùng `difflib.SequenceMatcher` LCS) và hỗ trợ `stable_id` trên nút IR để bảo toàn `occurrence` của phần tử cũ ngay cả khi chèn nội dung trùng lặp.
3. **Giai đoạn 3 (Ổn định Seed cho Khoảng cách Từ, Toán học và Bảng - P2)**:
   - Dẫn xuất `wgap` từ cặp `(prev_item.token_id, curr_item.token_id)`.
   - Sửa `MathLayoutEngine._scratch()` và `layout_lines()` trong [`chuviettay/layout/math_layout.py`](file:///d:/viet/app/chuviettay/layout/math_layout.py) sao chép đầy đủ `_token_counts` và `_token_last` trên mỗi lượt đo thử.
   - Dẫn xuất `tbl_border` từ định danh bảng cấu trúc ổn định `table_id` thay vì `total_tables`.
4. **Giai đoạn 4 (Chuẩn tắc hóa `derive_seed` v2, Ma trận Kiểm thử & Benchmark - P2)**:
   - Nâng cấp `derive_seed` sang mã hóa chuẩn tắc `rng-v2` (phân biệt `bool`, `int` ASCII độ dài tường minh không tràn số 64-bit/số âm, `str` chuẩn hóa NFC, `bytes`, `None`, `SeedContext`, `tuple`).
   - Cập nhật mã băm `.xopp` của ca `test_real_path_stable_variants` trong [`tests/test_golden_master_real_path.py`](file:///d:/viet/app/tests/test_golden_master_real_path.py#L149) trong khi giữ nguyên 100% 8 ca `GOLDEN_REAL` mặc định (`stable_variants=False`).
   - Bổ sung ma trận kiểm thử bất biến nét vẽ XOPP thực tế và đo kiểm benchmark tài liệu lớn.

---

## Technical Context

**Language/Version**: Python 3.12+ (Core Engine, Pyodide WASM), JavaScript ES2022+ (Web Client, Web Worker, Service Worker).

**Primary Dependencies**:
- Python: `hashlib.blake2b`, `unicodedata`, `difflib`, `math`, `random` (thư viện chuẩn CPython & Pyodide 314.0.7).
- Web: Native Web Worker, IndexedDB API, BroadcastChannel API.

**Storage**: IndexedDB (`chuviettay-db` v1: `profiles` object store với OCC monotonic timestamps).

**Testing**:
- Python: `pytest`, `tests/test_rng.py`, `tests/test_stable_variants.py`, `tests/test_golden_master_real_path.py`.
- JavaScript: Node.js built-in test runner (`node --test`), Playwright E2E.
- Pyodide Engine: `scripts/test_golden_pyodide.mjs` (8 Golden Master cases).

**Target Platform**: Hiện đại (Chromium, Firefox, Safari), PWA Offline-first, Pyodide Web Worker.

**Project Type**: Hybrid Web Application & Algorithmic Rendering Engine.

**Performance Goals**:
- Pipeline kết xuất văn bản dài không suy giảm đáng kể (chênh lệch trung vị `<= 10%` khi bổ sung `SeedContext` và `derive_seed` v2).
- Quá trình khôi phục Worker hoàn tất dưới 3s trong điều kiện bình thường; timeout ngắt kết nối an toàn đúng `10000ms` (hoặc `timeoutMs` cấu hình).

**Constraints**:
- Zero GUI/Tkinter dependencies trong mã nguồn web và worker.
- Giữ nguyên cấu hình `pyodide 314.0.7` trong `package.json`.
- 100% Golden Master byte-exact match cho toàn bộ 8 ca `GOLDEN_REAL` (`stable_variants=False`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Evaluation | Status |
| :--- | :--- | :---: |
| **I. Maintainability & Code Cleanliness** | Cấu trúc `SeedContext` phân định rõ ràng trách nhiệm; loại bỏ các bộ đếm ngẫu nhiên lệch nhau giữa `LayoutEngine` và `Writer`; mã nguồn tự tài liệu hóa với type annotations đầy đủ. | **PASS** |
| **II. Simple Architecture (KISS & YAGNI)** | Chỉ sử dụng thư viện chuẩn (`hashlib`, `unicodedata`, `difflib`); giải quyết trực diện các lỗi khôi phục Worker và va chạm khóa hạt giống. | **PASS** |
| **III. Comprehensive Automated Testing** | Bổ sung unit tests cho từng nhánh lỗi Worker (`ERROR`, `onerror`, `onmessageerror`, `timeout`, `load_bank` reject), test vectors cho `derive_seed` v2, và kiểm thử tích hợp bất biến nét vẽ XOPP. | **PASS** |
| **IV. Loose Coupling & High Cohesion** | `Writer` và `LayoutEngine` giao tiếp qua hợp đồng `SeedContext` minh bạch; tầng lưu trữ `storage.js` thực thi giao dịch độc lập với UI. | **PASS** |
| **Quality Gates (Golden Master & CI)** | Chế độ mặc định giữ nguyên 100% luồng ngẫu nhiên, không thay đổi băm SHA-256 của 8 ca Golden Master trên cả CPython và Pyodide. | **PASS** |

---

## Project Structure

### Documentation (this feature)

```text
specs/043-worker-recovery-seed-stability/
├── plan.md              # Kế hoạch triển khai kiến trúc (đã rà soát & cập nhật)
├── research.md          # Kết quả nghiên cứu và quyết định kỹ thuật
├── data-model.md        # Mô hình thực thể dữ liệu (SeedContext, CanonicalKey, WorkerRecoverySession)
├── quickstart.md        # Hướng dẫn chạy xác thực từng kịch bản
├── contracts/           # Hợp đồng giao tiếp kỹ thuật
│   ├── worker-recovery-contract.md
│   ├── seed-pipeline-contract.md
│   └── storage-concurrency-contract.md
└── tasks.md             # Sẽ được sinh qua /speckit-tasks
```

### Source Code Layout

```text
chuviettay/
├── document/
│   └── ir.py               # Bổ sung trường tùy chọn stable_id trên các nút IR & hàm align_document_seeds
├── model/
│   ├── rng.py              # SeedContext, encode_canonical_key, derive_seed v2 (rng-v2), ScopedRNG
│   └── writer.py           # Writer.token/symbol/number nhận SeedContext, cô lập _token_last, sửa jitter/number
├── layout/
│   ├── engine.py           # DocumentLayoutEngine truyền SeedContext, wgap theo token_id, tbl_border theo table_id
│   └── math_layout.py      # MathLayoutEngine._scratch() sao chép đầy đủ trạng thái Writer cho từng probe
├── fidelity/
│   └── engine.py           # FidelityLayoutEngine đồng bộ SeedContext và wgap với Writer

webapp/
├── js/
│   ├── app.js              # recoverWorker() kiểm tra kết quả, timeout 10s, giữ nút Thử lại khi lỗi, sửa onWorkerReady
│   └── storage.js          # incrementTeachCount, resetTeachCount giao dịch nguyên tử & đồng bộ localSyncedTimestamp

tests/
├── js/
│   ├── worker_resilience.test.mjs  # Unit tests cho ERROR, onerror, onmessageerror, timeout, load_bank error
│   └── storage.test.mjs            # Unit tests cho atomic incrementTeachCount / resetTeachCount & anti-resurrection
├── test_rng.py                     # Unit tests cho canonical key encoding, int >= 2**63, negative seed, test vectors
├── test_stable_variants.py         # Ma trận kiểm thử bất biến nét vẽ XOPP (chèn từ trùng, bảng, toán, benchmark)
└── test_golden_master_real_path.py # Bảo toàn 8 ca GOLDEN_REAL và cập nhật hash v2 cho test_real_path_stable_variants
```

---

## Complexity Tracking

> Không có vi phạm nguyên tắc Constitution nào cần biện minh. Toàn bộ thiết kế bám sát kiến trúc hiện hành và tuân thủ nguyên tắc tối giản.
