# Implementation Plan: Tối ưu hóa tìm ký tự giữ chỗ PUA và kiểm thử cạn kiệt toàn bộ vùng giữ chỗ

**Branch**: `063-pua-placeholder-optimization` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/063-pua-placeholder-optimization/spec.md`

---

## Summary

Sau commit `81df7a2` (CI 5/5 xanh), cơ chế dấu giữ chỗ PUA đã giải quyết trọn vẹn lỗi bảo toàn LaTeX (`\$\$` do người dùng viết không bị thay thế hàng loạt) và bảo vệ dấu đóng giả ở trích dẫn lồng nhau.
Kế hoạch triển khai Feature 063 giải quyết hai điểm cải tiến tiếp theo:
1. **Tối ưu hiệu năng chọn ký tự PUA (`_choose_fake_close_placeholder`)**:
   - Bổ sung fast-path: nếu ký tự đầu dãy `U+E000` không có trong văn bản, trả về ngay lập tức ($O(1)$ thêm, không tốn bộ nhớ).
   - Nếu có va chạm: tận dụng `set(text)` lọc `used_cps: set[int]` bằng C, kiểm tra `len(used_cps) == _FAKE_CLOSE_PUA_COUNT` để thoát sớm $O(1)$ nếu cạn kiệt, sau đó duyệt `range(0xE001, 0xF8FF + 1)` tra cứu số nguyên $O(1)$. Giảm độ phức tạp từ $O(k \times N)$ xuống $O(N)$ trong C khi gặp chuỗi nhiều ký tự PUA liên tiếp.
2. **Kiểm thử biên và dự phòng cạn kiệt toàn bộ 6.400 ký tự PUA**:
   - Bổ sung kiểm thử đơn vị xác nhận hàm trả về `None` khi văn bản chứa đủ 6.400 ký tự từ `U+E000` đến `U+F8FF`.
   - Bổ sung kiểm thử tích hợp E2E qua `import_text()` xác nhận luồng dự phòng (graceful fallback) an toàn khi `fake_close_placeholder=None`: không ném exception, không làm biến đổi ký tự PUA của người dùng, không rò rỉ ký tự lạ.

---

## Technical Context

**Language/Version**: Python ≥ 3.10 (CI: 3.12, 3.13, 3.14; Pyodide 314.0.7)

**Primary Dependencies**: `markdown-it-py` 4.2.0, `mdit-py-plugins` 0.6.1 (dollarmath, amsmath) — không thêm bất kỳ phụ thuộc mới nào

**Storage**: N/A

**Testing**: `pytest`, `ruff`, `node scripts/test_golden_pyodide.mjs`

**Target Platform**: CPython (Windows dev, Ubuntu CI) và Pyodide/WebAssembly trong Web Client

**Project Type**: Document importer pipeline (thư viện nội bộ) + test suite

**Performance Goals**:
- Trường hợp thông thường: kiểm tra tức thì $O(1)$ không tốn thêm bộ nhớ.
- Trường hợp va chạm $k$ ký tự: quét 1 lần $O(N)$, bộ nhớ tối đa 6.400 ký tự (vài chục KB), tra cứu set $O(1)$.
- Không làm tăng thời gian chạy test suite.

**Constraints**:
- Giữ nguyên chữ ký và kiểu trả về: `_choose_fake_close_placeholder(cls, text: str) -> str | None`.
- Không thay đổi hành vi đã đạt được của Feature 062: bảo toàn tuyệt đối công thức LaTeX và khôi phục dấu đóng giả.
- Fallback an toàn tuyệt đối khi cạn kiệt PUA: không ném exception, không sửa đổi dữ liệu người dùng.

**Scale/Scope**: 2 tệp mã:
- `chuviettay/importer/markdown_importer.py`
- `tests/test_markdown_math_block_isolation.py`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Trước Phase 0 | Sau Phase 1 | Đánh giá & Ghi chú |
| :--- | :---: | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | PASS | PASS | Mã nguồn rõ ràng, phân tách tường minh giữa fast-path và slow-path, có docstring giải thích chi tiết. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | PASS | Dùng thuần Python set có sẵn, không phát minh cấu trúc dữ liệu mới, không thêm dependency. |
| **III. Comprehensive Automated Testing** | PASS | PASS | Kiểm thử đầy đủ các kịch bản: fast-path, chuỗi va chạm, va chạm ngắt quãng, và cạn kiệt toàn bộ 6.400 ký tự. |
| **IV. Loose Coupling & High Cohesion** | PASS | PASS | Giao diện nội bộ cô lập, không ảnh hưởng đến các module khác trong hệ thống. |

Không có bất kỳ vi phạm hiến pháp nào.

---

## Project Structure

### Documentation (this feature)

```text
specs/063-pua-placeholder-optimization/
├── spec.md                                      # Đặc tả tính năng
├── plan.md                                      # Kế hoạch triển khai (tệp này)
├── research.md                                  # Nghiên cứu thuật toán & quyết định kỹ thuật
├── data-model.md                                # Mô hình dữ liệu & các bất biến hệ thống
├── quickstart.md                                # Hướng dẫn chạy và kiểm chứng nhanh
├── contracts/
│   └── pua-placeholder-optimization-contract.md # Hợp đồng API & bảng ca kiểm thử
└── checklists/
    └── requirements.md                          # Bảng kiểm định chất lượng yêu cầu
