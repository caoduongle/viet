# Implementation Plan: Đồng bộ độ dày nét hiển thị giữa Dạy chữ và Kho mẫu (Bank Stroke Width Consistency)

**Branch**: `022-bank-stroke-width-consistency` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-bank-stroke-width-consistency/spec.md`

## Summary

Khắc phục lỗi trực quan nét vẽ bị phóng đại thành nét siêu đậm bất thường trong tab Kho mẫu (nhất là với các ký tự hẹp hoặc chữ số như "2") bằng cách:
1. Chuẩn hoá thuật toán tính `viewBox` của `createSvgFromStrokes` với khung tham chiếu chiều cao dòng kẻ tối thiểu (`minVbHeight = 24pt`), căn giữa toạ độ mẫu.
2. Thêm thuộc tính `vector-effect="non-scaling-stroke"` vào các phần tử `<polyline>` để cố định độ dày nét hiển thị thực tế trên màn hình (~1.8px) không bị co giãn theo độ nhỏ của `viewBox`.
3. Bổ sung đường dóng chân chữ mờ (baseline) trong modal chi tiết mẫu giúp người dùng định vị chuẩn xác nét chữ.

## Technical Context

**Language/Version**: JavaScript (ESM ES2022) chạy trong Browser / Node.js
**Primary Dependencies**: Không có thêm thư viện mới (thuần Native SVG / DOM)
**Storage**: IndexedDB qua Web Locks (giữ nguyên cấu trúc dữ liệu `Bank` hiện tại)
**Testing**: Node test runner (`node --test tests/js/paper.test.mjs`), Playwright E2E (`tests/e2e/bank.spec.ts`)
**Target Platform**: Hiện đại (Chromium / Firefox / Safari, PWA Offline)
**Project Type**: Static Web Client SPA + Web Worker Pyodide
**Performance Goals**: Sinh thumbnail tức thì (< 5ms cho mỗi mẫu), không gây giật lag lưới thẻ
**Constraints**: 
- Zero Remote CDN
- Không sửa cấu trúc lõi `chuviettay/model/`
- Giữ nguyên 100% hash của 8 ca Golden Master Pyodide

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Hàm `createSvgFromStrokes` được tách bạch rõ ràng, tài liệu hoá JSDoc đầy đủ, tính toán hình học trực quan.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Không thêm thư viện ngoài; tận dụng triệt để tính năng chuẩn của SVG (`viewBox`, `vector-effect`).
- [x] **III. Comprehensive Automated Testing**: Bổ sung kịch bản kiểm tra SVG thumbnail trong unit test và E2E.
- [x] **IV. Loose Coupling & High Cohesion**: Chỉ tác động đến tầng hiển thị frontend (`webapp/js/bank.js`), không gây ảnh hưởng đến thuật toán ghép chữ của `Writer` hay định dạng `.xopp`.

## Project Structure

### Documentation (this feature)

```text
specs/022-bank-stroke-width-consistency/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── svg-thumbnail.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
webapp/
├── js/
│   ├── bank.js          # Sửa hàm createSvgFromStrokes: viewBox chuẩn hoá & non-scaling-stroke
│   └── canvas.js        # Đối chiếu đồng bộ thông số độ dày nét
tests/
├── js/
│   └── paper.test.mjs   # Bổ sung unit test cho createSvgFromStrokes
└── e2e/
    └── bank.spec.ts     # Thêm assert kiểm tra thuộc tính SVG trong modal chi tiết mẫu
```

## Plan Workflow & Milestones

1. **Phase 0: Research & Formulation** (Đã hoàn thành trong `research.md`).
2. **Phase 1: Design & Contract Definition** (Đã hoàn thành trong `data-model.md`, `contracts/`, `quickstart.md`).
3. **Phase 2: Task Breakdown** (Sẽ thực thi qua lệnh `/speckit-tasks`).
