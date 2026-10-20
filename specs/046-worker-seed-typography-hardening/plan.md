# Implementation Plan: Worker Resilience, Seed Integrity & Typography Hardening

**Branch**: `046-worker-seed-typography-hardening` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/046-worker-seed-typography-hardening/spec.md`

## Summary

Triển khai gói gia cố kỹ thuật và hoàn thiện hệ thống toàn diện sau rà soát mã nguồn:
1. **Phục hồi Worker an toàn và triệt tiêu treo vô thời hạn**: Quản lý phiên phục hồi theo thế hệ Worker (`workerGeneration`), bảo đảm Promise giải quyết dứt điểm đúng 1 lần khi thế hệ bị thay đổi giữa chừng; mở rộng bộ đếm thời gian bao bọc cả giai đoạn `READY` và khởi tạo giao diện sau đó, bảo đảm cờ `isRecovering` luôn được giải phóng và nút "Thử lại" không bị kẹt.
2. **Khởi tạo UI có tính lũy suy (Idempotent) và dọn dẹp listeners**: Áp dụng cơ chế dọn dẹp (cleanup với `AbortController` / cờ kiểm soát gắn kết) cho `bank.js`, `write.js`, `teach.js`, ngăn ngừa việc gắn trùng lặp listener khi chu trình khởi tạo bị lỗi rồi thử lại.
3. **Cô lập Seed Namespace & Tính toàn vẹn của Seed**:
   - Phân tách không gian tên seed của `Heading` (`heading`) độc lập với `Paragraph` (`text`), bảo đảm việc thêm/sửa đoạn văn bản không làm biến dạng nét chữ tiêu đề.
   - Chuyển tiếp đầy đủ trường `occurrence` và `stable_id` khi chuyển đổi `MathBlock` trong ô bảng thành phần tử nội dòng.
   - Phản ánh chỉ số phân đoạn `sub_index` vào định danh hình học của các chunk trong token dài.
4. **Chuẩn hóa chữ số bền vững & Thu hẹp khoảng cách dấu âm**:
   - Xử lý ổn định các mẫu chữ số dị biệt cực đoan (`< 0.35 * xh` hoặc `> 3.0 * xh`) bằng cơ chế co giãn tỷ lệ thích ứng trực tiếp về dải chuẩn lining figures `1.20 * xh` và bảo vệ trước mẫu suy biến rỗng.
   - Đồng bộ hóa 100% khoảng cách quanh dấu thập phân (`,` và `.`) giữa hàm đo đạc độ rộng `measure_text_width()` và hàm kết xuất nét `number()`.
   - Thu hẹp khoảng cách ngang giữa dấu trừ (`-`) và chữ số đầu tiên trong các số âm (`-25`, `-0,39`) về dải tự nhiên `0.05 * xh .. 0.12 * xh`.
5. **Mở rộng kiểm thử tự động toàn diện & Củng cố CI**: Bổ sung bộ kiểm thử tự động chuyên biệt cho Worker resilience, chống trùng lặp UI listener, tính cô lập seed và hình học dấu âm/mẫu số dị biệt.

## Technical Context

**Language/Version**: Python 3.10+ (Core Engine, Document IR, Typography), Modern JavaScript ES2022+ (Web Client & Pyodide Worker)  
**Primary Dependencies**: Thư viện chuẩn (`re`, `math`, `random`, `dataclasses`, `difflib`), Pyodide 314.0.7, Web Standards (`AbortController`, `Web Worker`)  
**Storage**: IndexedDB (`localforage`), file nén `.json.gz` (tương thích ngược 100%)  
**Testing**: `pytest` (CPython), Node.js runner (`node --test`), `scripts/test_golden_pyodide.mjs`  
**Target Platform**: Desktop (Python CLI) & Web Client (Pyodide Worker tĩnh)  
**Project Type**: Core Handwriting Layout Engine & Client-Side Static Web App  
**Performance Goals**: Phục hồi Worker nhanh chóng, đo độ rộng văn bản khớp kết xuất `< 0.05 * xh`, zero memory leak / promise leak  
**Constraints**: 100% offline-capable, bảo toàn toàn bộ 1259+ test hiện có của dự án, zero regression  
**Scale/Scope**: Tác động trực tiếp đến `webapp/js/app.js`, `webapp/js/bank.js`, `webapp/js/write.js`, `chuviettay/layout/engine.py`, `chuviettay/document/ir.py`, `chuviettay/model/writer.py`  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Tách bạch rõ ràng giữa cơ chế vòng đời Worker, đăng ký listener DOM, cấu trúc Document IR và chuẩn hóa hình học nét số.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Sử dụng các API chuẩn của Web (`AbortController`) và các tham số rõ ràng trong hàm Python; không đưa thêm thư viện ngoài phức tạp.
- [x] **III. Comprehensive Automated Testing**: Thiết lập bộ unit test và integration test tự động cho cả JavaScript (Worker resilience, duplicate listener) và Python (seed isolation, math block in table, extreme typography).
- [x] **IV. Loose Coupling & High Cohesion**: Các module giữ đúng trách nhiệm: `ir.py` quản lý cấu trúc cây tài liệu và ánh xạ seed, `engine.py` quản lý định tuyến bố cục, `writer.py` quản lý chuẩn hóa nét, `app.js` quản lý vòng đời Worker.

## Project Structure

### Documentation (this feature)

```text
specs/046-worker-seed-typography-hardening/
├── plan.md              # Kế hoạch triển khai (file này)
├── research.md          # Phân tích nguyên nhân & các quyết định kỹ thuật
├── data-model.md        # Mô hình trạng thái, chuyển đổi và các bất biến
├── quickstart.md        # Hướng dẫn kiểm chứng & chạy thử nghiệm
├── contracts/
│   └── hardening-contract.md # Hợp đồng giao diện Worker, UI, IR và Typography
├── checklists/
│   └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
└── tasks.md             # Sẽ được sinh bởi /speckit-tasks
```

### Source Code (affected paths)

```text
webapp/
├── js/
│   ├── app.js           # Quản lý phiên phục hồi Worker theo thế hệ và bọc timer cho onWorkerReady
│   ├── bank.js          # Hỗ trợ AbortSignal / kiểm tra cờ listener idempotent
│   └── write.js         # Hỗ trợ AbortSignal / kiểm tra cờ listener idempotent
chuviettay/
├── document/
│   └── ir.py            # Tách riêng context_prefix="heading" trong align_document_seeds()
├── layout/
│   └── engine.py        # Truyền context_prefix="heading" khi render Heading, chuyển tiếp occurrence MathBlock trong bảng, gắn sub_index vào render_id
├── model/
│   └── writer.py        # Co giãn tỷ lệ thích ứng cho mẫu số cực đoan, đồng bộ measure_text_width, thu hẹp khoảng cách dấu âm
tests/
├── test_worker_resilience.mjs          # Test JavaScript kiểm chứng phục hồi Worker đa thế hệ và chống gắn trùng listener
└── test_system_hardening_feature_046.py # Test Python kiểm chứng seed Heading, table math, chunk sub_index, typography
```

**Structure Decision**: Tập trung trực tiếp vào các tệp nguồn lõi cần gia cố của `webapp/` và `chuviettay/`, không phát sinh cấu trúc dư thừa.

## Complexity Tracking

*(Không có vi phạm hiến pháp)*
