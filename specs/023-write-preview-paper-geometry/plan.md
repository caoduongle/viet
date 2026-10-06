# Implementation Plan: Sửa kích thước xem trước giấy và hình học xem trước tab Viết chữ

**Branch**: `specs/023-write-preview-paper-geometry` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/023-write-preview-paper-geometry/spec.md`

## Summary

Khắc phục lỗi kích thước chữ xem trước quá nhỏ ở tab "Viết chữ" và hoàn thiện bộ điều khiển zoom cho khung xem trước giấy. Phương pháp kỹ thuật bao gồm:
1. Thiết lập kích thước pixel layout thực (`width`/`height` theo $px = pt \times \frac{96}{72} \times zoom$) cho `.paper-frame` và phần tử SVG thay vì dùng `transform: scale(...)`.
2. Thay thế `<select id="select-zoom">` bằng bộ điều khiển trực quan gồm nút `−`, nút `+`, nút `Fit` và nhãn hiển thị phần trăm (50% – 300%). Hỗ trợ tự động tính lại zoom ở chế độ Fit khi kích thước container/viewport thay đổi.
3. Sửa hoán đổi ngược quy ước kiểu giấy nền `lined` và `ruled` theo chuẩn Xournal++ v1.2.6 trong `paper.js`, cập nhật nhãn tiếng Việt trong `index.html` và đặt mặc định sang `lined`.
4. Cập nhật cổng hướng dẫn trong `README.md` về 8000 (khớp với `scripts/serve.mjs`).
5. Thêm test Playwright E2E xác minh kích thước pixel thật và không cuộn ngang ở chế độ Fit.

## Technical Context

**Language/Version**: HTML5, CSS3, JavaScript (ES2022 / Vanilla JS), Python 3.10+ (Pyodide Bridge & Pytest), Playwright (E2E testing).

**Primary Dependencies**: Không thêm thư viện ngoài mới. Tận dụng SVG native, CSS Flexbox/Overflow, Playwright Chromium test runner.

**Storage**: Local state trên giao diện người dùng (không đổi cấu trúc lưu trữ kho mẫu).

**Testing**: Pytest (`pytest -m "not benchmark"`), Playwright (`npm run test:e2e`).

**Target Platform**: Web browsers (Chromium, Firefox, WebKit), hỗ trợ desktop full size (1920×1080) và laptop (1366×768).

**Project Type**: Web frontend (Pyodide client) kết hợp Python core engine.

**Performance Goals**: Render SVG kích thước thật mượt mà, tính toán zoom và chuyển đổi chế độ Fit tức thì (< 16ms, 60fps), không gây giật lag khi gõ văn bản hoặc cuộn trang.

**Constraints**:
- Không thay đổi hằng số trong `chuviettay/config.py`.
- Không phá vỡ kiểm thử kiến trúc `tests/test_architecture.py`.
- Web chỉ gọi core engine qua `chuviettay/browser/bridge.py`.
- Giữ commit nhỏ với thông điệp tiếng Việt.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá tuân thủ | Trạng thái |
| :--- | :--- | :--- |
| **I. Maintainability & Code Cleanliness** | Mã nguồn SVG và DOM được tách bạch rõ ràng giữa tính toán hình học (`paper.js`) và tương tác sự kiện UI (`write.js`). Comment giải thích đầy đủ các công thức quy đổi pt sang px. | **PASS** |
| **II. Simple Architecture (KISS & YAGNI)** | Không sử dụng các framework hay thư viện zoom bên ngoài phức tạp; chỉ sử dụng tính toán kích thước layout pixel bản địa và sự kiện resize của trình duyệt. | **PASS** |
| **III. Comprehensive Automated Testing** | Bổ sung bài kiểm thử tự động Playwright E2E kiểm tra chính xác pixel của phần tử SVG ở các độ phân giải khác nhau và trạng thái cuộn. | **PASS** |
| **IV. Loose Coupling & High Cohesion** | Giữ nguyên ranh giới giao tiếp giữa Web Client và Lõi Python qua `bridge.py`. Không can thiệp vào tầng thuật toán sinh nét viết tay. | **PASS** |

## Project Structure

### Documentation (this feature)

```text
specs/023-write-preview-paper-geometry/
├── plan.md              # Kế hoạch triển khai
├── research.md          # Nghiên cứu kỹ thuật
├── data-model.md        # Mô hình thực thể và trạng thái
├── quickstart.md        # Hướng dẫn chạy thử và nghiệm thu
├── contracts/           # Hợp đồng UI/DOM
│   └── paper-preview-contract.md
└── tasks.md             # Danh sách tác vụ triển khai (Phase 2)
```

### Source Code (repository root)

```text
webapp/
├── css/
│   └── style.css        # Cập nhật .paper-frame, .preview-stage, zoom controls layout
├── js/
│   ├── paper.js         # Sửa render SVG kích thước thật, sửa lined vs ruled
│   └── write.js         # Cập nhật điều khiển zoom (-, +, Fit, %), lắng nghe resize
└── index.html           # Thêm nút zoom controls, cập nhật option background & default lined

tests/
└── e2e/
    └── paper-geometry.spec.ts  # Test Playwright đo đạc kích thước thực tế

README.md                # Cập nhật cổng 8000
```

**Structure Decision**: Sửa đổi trực tiếp các file web frontend tương ứng trong `webapp/`, viết test E2E mới trong `tests/e2e/`, giữ nguyên kiến trúc Python lõi.

## Complexity Tracking

*Không có vi phạm Constitution cần giải trình.*
