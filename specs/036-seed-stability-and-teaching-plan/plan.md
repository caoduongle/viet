# Implementation Plan: Cải tiến Seed Stability, Phân trang Bảng và Kế hoạch Dạy chữ

**Branch**: `feat/036-seed-stability` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/036-seed-stability-and-teaching-plan/spec.md`

---

## Summary

Triển khai gói giải pháp kỹ thuật toàn diện cải tiến cơ chế hạt giống ngẫu nhiên, hình học phân trang bảng và tối ưu kế hoạch dạy chữ trong package `chuviettay`:
1. **Kiểm chuẩn và minh bạch vòng đời Seed (WP1)**: Kiểm chuẩn miền giá trị $[0, 2^{32}-1]$ trong `WriteOptions.validate()`, xác định hạt giống hiệu dụng một lần duy nhất tại đầu phiên, bổ sung `WriteResult.seed_used`, hiển thị hướng dẫn tái tạo trên CLI, chuẩn hóa hàm thuần `parseSeed()` trên Web (chấp nhận 0), và phản hồi `ignored_options` trong `bridge.py`.
2. **Luồng ngẫu nhiên cục bộ đảm bảo Stable Variants (WP2)**: Xây dựng module thuần túy `chuviettay/model/rng.py` với thuật toán băm `blake2b` kết hợp Box-Muller biến đổi trực tiếp trên nền `Random.random()`. Neo khóa ngẫu nhiên độc lập theo token, word gap, sóng dòng, viền bảng và công thức toán. Viết lại `tests/test_stable_variants.py` chứng minh chuyển đổi từ đỏ sang xanh, bảo đảm giữ nguyên từng byte mã băm SHA-256 của chế độ mặc định (`stable_variants=False`).
3. **Hình học phân trang bảng và Bounding Box (P1/P2)**: Quét ô nguồn `source_cell_id` trên toàn bộ các hàng từ hàng 0, loại bỏ hoàn toàn nguy cơ ghi đè ô cùng cột; cấp phát định danh ô tăng đơn điệu độc lập trong `LaidOutCell` mà không làm bẩn `TableCell` trong Document IR; ưu tiên co tỉ lệ hoặc phân trang trước khi vẽ, loại bỏ việc kẹp toạ độ cơ học làm bẹt đáy nét chữ.
4. **Kế hoạch dạy chữ 38 mục cốt lõi & gỡ nghẽn hàng đợi (Teaching Plan)**: Đồng bộ `Bank.can()` công nhận các từ nguyên khối đã lưu trong `bank.words`; bổ sung `CORE_ESSENTIALS_38` (33 chữ cái thường + 5 dấu thanh) mở khóa 100% (700/700) từ trong `SEED`.
5. **Hoàn thiện tài liệu và kiểm chứng nghi vấn kỹ thuật (WP4)**: Cập nhật README, CHANGELOG bằng tiếng Việt chuẩn mực; kiểm chứng và xử lý đồng bộ các nghi vấn về `Random(-5)`, `MathLayoutEngine._scratch()` và `Writer.measure_text_width`.

---

## Technical Context

**Language/Version**: Python >= 3.10 (Hiện tại môi trường phát triển chạy Python 3.14, CI hỗ trợ Python 3.10, 3.12, 3.14).  
**Primary Dependencies**: Standard Library (`hashlib`, `math`, `secrets`, `random`, `time`, `unicodedata`). **Zero runtime external dependencies** (`dependencies = []`). Chạy tương thích 100% trong môi trường Pyodide/WebAssembly.  
**Storage**: Giữ nguyên schema lưu trữ `.json.gz` hiện tại của kho mẫu (không thay đổi cấu trúc tệp).  
**Testing**: `pytest` (Python), `node --test` & Playwright (Web/Pyodide).  
**Target Platform**: Desktop (Tkinter / CLI native) và Web Client (Pyodide in Web Worker).  
**Project Type**: Core Layout & Typography Engine.  
**Performance Goals**: Thời gian kết xuất tài liệu ~5.000 token ở chế độ `stable_variants=True` không chậm hơn quá 1.5 lần so với chế độ ngẫu nhiên tuần tự; các phép sinh số ngẫu nhiên ScopedRNG xử lý dưới microsecond.  
**Constraints**:
- Đường mặc định `stable_variants=False` phải giữ nguyên 100% từng byte: hash trong `tests/test_golden_master_real_path.py` và `scripts/test_golden_pyodide.mjs` không được đổi.
- KHÔNG đổi: `CO_BAN_CHARS` (thứ tự lưới hw3), fixture `sample_char_grid.xopp`, thuật toán ghép chữ/kerning trong `Writer.assemble_word`.
**Scale/Scope**: Tác động trực tiếp đến 7 module lõi (`model/rng.py`, `model/writer.py`, `model/bank.py`, `model/seed_words.py`, `layout/engine.py`, `layout/table_layout.py`, `controller/results.py`), tầng CLI/Bridge/Web và các bộ test tương ứng.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**:
  - Module `chuviettay/model/rng.py` được thiết kế thuần túy, tự tài liệu hóa với type hint đầy đủ và docstring tiếng Việt rõ ràng.
  - Các khóa neo ngữ cảnh có định dạng phân cấp chuẩn tắc, ngăn chặn xung đột không gian tên ngẫu nhiên.
  - Xóa bỏ triệt để các câu lệnh gán bẩn trường nội bộ vào Document IR (`TableCell`).
- [x] **II. Simple Architecture (KISS & YAGNI)**:
  - Sử dụng thuật toán Box-Muller trực tiếp và băm `blake2b` tích hợp sẵn trong thư viện chuẩn, không xây dựng framework ngẫu nhiên cồng kềnh.
  - Chỉ kích hoạt cơ chế `ScopedRNG` khi `stable_variants=True`; chế độ mặc định tiếp tục đi theo luồng tuần tự nguyên bản để đảm bảo sự tối giản và tương thích tuyệt đối.
- [x] **III. Comprehensive Automated Testing**:
  - Tuân thủ nghiêm ngặt nguyên tắc Red-to-Green: Viết lại `tests/test_stable_variants.py` và các test case tái hiện lỗi trước, chứng minh thất bại trên mã nguồn cũ và thành công trên mã nguồn mới.
  - Bổ sung bộ kiểm thử riêng cho vòng đời seed (`test_seed_lifecycle.py`), phân trang ô gộp (`test_table_continuation.py`), kế hoạch dạy chữ (`test_teaching_plan.py`) và web parseSeed (`test_web_parse_seed.test.mjs`).
  - Toàn bộ test suite tất định, không flaky.
- [x] **IV. Loose Coupling & High Cohesion**:
  - `ScopedRNG` được đóng gói độc lập trong tầng model, không phụ thuộc vào tầng layout hay UI.
  - Định danh ô trong phân trang bảng được quản lý độc lập tại tầng layout (`LaidOutCell`), bảo vệ tầng Document IR bất biến.
  - `Bank.can()` hoạt động độc lập và phản ánh chính xác khả năng kết xuất thực tế của kho mẫu.

---

## Project Structure

### Documentation (this feature)

```text
specs/036-seed-stability-and-teaching-plan/
├── plan.md              # Kế hoạch triển khai (file này)
├── research.md          # Kết quả nghiên cứu Phase 0 (Box-Muller, Random(-5), Full Scan)
├── data-model.md        # Mô hình dữ liệu & thực thể Phase 1 (ScopedRNG, WriteOptions, LaidOutCell)
├── quickstart.md        # Hướng dẫn kiểm chứng & chạy thử nghiệm tự động
├── contracts/           # Các hợp đồng kỹ thuật chi tiết
│   ├── CTR-036-SEED-LIFECYCLE.md           # Hợp đồng vòng đời seed và kiểm chuẩn
│   ├── CTR-036-LOCALIZED-RNG.md            # Hợp đồng luồng ngẫu nhiên cục bộ
│   ├── CTR-036-TABLE-FULL-SCAN-AND-CELL-ID.md # Hợp đồng phân trang bảng & an toàn bounding box
│   └── CTR-036-TEACHING-PLAN.md            # Hợp đồng 38 mục cốt lõi & gỡ nghẽn hàng đợi
└── checklists/
    └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
