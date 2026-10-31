# Implementation Plan: Xóa Lịch sử Hạt giống, Hoàn thiện Bộ nhớ đệm Kho mẫu và Kiểm chứng Nâng cao (seed-reset-bank-cache-hardening)

**Branch**: `069-seed-reset-bank-cache-hardening` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/069-seed-reset-bank-cache-hardening/spec.md`

## Summary

Kế hoạch triển khai xử lý dứt điểm 2 lỗi ranh giới luồng thực tế (P2), nâng cấp bộ kiểm thử hình thái nét toàn diện và mở rộng bài đo hiệu năng kho mẫu đa biến thể:
1. **P2 - Tự động xóa lịch sử hạt giống & Triệt tiêu Race Condition**:
   - Bổ sung thông điệp `clear_document_history` đi xuyên suốt từ `write.js` (khi xóa trắng hoặc mở file mới) $\to$ `py-worker.js` $\to$ `BrowserBridge` $\to$ `AppController`, ngăn chặn việc kế thừa nhầm occurrence từ tài liệu cũ.
   - Xử lý triệt để race condition khi xóa trắng lúc đang render: `clearPreview()` hủy các yêu cầu chờ (`hasPendingRequest = false; pendingParams = null;`) và `requestRender` hủy việc cập nhật DOM nếu ô soạn thảo đã bị xóa trắng.
   - Gọi `clear_document_history` có điều kiện trong `handleFileImport`: chỉ xóa lịch sử khi tệp mới đã được đọc/phân tích thành công (tránh mất lịch sử khi người dùng mở nhầm file lỗi).
2. **P2 - Hai giai đoạn cam kết cache Kho mẫu (Two-Phase Cache Commit)**:
   - Giữ khóa snapshot trong biến tạm và chỉ cập nhật `lastBankSnapshotCache` sau khi `applyFiltersAndRender()` hoàn tất thành công.
   - `applyFiltersAndRender()` kiểm tra chặt chẽ sự hiện diện của `#bank-cards-grid`; vô hiệu hóa cache khi có lỗi hoặc thiếu container để cho phép lượt gọi sau thử lại.
3. **P2 - Kiểm tra toàn diện hình thái nét (All Strokes Parity)**:
   - Bổ sung assertion `occs_d3[3] == 1` và so sánh 100% nét vẽ của tất cả các từ giữ lại qua các lượt sửa liên tiếp.
4. **P3 - Đo kiểm hiệu năng Kho mẫu Đa biến thể & Chuẩn hóa Tài liệu**:
   - Mở rộng benchmark trên 1.050 nhãn với 3.400+ mẫu nét ($t < 200$ ms).
   - Chuẩn hóa toàn bộ tài liệu kỹ thuật, giải thích minh bạch sự sai biệt giữa kết quả CI Linux (1.405 passed · 14 skipped · 7 deselected) và máy phát triển Windows (1.426 passed).

---

## Technical Context

**Language/Version**: Python 3.10+ (Pyodide 314.0.7 trong Web Worker) & Modern JavaScript (ES2022 Modules).

**Primary Dependencies**: Không thêm thư viện ngoài (Zero Remote CDN, tuân thủ kiến trúc Offline-First tuyệt đối).

**Storage**: IndexedDB (lưu trữ hồ sơ người dùng), MEMFS (`/tmp/active_bank.json.gz`), Local Files (.xopp, .txt, .md, .docx).

**Testing**: `pytest` (bộ kiểm thử Python), `@playwright/test` (kiểm thử trình duyệt E2E), `node --test` (kiểm thử JS).

**Target Platform**: Web Client hiện đại (Chromium, Firefox, Safari) và môi trường Python Core.

**Project Type**: Ứng dụng Web tĩnh PWA + Lõi kết xuất chữ viết tay Python đóng gói Pyodide.

**Performance Goals**: Trích xuất bản chụp kho mẫu quy mô lớn (1.050 nhãn, 3.400+ mẫu nét) hoàn tất trong $t < 200$ ms; căn chỉnh hạt giống tài liệu trong $t < 100$ ms.

**Constraints**: Tương thích ngược 100% với 1.426 bài test Python và 20/20 bài test Playwright E2E; an toàn bộ nhớ và ngăn ngừa XSS/HTML Injection.

