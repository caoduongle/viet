# Implementation Plan: Khống chế bộ nhớ tập hợp PUA và chuẩn hóa thống kê kiểm thử hiệu năng

**Branch**: `064-pua-memory-and-benchmark` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/064-pua-memory-and-benchmark/spec.md`

---

## Summary

Sau commit `a9da0c2`, logic chọn ký tự PUA và kiểm thử cạn kiệt đã chính xác và vượt qua CI. Tuy nhiên, việc sử dụng `set(text)` trong nhánh va chạm làm bộ nhớ tạm tăng theo số lượng ký tự phân biệt của toàn bộ văn bản thay vì bị chặn bởi 6.400 ký tự PUA. Ngoài ra, tuyên bố $O(1)$ cho nhánh kiểm tra nhanh cần được chuẩn hóa lại và cơ chế thử lại của bài benchmark đối kháng cần chuyển sang phương pháp thống kê trung vị (median) không thiên vị.

Kế hoạch giải quyết 3 điểm trọng tâm:
1. **Khống chế tuyệt đối bộ nhớ tập hợp PUA**:
   - Sử dụng regex pre-compiled `_PUA_RE = re.compile(r"[\uE000-\uF8FF]")` ở cấp module.
   - Nhánh va chạm dùng `_PUA_RE.finditer(text)` thêm trực tiếp vào `used_cps: set[int]`, dừng sớm ngay khi đạt 6.400 phần tử, loại bỏ hoàn toàn `set(text)` và không cấp phát danh sách trung gian.
   - Dung lượng tập hợp bộ nhớ phụ luôn bị chặn cứng $\le 6.400$ phần tử, đồng thời tăng tốc độ quét lên 20x trên tài liệu đa ngữ.
2. **Chuẩn hóa thống kê trung vị cho bài benchmark đối kháng**:
   - Trong `test_adversarial_complexity_multi_length_backticks_and_long_lines`, chạy 5 lượt đo độc lập và tính `median(ratios)`.
   - Loại bỏ nhánh chọn kết quả nhỏ hơn (`min`), bảo đảm tính khách quan, kháng nhiễu hệ điều hành tự nhiên mà không che giấu hồi quy hiệu năng.
3. **Chuẩn hóa tài liệu kỹ thuật & độ phức tạp**:
   - Cập nhật docstring phân định rõ: nhánh nhanh có thời gian duyệt chuỗi con $O(N)$ ở tầng C với bộ nhớ phụ $O(1)$; nhánh va chạm có 2 lượt quét chuỗi $O(N)$ với bộ nhớ phụ $O(\min(N, 6400))$.

---

## Technical Context

**Language/Version**: Python ≥ 3.10 (CI: 3.12, 3.13, 3.14; Pyodide 314.0.7)

**Primary Dependencies**: `markdown-it-py` 4.2.0, `mdit-py-plugins` 0.6.1 — không thêm bất kỳ phụ thuộc mới nào

**Storage**: N/A

**Testing**: `pytest`, `ruff`, `node scripts/test_golden_pyodide.mjs`

**Target Platform**: CPython và Pyodide/WebAssembly trong Web Client

**Project Type**: Document importer pipeline + test suite

**Performance & Memory Goals**:
- Dung lượng bộ nhớ phụ cho PUA selection luôn $\le 6.400$ phần tử trên mọi kích thước và kiểu văn bản.
- Tốc độ trích xuất PUA nhanh hơn 15–20x so với `set(text)` trên tài liệu đa ngữ.
- Bài benchmark đối kháng đạt $R_{\text{med}} \le 6.0$ một cách ổn định và không thiên vị.

**Constraints**:
- Giữ nguyên toàn bộ hành vi đúng đắn của Feature 062/063 (bảo toàn LaTeX `\$\$`, dấu đóng giả lồng nhau, cạn kiệt 6.400 ký tự trả về `None`).
- Không thêm thư viện ngoài.

**Scale/Scope**: 2 tệp mã:
- `chuviettay/importer/markdown_importer.py`
- `tests/test_markdown_math_block_isolation.py`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Trước Phase 0 | Sau Phase 1 | Đánh giá & Ghi chú |
| :--- | :---: | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | PASS | PASS | Tuyên bố độ phức tạp trong docstring chính xác, phân biệt rõ ràng giữa thời gian và bộ nhớ phụ. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | PASS | Dùng regex pre-compiled tiêu chuẩn, không thêm cấu trúc phức tạp. |
| **III. Comprehensive Automated Testing** | PASS | PASS | Benchmark dùng chuẩn thống kê trung vị khách quan; bổ sung kiểm thử bộ nhớ với văn bản đa ngữ 10.000 ký tự phân biệt. |
| **IV. Loose Coupling & High Cohesion** | PASS | PASS | Thay đổi cô lập bên trong module importer, không ảnh hưởng đến API công khai. |

---

## Project Structure

### Documentation (this feature)

```text
specs/064-pua-memory-and-benchmark/
├── spec.md                                      # Đặc tả tính năng
├── plan.md                                      # Kế hoạch triển khai (tệp này)
├── research.md                                  # Nghiên cứu thực nghiệm regex vs set(text) & trung vị
├── data-model.md                                # Mô hình dữ liệu & các bất biến
├── quickstart.md                                # Hướng dẫn chạy và kiểm chứng nhanh
├── contracts/
│   └── pua-memory-and-benchmark-contract.md     # Hợp đồng API & bảng ca kiểm thử
└── checklists/
    └── requirements.md                          # Bảng kiểm định chất lượng yêu cầu
