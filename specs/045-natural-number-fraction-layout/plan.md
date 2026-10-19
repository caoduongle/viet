# Implementation Plan: Cải thiện trình bày chữ số và phân số tự nhiên (Natural Number & Fraction Typography)

**Branch**: `045-natural-number-fraction-layout` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/045-natural-number-fraction-layout/spec.md`

## Summary

Triển khai cải tiến toàn diện hình học và typographic cho hệ thống kết xuất chữ số, số thập phân và phân số viết tay:
1. **Chuẩn hóa chữ số 2 chiều (`normalize_digit_sample`)**: Đưa toàn bộ chân chữ số về đường cơ sở (`y = 0.0`), quy chuẩn tỷ lệ chiều cao đồng nhất theo chuẩn lining figures (`~1.20 * xh`) nhằm khắc phục triệt để hiện tượng chữ số nhỏ, to thất thường và bay lơ lửng / tụt chân (như `4`, `6`, `7`, `8` so với `5`, `9`).
2. **Siết chặt khoảng cách chữ số và đồng bộ số thập phân**: Điều chỉnh khoảng cách giữa hai chữ số liên tiếp (`dgap`) trong dải tự nhiên `0.10 * xh` đến `0.18 * xh`; đồng bộ khoảng cách quanh dấu thập phân `,` để số thập phân (`0,39`, `0,0278`) hiển thị liền mạch, chấm dứt hiện tượng chữ số đầu dính vào dấu phẩy còn các chữ số sau bị đẩy văng ra xa (`0,3 9`).
3. **Tự động nhận diện dấu phẩy thập phân trong LaTeX toán (`LatexMathParser`)**: Dùng biểu thức chính quy với lookahead `,(?=[0-9])` để nhận diện số thập phân tiếng Việt viết bằng dấu phẩy tự nhiên (`$0,39$`, `$0,0278$`) thành một khối số thống nhất mà không phá vỡ dấu phẩy ngắt vế (`0,0278,`) hay dấu phẩy liệt kê (`(0, 1)`).
4. **Bố cục phân số nhỏ gọn, cân đối (`CompactFractionGeometry`)**: Tính toán khoảng hở quang học thực tế giữa nét tử số/mẫu số với thanh gạch ngang (`0.15 * xh` đến `0.25 * xh`), thu gọn độ dài gạch phân số thò ra hai bên (`0.15 * xh` đến `0.25 * xh`), và điều chỉnh tỷ lệ phân số trong các khối nhiều hàng (`cases`) để các hàng phân số nằm gọn ghẽ trên nền giấy kẻ ngang.

## Technical Context

**Language/Version**: Python 3.10+ (tương thích hoàn toàn với Web Pyodide và Desktop)  
**Primary Dependencies**: Thư viện chuẩn (`re`, `math`, `random`, `dataclasses`), các mô-đun lõi `chuviettay`  
**Storage**: N/A (không sửa đổi cấu trúc dữ liệu lưu file `.json.gz`, tương thích ngược 100% với các kho mẫu hiện có)  
**Testing**: `pytest` (bổ sung suite test đo khoảng cách, độ cao chữ số, căn chỉnh phân số và kiểm tra không hồi quy)  
**Target Platform**: Desktop (CLI) & Web Client (Pyodide Worker)  
**Project Type**: Core Handwriting Typography & Math Layout Engine  
**Performance Goals**: Xử lý microsecond trên mỗi token số/phân số; không làm tăng thời gian đo đạc và kết xuất tài liệu  
**Constraints**: Bảo toàn 100% các bài kiểm thử hiện có của toàn bộ dự án, zero regression  
**Scale/Scope**: Tác động trực tiếp đến `chuviettay/model/writer.py`, `chuviettay/math/parser.py`, `chuviettay/layout/math_layout.py`  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Logic chuẩn hóa chữ số và khoảng cách quang học phân số được đóng gói thành các hàm thuần túy với tài liệu, type hints rõ ràng, giữ gìn kiến trúc sạch.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Không bổ sung thêm thư viện ngoài hay các lớp kiến trúc phức tạp; tinh chỉnh trực tiếp các giải thuật hình học trong `Writer` và `MathLayoutEngine`.
- [x] **III. Comprehensive Automated Testing**: Thiết lập bộ unit test và regression test tự động đo đạc chính xác tọa độ baseline, khoảng hở tử/mẫu phân số và khoảng cách chữ số theo đơn vị `xh`.
- [x] **IV. Loose Coupling & High Cohesion**: `Writer` giữ đúng trách nhiệm chuẩn hóa nét chữ số, `LatexMathParser` phân tích cú pháp biểu thức toán, `MathLayoutEngine` quản lý hình học 2D. Sự kết hợp giữa các mô-đun diễn ra qua hợp đồng giao diện đã định nghĩa.

## Project Structure

### Documentation (this feature)

```text
specs/045-natural-number-fraction-layout/
├── plan.md              # Kế hoạch triển khai (file này)
├── research.md          # Phân tích nguyên nhân & các quyết định kỹ thuật
├── data-model.md        # Mô hình hình học & chuẩn hóa tọa độ chữ số / phân số
├── quickstart.md        # Hướng dẫn kiểm chứng & chạy thử nghiệm
├── contracts/
│   └── number-fraction-layout-contract.md # Hợp đồng giao diện hình học
├── checklists/
│   └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
└── tasks.md             # Sẽ được sinh bởi /speckit-tasks
```

### Source Code (affected paths)

```text
chuviettay/
├── model/
│   └── writer.py         # Chuẩn hóa baseline/chiều cao chữ số, siết chặt dgap và cân bằng khoảng cách số thập phân
├── math/
│   └── parser.py         # Nâng cấp _NUM_RE với lookahead nhận diện dấu phẩy thập phân tiếng Việt tự nhiên
├── layout/
│   └── math_layout.py    # Loại bỏ descent ảo cho TextNode số, tinh chỉnh gap và overhang cho phân số
tests/
├── test_writer.py        # Kiểm tra tính tương thích ngược
├── test_digits_and_punct.py # Kiểm tra nạp và sinh số
├── test_punctuation_spacing.py # Kiểm tra khoảng cách dấu câu và dgap
└── test_number_fraction_typography.py # Test suite chuyên biệt kiểm tra baseline, gap, và phân số cho Feature 045
```

**Structure Decision**: Cấu trúc đơn nhất tập trung vào các mô-đun xử lý nét và bố cục toán học của `chuviettay`, không tạo các thư mục thừa hay cấu trúc phân mảnh.

## Complexity Tracking

*(Không có vi phạm hiến pháp)*
