# Implementation Plan: Nhận Diện Khối Công Thức Toán Display Khi Xuống Dòng Và Ngăn Ngừa Đè Nét Cận Toán Tử

**Branch**: `053-markdown-math-block-isolation` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/053-markdown-math-block-isolation/spec.md`

---

## Summary

Triển khai giải pháp hai tầng khắc phục triệt để hiện tượng vỡ bố cục và đè nét công thức toán học được phản ánh qua 3 ảnh chụp màn hình:
1. **Tầng 1 — Tiền chuẩn hóa cách ly khối toán display (`MarkdownImporter`)**: Tự động phát hiện các cặp dấu `$$...$$` hoặc `\[...\]` bắt đầu ở dòng mới hoặc liền sau dấu hai chấm `:` mà thiếu dòng trống ngăn cách theo chuẩn CommonMark, tự động chèn ranh giới dòng trống chuẩn để `markdown-it-py` và `dollarmath_plugin` luôn nhận diện đúng là khối công thức độc lập `MathBlock` cấp 1 thay vì `MathInline`. Áp dụng cơ chế quét dòng an toàn (line-by-line scanning), bỏ qua các hàng bảng GFM (`|...|`), bảo toàn thụt lề trong danh sách, và chống ReDoS.
2. **Tầng 2 — Cưỡng chế khoảng hở quang học an toàn cận bên (`MathLayoutEngine`)**: Bổ sung thuật toán kiểm tra khoảng hở quang học tối thiểu ($\text{min\_gap} \ge 3.5\text{ pt}$) giữa chỉ số trên và chỉ số dưới khi toán tử lớn thẳng hàng ($\sum, \prod$, với `sup_dx == 0`) hiển thị ở chế độ cận bên (`stacked = False`), tự động bù trừ độ cao `sup_y` và `sub_y` để nét viết tay của hai chỉ số không bao giờ đè lấn lên nhau (không áp dụng cho các toán tử tích phân đã có độ lệch ngang `sup_dx > 0`).
3. **Đồng bộ phân phối Web Client**: Đóng gói lại `chuviettay.zip` qua `scripts/build_web.py` để Web Client Pyodide ngay lập tức được hưởng lợi từ các cải tiến này.

---

## Technical Context

**Language/Version**: Python 3.10 / 3.14 (Core Layout & Markdown Importer Engine), JavaScript ES2022+ (Web Client / Pyodide Worker)  

**Primary Dependencies**: `markdown-it-py`, `mdit_py_plugins`, Pyodide WebAssembly runtime, standard Python libraries (`re`, `math`, `typing`)  

**Storage**: N/A (không thay đổi cấu trúc dữ liệu lưu trữ kho chữ hay tệp xopp)  

**Testing**: `pytest tests/test_importer_markdown.py tests/test_markdown_math_import.py tests/test_math_layout.py tests/test_golden_master_real_path.py tests/test_build_web.py`  

**Target Platform**: CLI / Thư viện Python cục bộ và Trình duyệt Web tĩnh PWA (Chrome, Edge, Firefox, Safari)  

**Project Type**: Trình chuyển đổi tài liệu & Engine bố cục công thức toán học viết tay  

**Performance Goals**:
- Thời gian chuẩn hóa chuỗi Markdown: $< 0.5\text{ ms}$ cho văn bản dài 10.000 ký tự (độ phức tạp $O(L)$ tuyến tính)
- Độ trễ bổ sung cho tính toán khoảng hở cận bên: $< 0.01\text{ ms}$ mỗi biểu thức toán học

**Constraints**:
- Bảo toàn nguyên vẹn 100% nội dung bên trong các đoạn mã (`_CODE_SEGMENT`: ```, ~~~, `)
- Không làm sai lệch hoặc phá vỡ các trường hợp công thức nội dòng chuẩn đặt trong `$ $`
- Bảo toàn 100% kết quả kiểm thử Golden Master SHA-256 (`tests/test_golden_master_real_path.py`)

**Scale/Scope**:
- 2 tệp mã nguồn Python cốt lõi: `chuviettay/importer/markdown_importer.py`, `chuviettay/layout/math_layout.py`
- 2 tệp kiểm thử tự động mở rộng: `tests/test_importer_markdown.py`, `tests/test_math_layout.py`
- 1 lần đóng gói web client: `scripts/build_web.py`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Nguyên tắc Hiến pháp | Yêu cầu Kỹ thuật | Trạng thái | Đánh giá Tuân thủ |
|----------------------|------------------|------------|-------------------|
| **I. Maintainability & Code Cleanliness** | Mã nguồn rõ ràng, tự tài liệu hóa, có tài liệu giải thích lý do thiết kế (nghiên cứu TeX Rule 18 và CommonMark paragraph boundaries). | **PASS** | Tách hàm chuyên biệt `_isolate_display_math_blocks`, có chú thích rõ ràng về regex và mục đích. |
| **II. Simple Architecture (KISS & YAGNI)** | Ưu tiên giải pháp tiền xử lý dòng trống đơn giản, trực tiếp; không tạo thêm tầng trừu tượng hay phụ thuộc thư viện mới. | **PASS** | Tận dụng regex bảo vệ code block sẵn có trong `markdown_importer.py`, không thêm dependency. |
| **III. Comprehensive Automated Testing** | Tất cả các ca lỗi (Ảnh 1, 2, 3) và các trường hợp biên phải có unit test tự động và kiểm thử hồi quy. | **PASS** | Bổ sung test cases bao phủ đầy đủ các trường hợp: không có dòng trống, dính dấu hai chấm, nhiều khối liên tiếp, và khoảng hở cận bên $\ge 3.5\text{ pt}$. |
| **IV. Loose Coupling & High Cohesion** | Giữ nguyên ranh giới phân tách: `markdown_importer` chịu trách nhiệm tạo đúng IR `MathBlock`; `math_layout` chịu trách nhiệm về khoảng cách quang học nét vẽ. | **PASS** | Ranh giới trách nhiệm rõ ràng, không có sự phụ thuộc chéo hay rò rỉ chi tiết cài đặt giữa hai module. |
| **V. Golden Master Invariance** | Không được làm sai lệch mã băm SHA-256 của 9 bài kiểm thử Golden Master. | **PASS** | Các cải tiến tập trung vào ca lỗi nhận diện khối toán thiếu dòng trống và cận bên đè nét; các ca chuẩn không bị ảnh hưởng. |

*Gate Status*: **PASSED**

---

## Project Structure

### Documentation (this feature)

```text
specs/053-markdown-math-block-isolation/
├── spec.md              # Đặc tả yêu cầu tính năng từ người dùng
├── checklists/
│   └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
├── plan.md              # Kế hoạch triển khai kiến trúc chi tiết (File này)
├── research.md          # Nghiên cứu kỹ thuật, nguyên nhân cốt lõi và quyết định
├── data-model.md        # Mô hình thực thể IR, máy trạng thái và hình học cận bên
├── contracts/           # Hợp đồng giao tiếp giữa các module
│   ├── markdown-math-block-contract.md
│   └── operator-limits-clearance-contract.md
└── quickstart.md        # Hướng dẫn kiểm chứng và các kịch bản chạy thử nghiệm
```

### Source Code (repository root)

```text
chuviettay/
├── importer/
│   └── markdown_importer.py  # Bổ sung tiền chuẩn hóa cách ly khối $$...$$ trong _normalize_math_delimiters
└── layout/
    └── math_layout.py        # Bổ sung kiểm tra và bảo đảm khoảng hở quang học tối thiểu trong _m_NAry

tests/
├── test_importer_markdown.py # Thêm test cases nhận diện MathBlock khi xuống dòng đơn và sau dấu hai chấm
└── test_math_layout.py       # Thêm test cases đo khoảng hở quang học giữa sup và sub của toán tử lớn

scripts/
└── build_web.py              # Đóng gói chuviettay.zip cập nhật cho Web Client
```

**Structure Decision**: Tính năng thuộc phạm vi engine lõi Python (`chuviettay/importer` và `chuviettay/layout`) kèm cập nhật bản phân phối Web Client (`webapp/dist/pyodide/`).

---

## Complexity Tracking

> Không có vi phạm Hiến pháp nào cần giải trình.