```

### Source Code (affected paths)

```text
chuviettay/
├── model/
│   ├── rng.py            # [MỚI] Module sinh số ngẫu nhiên cục bộ (blake2b + Box-Muller)
│   ├── writer.py         # Tích hợp ScopedRNG, chống lặp biến thể cục bộ, đồng bộ measure_text_width
│   ├── bank.py           # Cập nhật Bank.can() công nhận từ nguyên khối trong bank.words
│   └── seed_words.py     # Định nghĩa CORE_ESSENTIALS_38 và get_core_essentials_38()
├── layout/
│   ├── engine.py         # Quét ô nguồn toàn bảng từ hàng 0, an toàn bounding box, ScopedRNG khi stable
│   ├── table_layout.py   # Định danh ô tăng đơn điệu trong LaidOutCell, bảo toàn TableCell IR
│   └── math_layout.py    # Truyền đầy đủ tham số sang _scratch(), ScopedRNG cho math khi stable
├── controller/
│   ├── results.py        # WriteOptions.validate() và WriteResult.seed_used
│   └── app_controller.py # Xác định hạt giống hiệu dụng, ưu tiên 38 mục cốt lõi trong hàng đợi
├── fidelity/
│   └── engine.py         # Truyền đủ tham số sang Writer và ghi nhận seed_used
├── browser/
│   └── bridge.py         # Trả về ignored_options và seed_used
├── cli.py                # Bổ sung trợ giúp --seed và in thông báo tái tạo kết quả
webapp/
└── js/
    └── write.js          # Tách hàm parseSeed(), chấp nhận 0, giữ nguyên seed hiện tại khi lỗi
