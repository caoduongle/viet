# Implementation Plan: Cách ly Lỗi Muộn Worker, Đồng bộ Ngữ cảnh Đo Độ rộng Số và Chống Dính Nét Dấu câu

**Branch**: `049-worker-error-guard-punct-spacing` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/049-worker-error-guard-punct-spacing/spec.md`

## Summary
Triển khai giải pháp toàn diện cho 4 mục tiêu cốt lõi:
1. **P1 — Cách ly lỗi Worker muộn**: Chặn đứng các sự kiện lỗi muộn (`onerror`, `onmessageerror`) từ Worker cũ trong `webapp/js/app.js` bằng bộ lọc `generation !== workerGeneration`, ngăn chặn việc phá hủy phiên Worker mới hoặc làm hỏng trạng thái giao diện.
2. **P1 — Bộ kiểm thử hồi quy đa phiên Worker**: Bổ sung các ca kiểm thử hồi quy tự động trong `tests/js/worker_resilience.test.mjs` nhằm bảo vệ các luồng cạnh tranh lỗi muộn, trạng thái trung gian đa phiên, và timeout sau `READY`.
3. **P2 — Đồng bộ ngữ cảnh đo độ rộng số**: Mở rộng `Writer.measure_text_width` chấp nhận tham số `context: SeedContext | None = None` và cập nhật `DocumentLayoutEngine._layout_inlines` truyền đúng `SeedContext` của phần tử trước khi đo độ rộng, bảo đảm tính nhất quán 100% giữa bước ước lượng và bước kết xuất thực tế.
4. **P2 / Visual — Chống dính nét quang học**: Áp dụng sàn khoảng hở quang học hình học thực tế cho dấu phẩy/chấm thập phân (`Writer.number`), dấu ngoặc toán học (`MathLayoutEngine._row_gaps` và `_m_Delimited`), và dấu câu kết thúc (`Writer.token`), giải quyết triệt để lỗi dính nét trong các tài liệu toán học (như `0,39`, `F_X(1)`, `P(...)`, `ta có:`) trong khi bảo toàn 100% kết quả Golden Master SHA-256.

## Technical Context

**Language/Version**: Python 3.10 / 3.14 (Backend/Engine), ES2022 JavaScript (Frontend/Pyodide Worker)
**Primary Dependencies**: Pyodide, standard web APIs (IndexedDB, Web Worker, AbortController), pytest, node:test
**Storage**: IndexedDB (trình duyệt), JSON gzip (`.json.gz`) trên ổ đĩa
**Testing**: `node --test "tests/js/*.test.mjs"`, `pytest`
**Target Platform**: Trình duyệt Web (Chrome, Edge, Firefox, Safari) + CLI trên Windows/Linux/macOS
**Project Type**: Thư viện Python + CLI + Web Application
**Performance Goals**: Đo độ rộng O(1) hoặc O(N) theo số ký tự, không gây giật lag khi gõ văn bản; phục hồi Worker < 10s.
**Constraints**: Bảo toàn 100% Golden Master SHA-256 (`tests/data/kho_mau_tong_hop.json.gz` không được sửa đổi). Không phá vỡ tương thích ngược của API `measure_text_width`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá | Trạng thái |
|------------|----------|------------|
| **1. Tính toàn vẹn của Fixture Kho mẫu** | Tuyệt đối không chỉnh sửa `tests/data/kho_mau_tong_hop.json.gz`. | **PASS** |
| **2. Tương thích Golden Master** | Toàn bộ 9/9 bài test trong `tests/test_golden_master_real_path.py` phải PASS với SHA-256 khớp 100%. | **PASS** |
| **3. Kiểm thử tự động trên CI** | Mọi test JS phải nằm trong `tests/js/*.test.mjs` để lệnh `npm run test:unit` quét được. | **PASS** |
| **4. Ngăn chặn Zombie Worker** | Mọi Worker cũ hoặc treo quá hạn phải bị `terminate()` vật lý. | **PASS** |
| **5. Giới hạn phạm vi (Scope Boundary)** | Không sửa đổi các thành phần ngoài phạm vi Worker resilience, context measurement và optical spacing. | **PASS** |

## Project Structure

### Documentation (this feature)

```text
specs/049-worker-error-guard-punct-spacing/
├── plan.md              # Kế hoạch triển khai kiến trúc chi tiết
├── research.md          # Nghiên cứu kỹ thuật, phân tích nguyên nhân gốc rễ
├── data-model.md        # Mô hình thực thể, trạng thái Worker và công thức quang học
├── quickstart.md        # Hướng dẫn kiểm chứng và kịch bản xác minh
├── contracts/           # Hợp đồng ràng buộc giữa các module
│   ├── worker-error-isolation-contract.md
│   ├── context-aware-measurement-contract.md
│   └── punctuation-optical-clearance-contract.md
└── tasks.md             # Sẽ được tạo bởi lệnh /speckit-tasks
```

### Source Code (repository root)

```text
webapp/
└── js/
    └── app.js                        # Thêm generation guard trong onerror và onmessageerror

tests/
├── js/
│   └── worker_resilience.test.mjs    # Bổ sung unit tests cho late error từ Worker cũ
├── test_golden_master_real_path.py   # Golden Master regression test (9 tests)
├── test_math_layout.py               # Kiểm thử bố cục công thức toán
├── test_math_layout_extended.py      # Kiểm thử mở rộng khoảng cách toán
└── test_punctuation_optical_spacing.py # Test mới cho optical clearance và context measurement

chuviettay/
├── model/
│   ├── writer.py                     # Mở rộng measure_text_width(context) & number optical clearance
│   └── text_utils.py                 # Vector fallback cho : và ;
└── layout/
    ├── engine.py                     # Truyền SeedContext vào measure_text_width trong _layout_inlines
    └── math_layout.py                # Nâng cấp _HUG và kiểm tra khoảng hở quang học giữa ngoặc và số
```

## Phase 0: Research Summary

Đã hoàn thành phân tích trong [research.md](research.md):
- **Phát hiện race condition**: Trong `attachWorkerHandlers`, `targetWorker.onerror` và `targetWorker.onmessageerror` sử dụng `boundSession` từ closure nên `currentSession.generation === generation` luôn đúng đối với Worker cũ, dẫn đến việc gọi nhầm `handleWorkerFatalError()`.
- **Phát hiện thiếu sót đo độ rộng**: `measure_text_width` bỏ qua ngữ cảnh phân vùng (`heading`, `cell`), dẫn đến chọn sai biến thể chữ số khi kho mẫu có nhiều biến thể với độ rộng khác nhau.
- **Phát hiện nguyên nhân dính nét**: `_HUG = 0.02` trong `MathLayoutEngine` khiến khoảng cách giữa dấu ngoặc và chữ số chỉ là ~0.25mm (nhỏ hơn bề dày nét bút). Dấu phẩy thập phân trong `Writer.number()` không có sàn khoảng hở quang học theo biên nét vẽ thực tế.

## Phase 1: Design & Contracts Summary

Đã định nghĩa đầy đủ các văn bản đặc tả:
- [data-model.md](data-model.md): Mô hình trạng thái vòng đời Worker, cấu trúc `SeedContext`, và các công thức tính khoảng hở quang học.
- [contracts/worker-error-isolation-contract.md](contracts/worker-error-isolation-contract.md): Ràng buộc cô lập lỗi Worker cũ.
- [contracts/context-aware-measurement-contract.md](contracts/context-aware-measurement-contract.md): Ràng buộc tính thuần túy và độ chính xác của phép đo độ rộng nhận biết ngữ cảnh.
- [contracts/punctuation-optical-clearance-contract.md](contracts/punctuation-optical-clearance-contract.md): Ràng buộc sàn khoảng hở hình học và tính bất biến của Golden Master.
- [quickstart.md](quickstart.md): Các lệnh kiểm thử xác nhận chất lượng.

## Implementation Architecture & Phases

### Phase 1: Worker Error Guard & Regression Tests (P1)
- Chỉnh sửa `webapp/js/app.js`: Đặt kiểm tra `if (generation !== workerGeneration)` tại dòng đầu của `targetWorker.onerror` và `targetWorker.onmessageerror`.
- Chỉnh sửa `tests/js/worker_resilience.test.mjs`: Thêm test case giả lập Worker A gửi lỗi sau khi Worker B đã hoạt động; kiểm tra tính ổn định của hàng đợi yêu cầu và giao diện.

### Phase 2: Context-Aware Number Measurement (P2)
- Chỉnh sửa `chuviettay/model/writer.py`: Thêm `context: SeedContext | None = None` vào `measure_text_width()`, lưu và phục hồi `_current_context`, chuyển tiếp `context` vào `self.number()`.
- Chỉnh sửa `chuviettay/layout/engine.py`: Xác định `tok_occ` trước khi gọi `measure_text_width` và khởi tạo `SeedContext(content_type=context_prefix, element_id=tok, occurrence=tok_occ)`.
- Chỉnh sửa `chuviettay/layout/engine.py` (table layout): Khởi tạo `SeedContext` phù hợp khi đo độ rộng ô bảng.

### Phase 3: Optical Spacing Hardening (P2 / Visual)
- Chỉnh sửa `chuviettay/model/writer.py`:
  - Trong `Writer.number()`: Tính biên phải thực tế `prev_ink_max_x` trước khi đặt dấu phẩy/chấm, bảo đảm sàn khoảng hở trước `>= max(0.10 * xh, 0.8 * pen_w)` và sau `>= max(0.10 * xh, 0.75 * pen_w)`.
  - Trong `Writer.token()`: Căn chỉnh vị trí đặt dấu theo `p_min_x` thực tế của dấu câu và bảo đảm sàn khoảng hở đuôi.
- Chỉnh sửa `chuviettay/model/text_utils.py`: Bổ sung vector fallback cho `:` và `;`.
- Chỉnh sửa `chuviettay/layout/math_layout.py`:
  - Nâng cấp `_HUG` trong `_row_gaps` từ `0.02` lên `0.08`.
  - Trong `_m_MathRow`, bổ sung cơ chế kiểm tra sàn khoảng hở quang học hình học thực tế (`prev_glyph_ink_max_x + min_clearance`) ngăn nét vẽ các glyph liền kề (đặc biệt là dấu ngoặc và chữ số) đè lên nhau kể cả khi glyph có nét vươn ngoài kích thước danh nghĩa.
  - Cập nhật `pad` trong `_m_Delimited`.

### Phase 4: Full Verification & Regression Guard
- Chạy `npm run test:unit` và `npm run lint:js`.
- Chạy `pytest tests/test_golden_master_real_path.py` (khẳng định 9/9 ca kiểm thử SHA-256 khớp 100%).
- Chạy toàn bộ test suite Python (`pytest`).