**Scale/Scope**: Tác động trực tiếp vào 5 tệp mã nguồn (`bridge.py`, `app_controller.py`, `write.js`, `bank.js`, `py-worker.js`) và 4 tệp kiểm thử (`test_bridge.py`, `test_stable_variants.py`, `test_performance_regression.py`, `tests/e2e/write.spec.ts`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp | Đánh giá Tuân thủ | Kết luận |
| :--- | :--- | :---: |
| **I. Maintainability & Code Cleanliness** | Đặt tên rõ ràng (`clear_document_history`), phân tách luồng điều khiển minh bạch, chú thích rõ nguyên nhân (why). | ✅ PASS |
| **II. Simple Architecture (KISS & YAGNI)** | Sử dụng thông điệp trực tiếp giữa Worker và Bridge, áp dụng mô hình Two-Phase Cache Commit đơn giản, không đẻ thêm middleware hay lớp trừu tượng phức tạp. | ✅ PASS |
| **III. Comprehensive Automated Testing** | Xây dựng kiểm thử độc lập cho cả 4 User Stories: E2E Playwright cho luồng xóa/mở file; Unit test cho Two-Phase Cache; All Strokes Parity trong `test_stable_variants.py`; Benchmark lớn trong `test_performance_regression.py`. | ✅ PASS |
| **IV. Loose Coupling & High Cohesion** | Thao tác xóa lịch sử đi qua hợp đồng thông điệp tường minh, không can thiệp vào biến nội bộ của controller từ phía giao diện. | ✅ PASS |
| **Quality Gates & CI Alignment** | Toàn bộ các kiểm thử phải xanh (ALL PASS), `ruff check` sạch, `build_web.py` pass 100% sanity check. | ✅ PASS |

---

## Project Structure

### Documentation (this feature)

```text
specs/069-seed-reset-bank-cache-hardening/
├── spec.md              # Đặc tả tính năng và yêu cầu
├── plan.md              # Kế hoạch triển khai kỹ thuật (tệp này)
├── research.md          # Kết quả nghiên cứu và quyết định kỹ thuật
├── data-model.md        # Mô hình dữ liệu, vòng đời trạng thái và máy trạng thái cache
├── quickstart.md        # Hướng dẫn kiểm chứng độc lập 4 kịch bản
├── checklists/
│   └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
└── contracts/
    └── seed-reset-bank-cache-contract.md # Hợp đồng thông điệp và giao diện
```

### Source Code (affected paths)

```text
chuviettay/
├── browser/
│   └── bridge.py                    # Bổ sung phương thức clear_document_history()
└── controller/
    └── app_controller.py            # Duy trì phương thức clear_document_history() và đệ quy _sync_occurrences

webapp/
├── js/
│   ├── write.js                     # Gửi clear_document_history khi text rỗng hoặc import file mới
│   ├── bank.js                      # Cập nhật cache Two-Phase Commit an toàn trong refreshBankView
│   └── worker/
│       └── py-worker.js             # Nhận thông điệp clear_document_history và gọi qua Bridge
└── dist/                            # Tệp phân phối tĩnh (được cập nhật qua build_web.py)

tests/
├── test_bridge.py                   # Kiểm thử bridge.clear_document_history
├── test_stable_variants.py          # Bổ sung assert occs_d3[3] == 1 và all strokes parity check
├── test_performance_regression.py   # Mở rộng bài benchmark 1.050 nhãn với 3.400+ samples nét
├── js/
│   └── bank_cache.test.mjs          # Unit test cho Two-Phase Cache Commit trong bank.js
└── e2e/
    └── write.spec.ts                # E2E test cho xóa trắng và mở tài liệu mới không kế thừa seed cũ
```

**Structure Decision**: Cấu trúc tuân thủ kiến trúc phân tầng hiện tại của repository. Giao tiếp giữa Frontend và Python Core đi qua lớp Web Worker Message Dispatcher và BrowserBridge.

---

## Complexity Tracking

> Không có vi phạm Hiến pháp nào cần biện minh. Giải pháp sử dụng các mẫu thiết kế tối giản và tự nhiên nhất sẵn có trong dự án.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|:---|:---|:---|
| *Không có* | *Không áp dụng* | *Không áp dụng* |