tests/
├── test_seed_lifecycle.py        # [MỚI] Kiểm chuẩn seed, Random(-5), tái tạo byte-exact
├── test_stable_variants.py       # [VIẾT LẠI] Kiểm tra biến thể thật, prepend/shift invariance
├── test_table_continuation.py    # [MỚI/CẬP NHẬT] Ô gộp 3+ trang từ hàng 0, không bẹt nét chữ
├── test_teaching_plan.py         # [MỚI] 38 mục cốt lõi mở khóa 700 từ SEED, Bank.can gỡ tắc nghẽn
├── test_web_parse_seed.test.mjs  # [MỚI] Node test cho hàm parseSeed()
└── test_golden_master_real_path.py # Bảo toàn 100% hash cũ, thêm ca golden cho stable_variants=True
```

---

## Complexity Tracking

*Không phát hiện vi phạm Hiến pháp nào cần giải trình phức tạp.*  
Mọi cải tiến đều sử dụng thư viện chuẩn của ngôn ngữ Python, không thêm tầng trừu tượng không cần thiết, tôn trọng nguyên tắc KISS và YAGNI.

---

## Re-evaluation of Constitution Check Post-Design

- **Maintainability**: Toàn bộ các hợp đồng kỹ thuật và mô hình dữ liệu đã được định nghĩa minh bạch.
- **KISS/YAGNI**: Giải pháp ScopedRNG tối giản (chỉ bọc `random()` với Box-Muller và blake2b), không lạm dụng trừu tượng phức tạp.
- **Comprehensive Automated Testing**: Đầy đủ 6 kịch bản kiểm thử độc lập bao quát từ unit test đến golden master và node test.
- **Loose Coupling**: Tách biệt rõ ràng giữa sinh ngẫu nhiên (model/rng), kết xuất hình học (layout/engine) và mô hình tài liệu (document/ir).
