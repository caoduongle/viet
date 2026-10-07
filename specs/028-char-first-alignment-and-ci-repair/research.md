# Phase 0: Research & Technical Decisions

**Feature**: Đồng Bộ Mô Hình Char-First, Khắc Phục Dấu Thanh & Sửa Lỗi CI Toàn Diện  
**Branch**: `028-char-first-alignment-and-ci-repair`  
**Date**: 2026-10-07  

---

## 1. Research Topic 1: Quy Tắc Kiểm Tra Khả Năng Viết Thống Nhất (Single-Source Render Readiness)

### Vấn đề thực tế
Trong `chuviettay/model/bank.py`, phương thức `Bank.can(w)` còn chứa các dòng kiểm tra kho cũ:
```python
if w in self.digits or w in self.punct or w in self.symbols or w in self.words:
    return True
T = tone_info(w)[0]
if strip_tone(w) in self.tl and (not T or bool(self.marks.get(T))):
    return True
```
Trong khi đó, `Writer.word(core)` và `Writer.assemble_word(core)` theo kiến trúc tính năng 026 đã loại bỏ hoàn toàn việc tìm mẫu từ nguyên khối trong `self.words` và `self.tl`, mà chỉ ghép từ các ký tự đơn lẻ (`letters`, `marks`, `digits`, `punct`, `symbols`).
Hậu quả:
- Nếu một kho mẫu có từ "xin" trong `words` nhưng không có các chữ cái 'x', 'i', 'n' trong `letters`, `Bank.can("xin")` trả về `True`, nhưng `Writer.word("xin")` trả về `None` (thất bại).
- Gây bất nhất trong toàn bộ hệ thống: CLI báo viết được, Controller báo không thiếu từ, nhưng file xuất ra bị trắng hoặc thiếu nét.

### Quyết định kỹ thuật
- **Decision**: Thống nhất quy tắc kiểm tra tính khả thi kết xuất thành một logic duy nhất cho toàn bộ hệ thống.
  1. Với token đơn lẻ (độ dài 1 ký tự hoặc nằm trong danh mục ký hiệu/dấu câu/chữ số): Kiểm tra trực tiếp trong `self.letters`, `self.digits`, `self.punct`, `self.symbols`, hoặc `self.marks`.
  2. Với từ / cụm từ (từ chữ cái ghép lại): Áp dụng chuẩn Dual-Path giống `Writer.assemble_word`:
     - Path 1: Tất cả ký tự nguyên khối (kể cả ký tự có sẵn dấu Unicode NFC như 'à', 'ê') đều có mẫu trong `self.letters` (hoặc dạng chữ thường tương ứng nếu cho phép case-insensitivity).
     - Path 2: Nếu Path 1 thiếu, phân rã từ qua `split_letters(w) -> (chars, T, vi)`. Điều kiện bắt buộc: tất cả các ký tự `chars` đều có mẫu trong `self.letters` VÀ nếu `T` có dấu thanh thì `self.marks[T]` phải có ít nhất 1 mẫu nét.
  3. Loại bỏ hoàn toàn việc kiểm tra `w in self.words` và `strip_tone(w) in self.tl` trong `Bank.can()`.
- **Rationale**: Đảm bảo hợp đồng bất biến: `Bank.can(w) == True` $\iff$ `Writer.word(w) is not None`.
- **Alternatives considered**:
  - Giữ fallback về `self.words` cho Writer: Bị loại bỏ vì mục tiêu chiến lược của dự án là chuyển dịch dứt điểm sang char-first để tối ưu dung lượng kho mẫu và giải phóng người dùng khỏi việc học từng từ đơn lẻ.

---

## 2. Research Topic 2: Tách API Hàng Đợi Web Client & Bảo Toàn Nhãn Dấu Thanh

### Vấn đề thực tế
Trong `webapp/js/teach.js`, hàm `loadQueue(words)` thực hiện:
```javascript
for (const item of words) {
  const normalized = String(item).normalize("NFC");
  for (const ch of normalized) {
    if (!/\s/.test(ch) && !this.queue.includes(ch)) {
      this.queue.push(ch);
    }
  }
}
```
Khi người dùng bấm nạp nhóm "Dấu thanh rời" (`dau_thanh`), backend trả về danh sách token:
`["dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng"]`.
Hàm `loadQueue` lặp qua chuỗi `normalized` và tách từng code point, khiến các nhãn nghiệp vụ bị phân rã thành: `'d'`, `'ấ'`, `'u'`, `'s'`, `'ắ'`, `'c'`,... Người dùng bị bắt dạy các chữ cái thay vì dạy dấu thanh!

