# Báo cáo Đo lường Bản gốc & Hiện trạng Trước khi sửa (Phase 0)

**Tài liệu tham chiếu**: `2026-09-20-Note-17-02.xopp` (13 trang, 9.073 nét viết tay thật của người dùng)  
**Kho mẫu kiểm tra**: `kho_mau_ky_tu.json.gz` (178 ký tự đơn trong `words`)  
**Mẫu nghiệm thu chuẩn**: `tests/data/accept_sample.txt`  
**Công cụ đo đạc**: `tools/measure_ink.py`  
**Công cụ kết xuất hình ảnh**: `tools/render_xopp.py`  
**Ngày thực hiện**: 2026-10-03  

---

## 1. Bảng Số liệu Đo lường Khách quan (Objective Measurements)

| Chỉ số hình học | (A) Ghi chú gốc (`Note-17-02.xopp`) | (B) Kho mẫu thô (`kho_mau_ky_tu`) | (C) Kết quả lỗi trước sửa (`before_fix.xopp`) | (D) Thử nghiệm `--scale 2` (`scale2.xopp`) | **Mục tiêu nghiệm thu (Proposed Targets)** |
|---|---|---|---|---|---|
| **Số nét phân tích** | 9.073 nét | 178 mẫu chữ | 57 nét (chỉ 11/40 từ) | 57 nét (11/40 từ) | Đầy đủ 100% từ trong văn bản |
| **x-height thực tế (trung vị)** | **7,94 pt** | 3,85 – 4,17 pt | **4,43 pt** | 8,10 pt | **7,94 pt ± 10%** (7,15 – 8,73 pt) |
| **Độ dày bút vẽ** | 1,41 pt | 1,41 pt | 1,41 pt | 1,41 pt | Giữ nguyên độ dày người dùng chọn |
| **Tỉ lệ `độ dày bút / x-height`** | **0,178 (17,8%)** | 0,34 – 0,43 (34–43%) | **0,317 (31,7%)** | 0,174 (17,4%) | **0,178 ± 15%** (15,1% – 20,5%) |
| **Khoảng cách trong từ (trung vị)** | **1,42 pt** | N/A (chữ đơn) | 1,01 pt | 2,12 pt | **1,40 – 2,00 pt** (tự nhiên theo chữ) |
| **Khoảng cách giữa các từ (trung vị)**| **13,17 pt** | N/A (chữ đơn) | 64,41 pt (do trống từ) | 59,87 pt (do trống từ)| **12,0 – 15,0 pt** |
| **Tỉ lệ chồng bbox lớn nhất** | N/A (nét viết liền) | N/A | **51,7%** | **74,5%** | **≤ 10,0%** (cho chữ thường) |
| **Khe hở nét nhỏ nhất** | N/A | N/A | **0,03 pt (0,02x bút)** | **0,08 pt (0,06x bút)**| **≥ 0,80x độ dày bút (≥ 1,13 pt)** |
| **Độ lệch chuẩn x-height** | 1,70 pt | 1,30 pt | 0,94 pt | 1,71 pt | Giảm ≥ 50% độ phân tán chữ thường |
| **Từ bị bỏ trống do thiếu mẫu** | 0 từ | N/A | **27 / 40 mục** (67,5%) | **27 / 40 mục** (67,5%) | **0 từ** (báo rõ nếu thiếu ký tự) |

---

## 2. Phân tích Dữ liệu Đo đạc & Kiểm chứng Chẩn đoán

### 2.1. x-Height thực tế của người dùng: 7,94 pt (không phải 8,6 pt)
- Bằng phân tích phân vị trên 9.073 nét chữ thật, trung vị chiều cao nhóm chữ thường của người dùng là **7,94 pt**.
- Nhận định thô 8,6 pt trước đây bị lệch do ảnh hưởng của các nét thân vươn cao (ascender `b, d, h, k, l, t`) và các số viết tay.
- **Đề xuất**: Dùng **$xh_{\text{target}} \approx 7,94\,\text{pt}$** làm mốc chuẩn hoá thay vì 8,6 pt.

### 2.2. Hiện tượng "Cục mực" do lệch tỉ lệ bút / x-height
- Chữ thường trong kho người dùng viết vào lưới quá nhỏ: `e` (3,26 pt), `u` (3,33 pt), `o` (3,39 pt), `a` (3,85 pt), trong khi bút vẽ cố định là 1,41 pt.
- Tỉ lệ bút / x-height lên tới **36,6%** (gấp hơn 2 lần so với bản ghi chú thật là **17,8%**). Mực chiếm hơn một phần ba chiều cao con chữ, khiến chữ bị bết lại thành một cục.
- Khi người dùng dùng lệnh `--scale 2`, x-height tăng lên 8,10 pt và tỉ lệ bút về 17,4% (rất đẹp về độ thanh mảnh), **nhưng các chữ lại dính chặt vào nhau hơn** (chồng bbox tăng từ 51,7% lên 74,5%) do lỗi công thức tiến con trỏ.

### 2.3. Lỗi công thức tiến con trỏ: `advance = max(0.2*xh, w - overlap)`
- Bề rộng `w` trong kho là khoảng cách mép-đến-mép (`max_x - min_x`), không có khoảng đệm biên (lsb/rsb = 0).
- Trừ đi `overlap` (từ 0,3 đến 1,2 pt) đồng nghĩa với việc bắt buộc chữ sau phải đặt lẹm vào hộp chữ trước.
- Với chữ nhỏ và nét bút 1,41 pt, mép nét của chữ sau chạm thẳng vào nét của chữ trước, khe hở điểm gần nhất chỉ còn **0,03 pt** (tương đương 0,02 lần độ dày nét bút, tức tiếp xúc trực tiếp).

---

