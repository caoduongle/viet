# Implementation Plan: Ổn định Dòng kết xuất và Tính tái lập Hạt giống (Render Pipeline Seed Stability)

**Branch**: `037-render-pipeline-seed-stability` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/037-render-pipeline-seed-stability/spec.md`

---

## Summary

Triển khai giải pháp kỹ thuật giải quyết dứt điểm các lỗi và khoảng trống tồn đọng từ đợt rà soát repo commit `4d7e5ba`:
1. **Bảo tồn Metadata Token trong Pipeline Kết xuất (P1)**: Xây dựng lớp `RenderItem` (`dataclass(slots=True)`) thay thế tuple rời rạc, bảo tồn định danh token, chuỗi ký tự, thứ tự xuất hiện, độ rộng và nét vẽ xuyên suốt quá trình tính toán dòng và ô bảng (`chuviettay/layout/engine.py` và `table_layout.py`).
2. **Neo giữ Ngẫu nhiên Hình học Nét bền vững (P1)**: Dẫn xuất hạt giống hình học nét từ cặp định danh ổn định `(token, occurrence)` thay vì chỉ số phần tử dòng `it_idx` hay tọa độ Y biến thiên. Khi `stable_variants=True`, triệt tiêu sóng dòng vĩ mô (`slope=0, amp=0, xo=start_x`) để bảo đảm tính bất biến tuyệt đối khi ngắt dòng thay đổi do chèn tiền tố.
3. **Cô lập Ngữ cảnh Hạt giống Toán học và Chữ số (P2)**: Cập nhật `Writer.number()` tự thiết lập ngữ cảnh `_current_tok` và `_current_k` khi `stable_variants=True`; cấp phát `MathRenderContext` độc lập cho từng công thức toán trong `MathLayoutEngine`, đồng bộ hóa 100% giữa bước đo thử `_scratch()` và bước vẽ thật.
4. **Kiểm thử Tích hợp Cả Hai Engine (P2)**: Bổ sung bài kiểm thử tự động tái lập bit-exact qua `seed_used` trên `FidelityLayoutEngine` (tệp Word .docx) và bài kiểm thử tích hợp chèn từ với `jitter=1.0` trên toàn bộ pipeline của `DocumentLayoutEngine`.
5. **Đồng bộ Giao diện Người dùng và Làm rõ Cam kết (Desktop & Web)**:
   - Thêm checkbox *"Kiểu chữ ổn định"* vào Desktop GUI (`write_tab.py`).
   - Cập nhật `write_report_lines()` tự động in `Seed đã dùng: <seed_used>` cho cả Desktop GUI và CLI.
   - Bổ sung nhãn báo lỗi trực quan `#opt-seed-error` dưới ô nhập seed trên Web Client (`write.js`).
   - Tài liệu hóa rõ ràng trong `chuviettay/model/rng.py`: cam kết bit-exact 100% trên cùng runtime CPython, tương đương thống kê giữa các nền tảng khác biệt.

---

## Technical Context

