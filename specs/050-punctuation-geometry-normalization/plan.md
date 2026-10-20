# Implementation Plan: Chuẩn hóa Hình học, Kích thước và Vị trí Quang học cho Dấu câu

**Branch**: `050-punctuation-geometry-normalization` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/050-punctuation-geometry-normalization/spec.md`

## Summary

Triển khai giải pháp toàn diện cho việc chuẩn hóa kích thước, vị trí dọc và khoảng cách quang học cho hệ thống dấu câu tiếng Việt và ký hiệu toán học:
1. **P1 — Chuẩn hóa dấu ngoặc đơn `(`, `)` và bao quanh**: Khắc phục hiện tượng dấu ngoặc lùn (`< 0.8 * xh`), đưa chiều cao lên `1.45 * xh` (vươn từ `-1.25 * xh` tới `+0.20 * xh`, cao hơn chữ số), loại bỏ triệt để hiện tượng `)` chập vào thân chữ số `1` trong các cụm như `(random_state=2026)`, `P(X >= 1)`, `k!(e^\lambda - 1)`, `\log_{10}(\lfloor x \rfloor + 1)`.
2. **P1 — Neo đường cơ sở cho dấu phẩy `,` và dấu chấm `.`**: Khắc phục hiện tượng dấu phẩy/chấm bay lơ lửng giữa dòng chữ (`max_y < 0`) hoặc quá to (`h > 0.5 * xh`), đưa dấu phẩy về chiều cao `0.38 * xh` với đỉnh tại `-0.14 * xh` và đuôi tại `+0.24 * xh`, dấu chấm bám sát đường cơ sở `max_y = 0.0` và sửa lỗi báo thiếu mẫu sai cho chuỗi ba chấm `...`.
3. **P2 — Chuẩn hóa dấu hai chấm `:`, chấm phẩy `;`, chấm than `!`, hỏi `?` và nháy `'`, `"`**: Căn thẳng trục dọc hai chấm trong vùng chữ thường, định vị chấm phẩy, nâng chiều cao `!` và `?` lên `1.18 * xh` chạm đường cơ sở, và đưa dấu nháy lên vùng đỉnh chữ.
4. **P1 — Bảo toàn 100% Golden Master & Đồng bộ Bản đóng gói Web**: Cơ chế dung sai thông minh bảo toàn tuyệt đối 9/9 kết quả Golden Master SHA-256; cập nhật tự động `webapp/dist/pyodide/chuviettay.zip` và service worker.

---

## Technical Context

**Language/Version**: Python 3.10 / 3.14 (Core Layout & Handwriting Synthesis Engine), ES2022 JavaScript (Frontend/Pyodide Worker)  
**Primary Dependencies**: Standard Python libraries (gzip, json, math, re), Pyodide (WASM runtime), pytest, node:test  
**Storage**: JSON gzip (`.json.gz`) trên hệ thống tệp cục bộ, IndexedDB trên trình duyệt  
**Testing**: `pytest tests/`, `node --test "tests/js/*.test.mjs"`, `python scripts/build_web.py`  
**Target Platform**: CLI/Thư viện Python (Windows/macOS/Linux) và Trình duyệt Web tĩnh (Chrome, Edge, Firefox, Safari)  
**Project Type**: Thư viện xử lý đồ họa vector / Engine bố cục văn bản & công thức toán / Ứng dụng Web PWA  
**Performance Goals**: Chuẩn hóa hình học thực hiện O(N) với N là số điểm của dấu câu (< 30 điểm/mẫu), tiêu tốn < 0.05ms mỗi lần nạp mẫu; không làm tăng thời gian kết xuất tài liệu.  
**Constraints**: Bảo toàn 100% mã băm SHA-256 của toàn bộ 9 ca kiểm thử Golden Master (`tests/test_golden_master_real_path.py`). Không phá vỡ tương thích API hiện hữu của `Writer.token()` và `Writer.number()`.  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Nguyên tắc Hiến pháp | Yêu cầu Kỹ thuật | Trạng thái | Đánh giá Tuân thủ |
|----------------------|------------------|------------|-------------------|
| **I. Maintainability & Code Cleanliness** | Mã nguồn chuẩn hóa phải tự tài liệu hóa, có bảng tham số `PUNCT_METRIC_PROFILES` rõ ràng. | **PASS** | Phân loại rõ ràng 8 nhóm hình học ngữ nghĩa, giải thích cặn kẽ các hệ số so với `xh`. |
| **II. Simple Architecture (KISS & YAGNI)** | Ưu tiên giải pháp biến đổi hình học trực tiếp, không bổ sung framework hay dependency mới. | **PASS** | Tận dụng phép biến đổi affine và sàn khoảng cách hiện có, không thêm thư viện ngoài. |
| **III. Comprehensive Automated Testing** | Mọi ca kiểm thử mới phải có unit tests tự động, kiểm tra kích thước, tọa độ, và hồi quy. | **PASS** | Tạo tệp `tests/test_punctuation_geometry.py` với đầy đủ các ca kiểm tra độc lập và kiểm tra Golden Master. |
| **IV. Loose Coupling & High Cohesion** | `_normalize_punct_sample` giữ trách nhiệm đơn nhất về hình học mẫu; `math_layout.py` giữ trách nhiệm về khoảng cách toán. | **PASS** | Giữ nguyên ranh giới phân tách rõ ràng giữa module model (`Writer`) và layout (`MathLayoutEngine`). |
| **V. Golden Master Invariance** | Không được làm sai lệch mã băm SHA-256 của 9 bài kiểm thử Golden Master. | **PASS** | Cơ chế Invariance Guard kiểm tra dung sai mẫu chuẩn của `tiny_bank` để giữ nguyên 100% tọa độ y. |