## 3. Báo cáo Kết quả Điều tra Mục 3.6 (Nguồn gốc Ảnh lỗi & Dấu thanh)

### Hiện tượng:
- Ảnh lỗi đính kèm `anhloi.png` có đầy đủ các chữ có dấu ("Lời giả Phần A", "Bài 1 Chạy một...", "Điều kiện lọc..."), mặc dù chữ bị dính nhau.
- Khi chạy repo hiện tại (commit `c00ec69`) với kho đính kèm `kho_mau_ky_tu.json.gz`, toàn bộ 28 từ có dấu bị bỏ trống và CLI báo: `Dấu thanh có mẫu để ghép: 0 0 0 0 0`.

### Kết quả điều tra thực nghiệm:
1. **Dữ liệu kho `kho_mau_ky_tu.json.gz`**:
   - Kho chứa đúng 178 khoá trong `words`.
   - **Tất cả các nguyên âm có dấu tiếng Việt đều có mẫu sẵn** (dạng precomposed): `à, á, â, ã, è, é, ê, ì, í, ò, ó, ô, õ, ù, ú, ý, ă, đ, ĩ, ũ, ơ, ư, ạ, ả, ấn, ầ, ẩ, ẫ, ậ, ắ, ằ, ẳ, ẵ, ặ, ẹ, ẻ, ẽ, ế, ề, ể, ễ, ệ, ỉ, ị, ọ, ỏ, ố, ồ, ổ, ỗ, ộ, ớ, ờ, ở, ỡ, ợ, ụ, ủ, ứng, ừ, ử, ữ, ự, ỳ, ỵ, ỷ, ỹ`.
   - Trường `marks` trong kho hoàn toàn rỗng `{}` (0 mẫu dấu thanh rời).
2. **Nguyên nhân commit `c00ec69` làm mất dấu**:
   - Commit `c00ec69` đưa vào hàm `split_letters(word)`: hàm này bóc tách dấu thanh ra khỏi nguyên âm (`unaccented = strip_tone(word)`). Từ `"bài"` bị tách thành `['b', 'a']` và dấu huyền `\u0300`.
   - Trong `Writer.assemble_word`, mã nguồn kiểm tra cứng: `if T and not self.b.marks.get(T): return None`.
   - Vì kho không có mẫu trong `marks`, hàm trả về `None` ngay lập tức, từ chối ghép dù trong kho **đang có sẵn mẫu chữ `à`**!
   - Thêm vào đó, hàm `find_tone` dùng ngưỡng cứng theo `xh=7`, khiến 28/120 chữ có dấu trong tờ lưới cũ không tách được dấu thanh rời.
3. **Nguồn gốc ảnh `anhloi.png`**:
   - Ảnh `anhloi.png` được sinh ra từ mã thử nghiệm ghép ký tự trực tiếp theo chuỗi ký tự Unicode (`word_chars = list(unicodedata.normalize('NFC', word))`), tra thẳng vào `bank.words[ch]` mà không qua bước bóc tách dấu thanh rời.
   - Do dùng chung cơ chế tiến con trỏ `w - overlap` trên các ký tự có sẵn dấu này, các chữ cái bị dính bết vào nhau y hệt như các từ không dấu ("pipeline", "penguins").

### Giải pháp kỹ thuật chốt cho Phase 1 & 2:
- **Cơ chế ghép kép (Dual-Path Assembly)**:
  - Khi duyệt từ tiếng Việt, kiểm tra nếu ký tự nguyên âm có dấu (ví dụ `à` trong `bài`, `ờ` trong `Lời`) đã có sẵn mẫu trong `bank.letters` hoặc `bank.words`, **ưu tiên dùng trực tiếp mẫu nguyên vẹn này**. Điều này kích hoạt ngay lập tức 100% các từ có dấu cho kho hiện tại của người dùng.
  - Chỉ khi kho thiếu mẫu nguyên âm có dấu thì mới dùng cơ chế dự phòng: chữ cái cơ sở + dấu thanh rời trong `bank.marks`.
  - Trong công cụ di trú `migrate_letter_bank.py`, bóc tách dấu thanh dựa trên **nhãn ô đã biết** (ví dụ biết chắc ô là `á` thì nét phụ là `sắc`, nét chính là `a`) với ngưỡng tỉ lệ tương đối theo chính con chữ đó, không dùng ngưỡng pixel cứng, giải quyết dứt điểm 28 chữ bị lỗi nhận diện dấu.

---

## 4. Mục tiêu Số Nghiệm thu Đề xuất (Chờ Người dùng Xác nhận)

Dựa trên số đo thực tế từ 13 trang note gốc, đề xuất các mục tiêu số chính thức:

1. **x-Height chuẩn hoá**: $xh_{\text{target}} = 7,94\,\text{pt}$ (dung sai $\pm 10\%$, tức từ $7,15$ đến $8,73\,\text{pt}$).
2. **Độ đậm nét**: Giữ nguyên tỉ lệ độ dày bút / x-height trong khoảng $0,15 – 0,20$ (chuẩn ghi chú là $0,178$).
3. **Sàn khe hở tối thiểu**: Giữa 2 chữ cái liền kề bất kỳ, khoảng cách Euclidean nhỏ nhất giữa 2 nét $\ge 0,8 \times \text{độ dày bút}$ ($\ge 1,13\,\text{pt}$ với bút 1,41).
4. **Giới hạn chồng Bbox**: Không cặp chữ cái thường liền kề nào chồng bbox quá **10%** bề rộng chữ nhỏ hơn.
5. **Độ phủ mẫu nghiệm thu**: 100% các từ trong `tests/data/accept_sample.txt` được hiển thị nét viết tay đầy đủ (không còn 27 mục bỏ trống như trước sửa).
