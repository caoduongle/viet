# Implementation Plan: Đồng Bộ Kho Mẫu Và Kết Xuất Xem Trước Tab Viết Chữ

**Branch**: `052-write-preview-bank-sync` | **Date**: 2026-10-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/052-write-preview-bank-sync/spec.md`

## Summary

Khắc phục lỗi lệch pha bất đồng bộ giữa tiến trình nạp kho mẫu từ IndexedDB vào Web Worker Pyodide và tiến trình kết xuất ban đầu của Tab Viết chữ. Tự động kích hoạt làm mới bản xem trước (`triggerPreviewImmediate`) khi kho mẫu hoàn tất nạp (`load_bank`), khi người dùng chuyển sang Tab Viết chữ (`switchTab("write")`), và khi nhận tín hiệu đồng bộ đa tab (`BANK_SYNCHRONIZED`), bảo đảm bản xem trước luôn hiển thị nét viết tay đầy đủ của các ký tự đã có trong kho mà không cần người dùng thao tác thủ công (gõ phím hay đổi seed).

## Technical Context

**Language/Version**: JavaScript (ES2022+), HTML5, CSS3, Python 3.10+ (Pyodide 314.0.7)

**Primary Dependencies**: Web Worker API, IndexedDB API, BroadcastChannel API, Pyodide WebAssembly runtime

**Storage**: IndexedDB (`chuviettay_profiles`, `chuviettay_settings`) thông qua Web Locks (`navigator.locks`)

**Testing**: Node.js test runner (`node --test "tests/js/*.test.mjs"`), Playwright E2E

**Target Platform**: Các trình duyệt web hiện đại hỗ trợ WebAssembly và Web Worker (Chrome, Firefox, Safari, Edge)

**Project Type**: Static Web App (PWA) Client-Side

**Performance Goals**:
- Độ trễ làm mới bản xem trước sau khi kho nạp xong: $< 150\text{ ms}$
- Tận dụng cơ chế *One Pending Request* sẵn có để chống render dồn dập hoặc duplicate execution

**Constraints**:
- Không thay đổi cấu trúc dữ liệu lưu trong IndexedDB
- Không làm ảnh hưởng đến cơ chế debounce gõ phím 250ms của Tab Viết
- Tương thích 100% với các tính năng quản lý biến thể và phục hồi Worker đã có

**Scale/Scope**:
- 2 tệp frontend cốt lõi: `webapp/js/app.js`, `webapp/js/write.js`
- 1 tệp kiểm thử tự động mới: `tests/js/write_preview_sync.test.mjs`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Mã nguồn rõ ràng, tự tài liệu hóa với các hàm xuất khẩu tường minh (`triggerPreviewImmediate`), không dùng cờ ẩn hay biến toàn cục không kiểm soát.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Không tạo thêm tầng trừu tượng hay thư viện ngoài; tận dụng trực tiếp hàm `triggerPreviewImmediate()` sẵn có và móc nối vào đúng các điểm chuyển trạng thái vòng đời.
- [x] **III. Comprehensive Automated Testing**: Bổ sung kiểm thử tự động tại `tests/js/write_preview_sync.test.mjs` mô phỏng đầy đủ chu trình khởi tạo, chuyển tab và nhận tín hiệu BroadcastChannel.
- [x] **IV. Loose Coupling & High Cohesion**: `app.js` giữ vai trò điều phối vòng đời cấp cao; `write.js` giữ tính gắn kết cao về logic soạn thảo và kết xuất bản xem trước.

*Gate Status*: **PASSED**

## Project Structure

### Documentation (this feature)

```text
specs/052-write-preview-bank-sync/
├── spec.md              # Đặc tả yêu cầu tính năng
├── checklists/
│   └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
├── plan.md              # Kế hoạch thực hiện (file này)
├── research.md          # Kết quả nghiên cứu kỹ thuật Phase 0
├── data-model.md        # Mô hình thực thể & máy trạng thái Phase 1
├── contracts/
│   └── preview-sync-contract.md # Hợp đồng giao tiếp giữa app.js và write.js
└── quickstart.md        # Hướng dẫn kiểm thử và xác thực
```

### Source Code (repository root)

```text
webapp/
├── js/
│   ├── app.js           # Bổ sung triggerPreviewImmediate() tại load_bank, switchTab và BANK_SYNCHRONIZED
│   └── write.js         # Xuất khẩu triggerPreviewImmediate và hỗ trợ kiểm tra trạng thái đồng bộ
tests/
└── js/
    └── write_preview_sync.test.mjs # Test suite tự động xác minh tính năng đồng bộ bản xem trước
```

**Structure Decision**: Tính năng thuộc phạm vi frontend Web Client, mã nguồn nằm gọn trong thư mục `webapp/js/` và test tự động nằm trong `tests/js/`.

## Complexity Tracking

> Không có vi phạm Hiến pháp nào cần giải trình.