```

### Source Code (repository root)

```text
chuviettay/
└── importer/
    └── markdown_importer.py
        # ~ _choose_fake_close_placeholder(cls, text: str) -> str | None
        #   - Fast-path kiểm tra first_pua
        #   - Slow-path lọc used_cps = {ord(c) for c in set(text) if ...} và duyệt tìm ký tự chưa dùng
        #   - Thoát sớm O(1) và trả về None khi cạn kiệt 6.400 ký tự

tests/
└── test_markdown_math_block_isolation.py
    # + test_choose_fake_close_placeholder_optimization()
    #   - T-FAST-PATH: không có U+E000
    #   - T-EMPTY: chuỗi rỗng
    #   - T-COLL-MULTI: chuỗi nhiều ký tự PUA liên tiếp
    #   - T-COLL-SPARSE: va chạm ngắt quãng
    #   - T-EXHAUST-NONE: cạn kiệt 6.400 ký tự trả về None
    # + test_fake_close_pua_exhaustion_e2e_fallback()
    #   - T-EXHAUST-E2E: nhập tài liệu chứa đủ 6.400 ký tự PUA kèm khối toán trong blockquote
```

---

## Complexity Tracking

Không có vi phạm hiến pháp hoặc độ phức tạp không chính đáng.

| Thành phần | Mức độ phức tạp | Lý do cần thiết | Giải pháp đơn giản hơn bị từ chối vì |
| :--- | :--- | :--- | :--- |
| `used_pua = {c for c in text if ...}` | Tối thiểu ($O(N)$) | Tránh việc quét lại toàn chuỗi lặp đi lặp lại $k$ lần khi có nhiều ký tự PUA | Lặp `ch not in text` có độ phức tạp xấu nhất $O(k \times N)$ |

---

## Risks & Mitigations

| Rủi ro | Mức độ | Biện pháp giảm thiểu |
| :--- | :---: | :--- |
| Tạo `used_pua` làm chậm các văn bản thông thường không có PUA | Thấp | Đã có fast-path kiểm tra `first_pua not in text` trước; nếu không có thì trả về ngay tức thời không tạo set. |
| Tài liệu chứa đủ 6.400 ký tự PUA gây lỗi phân tích cú pháp | Rất thấp | `import_text` và `_isolate_display_math_blocks` đã được thiết kế để nhận diện `placeholder=None` và fallback an toàn, có bài test E2E xác nhận. |
| Tác động ngoài ý muốn tới các bài kiểm thử LaTeX của commit 81df7a2 | Cực thấp | Thuật toán vẫn trả về cùng các ký tự PUA theo thứ tự tăng dần; 100% các bài test hiện có tiếp tục chạy và vượt qua. |
