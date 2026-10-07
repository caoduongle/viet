# Implementation Plan: Khắc Phục Lỗi Làm Mới Khi Xóa Hàng Loạt Trên Web Client

**Branch**: `029-fix-batch-delete-refresh` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-fix-batch-delete-refresh/spec.md`

## Summary

Khắc phục lỗi tham chiếu `ReferenceError: refreshBankTab is not defined` khi người dùng thực hiện thao tác "Xoá đã chọn" trên Web Client bằng cách chuẩn hóa lời gọi hàm làm mới giao diện thành `refreshBankView()`, đồng bộ hóa bản build phân phối trong `webapp/dist/` thông qua `scripts/build_web.py`, và bổ sung kịch bản kiểm thử E2E tự động xác thực luồng xóa hàng loạt.

## Technical Context

**Language/Version**: JavaScript (ES2022 / ES Modules), Python 3.12 (Build script), TypeScript/Playwright (E2E Tests)

**Primary Dependencies**: `@playwright/test` (E2E test), `pyodide` (Web client engine)

**Storage**: IndexedDB (trình duyệt), BroadcastChannel (đồng bộ đa tab)

**Testing**: `npx playwright test tests/e2e/bank.spec.ts`

**Target Platform**: Web Browser (Chrome, Firefox, Safari, Edge), PWA

**Project Type**: Web application client (Frontend)

**Performance Goals**: Thao tác xóa và làm mới giao diện hoàn tất dưới 300ms sau khi worker xử lý xong

**Constraints**: Không thay đổi logic xóa phía backend Python; tuân thủ triệt để cấu trúc modul ES6

**Scale/Scope**: Thao tác xóa từ 1 đến hàng trăm nhãn ký tự trong kho mẫu

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá Tuân thủ | Ghi chú |
| :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | **PASS** | Sử dụng đúng định danh hàm chuẩn `refreshBankView()`, loại bỏ lỗi typo tham chiếu. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Sửa trực tiếp tại điểm gọi lỗi, không tạo lớp bọc thừa hay trừu tượng hóa không cần thiết. |
| **III. Comprehensive Automated Testing** | **PASS** | Bổ sung kiểm thử E2E Playwright bao phủ toàn bộ luồng chọn hàng loạt $\to$ xác nhận $\to$ làm mới. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Tab kho mẫu tiếp tục duy trì cơ chế gọi worker và storage tách bạch. |
| **Quality Gates & Verification** | **PASS** | Đảm bảo lint sạch và CI xanh 100%. |

## Project Structure

### Documentation (this feature)

```text
specs/029-fix-batch-delete-refresh/
├── plan.md              # Kế hoạch triển khai (file này)
├── research.md          # Nghiên cứu nguyên nhân gốc rễ và quyết định kỹ thuật
├── data-model.md        # Mô hình trạng thái chọn hàng loạt và thông điệp worker
├── quickstart.md        # Hướng dẫn kiểm chứng tự động và thủ công
└── contracts/
    └── batch-delete-ui-contract.md  # Hợp đồng tuần tự UI và định danh hàm
```

### Source Code (repository root)

```text
webapp/
├── js/
│   └── bank.js          # Sửa refreshBankTab -> refreshBankView
└── dist/
    └── js/
        └── bank.js      # Bản build phân phối được cập nhật

scripts/
└── build_web.py         # Script đóng gói và cập nhật bản build web

tests/
└── e2e/
    └── bank.spec.ts     # Kịch bản kiểm thử E2E xác thực xóa hàng loạt
```

**Structure Decision**: Sửa đổi trực tiếp tại tầng điều khiển giao diện `webapp/js/bank.js`, tái xây dựng bản phân phối qua `scripts/build_web.py` và cập nhật kiểm thử Playwright tại `tests/e2e/bank.spec.ts`.

## Complexity Tracking

> Không có vi phạm Constitution nào cần giải trình.
