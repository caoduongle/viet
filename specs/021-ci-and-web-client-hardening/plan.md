# Implementation Plan: 021 — Sửa lỗi CI và hoàn thiện Web Client

**Branch**: `021-ci-and-web-client-hardening` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-ci-and-web-client-hardening/spec.md`

## Summary

Dự án chuyển sang mô hình Static Web App thuần client-side chạy Pyodide 314.0.7 trong Web Worker.
Kế hoạch thực hiện chia làm 2 giai đoạn:
1. **Phần A (P1)**: Sửa dứt điểm 2 lỗi CI đang đỏ:
   - Cách ly `tests/test_build_web.py` vào thư mục tạm `tmp_path`, đăng ký marker `web` trong `pytest.ini`, hỗ trợ cờ `--dist` an toàn tuyệt đối trong `scripts/build_web.py`, skip an toàn khi thiếu `node_modules` trừ khi có `REQUIRE_WEB_BUILD=1`.
   - Loại bỏ `pyinstaller` khỏi `requirements-dev.txt`, cập nhật `README.md` và `pyproject.toml`, cấu hình lại `ci.yml` job `web-client` và `test-python-314`.
2. **Phần B (P2)**: Khắc phục các lỗi thực tế phát hiện được:
   - Sinh `CACHE_NAME` và `PRECACHE_URLS` động theo mã băm SHA-256 trong `sw.js` để Service Worker tự động nhận bản mới.
   - Bổ sung `typing_extensions` vào `vendor_lock.json` và nạp trước `python_docx` trong worker để sửa lỗi mở `.docx`.
   - Đưa `tests/js/` và `tests/browser/` vào `package.json` và CI, sửa tính đa nền tảng trong `zip.test.mjs`.
   - Khử hard-code `/lib/python3.14/site-packages` trong worker và scripts.
   - Thêm các regression test Playwright cho cập nhật SW và upload `.docx`.

## Technical Context

**Language/Version**: Python 3.10+ (lõi), Pyodide 314.0.7 / Python 3.14 (WASM), Node.js 22 & 24, JavaScript ES modules.

**Primary Dependencies**: Pyodide 314.0.7, Playwright, pytest, pytest-timeout, ruff.

**Storage**: IndexedDB (trình duyệt), Local filesystem / memory (CPython).

**Testing**: pytest (CPython unit/integration/architecture), Node test runner (`node --test`), Playwright E2E.

**Target Platform**: GitHub Actions (Ubuntu/Linux), Render Static Site, Cross-platform browsers (Chromium/Firefox/WebKit).

**Project Type**: Static Web App (PWA) + Python stdlib core library.

**Performance Goals**: Thời gian chạy CI < 5 phút cho test-core, build dist < 10s, Golden Master 8/8 byte-to-byte match.

**Constraints**:
- Zero Remote CDN: Toàn bộ assets tự host trong dist.
- Zero Core Dependencies: Lõi `chuviettay` thuần stdlib.
- Bảo toàn 1.116 tests CPython gốc và 8/8 Golden Master Pyodide.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Maintainability & Code Cleanliness)**: PASS. Tách bạch rõ cấu hình build, kiểm thử cách ly không làm ô nhiễm thư mục dist thực.
- **Principle II (Simple Architecture / KISS & YAGNI)**: PASS. Sử dụng cơ chế stdlib cho retry tải wheel, argparse đơn giản, không thêm framework phức tạp.
- **Principle III (Comprehensive Automated Testing)**: PASS. Mỗi lỗi đều có regression test tương ứng (A2, B1, B2, B3).
- **Principle IV (Loose Coupling & High Cohesion)**: PASS. Mã build web và worker độc lập với mã lõi thuật toán.

## Project Structure

### Documentation (this feature)

```text
specs/021-ci-and-web-client-hardening/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-and-worker.md
└── checklists/
    └── requirements.md
```

### Source Code (affected paths)

```text
.github/workflows/
└── ci.yml                   # Cập nhật job web-client và test-python-314
scripts/
├── build_web.py             # Hỗ trợ --dist, an toàn filesystem, dynamic hash sw.js, vendor wheels
├── vendor_lock.json         # Bổ sung typing-extensions
├── test_golden_pyodide.mjs  # Khử hard-code site-packages
└── serve.mjs
webapp/
├── js/
│   └── worker/
│       └── py-worker.js     # Khử hard-code site-packages, nạp typing-extensions trước docx
├── sw.js                    # Template Service Worker
├── package.json             # Thêm test:unit, test:browser
├── pytest.ini               # Thêm marker web
├── pyproject.toml           # Bỏ [tool.pytest.ini_options] thừa
├── requirements-dev.txt     # Bỏ pyinstaller
├── README.md                # Cập nhật hướng dẫn requirements-build.txt
tests/
├── test_build_web.py        # Viết lại cách ly vào tmp_path, skip khi thiếu node_modules
├── js/
│   └── zip.test.mjs         # Hỗ trợ đa nền tảng
└── e2e/
    ├── sw-update.spec.ts    # Regression test cho B1
    └── docx-import.spec.ts  # Regression test cho B2
```

**Structure Decision**: Cấu trúc bám sát hiện trạng mã nguồn của repo, không tạo thêm các phân tầng kiến trúc mới.

## Complexity Tracking

Không có vi phạm nguyên tắc Constitution nào. Mọi thay đổi đều tinh gọn và phục vụ trực tiếp cho việc sửa lỗi và ổn định CI.