### Quyết định kỹ thuật
- **Decision**: Tách biệt rõ ràng 2 kênh nạp vào hàng đợi dạy chữ trên Web Client:
  1. `addCharactersFromText(text)` (hoặc hàm xử lý ô nhập văn bản tự do `addWordFromInput`): Nhận chuỗi văn bản tự do từ người dùng, chuẩn hoá NFC, lọc bỏ khoảng trắng và tách thành các ký tự đơn lẻ (code points) để đưa vào hàng đợi.
  2. `addCatalogLabels(labels)`: Nhận danh sách các nhãn nghiệp vụ từ danh mục (Catalog) hoặc từ backend (`get_missing_chars`). Giữ nguyên vẹn toàn bộ nhãn chuỗi (ví dụ: `"dấu sắc"`, `"dấu huyền"`, `"alpha"`, v.v.), chỉ chuẩn hoá chuỗi NFC và loại trừ trùng lặp với các mục đã có trong hàng đợi.
  3. Cập nhật `loadQueue(items, isCatalog = false)` để có thể tái sử dụng an toàn khi nạp trạng thái hàng đợi ban đầu.
- **Rationale**: Giữ tính phân tách trách nhiệm (Separation of Concerns): văn bản người dùng gõ cần bóc tách ký tự, nhưng nhãn do danh mục hệ thống cung cấp là đơn vị ngữ nghĩa nguyên tử (atomic business tokens).
- **Alternatives considered**:
  - Dùng regex kiểm tra nếu chuỗi bắt đầu bằng "dấu " thì không tách: Bị loại bỏ vì thiếu tính mở rộng nếu sau này thêm các nhãn ký hiệu nhiều ký tự khác. Tách theo API caller là sạch và tường minh nhất.

---

## 3. Research Topic 3: Bảo Toàn Mẫu Dấu Thanh Đa Nét Khi Dạy Trực Tiếp

### Vấn đề thực tế
Trong `chuviettay/controller/app_controller.py`, hàm `teach_char()` xử lý dấu thanh:
```python
if cat == "marks":
    tone_code = xopp.HW3_TONE_MAP.get(label.lower(), label)
    if rel_strokes:
        instance = bank.add_tone_sample(tone_code, rel_strokes[0])
    else:
        instance = {}
```
Chỉ lấy `rel_strokes[0]`, làm mất toàn bộ nét thứ 2 trở đi nếu người dùng vẽ dấu thanh bằng 2 nét (ví dụ: dấu hỏi viết bằng nét móc + nét gập, hoặc dấu ngã gồm 2 đoạn). Trong khi đó, `Bank.add_tone_sample` đã có sẵn chữ ký:
`def add_tone_sample(self, tone: str, strokes: list[Stroke] | Stroke, ...) -> dict:`

### Quyết định kỹ thuật
- **Decision**:
  - Truyền toàn bộ `rel_strokes` (danh sách tất cả các nét) vào `bank.add_tone_sample(tone_code, rel_strokes)`.
  - Trong `Bank.add_tone_sample`, chuẩn hoá cấu trúc lưu trữ: nếu đầu vào là `list[Stroke]`, tính bounding box và trọng tâm cho toàn bộ tập nét, đưa tất cả các nét về toạ độ tương đối chuẩn quanh gốc (0, 0).
  - Bổ sung unit test kiểm tra dạy dấu thanh với 2 và 3 nét bút rời, đảm bảo sau khi lưu vào đĩa và nạp lại, cấu trúc đa nét vẫn còn nguyên 100%.
- **Rationale**: Tôn trọng chữ viết tay tự nhiên của người dùng; dấu hỏi và dấu ngã thường xuyên được vẽ bằng nhiều nét bút ngắt quãng tuỳ theo thói quen cá nhân.
- **Alternatives considered**:
  - Ép nối các nét thành một nét duy nhất: Bị loại bỏ vì tạo ra nét nối phụ (extranous connective stroke) làm xấu nét chữ khi kết xuất.

---

## 4. Research Topic 4: Xuất File Kiểm Tra Kho Mẫu (.xopp) Đầy Đủ Marks

### Vấn đề thực tế
Trong `AppController.export_check()`, tập hợp khóa để sinh file kiểm tra:
```python
keys_set = set()
keys_set.update(getattr(bank, "letters", {}).keys())
keys_set.update(bank.digits.keys())
keys_set.update(bank.punct.keys())
keys_set.update(getattr(bank, "symbols", {}).keys())
```
Hoàn toàn bỏ sót `bank.marks`. Ngoài ra, các khóa của dấu thanh trong `bank.marks` là mã combining accent Unicode (`̀`, `́`, `̉`, `̃`, `̣`), không thích hợp làm nhãn hiển thị trong lưới ô kiểm tra.

