# Implementation Plan: Chuẩn hóa script benchmark PUA và tích hợp CI smoke test

**Branch**: `066-pua-benchmark-hardening` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/066-pua-benchmark-hardening/spec.md`

---

## Summary

Feature 066 hoàn thiện 3 điểm P3 từ lần rà soát commit `3b20612`:
1. **Chuẩn hóa `--rounds` & sinh dữ liệu thực sự đa ngữ**:
   - Áp dụng tham số `--rounds` nhất quán cho cả kịch bản chính và kịch bản đối kháng trong `scripts/benchmark_pua_memory.py`.
   - Nâng cấp `make_multilingual_text()` kết hợp 4 hệ ký tự Unicode: CJK/Hán Nôm (`U+4E00..`), Cyrillic (`U+0410..`), Hy Lạp (`U+0391..`), Ký hiệu toán học (`U+2200..`) và PUA `\ue000`.
   - Tính toán kích thước byte UTF-8 thực tế bằng `len(text.encode("utf-8"))`, loại bỏ hoàn toàn các con số ước lượng cứng.
2. **Kiểm thử tự động Smoke Test cho script benchmark**:
   - Thêm bài kiểm thử `tests/test_benchmark_pua_smoke.py` chạy script qua subprocess với `--rounds 1 --json`, xác nhận mã thoát 0 và tính hợp lệ của cấu trúc JSON.
3. **Tích hợp Smoke Test vào Continuous Integration (CI)**:
   - Thêm bước thực thi `python scripts/benchmark_pua_memory.py --rounds 1 --json` vào các job kiểm thử Python trong `.github/workflows/ci.yml`.

---

## Technical Context

**Language/Version**: Python 3.10+ (Đã kiểm chứng tương thích CPython 3.10, 3.12, 3.13, 3.14).

**Primary Dependencies**: 100% thư viện chuẩn của Python (`re`, `tracemalloc`, `time`, `platform`, `sys`, `gc`, `json`, `subprocess`, `argparse`). Không thêm thư viện thứ ba.

**Storage**: Bộ nhớ RAM trong tiến trình thử nghiệm.

**Testing**: `pytest` và kiểm thử tự động `subprocess` smoke test.

**Target Platform**: GitHub Actions CI (Ubuntu) và môi trường phát triển cục bộ (Windows, macOS, Linux).

**Project Type**: Kịch bản công cụ hỗ trợ (`scripts/benchmark_pua_memory.py`), bộ kiểm thử (`tests/test_benchmark_pua_smoke.py`) và CI workflow (`.github/workflows/ci.yml`).

**Performance Goals**:
- Script benchmark chạy với `--rounds 1 --json` hoàn tất trong dưới 3 giây.
- Bước smoke test trong CI không làm tăng thời gian chạy job quá 5 giây.

**Constraints**:
- Không phụ thuộc vào ngưỡng thời gian tuyệt đối trong bài kiểm thử tự động.
- Không phá vỡ các luồng build hay các job CI hiện tại.

**Scale/Scope**: Giới hạn trong 3 tệp chính:
- `scripts/benchmark_pua_memory.py`
- `tests/test_benchmark_pua_smoke.py`
- `.github/workflows/ci.yml`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp (Constitution Principle) | Đánh giá Tuân thủ | Ghi chú & Biện minh |
| :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | **PASS** | Tự tài liệu hóa, xóa bỏ ước lượng cứng, tính toán kích thước động chính xác. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Tái sử dụng tham số `--rounds` nhất quán, không đẻ thêm cờ phức tạp, dùng thư viện chuẩn. |
| **III. Comprehensive Automated Testing** | **PASS** | Bổ sung smoke test tự động cấp repo và tích hợp trực tiếp vào CI workflow. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Script benchmark độc lập không can thiệp vào logic nghiệp vụ của importer. |
| **CI & Quality Verification Workflow** | **PASS** | Tự động hóa kiểm tra script trên toàn bộ matrix Python của CI. |

---

## Project Structure

### Documentation (this feature)

```text
specs/066-pua-benchmark-hardening/
├── plan.md              # Kế hoạch triển khai kiến trúc chi tiết
├── research.md          # Phân tích kỹ thuật và quyết định giải pháp
├── data-model.md        # Mô hình dữ liệu MultilingualCorpus và BenchmarkJsonReportSchema
├── quickstart.md        # Hướng dẫn kiểm chứng từng bước
├── contracts/
│   └── benchmark-hardening-contract.md  # Hợp đồng CLI schema và CI workflow
└── checklists/
    └── requirements.md  # Danh mục thẩm định chất lượng đặc tả
```

### Source Code (repository root)

```text
scripts/
└── benchmark_pua_memory.py           # Chuẩn hóa --rounds, sinh dữ liệu 4 họ chữ, đo byte động

tests/
└── test_benchmark_pua_smoke.py       # Bài kiểm thử tự động pytest smoke test

.github/workflows/
└── ci.yml                            # Tích hợp bước benchmark smoke test vào CI matrix
```

---

## Complexity Tracking

> Không có vi phạm kiến trúc nào. Tất cả giải pháp đều đơn giản, tinh gọn và hướng tới độ tin cậy dài hạn.
