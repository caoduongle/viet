# Implementation Plan: Gia cố Bảo toàn Nội dung Tài liệu, Độ ổn định Biến thể Nét chữ và Hiệu năng Kho mẫu

**Branch**: `067-content-seed-bank-hardening` | **Date**: 2026-10-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/067-content-seed-bank-hardening/spec.md`

---

## Summary

Triển khai kế hoạch gia cố toàn diện theo lộ trình 3 giai đoạn từ báo cáo rà soát commit `3b20612` (đã hiệu chỉnh qua bước Engineering Review):
1. **Giai đoạn 1 — Tính đúng đắn và bảo toàn nội dung (P1)**:
   - Bảo toàn các mã chuẩn trong `ImportResult.unsupported` (`"code_block"`, `"hr: horizontal rule"`, `"table: table inside list item"`), bổ sung ghi nhận `"image"` / `"image: {alt}"` vào `unsupported` (đồng thời giữ văn bản thay thế) và ghi nhận thông báo làm phẳng `blockquote` vào `ImportResult.warnings` trong `chuviettay/importer/markdown_importer.py`.
   - Chuyển tiếp danh sách `unsupported` từ `MarkdownImporter` qua `BrowserBridge.write_text` sang Web UI.
   - Hiển thị cả `warnings` và `unsupported` (chuyển đổi sang thông báo tiếng Việt rõ nghĩa) trên giao diện `webapp/js/write.js`, đồng thời bảo toàn thông báo nạp tệp DOCX (chế độ Content-First) qua lượt preview render tự động ngay sau khi mở tệp.
   - Chặn nhánh fast-path khi văn bản chứa `"&#"` và mở rộng `_collect_used_pua_codepoints` quét thực thể HTML số (`&#x...;`, `&#...;`, kể cả có số `0` đứng đầu) để ngăn chặn triệt để va chạm ký tự PUA sau giải mã.
   - Sửa nhận diện dấu thoát công thức trong `_convert_delimited` bằng thuật toán đếm số dấu gạch chéo ngược (`\`) liên tiếp chẵn/lẻ cho cả dấu mở và dấu đóng, đồng thời xử lý an toàn khoảng trắng thoát `\ ` ở cuối công thức nội dòng.
2. **Giai đoạn 2 — Chất lượng chữ và tính ổn định (P2)**:
   - Kết hợp cắt bỏ tiền tố/hậu tố chung trong thời gian $O(N)$ với `SequenceMatcher(..., autojunk=False)` trên đoạn chỉnh sửa trung gian trong `align_document_seeds` (`chuviettay/document/ir.py`), bảo toàn 100% biến thể nét chữ cho tài liệu dài có 300–1.000+ từ lặp lại mà không gây suy giảm bậc hai $O(N^2)$.
   - Bổ sung kiểm tra hợp lệ nghiêm ngặt cho `letter_gap` ($[0.0, 10.0]$), `target_xh` ($(0.0, 100.0]$), `pen_clearance_factor` ($[0.0, 10.0]$), từ chối kiểu `bool` ở tất cả các trường số học và kiểm tra `isinstance(..., bool)` cho toàn bộ các cờ logic trong `WriteOptions.validate()`.
3. **Giai đoạn 3 — Trải nghiệm và hiệu năng (P3)**:
   - Bổ sung API `get_bank_snapshot()` trong `BrowserBridge`, đăng ký điều phối trong `webapp/js/worker/py-worker.js`, và cập nhật `webapp/js/bank.js` để tải toàn bộ dữ liệu tab Kho mẫu trong 1 lượt gọi Worker, đối chiếu `(revision, profileId)` để bỏ qua dựng lại DOM thừa và hiển thị lỗi trực quan.
   - Xây dựng bộ kiểm thử hồi quy hiệu năng (`tests/test_performance_regression.py`) tách biệt giữa kiểm thử bất biến xác định chạy trên CI và các phép đo `@pytest.mark.benchmark` theo yêu cầu.

---

## Technical Context

**Language/Version**: Python 3.10+ (tương thích CPython 3.10, 3.12, 3.13, 3.14 và Pyodide WebAssembly) cùng JavaScript chuẩn (ES2022).

**Primary Dependencies**:
- Core Python: `markdown-it-py`, `mdit_py_plugins`, thư viện chuẩn (`math`, `re`, `difflib`, `dataclasses`, `time`, `tracemalloc`).
- Web Client: Vanilla JavaScript, Web Worker (`py-worker.js`), Pyodide.

**Storage**:
- Bộ nhớ RAM & MEMFS trong tiến trình Python/Pyodide.
- IndexedDB (`chuviettay_db`) lưu trữ kho mẫu trên trình duyệt.

**Testing**: `pytest` với `pytest-timeout`, kiểm thử đơn vị Web JS và kiểm thử tự động trên GitHub Actions CI.

**Target Platform**: Môi trường Web Client (chạy offline trên trình duyệt qua Pyodide) và CLI/Library trên Windows, macOS, Linux.

**Project Type**: Hệ thống thư viện cốt lõi (`chuviettay`), cầu nối Web Worker (`BrowserBridge` + `py-worker.js`), ứng dụng web (`webapp`) và bộ kiểm thử (`tests`).

**Performance Goals**:
- Đối chiếu hạt giống tài liệu 1.000 từ lặp lại khi chỉnh sửa cục bộ: $< 20\text{ms}$ nhờ cắt tiền tố/hậu tố $O(N)$, và $< 200\text{ms}$ trong trường hợp xấu nhất.
- Phân tích cú pháp Markdown 100 KB: tuyến tính $O(n)$.
- Làm mới tab Kho mẫu: giảm từ 4 lượt gọi Worker tuần tự xuống 1 lượt gọi `get_bank_snapshot` duy nhất.

**Constraints**:
- Bảo toàn 100% tính tương thích ngược của `ImportResult.unsupported` và toàn bộ hơn 1.330 bài kiểm thử hiện hành.
- Không thêm bất kỳ thư viện bên ngoài mới nào.
- Không gây flaky test do ngưỡng thời gian cứng trên GitHub Actions CI.

**Scale/Scope**: Bao phủ 4 tệp Python cốt lõi (`markdown_importer.py`, `bridge.py`, `ir.py`, `composer.py`), 3 tệp JavaScript (`write.js`, `bank.js`, `worker/py-worker.js`), và các tệp kiểm thử liên quan.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp (Constitution Principle) | Đánh giá Tuân thủ | Ghi chú & Biện minh |
| :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | **PASS** | Phân tách rõ mã chuẩn `unsupported` ở tầng Importer và chuỗi hiển thị tiếng Việt ở tầng UI; loại bỏ hoàn toàn các khối `catch (_) {}` nuốt lỗi. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Cắt tiền tố/hậu tố $O(N)$ kết hợp `SequenceMatcher(..., autojunk=False)` giải quyết triệt để bài toán từ lặp mà không cần thêm thuật toán diff phức tạp. |
| **III. Comprehensive Automated Testing** | **PASS** | Phân tách kiểm thử bất biến chạy trên CI và kiểm thử `@pytest.mark.benchmark`, đảm bảo CI không bao giờ bị flaky. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Giữ vững ranh giới kiến trúc: `BrowserBridge` + `py-worker.js` làm cầu nối duy nhất; Document IR độc lập với giao diện. |
| **CI & Quality Verification Workflow** | **PASS** | Tương thích hoàn toàn với cờ `-m "not benchmark"` trong `.github/workflows/ci.yml`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/067-content-seed-bank-hardening/
├── plan.md              # Kế hoạch triển khai kiến trúc chi tiết (Artifact này)
├── research.md          # Kết quả nghiên cứu kỹ thuật và quyết định giải pháp
├── data-model.md        # Mô hình thực thể và quy tắc kiểm tra hợp lệ
├── quickstart.md        # Hướng dẫn kiểm chứng từng bước
├── contracts/
│   └── content-seed-bank-contract.md # Hợp đồng API và thông điệp giao diện
└── checklists/
    └── requirements.md  # Thẩm định chất lượng đặc tả (đạt 16/16 tiêu chí)
```

### Source Code (repository root)

```text
chuviettay/
├── importer/
│   └── markdown_importer.py    # Ghi nhận image vào unsupported, blockquote vào warnings, PUA entity fix, delimiter even/odd escape
├── browser/
│   └── bridge.py               # Chuyển tiếp unsupported trong write_text, thêm get_bank_snapshot & bank_revision
├── document/
│   └── ir.py                   # align_document_seeds: cắt prefix/suffix O(N) + SequenceMatcher(autojunk=False)
└── model/
    └── composer.py             # WriteOptions.validate kiểm tra letter_gap, target_xh, pen_clearance_factor, chặn bool ở số học & kiểm tra cờ bool

webapp/js/
├── worker/
│   └── py-worker.js            # Đăng ký nhánh điều phối method === "get_bank_snapshot"
├── write.js                    # Hiển thị cả warnings + unsupported, giữ thông báo nạp DOCX qua lượt render đầu
└── bank.js                     # Gọi get_bank_snapshot 1 lượt, đối chiếu (revision, profileId), hiển thị lỗi rõ ràng

tests/
├── test_markdown_importer.py   # Kiểm thử PUA HTML entity, escape chẵn/lẻ, image unsupported & blockquote warning
├── test_browser_bridge.py      # Kiểm thử get_bank_snapshot, bank_revision và chuyển tiếp unsupported
├── test_stable_variants.py     # Kiểm thử đối chiếu hạt giống 300 - 1.000 từ lặp lại & kiểm tra tọa độ nét vẽ
├── test_composer.py            # Kiểm thử validate cho letter_gap, target_xh, pen_clearance_factor và kiểu bool
└── test_performance_regression.py # Kiểm thử bất biến hiệu năng (CI) và benchmark chuyên sâu (@pytest.mark.benchmark)
```

---

## Complexity Tracking

> Không có vi phạm nguyên tắc Hiến pháp nào. Toàn bộ 7 điểm rủi ro phát hiện qua bước Engineering Review đã được giải quyết triệt để ngay trong thiết kế.
