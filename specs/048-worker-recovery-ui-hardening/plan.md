# Implementation Plan: Củng cố Phục hồi Worker, Quản lý Vòng đời Giao diện và Đo đạc Chữ số Đa biến thể

**Branch**: `048-worker-recovery-ui-hardening` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/048-worker-recovery-ui-hardening/spec.md`

## Summary

Củng cố toàn diện tính kiên cường của hệ thống Web Client và độ chính xác hình học của thư viện lõi:
1. **Worker Recovery Session Guard**: Bảo vệ khối `finally` trong `recoverWorker()` (`webapp/js/app.js`), triệt tiêu race condition bằng cách chỉ cho phép phiên phục hồi hiện hành (`activeRecoverySession === session`) cập nhật các cờ toàn cục (`isRecovering`, `recoveryPromise`, mở khóa nút Thử lại).
2. **CI Worker Resilience Integration**: Hợp nhất toàn bộ các ca kiểm thử độ kiên cường của Worker vào `tests/js/worker_resilience.test.mjs`, bảo đảm lệnh `npm run test:unit` trong CI thực thi 100% các kịch bản kiểm thử, xóa bỏ tệp mồ côi `tests/test_worker_resilience.mjs`.
3. **UI Event Listener & Observer Teardown**: Bổ sung `AbortSignal` và phương thức `destroy()` cho `TeachController` (`webapp/js/teach.js`), thu hồi triệt để sự kiện trên `document`, quản lý ngắt kết nối `ResizeObserver` trong `setupPreviewNavigation` (`webapp/js/write.js`), và đảm bảo tính lũy đẳng cho các trình lắng nghe thông báo sao lưu.
4. **Physical Worker Termination on Post-READY Timeout**: Khi bước nạp giao diện sau tín hiệu `READY` quá hạn, hệ thống chấm dứt vật lý tiến trình Worker (`worker.terminate()`), tăng `workerGeneration` và hủy tham chiếu để ngăn chặn hoàn toàn "Worker ma".
5. **Extreme Digit Geometry Sanitization & Multi-Variant Width Parity**: Xử lý an toàn mẫu chữ số suy biến (`sample_h <= 1e-3`) trong `_normalize_digit_sample`, và đồng bộ thuật toán tính độ rộng số của `measure_text_width()` với `number()` trong `chuviettay/model/writer.py` để sai lệch luôn $\le 0.05 \times x_h$ trên mọi cấu hình kho mẫu.

## Technical Context

**Language/Version**: JavaScript (ES Modules, Web Workers, IndexedDB, Node.js 20+), Python 3.10+ (Pyodide WebAssembly in browser, CPython in tests)

**Primary Dependencies**: `node:test`, `node:assert/strict`, `pytest`, `pytest-timeout`, `pyodide`

**Storage**: IndexedDB (`idb-keyval` / `storage.js`), Virtual In-Memory FS (Pyodide)

**Testing**: Node.js built-in test runner (`npm run test:unit`), Pytest (`pytest`)

**Target Platform**: Modern Web Browsers (Chrome, Firefox, Edge, Safari), Cross-platform CI (Ubuntu/Windows)

**Project Type**: Web Client Application + Core Typography Engine

**Performance Goals**:
- Thời gian dọn dẹp và hủy listener/observer giao diện < 5ms.
- Bắt tay và phục hồi Worker phản ứng ngay lập tức khi phát hiện lỗi hoặc timeout.
- Độ sai lệch giữa `measure_text_width` và `number` cho chuỗi số $\le 0.05 \times x_h$.

**Constraints**:
- Không làm thay đổi kết quả kiểm thử Golden Master (giữ nguyên `tests/data/kho_mau_tong_hop.json.gz`).
- 100% kiểm thử tự động trong CI phải pass deterministically.
- Không để tồn tại bất kỳ zombie Worker hay rò rỉ listener DOM nào.

**Scale/Scope**:
- 4 tệp JavaScript (`webapp/js/app.js`, `webapp/js/teach.js`, `webapp/js/write.js`, `package.json`).
- 1 tệp Python lõi (`chuviettay/model/writer.py`).
- 3 bộ kiểm thử (`tests/js/worker_resilience.test.mjs`, `tests/test_system_hardening_feature_046.py`, `tests/test_number_fraction_typography.py`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến chương | Đánh giá | Ghi chú tuân thủ |
| :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | **PASS** | Loại bỏ hoàn toàn tệp kiểm thử dư thừa/trùng lặp, tái cấu trúc khối `finally` và quản lý vòng đời rõ ràng, có tài liệu hợp đồng và hợp nhất kiểm thử. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Sử dụng trực tiếp cơ chế chuẩn `AbortSignal` và so sánh con trỏ phiên `activeRecoverySession === session`, không tạo thêm các lớp trừu tượng phức tạp không cần thiết. |
| **III. Comprehensive Automated Testing** | **PASS** | Khắc phục lỗ hổng kiểm thử CI bằng cách đưa toàn bộ các ca kiểm thử Worker resilience vào `npm run test:unit`, bổ sung kiểm thử các ca biên (race condition, post-READY timeout, degenerate digits). |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Tách biệt ranh giới quản lý vòng đời giữa tầng điều phối Worker (`app.js`), tầng giao diện (`teach.js`, `write.js`), và tầng xử lý hình học chữ viết (`writer.py`). |

## Project Structure

### Documentation (this feature)

```text
specs/048-worker-recovery-ui-hardening/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 technical research & decisions
├── data-model.md        # Phase 1 data structures & state models
├── quickstart.md        # Phase 1 verification guide
├── contracts/           # Phase 1 behavioral contracts
│   ├── worker-recovery-contract.md
│   ├── ui-lifecycle-contract.md
│   └── writer-number-parity-contract.md
└── checklists/
    └── requirements.md  # Quality validation checklist
```

### Source Code (affected paths)

```text
webapp/js/
├── app.js               # Worker recovery session isolation & post-READY physical termination
├── teach.js             # TeachController AbortSignal & global keydown listener cleanup
└── write.js             # setupPreviewNavigation ResizeObserver disconnect & signal binding

chuviettay/model/
└── writer.py            # Degenerate digit fallback in _normalize_digit_sample & number/measure sync

tests/
├── js/
│   └── worker_resilience.test.mjs  # Consolidated unit test suite for Worker recovery & UI idempotency
├── test_system_hardening_feature_046.py # Multi-variant number sync & bounding box assertions
└── test_number_fraction_typography.py  # Decimal typography & bounding box tests

package.json             # Verification of test:unit command
```

**Structure Decision**: Cấu trúc module hiện tại của dự án đã phân tách rõ ràng giữa Web Client (`webapp/js/`), Python core (`chuviettay/`), và Tests (`tests/`). Kế hoạch tận dụng trực tiếp cấu trúc này, khắc phục việc đặt tệp kiểm thử sai vị trí và dọn dẹp các tệp mồ côi.

## Complexity Tracking

Không có vi phạm hay ngoại lệ nào so với Hiến chương dự án (Constitution). Mọi giải pháp đều tuân thủ nguyên tắc đơn giản, tái sử dụng các API chuẩn của nền tảng (DOM `AbortSignal`, Node.js test runner, `pytest`).
