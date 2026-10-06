# Implementation Plan: 025 — Sửa lỗi CI Kiểm Thử Tự Động (Playwright E2E & GUI Tkinter)

**Branch**: `025-fix-ci-tests` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/025-fix-ci-tests/spec.md`

## Summary

Triển khai các bản vá hoàn thiện cho CI (`local data/fix-sw-update.patch` và `local data/fix_test_gui.patch`) nhằm khắc phục triệt để:
1. **Lỗi kiểm thử E2E Service Worker (`tests/e2e/sw-update.spec.ts`)**:
   - Loại bỏ phụ thuộc cứng vào lệnh `py -3` (vốn chỉ có trên Windows) bằng hàm dò tìm interpreter Python tương thích trên mọi hệ điều hành (`process.env.PYTHON`, `python3`, `python`, `py -3` trên win32).
   - Nâng cấp máy chủ kiểm thử tĩnh `scripts/serve.mjs` để nhận `PORT` và `DIST_DIR` qua biến môi trường, đồng thời xử lý an toàn giải mã URL và chặn triệt để path traversal.
   - Cô lập hoàn toàn môi trường build và phục vụ của `sw-update.spec.ts` sang thư mục tạm (`tmpDist`) và cổng mạng riêng (`SW_PORT = 8101`), loại bỏ nguy cơ đụng độ tài nguyên tĩnh khi chạy Playwright đa worker (`--workers=2`).
   - Đảm bảo dọn dẹp sạch sẽ tài nguyên (khôi phục `app.js`, hủy tiến trình server con, xoá `tmpDist`) trong khối `finally`.
2. **Lỗi kiểm thử GUI Tkinter (`tests/test_gui.py`)**:
   - Thay thế bài test lỗi thời `test_nap_tu_thong_dung` (kỳ vọng mock `simpledialog.askinteger` đã bị xoá) bằng hai bài test mới `test_nap_bo_ky_tu_co_ban` và `test_huy_bo_ky_tu_khong_them_gi`.
   - Kiểm tra chính xác luồng mở cửa sổ Toplevel "Chọn bộ ký tự", nạp các ký tự còn thiếu vào hàng đợi dạy, và đóng dialog an toàn.

## Technical Context

**Language/Version**: Python 3.10+ (CPython), Node.js 22/24, TypeScript / JavaScript ES modules.

**Primary Dependencies**: Playwright (@playwright/test), Pytest, Tkinter / Tcl.

**Storage**: Local filesystem (`os.tmpdir()` cho build tạm, `webapp/dist` tĩnh).

**Testing**: `npx playwright test --workers=2`, `pytest tests/test_gui.py` (với `xvfb-run` trên Linux).

**Target Platform**: Linux CI (GitHub Actions Ubuntu runner), Windows, macOS.

**Project Type**: Web Client Test Harness & Desktop GUI Test Suite.

**Performance Goals**: Playwright E2E 14 tests vượt qua trong < 2 phút với 2 workers song song; test GUI chạy trong < 5s.

**Constraints**:
- Zero Core Mutation: Không sửa đổi logic nghiệp vụ trong `chuviettay/model` hay `chuviettay/controller`.
- Safe Cleanup: Tuyệt đối không để lại file mã nguồn ô nhiễm (`app.js`) hay server con bị mồ côi (zombie process) sau khi test chạy xong.
- 100% Backward Compatibility: Server `scripts/serve.mjs` giữ nguyên cổng mặc định 8000 và thư mục `webapp/dist` khi không truyền biến môi trường.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Maintainability & Code Cleanliness)**: PASS. Loại bỏ code test thừa đã lỗi thời, phân định rõ ràng các bước dọn dẹp với try/catch/finally.
- **Principle II (Simple Architecture / KISS & YAGNI)**: PASS. Sử dụng biến môi trường chuẩn của Node.js (`process.env.PORT`, `process.env.DIST_DIR`) và các API stdlib sẵn có (`execFileSync`, `spawn`, `fs.mkdtempSync`).
- **Principle III (Comprehensive Automated Testing)**: PASS. Sửa đúng 2 test case đang gây đỏ CI, kiểm thử đa nền tảng và chạy song song an toàn.
- **Principle IV (Loose Coupling & High Cohesion)**: PASS. Độc lập hoá test case `sw-update.spec.ts` khỏi `webapp/dist` dùng chung của các test case khác.

## Project Structure

### Documentation (this feature)

```text
specs/025-fix-ci-tests/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── serve-env.md
├── quickstart.md
└── checklists/
    └── requirements.md
```

### Source Code (affected paths)

```text
scripts/
└── serve.mjs                 # Thêm PORT, DIST_DIR, giải mã URL, chặn path traversal

tests/
├── e2e/
│   └── sw-update.spec.ts     # Đa nền tảng Python, build/serve tạm trên cổng 8101, dọn dẹp an toàn
└── test_gui.py               # Thay test_nap_tu_thong_dung bằng test_nap_bo_ky_tu_co_ban & test_huy
```

**Structure Decision**: Giữ đúng phạm vi 3 file bị ảnh hưởng trực tiếp bởi 2 patch, không thay đổi cấu trúc thư mục repo.

## Complexity Tracking

*Không có vi phạm hiến pháp cần biện minh.*
