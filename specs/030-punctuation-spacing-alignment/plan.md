# Implementation Plan: Punctuation Spacing, Natural Alignment & Digit Spacing

**Branch**: `030-punctuation-spacing-alignment` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/030-punctuation-spacing-alignment/spec.md`

## Summary

Cải tiến cơ chế định vị hình học typographic trong `Writer` nhằm giải quyết dứt điểm 2 lỗi giao diện:
1. **Dấu câu bị dính sát vào từ / lệch tọa độ**: Chuẩn hóa gốc tọa độ `min_x = 0.0` cho tất cả các mẫu dấu câu (`punct`), căn mốc xuất phát của dấu câu đuôi (`trail`) dựa trên tọa độ cực đại thực tế (`max_x`) của nét chữ đứng trước cộng thêm khoảng đệm an toàn quang học (`clearance_gap = max(0.8 * pen_w, 0.18 * xh)`).
2. **Các chữ số cách nhau quá xa**: Chuẩn hóa và siết chặt khoảng cách giữa các chữ số liên tiếp (`dgaps` trong `Writer.number()`) theo tỷ lệ chiều cao chữ `xh` (`[0.08 * xh, 0.22 * xh]`), loại bỏ hiện tượng các chữ số trong cùng một số bị rời rạc thành các ký tự độc lập.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: Standard library (`math`, `re`, `random`), `chuviettay` core engine modules  
**Storage**: N/A (không sửa đổi schema lưu trữ file `.json.gz`, tương thích ngược 100% với kho mẫu hiện có)  
**Testing**: `pytest` (bổ sung suite test cho khoảng cách dấu câu, kiểm tra va chạm nét và khoảng cách chữ số)  
**Target Platform**: Desktop (Tkinter/Native CLI) & Web Client (Pyodide Web Worker)  
**Project Type**: Core Handwriting Layout Engine  
**Performance Goals**: Không làm tăng độ phức tạp thời gian kết xuất; xử lý microsecond trên mỗi token  
**Constraints**: Bảo toàn 100% kết quả kiểm thử hiện có (1145 test pass), zero regression  
**Scale/Scope**: Tác động trực tiếp đến `chuviettay/model/writer.py`, `chuviettay/layout/engine.py`, `chuviettay/layout/math_layout.py`  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Logic chuẩn hóa dấu câu và khoảng cách chữ số được viết tường minh, có type hint, tách nhỏ hàm helper phụ trợ rõ ràng.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Không tạo thêm tầng trừu tượng hay cấu trúc dữ liệu phức tạp; tinh chỉnh trực tiếp giải thuật định vị nét trong `Writer.token()` và `Writer.number()`.
- [x] **III. Comprehensive Automated Testing**: Viết unit test tự động đo đạc khoảng hở, kiểm tra zero-collision và khoảng cách chữ số trong cả văn bản thường lẫn công thức toán.
- [x] **IV. Loose Coupling & High Cohesion**: Writer tiếp tục giữ đúng vai trò sinh nét token, MathLayoutEngine và TableLayoutEngine tự động thừa hưởng kết quả mà không cần can thiệp chéo mã nguồn riêng tư.

## Project Structure

### Documentation (this feature)

```text
specs/030-punctuation-spacing-alignment/
├── plan.md              # Kế hoạch triển khai (file này)
├── research.md          # Phân tích nguyên nhân & giải pháp kỹ thuật
├── data-model.md        # Mô hình hình học & chuẩn hóa tọa độ
├── quickstart.md        # Hướng dẫn kiểm chứng & chạy thử nghiệm
├── contracts/
│   └── writer-contract.md # Hợp đồng giao diện hình học cho Writer
├── checklists/
│   └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
└── tasks.md             # Sẽ được sinh bởi /speckit-tasks
```

### Source Code (affected paths)

```text
chuviettay/
├── model/
│   └── writer.py         # Cải tiến chuẩn hóa punct, clearance gap và giới hạn dgap
├── layout/
│   ├── engine.py         # Kiểm tra tính đồng bộ inline spacing
│   └── math_layout.py    # Kiểm tra kích thước TextNode số học
tests/
├── test_writer.py        # Cập nhật và bổ sung test case
├── test_digits_and_punct.py # Cập nhật test case kiểm tra gap
└── test_punctuation_spacing.py # Test suite chuyên sâu cho feature 030
```

**Structure Decision**: Cấu trúc module đơn nhất trong repository, tập trung chính xác vào mô-đun kết xuất nét viết tay `chuviettay/model/writer.py`.

## Complexity Tracking

*(Không có vi phạm hiến pháp)*