**Language/Version**: Python >= 3.10 (Môi trường hiện tại: Python 3.10+; hỗ trợ CI Python 3.10, 3.12, 3.14).  
**Primary Dependencies**: Standard Library (`hashlib`, `math`, `secrets`, `random`, `dataclasses`). **Zero runtime external dependencies** (`dependencies = []`). Tương thích 100% với môi trường Pyodide/WebAssembly.  
**Storage**: Giữ nguyên schema kho mẫu `.json.gz` hiện tại.  
**Testing**: `pytest`, `pytest-timeout` (Python), `node --test` (Web Client).  
**Target Platform**: Desktop (Tkinter GUI, CLI native) và Web Client (Pyodide Web Worker).  
**Project Type**: Core Typography, Layout Engine & Multi-Interface Client.  
**Performance Goals**: Thời gian kết xuất tài liệu ~5.000 token không suy giảm; các thao tác sinh số ngẫu nhiên cục bộ `ScopedRNG` dưới microsecond.  
**Constraints**:
- Chế độ mặc định `stable_variants=False` giữ nguyên 100% từng byte: hash trong `test_golden_master_real_path.py` không được đổi.
- `RenderItem` phải hỗ trợ truy cập chỉ số kiểu tuple `item[0]`, `item[1]`, `item[2]`, `item[4]` để tương thích ngược hoàn toàn.
**Scale/Scope**: Tác động trực tiếp đến 7 module cốt lõi (`layout/engine.py`, `layout/table_layout.py`, `layout/math_layout.py`, `model/writer.py`, `model/rng.py`, `formatting.py`, `view/write_tab.py`), giao diện web (`webapp/js/write.js`), và các tệp test (`tests/test_seed_lifecycle.py`, `tests/test_stable_variants.py`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**:
  - `RenderItem` thay thế các tuple ma thuật rời rạc bằng cấu trúc dữ liệu tự mô tả, có kiểu dữ liệu tường minh, loại bỏ lỗi truy cập sai chỉ số tuple.
  - Các khóa ScopedRNG có phân cấp không gian tên chuẩn mực: `("tok", token, occurrence, "geom")`, `("math", formula_id)`.
- [x] **II. Simple Architecture (KISS & YAGNI)**:
  - Sử dụng `dataclass(slots=True)` sẵn có của Python chuẩn, không đưa vào thư viện Pydantic hay bên thứ ba.
  - `write_report_lines()` được sử dụng làm điểm tập trung duy nhất để xuất thông tin `seed_used`, loại bỏ mã nguồn in riêng lẻ trùng lặp giữa CLI và GUI.
- [x] **III. Comprehensive Automated Testing**:
  - Tuân thủ nguyên tắc Red-to-Green: Bổ sung kiểm thử tích hợp tái hiện lỗi mất token metadata và lỗi sai ngữ cảnh số trong toán học trước khi sửa mã.
  - Bao phủ kiểm thử tự động trên cả hai engine (Semantic và Fidelity) với `jitter > 0`.
- [x] **IV. Loose Coupling & High Cohesion**:
  - `MathRenderContext` cô lập hoàn toàn trạng thái sinh số ngẫu nhiên của biểu thức toán học, không làm rò rỉ bộ đếm sang tầng văn bản.
  - `RenderItem` chỉ đóng vai trò chứa dữ liệu bố cục hiển thị, không làm bẩn cấu trúc Document IR gốc.

---

## Project Structure

### Documentation (this feature)

```text
specs/037-render-pipeline-seed-stability/
├── plan.md              # Kế hoạch triển khai (file này)
├── research.md          # Nghiên cứu kỹ thuật Phase 0 (RenderItem, Macro Drift, Math Scoping)
├── data-model.md        # Mô hình thực thể Phase 1 (RenderItem, TokenIdentifier, MathRenderContext)
├── quickstart.md        # Hướng dẫn kiểm chứng và chạy thử nghiệm
├── contracts/           # Các hợp đồng kỹ thuật chi tiết
│   ├── CTR-037-RENDER-ITEM-METADATA.md      # Hợp đồng cấu trúc RenderItem
│   ├── CTR-037-STABLE-STROKE-GEOMETRY.md    # Hợp đồng neo giữ ngẫu nhiên hình học nét chữ
│   ├── CTR-037-MATH-RNG-SCOPING.md          # Hợp đồng cô lập ngữ cảnh hạt giống toán học
│   └── CTR-037-UI-SEED-ALIGNMENT.md         # Hợp đồng đồng bộ giao diện Desktop GUI & Web Client
└── checklists/
    └── requirements.md  # Bảng kiểm định chất lượng đặc tả
```

### Source Code (affected paths)

```text
chuviettay/
├── model/
│   ├── rng.py            # Cập nhật docstring phân định rõ 2 phạm vi cam kết bit-exact
│   └── writer.py         # Cập nhật Writer.number() thiết lập _current_tok & _current_k khi stable
├── layout/
│   ├── engine.py         # Định nghĩa RenderItem, neo geom_rng vào (token, occ), triệt tiêu drift khi stable
│   ├── table_layout.py   # Sử dụng RenderItem trong ô bảng, bảo toàn metadata khi ngắt dòng đa trang
│   └── math_layout.py    # Đồng bộ hóa cấu hình Writer trong _scratch() và layout_lines()
├── formatting.py         # write_report_lines() tự động bổ sung dòng thông tin seed_used
├── view/
│   └── write_tab.py      # Bổ sung checkbox "Kiểu chữ ổn định (stable_variants)"
├── cli.py                # Xóa mã in lặp seed_used ngoài write_report_lines
webapp/
├── js/
│   └── write.js          # Bổ sung nhãn báo lỗi trực quan #opt-seed-error dưới ô nhập seed
tests/
├── test_seed_lifecycle.py   # Thêm test tái lập bit-exact cho FidelityLayoutEngine và write_report_lines
└── test_stable_variants.py  # Thêm test tích hợp chèn từ với jitter=1.0 và độc lập ngữ cảnh toán học
```

---

## Complexity Tracking

*Không có vi phạm nguyên tắc Hiến chương cần biện minh.*
