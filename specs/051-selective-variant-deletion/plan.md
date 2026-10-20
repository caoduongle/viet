# Implementation Plan: Chọn và Xóa Biến Thể Mẫu Nét Tùy Chọn Trong Kho Mẫu

**Branch**: `051-selective-variant-deletion` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/051-selective-variant-deletion/spec.md`

## Summary

Triển khai giải pháp cho phép người dùng chọn và xóa các biến thể mẫu nét cụ thể của một nhãn trong modal chi tiết nhãn thay vì chỉ có một lựa chọn duy nhất là xóa toàn bộ nhãn:
1. **P1 — Chọn và xóa nhiều biến thể mẫu nét (Batch Variant Deletion)**: Cho phép tích chọn một hoặc nhiều thẻ biến thể trong modal, hiển thị số lượng đã chọn, và nút hành động "Xoá [N] biến thể đã chọn" kèm hộp thoại xác nhận an toàn.
2. **P2 — Xóa nhanh từng biến thể đơn lẻ (Single Variant Quick Delete)**: Cung cấp biểu tượng thùng rác xóa nhanh trên từng thẻ mẫu nét để gỡ bỏ mẫu xấu chỉ với một cú nhấp và xác nhận.
3. **P3 — Tự động dọn dẹp nhãn khi hết biến thể (Empty Label Cleanup)**: Khi tất cả biến thể của nhãn bị xóa, hệ thống tự động gỡ bỏ nhãn khỏi kho mẫu nét, tạo tombstone đồng bộ đa tab, đóng modal và bảo lưu nút "Xoá nhãn này" hiện có.
4. **Toàn vẹn Dữ liệu & Bảo mật**: Thuật toán xóa theo chỉ số giảm dần (Reverse Index Removal) ngăn chặn hiện tượng index shift; tái lập chỉ mục tìm kiếm `tl` và `marks`; tuân thủ nghiêm ngặt hợp đồng thoát chuỗi HTML (`escapeHtml()`) chống lỗ hổng DOM XSS.

---

## Technical Context

**Language/Version**: Python 3.10 / 3.14 (Core Data Model & Controller), ES2022 JavaScript (Frontend Web Client & Pyodide Worker)  
**Primary Dependencies**: Standard Python libraries (gzip, json, copy, time), Pyodide (WASM runtime), pytest, node:test  
**Storage**: JSON gzip (`.json.gz`) trên hệ thống tệp và IndexedDB (`chuviettay_db`) đa tab qua BroadcastChannel  
**Testing**: `pytest tests/test_bank_variant_deletion.py`, `node --test tests/js/bank_safety.test.mjs`, `python scripts/build_web.py`  
**Target Platform**: Ứng dụng Web PWA tĩnh chạy trong trình duyệt (Chrome, Edge, Firefox, Safari) và thư viện/CLI Python cục bộ  
**Project Type**: Ứng dụng web viết chữ tay kết hợp động cơ WASM client-side  
**Performance Goals**: Thao tác xóa biến thể thực hiện trong $O(N)$ với $N \le 20$ mẫu của nhãn, thời gian xử lý $< 10$ms; giao diện cập nhật ngay lập tức $(< 100$ms)  
**Constraints**: Không làm thay đổi cấu trúc schema `.json.gz`; đảm bảo an toàn luồng (`with self._lock:`); tuân thủ 100% hợp đồng DOM XSS  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Nguyên tắc Hiến pháp | Yêu cầu Kỹ thuật | Trạng thái | Đánh giá Tuân thủ |
|----------------------|------------------|------------|-------------------|
| **I. Maintainability & Code Cleanliness** | Hàm nghiệp vụ phải tự tài liệu hóa, có type hint rõ ràng, thuật toán xóa minh bạch. | **PASS** | `Bank.drop_samples` và `AppController.drop_label_samples` có tài liệu rõ ràng, xử lý danh sách chỉ số giảm dần chuẩn xác. |
| **II. Simple Architecture (KISS & YAGNI)** | Tận dụng hạ tầng hiện có, không bổ sung thư viện hay kiến trúc phức tạp không cần thiết. | **PASS** | Mở rộng trực tiếp các phương thức trên `Bank`, `Controller`, `Bridge` và `bank.js`, tái sử dụng kênh đồng bộ IndexedDB. |
| **III. Comprehensive Automated Testing** | Tất cả logic xóa, trường hợp biên (xóa 1 mẫu, xóa nhiều mẫu, xóa hết mẫu, chỉ số âm/vượt biên) phải được kiểm thử tự động. | **PASS** | Thiết kế bộ kiểm thử chuyên biệt `tests/test_bank_variant_deletion.py` và cập nhật kiểm thử an toàn JS `bank_safety.test.mjs`. |
| **IV. Loose Coupling & High Cohesion** | Phân định ranh giới trách nhiệm rõ ràng giữa Model, Controller, Bridge và View. | **PASS** | `Bank` chịu trách nhiệm thay đổi dữ liệu; `AppController` chịu trách nhiệm ghi đĩa; `Bridge` bọc JSON; `bank.js` điều phối DOM. |

---

## Project Structure

### Documentation (this feature)

```text
specs/051-selective-variant-deletion/
├── plan.md              # Kế hoạch triển khai kiến trúc chi tiết (Artifact này)
├── research.md          # Nghiên cứu kỹ thuật, phân tích nguyên nhân và quyết định thiết kế
├── data-model.md        # Mô hình dữ liệu thực thể, ràng buộc bất biến và biểu đồ trạng thái
├── quickstart.md        # Hướng dẫn kiểm chứng và các kịch bản chạy thử nghiệm
└── contracts/           # Hợp đồng giao tiếp giữa các thành phần
    ├── variant-deletion-contract.md
    └── ui-interaction-contract.md
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   └── bank.py                       # Bổ sung Bank.drop_samples(label, indices, category)
├── controller/
│   └── app_controller.py            # Bổ sung AppController.drop_label_samples(label, indices, category)
└── browser/
    └── bridge.py                     # Bổ sung BrowserBridge.drop_label_samples(label, indices, category)