### Quyết định kỹ thuật
- **Decision**:
  - Bổ sung bảng ánh xạ nhãn hiển thị cho 5 dấu thanh:
    ```python
    TONE_DISPLAY_LABELS = {
        "\u0300": "dấu huyền",
        "\u0301": "dấu sắc",
        "\u0309": "dấu hỏi",
        "\u0303": "dấu ngã",
        "\u0323": "dấu nặng",
    }
    ```
  - Trong `export_check()`, duyệt qua `bank.marks`. Với mỗi mã dấu thanh có ít nhất 1 mẫu nét:
    - Thêm nhãn hiển thị trực quan (ví dụ `"dấu sắc"`) vào danh sách `keys`.
    - Lấy mẫu nét đầu tiên trong `bank.marks[tone]` gán vào từ điển `samples[nhãn]`.
  - File lưới `.xopp` kết quả sẽ chứa đầy đủ 5 phân loại: chữ cái, chữ số, dấu câu, ký hiệu, và dấu thanh.
- **Rationale**: Đáp ứng đầy đủ tiêu chí nghiệm thu FR-006 và SC-005, cho phép người dùng kiểm tra trực quan toàn bộ kho mẫu trên Xournal++ trước khi sử dụng.
- **Alternatives considered**:
  - Hiển thị trực tiếp ký tự combining Unicode: Bị loại bỏ vì combining character không có thân chữ sẽ bị hiển thị lỗi hoặc đè lên viền ô lưới trong Xournal++.

---

## 5. Research Topic 5: Cải Thiện Kiểm Chứng Hình Học Chống Dính Nét (Stroke Clearance)

### Vấn đề thực tế
Hàm `min_stroke_clearance(strokes_a, strokes_b)` trong `chuviettay/model/text_utils.py` hiện tính khoảng cách giữa các điểm nút (vertices) của nét:
```python
for xa, ya in subset_a:
    for xb, yb in subset_b:
        d_sq = (xb - xa)**2 + (yb - ya)**2
```
Điểm yếu hình học:
1. Hai đoạn thẳng có thể giao nhau hoặc tiến rất sát nhau tại điểm giữa giữa 2 đỉnh mà khoảng cách đỉnh-đỉnh không phát hiện ra.
2. Trong `Writer.assemble_word()`, bước kiểm tra khe hở chỉ so sánh ký tự mới với ký tự vừa đặt ngay trước đó (`prev_placed_strokes`), chưa kiểm tra toàn diện với các nét vươn dài (ascender / descender) của các ký tự trước đó trong từ.

### Quyết định kỹ thuật
- **Decision**:
  1. Xây dựng thuật toán tính khoảng cách nhỏ nhất giữa hai đoạn thẳng 2D $S_1 = [P_1, P_2]$ và $S_2 = [Q_1, Q_2]$:
     - Đoạn thẳng $S_1(s) = P_1 + s \cdot (P_2 - P_1), s \in [0, 1]$.
     - Đoạn thẳng $S_2(t) = Q_1 + t \cdot (Q_2 - Q_1), t \in [0, 1]$.
     - Tìm khoảng cách cực tiểu giữa 2 đoạn trong không gian 2D với thời gian tính toán tối ưu trong Pure Python (không cần numpy, tránh thêm dependency theo Constitution Principle II).
  2. Bounding Box Pruning:
     - Tính bounding box cho từng đoạn nét hoặc từng nét.
     - Nếu bounding box mở rộng của 2 nét cách nhau lớn hơn ngưỡng an toàn $D_{safe}$, bỏ qua kiểm tra chi tiết.
  3. Trong `Writer.assemble_word()`:
     - So sánh ký tự đang đặt với tập hợp các nét gần nhất của các ký tự đã đặt trong từ (những nét có bounding box $X_{max} \ge cur\_x - 2 \cdot xh$).
     - Nếu khoảng cách đoạn nét nhỏ hơn `clearance_floor = pen_clearance_factor * pen_w`, tịnh tiến ký tự sang phải một lượng đủ để đảm bảo khe hở hình học.