```

### Source Code (repository root)

```text
chuviettay/
└── importer/
    └── markdown_importer.py
        # + _PUA_RE = re.compile(r"[\uE000-\uF8FF]")
        # ~ _choose_fake_close_placeholder:
        #     dùng _PUA_RE.finditer(text) với thoát sớm thay cho set(text)
        #     cập nhật docstring phân định rõ O(N) thời gian và O(1) / O(min(N,6400)) bộ nhớ phụ

tests/
└── test_markdown_math_block_isolation.py
    # + test_pua_memory_bounded_multilingual()
    #     kiểm chứng văn bản 10.000 ký tự phân biệt + \ue000 -> used_cps chỉ chứa đúng 1 phần tử
    # ~ test_adversarial_complexity_multi_length_backticks_and_long_lines:
    #     chạy 5 lượt đo cố định, lấy statistics.median(ratios) <= 6.0, log chi tiết từng lượt
```

---

## Complexity Tracking

Không có vi phạm hiến pháp hoặc độ phức tạp không chính đáng.

| Thành phần | Mức độ phức tạp | Lý do cần thiết | Giải pháp đơn giản hơn bị từ chối vì |
| :--- | :--- | :--- | :--- |
| `_PUA_RE.findall(text)` | Tối thiểu ($O(N)$ ở C) | Khống chế cứng bộ nhớ $\le 6.400$ phần tử, loại bỏ việc nạp toàn bộ ký tự phân biệt của tài liệu | `set(text)` tiêu tốn bộ nhớ theo bảng chữ cái tài liệu; generator chậm hơn 20 lần |
| `statistics.median` 5 lượt | Tối thiểu | Kháng nhiễu khách quan, không thiên vị | Chọn `min(ratio, retry)` tạo xu hướng thiên vị kết quả đo thấp |

---

## Risks & Mitigations

| Rủi ro | Mức độ | Biện pháp giảm thiểu |
| :--- | :---: | :--- |
| `_PUA_RE.findall` chậm hơn khi có 6.400 ký tự PUA | Rất thấp | Đo đạc thực tế cho thấy `findall` chỉ mất 5.3ms (nhanh gấp 15 lần `set(text)` 78ms do được tối ưu ở tầng C). |
| 5 lượt đo kéo dài thời gian chạy bài test đối kháng | Thấp | Mỗi lượt đo chỉ tốn ~0.8s, tổng 5 lượt tốn ~4s, hoàn toàn nằm trong giới hạn kiểm thử chấp nhận được. |