---

## Project Structure

### Documentation (this feature)

```text
specs/050-punctuation-geometry-normalization/
├── plan.md              # Kế hoạch triển khai kiến trúc chi tiết (Artifact này)
├── research.md          # Nghiên cứu kỹ thuật, phân tích nguyên nhân gốc rễ và quyết định thiết kế
├── data-model.md        # Mô hình phân loại nhóm dấu câu, hồ sơ hình học và quy tắc khoảng hở
├── quickstart.md        # Hướng dẫn kiểm chứng và các kịch bản chạy thử nghiệm
└── contracts/           # Hợp đồng ràng buộc giữa các module
    ├── punctuation-normalization-contract.md
    ├── math-delimiter-clearance-contract.md
    └── web-distribution-sync-contract.md
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── text_utils.py                 # PUNCT_METRIC_PROFILES, classify_punct_category(char)
│   └── writer.py                     # Cập nhật _normalize_punct_sample(inst, char), get_char_advance_width, sửa lỗi token "..."
└── layout/
    └── math_layout.py                # Nâng sàn min_clearance và pad chống dính nét cho chữ số 1 và dấu )

webapp/
└── dist/                             # Được đồng bộ lại qua scripts/build_web.py
    ├── pyodide/
    │   └── chuviettay.zip            # Gói mã nguồn phân phối Python WASM mới nhất
    └── sw.js                         # Service worker cập nhật cache hash

tests/
├── test_punctuation_geometry.py      # Bộ kiểm thử mới cho hình học dấu câu, vị trí baseline, và khoảng cách 1)
├── test_golden_master_real_path.py   # Kiểm thử bảo toàn 9/9 Golden Master SHA-256
├── test_math_layout.py               # Kiểm thử bố cục công thức toán
└── test_build_web.py                 # Kiểm thử tính toàn vẹn bản đóng gói web
```

---

## Complexity Tracking

*Không phát sinh vi phạm hiến pháp; không cần theo dõi độ phức tạp ngoại lệ.*

---

## Phase 0: Research Summary

Đã hoàn thành phân tích trong [research.md](research.md):
- **Phân tích hình học kho mẫu thực tế**: Dấu ngoặc `(` và `)` chỉ cao `0.715 * xh` (`h ≈ 5.68pt`), thấp hơn nhiều so với chữ số `1` (`1.20 * xh ≈ 9.53pt`), dẫn đến việc hai đầu dấu `)` cắm vào thân số `1` tạo thành vòng khép kín `D`. Dấu phẩy `,` và dấu chấm `.` bị vẽ lơ lửng ở giữa dòng.
- **Phân tích lỗi báo thiếu mẫu**: Khối điều kiện `if not core and not lead and trail == tok` ở cuối `Writer.token()` vô tình ghi đè `miss = [tok]` khi `tok == "..."`, dù cả 3 dấu chấm đã được vẽ thành công.
- **Chiến lược Invariance Guard**: Dấu chấm và dấu phẩy trong `tests/conftest.py` (`tiny_bank_dict()`) vốn đã bám đúng đường cơ sở và nằm trong dải kích thước hợp lệ; hệ thống sẽ giữ nguyên 100% tọa độ y của các mẫu này để bảo toàn tuyệt đối 9/9 mã băm Golden Master.

---

## Phase 1: Design & Contracts Summary

Đã đặc tả đầy đủ các tài liệu thiết kế:
- [data-model.md](data-model.md): Mô hình phân loại 8 nhóm dấu câu, bảng tham số mục tiêu và mô hình sàn khoảng cách quang học.
- [contracts/punctuation-normalization-contract.md](contracts/punctuation-normalization-contract.md): Ràng buộc đối với hàm chuẩn hóa `_normalize_punct_sample`.
- [contracts/math-delimiter-clearance-contract.md](contracts/math-delimiter-clearance-contract.md): Ràng buộc đối với khoảng hở quang học giữa chữ số `1` và dấu đóng ngoặc `)` / dấu phẩy `,`.
- [contracts/web-distribution-sync-contract.md](contracts/web-distribution-sync-contract.md): Quy chuẩn đóng gói và kiểm thử bản Web tĩnh.
- [quickstart.md](quickstart.md): Các lệnh kiểm chứng từng kịch bản chấp thuận.