- **Rationale**: Đảm bảo bảo chứng vật lý chống bết mực (no ink bleeding) đúng như tài liệu hướng dẫn cam kết, loại bỏ hoàn toàn các sai số của phép đo điểm rời rạc.
  4. Xử lý đoạn suy biến (Degenerate Segments):
     - Khi một nét vẽ chỉ có 1 điểm hoặc hai điểm trùng nhau ($P_1 = P_2$), độ dài đoạn thẳng bằng 0. Thuật toán `segment_distance` tự động chuyển sang phép đo khoảng cách từ điểm tới đoạn thẳng (point-to-segment distance), và nếu cả hai đoạn đều suy biến thì chuyển sang khoảng cách điểm-điểm (point-to-point distance), loại bỏ nguy cơ `ZeroDivisionError`.
  5. Hiệu chỉnh hướng dịch chuyển dấu thanh trong `Writer.assemble_word`:
     - Với các dấu thanh trên (sắc, huyền, hỏi, ngã), trục tọa độ $y$ hướng lên là âm, do đó khi khoảng cách nhỏ hơn ngưỡng khe hở an toàn, dịch chuyển lên trên bằng `cy -= (clearance_floor - dist_mark)`.
     - Với dấu nặng ($T == NANG$), dấu nằm dưới chân chữ ($y > 0$), do đó dịch chuyển xuống dưới bằng `cy += (clearance_floor - dist_mark)`. Tránh tình trạng dấu nặng bị kéo ngược lên đâm vào thân chữ cái.

---

## 6. Research Topic 6: Đồng Bộ missing_letters_ranked & Cải Biến Bộ Kiểm Thử (CI Repair)

### Vấn đề thực tế
1. Trong `chuviettay/model/text_utils.py`, hàm `missing_letters_ranked()` vẫn còn chứa nhánh kiểm tra `words_bank` (dòng 145-148), dẫn đến khả năng báo một ký tự "không thiếu" nếu nó vô tình trùng tên với một mục trong `words_bank` cũ, gây bất nhất với `Bank.can()`.
2. `chuviettay/formatting.py`: `format_stats_gui` vẫn mở đầu bằng `"%d từ, %d mẫu" % (stats.n_words, stats.n_samples)`.
3. Trong `AppController.export_check()`, các mẫu dấu thanh trong `bank.marks` có tọa độ cục bộ quanh $(0, 0)$. Khi đưa vào lưới `.xopp` chuẩn `hw3` (vốn căn theo đường chân chữ `BASE`), nếu không tịnh tiến theo trục $y$ tương ứng với vị trí dấu thanh (dấu trên: $\approx -1.25 \cdot xh$, dấu nặng: $\approx +0.3 \cdot xh$), nét dấu thanh sẽ bị vẽ lệch đè ngay lên đường kẻ chân chữ.
4. Trên CI Ubuntu (`xvfb-run -a pytest`), các bài kiểm thử trong `tests/test_gui.py` gọi hàm cũ `b.selected_word()` và kiểm tra từ nguyên khối `"ch"`.
5. Trên Playwright (`npx playwright test`), test tìm từ `"xin"` thay vì tìm thẻ ký tự.

### Quyết định kỹ thuật
- **Decision**:
  1. Gỡ bỏ hoàn toàn việc tra cứu `words_bank` trong `missing_letters_ranked()`, đảm bảo tính nhất quán 100% với `Bank.can()`.
  2. Trong `AppController.export_check()`, khi nạp mẫu dấu thanh vào từ điển `samples` cho `xopp.make_grid`, tự động tịnh tiến toạ độ nét theo trục $y$ tương ứng:
     - Dấu trên (huyền, sắc, hỏi, ngã): tịnh tiến $dy = -1.25 \cdot xh$, đặt phía trên chữ mốc $o$.
     - Dấu nặng: tịnh tiến $dy = +0.30 \cdot xh$, đặt phía dưới chữ mốc $o$.
  3. `format_stats_gui`: Đổi dòng tiêu đề chính thành:
     `"%d ký tự có mẫu, %d mẫu nét" % (stats.n_letters + len(stats.digit_counts) + len(stats.punct_counts) + sum(1 for c in stats.tone_mark_counts.values() if c > 0), stats.n_samples)`
     Nếu `stats.n_words > 0`, bổ sung một dòng phụ chú: `"(Kho chứa %d mẫu từ nguyên khối tương thích)" % stats.n_words`.
  4. Hiện đại hoá các bài kiểm thử `test_gui.py`:
     - Cập nhật các assertion của `stats_lbl` và `word_list` để kiểm tra đúng số lượng ký tự và mẫu nét theo chuẩn char-first.
     - Cập nhật `test_tim_kiem_loc_danh_sach` và `test_xoa_tu_dung_tu_duoc_chon_ke_ca_khi_dang_loc` gọi `selected_items()` thay vì `selected_word()`.
  5. Cập nhật các bài kiểm thử Playwright (`bank.spec.ts`, `teach.spec.ts`) tương ứng.
