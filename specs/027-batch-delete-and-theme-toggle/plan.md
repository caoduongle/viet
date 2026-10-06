# Implementation Plan: Xóa Hàng Loạt Kho Mẫu và Chuyển Đổi Giao Diện Sáng / Tối

**Branch**: `specs/027-batch-delete-and-theme-toggle` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/027-batch-delete-and-theme-toggle/spec.md`

## Summary

Triển khai tính năng xóa hàng loạt ký tự trong tab Kho mẫu và chuyển đổi giao diện Sáng / Tối (Light / Dark Theme) trên cả Web Client và Desktop GUI.
- **Xóa hàng loạt**: Bổ sung `Bank.drop_batch()` / `AppController.drop_chars()` xử lý trong một lock transaction duy nhất, kết hợp giao diện đa chọn (checkbox trên Web, extended listbox trên Desktop) kèm cảnh báo xác nhận chi tiết.
- **Chuyển đổi giao diện**: Thiết lập bộ Design Tokens (CSS variables trên Web và Color Palette trên Desktop ttk), lưu trữ tùy chọn người dùng qua `localStorage` và file cấu hình, đồng thời tự động điều chỉnh màu tương phản cho khung vẽ canvas.

## Technical Context

**Language/Version**: Python 3.10+, JavaScript (ES2022 / Web Components / Vanilla JS)

**Primary Dependencies**: Tkinter / ttk (Desktop GUI), Pyodide (Web Client runtime), pytest (Test framework)

**Storage**: File nén JSON `.json.gz` (kho mẫu), `localStorage` (tùy chọn Web), `user_config.json` (tùy chọn Desktop)

**Testing**: `pytest` (Unit tests cho `Bank`, `Controller`, `Bridge`), Pyodide golden tests

**Target Platform**: Windows, Linux, macOS, Hiện đại Web Browsers (Chrome, Firefox, Safari, Edge)

**Project Type**: Python Desktop Application & Static Client-side Web App

**Performance Goals**: Xóa hàng loạt 50+ ký tự diễn ra dưới 200ms (1 lần I/O đĩa); chuyển đổi theme giao diện dưới 50ms không chớp nháy

**Constraints**: Không dùng thư viện ngoài cho theme; đáp ứng chuẩn tương phản WCAG AA; không làm mất tính toàn vẹn dữ liệu kho mẫu

**Scale/Scope**: Quản lý hàng trăm ký tự trong kho mẫu; 2 chế độ màu (Sáng / Tối)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Maintainability & Code Cleanliness)**: Đạt. Tách biệt rõ ràng giữa logic dữ liệu xóa hàng loạt (Model/Controller) và hiển thị giao diện (View/Web).
- **Principle II (KISS & YAGNI)**: Đạt. Dùng CSS Variables thuần cho Web và bảng màu chuẩn ttk cho Desktop, không引入 framework CSS hoặc thư viện theme cồng kềnh.
- **Principle III (Comprehensive Automated Testing)**: Đạt. Toàn bộ logic xóa hàng loạt và API bridge đều được kiểm thử tự động với pytest.
- **Principle IV (Loose Coupling & High Cohesion)**: Đạt. Module theme và batch delete không phụ thuộc vòng; duy trì đúng ranh giới MVC.

## Project Structure

### Documentation (this feature)

```text
specs/027-batch-delete-and-theme-toggle/
├── spec.md              # Đặc tả tính năng
├── plan.md              # Kế hoạch triển khai (file này)
├── research.md          # Kết quả nghiên cứu kỹ thuật
├── data-model.md        # Cấu trúc dữ liệu & trạng thái
├── quickstart.md        # Hướng dẫn kiểm thử và xác minh
├── checklists/
│   └── requirements.md  # Checklist chất lượng đặc tả
└── contracts/
    ├── controller-batch-delete-contract.md
    ├── web-bridge-contract.md
    └── theme-tokens-contract.md
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   └── bank.py             # drop_batch() thực thi xóa nhiều trong 1 lock & save
├── controller/
│   └── app_controller.py   # drop_chars(), get_theme_preference(), set_theme_preference()
├── browser/
│   └── bridge.py           # drop_chars() API cho web worker
├── view/
│   ├── bank_tab.py         # Multi-select listbox, nút chọn tất cả & xóa đã chọn
│   └── theme.py            # Bảng màu ttk và hàm apply_theme cho Desktop GUI
└── gui.py                  # Nút theme toggle trên thanh công cụ Desktop

webapp/
├── index.html              # Nút toggle theme ☀️/🌙, checkbox trên char-cards, thanh xóa hàng loạt
├── css/
│   └── style.css           # CSS variables cho [data-theme="light"] và [data-theme="dark"]
├── js/
│   ├── bank.js             # Logic chọn nhiều ký tự, xóa hàng loạt qua worker
│   ├── theme.js            # Module quản lý theme, localStorage, canvas adapt
│   └── worker/
│       └── py-worker.js    # Xử lý message 'drop_chars'
```

## Complexity Tracking

*Không có vi phạm nguyên tắc kiến trúc.*