---

## Implementation Architecture & Phases

### Phase 1: Chuẩn hóa Hình học Dấu câu trong Model Writer (P1 / P2)
- Định nghĩa `PUNCT_METRIC_PROFILES` và `classify_punct_category(char)` trong `chuviettay/model/text_utils.py`.
- Mở rộng chữ ký: `_normalize_punct_sample(self, inst: dict, char: str | None = None) -> tuple[list[Stroke], float]`.
- Cập nhật `Writer.get_char_advance_width()`: khi `char in b.punct`, gọi `self._normalize_punct_sample(sample, char)` cho toàn bộ dấu câu (không chỉ riêng `,` và `.`), tránh lệch số đo với `measure_text_width()`.
- Truyền `char` tại toàn bộ các điểm gọi trong `Writer.get_char_advance_width()`, `Writer.number()`, `Writer.token()`.
- Áp dụng `PUNCT_METRIC_PROFILES` với tỷ lệ co giãn bề rộng tự nhiên `scale_x = min(scale_y, (0.50 * xh) / max(raw_w, 1e-3))` và Invariance Guard cho `tiny_bank`:
  - Dấu ngoặc đơn `()`, vuông `[]`, nhọn `{}`: co giãn và dịch dọc đạt `h = 1.45 * xh`, `min_y = -1.25 * xh`, `max_y = +0.20 * xh`.
  - Dấu phẩy `,`: neo đỉnh tại `-0.14 * xh`, đuôi tại `+0.24 * xh` nếu mẫu đang bay lơ lửng hoặc ngoài dải `[0.20 * xh, 0.50 * xh]`.
  - Dấu chấm `.`: thu nhỏ nếu `> 0.22 * xh` và hạ đáy xuống đúng đường cơ sở `max_y = 0.0`.
  - Dấu hai chấm `:`, chấm phẩy `;`, dấu chấm than `!`, chấm hỏi `?`, dấu nháy `'`, `"`: chuẩn hóa theo đúng vùng tầng tương ứng.
  - Xử lý an toàn mẫu suy biến (`raw_h < 1e-3` hoặc `raw_w < 1e-3`), chống chia cho 0.
- Sửa lỗi báo thiếu mẫu chuỗi `...` trong `Writer.token()`: chỉ báo thiếu khi `miss` thực sự còn ký tự chưa vẽ được.

### Phase 2: Chống Dính Nét Toán học cho Chữ số 1 và Dấu Ngoặc (P1)
- Trong `chuviettay/layout/math_layout.py`:
  - Tính toán bù trừ độ giãn nét bút (stroke cap dilation $\approx 1.0 \times \text{pen\_w}$).
  - Trong `_m_MathRow`: nâng sàn `min_clearance` lên $\max(0.18 \times \text{xh} \times \text{eff},\, 1.2 \times \text{pen\_w})$ khi phần tử trước kết thúc bằng chữ số `1` hoặc phần tử sau là dấu đóng ngoặc `)`.
  - Trong `_m_Delimited`: kiểm tra biên mực thực tế `_get_item_ink_bounds_x(body)` và đặt dấu đóng `right` tại $\max(x_{\text{body}} + \text{body.size.width} + \text{pad},\, x_{\text{body}} + \text{body\_max\_x} + \text{min\_clearance})$.
- Trong `chuviettay/model/writer.py`:
  - Trong `token()`, bảo đảm `clearance_gap` giữa `core` (khi kết thúc bằng số 1) và `trail` (khi là dấu `)`) đạt tối thiểu $\max(0.18 \times \text{xh},\, 1.0 \times \text{pen\_w})$.

### Phase 3: Bộ Kiểm thử Tự động & Bảo toàn Golden Master (P1)
- Tạo tệp `tests/test_punctuation_geometry.py` với các ca kiểm thử:
  - Kiểm tra kích thước và vị trí dọc của dấu ngoặc đơn `(`, `)`.
  - Kiểm tra khoảng cách quang học nét mực giữa số `1` và `)` trong `P(X >= 1)`, `k!(e^\lambda - 1)`, `\log_{10}(\lfloor x \rfloor + 1)`.
  - Kiểm tra dấu phẩy `,` và chấm `.` bám sát đường cơ sở, không bay lơ lửng.
  - Kiểm tra dấu ba chấm `...` không bị báo thiếu mẫu.
  - Kiểm tra dấu hai chấm `:`, chấm phẩy `;`, chấm than `!`, chấm hỏi `?`.
- Chạy `pytest tests/test_golden_master_real_path.py` xác nhận 9/9 tests PASS 100%.

### Phase 4: Đóng gói và Đồng bộ Ứng dụng Web (P1)
- Chạy `python scripts/build_web.py` để tạo lại `webapp/dist/pyodide/chuviettay.zip` và cập nhật service worker.
- Chạy `npm run test:unit` và `pytest tests/test_build_web.py` để xác nhận tính toàn vẹn 100%.