webapp/
├── index.html                        # Bổ sung thanh công cụ batch delete và controls trên thẻ mẫu
├── css/
│   └── style.css                     # Bổ sung kiểu dáng cho .sample-item-card.selected, checkbox, delete-btn
├── js/
│   ├── bank.js                       # Logic quản lý chọn, xóa hàng loạt, xóa nhanh và làm mới modal
│   └── worker/
│       └── py-worker.js              # Khai báo message handler "drop_label_samples"
└── dist/                             # Bản đóng gói web phân phối (cập nhật qua scripts/build_web.py)

tests/
├── test_bank_variant_deletion.py     # Bộ kiểm thử tự động mới cho tính năng xóa biến thể
├── js/
│   └── bank_safety.test.mjs          # Kiểm thử hợp đồng an toàn DOM và giao diện JS
└── test_build_web.py                 # Kiểm thử tính toàn vẹn bản đóng gói web
```

**Structure Decision**: Cấu trúc ứng dụng phân tầng rõ ràng (Python Backend/Core Engine + JS Frontend Web Worker), tuân thủ kiến trúc hiện hữu của dự án ChuVietTay.

---

## Complexity Tracking

*Không phát sinh vi phạm hiến pháp; không cần theo dõi độ phức tạp ngoại lệ.*

---

## Phase 0: Research Summary

Đã hoàn thành phân tích trong [research.md](research.md):
- **Thuật toán xóa an toàn**: Sử dụng cơ chế đảo ngược chỉ số `sorted(set(indices), reverse=True)` để pop phần tử mà không gây trượt chỉ số (index shift).
- **Cơ chế dọn dẹp nhãn rỗng**: Khi số lượng mẫu còn lại bằng 0, nhãn được gỡ hoàn toàn khỏi kho mẫu và ghi nhận tombstone để đảm bảo đồng bộ đa tab.
- **Tái lập chỉ mục**: Gọi `self.rebuild()` khi xóa biến thể của từ (`words`) hoặc dấu thanh (`marks`) để làm sạch `tl` và `marks`.
- **Hợp đồng an toàn DOM**: Kiểm tra và bắt buộc sử dụng `escapeHtml()` khi kết xuất giao diện thẻ và thông báo lỗi.

---

## Phase 1: Design & Contracts Summary

Đã hoàn thành thiết kế chi tiết:
- **[data-model.md](data-model.md)**: Định nghĩa thực thể `SampleVariant`, `CharacterLabel`, cấu trúc payload IPC và biểu đồ chuyển trạng thái của modal chi tiết nhãn.
- **[contracts/variant-deletion-contract.md](contracts/variant-deletion-contract.md)**: Đặc tả hợp đồng API cho `Bank.drop_samples`, `AppController.drop_label_samples`, `BrowserBridge.drop_label_samples`, `py-worker.js`, và đồng bộ `storage.js`.
- **[contracts/ui-interaction-contract.md](contracts/ui-interaction-contract.md)**: Đặc tả hành vi giao diện, tương tác chọn thẻ, thanh công cụ hàng loạt, nút xóa nhanh, và hộp thoại cảnh báo an toàn.
- **[quickstart.md](quickstart.md)**: Hướng dẫn chi tiết cách chạy kiểm thử tự động và các bước nghiệm thu thủ công E2E trên trình duyệt.
