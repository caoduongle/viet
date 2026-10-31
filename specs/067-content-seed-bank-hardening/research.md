# Technical Research: Gia cố Bảo toàn Nội dung Tài liệu, Độ ổn định Biến thể Nét chữ và Hiệu năng Kho mẫu

**Feature**: `067-content-seed-bank-hardening`  
**Date**: 2026-10-31  
**Spec Reference**: [spec.md](./spec.md)

---

## 1. Nghiên cứu & Quyết định Kỹ thuật (Technical Decisions)

### Nghiên cứu 1: Cơ chế theo dõi thành phần Markdown không hỗ trợ, tương thích ngược hợp đồng kiểm thử & truyền thông báo về Web UI

#### Bối cảnh & Vấn đề
- Trong `chuviettay/importer/markdown_importer.py`, danh sách `ImportResult.unsupported` hiện đang có hợp đồng kiểm thử nghiêm ngặt trong:
  - `tests/test_markdown_math_import.py` (dòng 82 & 94): kiểm tra `assert res.unsupported == ["code_block"]` và `assert res.unsupported == ["hr: horizontal rule", "code_block: python"]`.
  - `tests/test_markdown_math_block_isolation.py` (dòng 1092 & 1134): kiểm tra `assert len(res.unsupported) == 0` đối với các tài liệu chứa khối công thức trong `blockquote` (`> $$...$$`).
- Ngoài ra, bước tiền xử lý `_isolate_display_math_blocks()` chèn thêm các dòng trống quanh khối `$$` và tách dòng `ta có:$$x$$`, làm dịch chuyển `token.map` của `markdown-it` so với số dòng gốc của người dùng.
- Thành phần `image` (`![alt](url)`) trong `_parse_inlines` hiện rơi vào nhánh `else:` (chỉ lấy `child.content` nếu có, hoặc biến mất hoàn toàn nếu `![](url)` không có alt text) mà không ghi nhận vào `unsupported`.
- Thành phần `blockquote_open` hiện bị bỏ qua thẻ mở/đóng và làm phẳng các khối con thành đoạn văn/khối toán thông thường mà không có cảnh báo trong `warnings`.
- Trong `chuviettay/browser/bridge.py` (`write_text`), chỉ có `res.warnings` được gom lại, còn `res.unsupported` bị bỏ sót, không được đưa vào `res_data`.
- Trên giao diện `webapp/js/write.js`, hàm `updateInfoPanel` chỉ đọc `res.warnings`. Hơn nữa, khi người dùng mở file `.docx`, hàm `handleFileImport` gọi `showWarning(...)` rồi lập tức gọi `triggerPreviewImmediate()`, khiến lượt render tiếp theo ghi đè mất cảnh báo DOCX.

#### Quyết định Thiết kế
1. **Bảo toàn hợp đồng mã định danh trong `MarkdownImporter` (`ImportResult.unsupported` & `ImportResult.warnings`)**:
   - **Giữ nguyên mã chuẩn trong `unsupported`**:
     - `fence` / `code_block`: `"code_block"` hoặc `f"code_block: {info}"` (khi có `info`).
     - `hr`: `"hr: horizontal rule"`.
     - Bảng trong danh sách: `"table: table inside list item"`.
     - **Bổ sung `image`** trong `_parse_inlines`: trích xuất văn bản thay thế (`child.content` hoặc các token con của `image`) thành `Text(alt)` nếu khác rỗng, đồng thời ghi vào `unsupported`: `f"image: {alt}"` (nếu có `alt`) hoặc `"image"`.
   - **Ghi nhận làm phẳng `blockquote` vào `warnings` (không đưa vào `unsupported`)**:
     - Khi gặp `blockquote_open` trong `_parse_blocks`, thêm thông báo duy nhất (deduplicated) vào `warnings`: `"Khối trích dẫn (blockquote) đã được chuyển về đoạn văn viết tay tiêu chuẩn."`. Cách này nhất quán 100% với thông báo giản lược định dạng inline (`strong_open`, `em_open`, `code_inline`) và bảo toàn `len(res.unsupported) == 0` cho các bài kiểm thử blockquote math hiện có.
2. **Cập nhật `BrowserBridge.write_text`**:
   - Khởi tạo `unsupported_list: list[str] = []`.
   - Gom `res.unsupported` từ tất cả các phân đoạn trang (`PAGEBREAK_RE.split`) và trả về trong phản hồi JSON: `"unsupported": unsupported_list`.
3. **Cập nhật `webapp/js/write.js`**:
   - Chuyển đổi các mã trong `res.unsupported` sang thông điệp tiếng Việt thân thiện (nêu rõ loại thành phần và cách xử lý: đã bỏ qua hoặc giữ văn bản thay thế) và hiển thị cùng `res.warnings` trong `#editor-warnings`.
   - Lưu trữ `pendingImportNotices` khi nạp tệp `.docx` để hiển thị kết hợp trong `updateInfoPanel` sau khi lượt render tự động hoàn tất; xóa `pendingImportNotices` khi người dùng mở tệp khác hoặc xóa trắng văn bản (`clearPreview`).

#### Phương án thay thế đã đánh giá
- *Thay đổi trực tiếp chuỗi trong `ImportResult.unsupported` sang câu tiếng Việt kèm `token.map`*: Bị từ chối vì làm gãy hợp đồng `test_unsupported_contract_for_hr_and_code_is_unchanged()` và báo sai số dòng khi `_isolate_display_math_blocks` chèn dòng trống.

---

### Nghiên cứu 2: Khắc phục va chạm ký tự PUA qua mã thực thể HTML (HTML Entities)

#### Bối cảnh & Vấn đề
- Trong `markdown_importer.py` (dòng 108–112), `_choose_fake_close_placeholder(text)` có nhánh kiểm tra nhanh:
  ```python
  first_pua = chr(_FAKE_CLOSE_PUA_START)
  if first_pua not in text:
      return first_pua
  ```
- Nếu người dùng nhập thực thể HTML như `&#xE000;`, `&#XE000;`, `&#x00e000;`, hoặc `&#57344;` (kể cả có số `0` đứng đầu `&#057344;`), ký tự `\ue000` không xuất hiện trực tiếp trong chuỗi `text` ban đầu. Nếu không kiểm tra `"&#" not in text` ở nhánh fast-path, hàm sẽ trả về ngay `\ue000` mà không gọi `_collect_used_pua_codepoints(text)`!
- Sau đó, `markdown-it` giải mã thực thể HTML thành `\ue000`, và `_restore_fake_close_placeholder` thay thế mọi `\ue000` thành `$$`, làm hỏng dữ liệu người dùng.

#### Quyết định Thiết kế
1. **Cập nhật điều kiện fast-path trong `_choose_fake_close_placeholder(text)`**:
   - Chỉ trả về sớm `first_pua` khi `first_pua not in text and "&#" not in text`.
2. **Mở rộng `_collect_used_pua_codepoints(text)` không gây suy giảm hiệu năng**:
   - Duyệt `_PUA_RE.finditer(text)` để thu thập các ký tự PUA trực tiếp.
   - Chỉ khi `"&#" in text` và `len(used_cps) < _FAKE_CLOSE_PUA_COUNT`: quét thêm biểu thức chính quy `_HTML_NUM_ENTITY_RE = re.compile(r"&#(?:[xX]([0-9a-fA-F]{1,6})|([0-9]{1,7}));")`. Nếu giá trị nguyên giải mã nằm trong `[_FAKE_CLOSE_PUA_START, _FAKE_CLOSE_PUA_END]`, thêm vào `used_cps`.
   - Nhờ kiểm tra `"&#" in text` ở tầng C trước khi chạy regex thực thể, các văn bản thông thường và tập dữ liệu benchmark 510.000 ký tự (`benchmark_pua_memory.py`) không chịu bất kỳ chi phí phụ nào.

---

### Nghiên cứu 3: Nhận diện dấu thoát công thức theo quy tắc chẵn/lẻ (Even/Odd Backslash Rule)

#### Bối cảnh & Vấn đề
- Trong `_convert_delimited(seg, opener, closer, ...)` của `markdown_importer.py`, hệ thống đang kiểm tra `j > 0 and seg[j - 1] == "\\"` và `while k > 0 and seg[k - 1] == "\\"`.
- Khi có số chẵn dấu gạch chéo ngược đứng ngay trước delimiter (ví dụ `\\\(x\)` — gồm 2 dấu `\` trước `\(`), 2 dấu `\` đầu tạo thành 1 dấu gạch chéo ngược được thoát (`\\`), nên `\(` phía sau là delimiter hợp lệ. Cách kiểm tra cũ chỉ nhìn 1 ký tự `seg[j - 1]` nên nhận nhầm là bị escape.
- Ngoài ra, khi `strip=True` (áp dụng cho `\(...\)`), nếu nội dung bên trong kết thúc bằng khoảng trắng được thoát `\ ` (ví dụ `\(x\ \)` — số lẻ dấu `\` trước khoảng trắng cuối), lệnh `body.strip()` sẽ cắt mất khoảng trắng cuối và để lại dấu `\` đơn sát trước dấu `$` đóng (`$x\$`), khiến `dollarmath_plugin` hiểu nhầm dấu `$` đóng bị escape!

#### Quyết định Thiết kế
1. **Hàm đếm số lượng dấu `\` liên tiếp ngay trước vị trí `idx`**:
   ```python
   @staticmethod
   def _count_preceding_backslashes(text: str, idx: int) -> int:
       p = idx - 1
       count = 0
       while p >= 0 and text[p] == "\\":
           count += 1
           p -= 1
       return count
   ```
2. **Áp dụng quy tắc chẵn/lẻ cho cả `opener` và `closer` trong `_convert_delimited`**:
   - Với `opener` tại `j`: nếu `_count_preceding_backslashes(seg, j) % 2 == 1` $\rightarrow$ delimiter bị escape, giữ nguyên `seg[i : j + len(opener)]` và tiếp tục từ `j + len(opener)`.
   - Với `closer` tại `k`: lặp `while k != -1 and _count_preceding_backslashes(seg, k) % 2 == 1:` để tìm `closer` đầu tiên có số chẵn dấu `\` đứng trước.
3. **Bảo vệ khoảng trắng thoát ở cuối `body` khi `strip=True`**:
   - Khi `strip=True`, thực hiện `body = body.lstrip()`. Ở phía phải, chỉ cắt khoảng trắng không bị thoát bởi số lẻ dấu `\` (hoặc nếu sau `rstrip()` mà `_count_preceding_backslashes(rstripped, len(rstripped)) % 2 == 1`, thì cắt bỏ dấu `\` thoát khoảng trắng dư thừa đó để chuỗi công thức LaTeX hợp lệ với `dollarmath_plugin(allow_space=False)`).

---

### Nghiên cứu 4: Tăng độ ổn định Seed khi tài liệu có nhiều từ lặp mà không gây suy giảm bậc hai $O(N^2)$

#### Bối cảnh & Vấn đề
- Trong `chuviettay/document/ir.py`, `align_document_seeds` dùng `difflib.SequenceMatcher(None, base_keys, edited_keys)` (mặc định `autojunk=True`). Với chuỗi $\ge 200$ phần tử, các từ xuất hiện $> 1\%$ (như "là", "và", "của") bị đánh dấu là popular junk và bị bỏ qua khi ghép khối LCS, làm toàn bộ các từ đó ở nửa sau tài liệu bị cấp `occurrence` mới.
- Tuy nhiên, kết quả đo thực nghiệm (`review_probe.py`) cho thấy nếu chỉ bật `autojunk=False` trên toàn bộ mảng mà không cắt gọt:
  - Với 1.000 từ `"là"` giống hệt nhau: mất ~389ms (vượt ngưỡng 200ms của `SC-007`).
  - Với 5.000 từ bài giảng thực tế: mất ~198ms; với 20.000 từ: mất ~4.147ms!
- Ngược lại, khi kết hợp **cắt bỏ tiền tố chung (common prefix) và hậu tố chung (common suffix) trong thời gian $O(N)$** trước khi gọi `SequenceMatcher(..., autojunk=False)` trên đoạn giữa đã thay đổi:
  - Với 1.000 từ `"là"` chèn đoạn mới ở giữa: thời gian giảm từ **389.5ms xuống < 1ms**!
  - Với 5.000 từ thực tế: giảm từ **197.7ms xuống 2.4ms**!
  - Với 20.000 từ thực tế: giảm từ **4.147ms xuống 13.7ms**!

#### Quyết định Thiết kế
1. **Cắt bỏ tiền tố và hậu tố chung trong $O(N)$**:
   - Tìm độ dài tiền tố chung `prefix_len` từ đầu hai dãy `base_keys` và `edited_keys`.
   - Tìm độ dài hậu tố chung `suffix_len` từ cuối hai dãy (không chồng lấn với `prefix_len`).
   - Ánh xạ trực tiếp `assigned_occs` cho toàn bộ phần tử thuộc `prefix_len` và `suffix_len` từ `base_elems`.
2. **Đối chiếu chính xác đoạn giữa bằng `SequenceMatcher(..., autojunk=False)`**:
   - Trên đoạn giữa `base_mid = base_keys[prefix_len : len(base_keys) - suffix_len]` và `edited_mid = edited_keys[prefix_len : len(edited_keys) - suffix_len]`, chạy `difflib.SequenceMatcher(None, base_mid, edited_mid, autojunk=(len(base_mid) + len(edited_mid) > 8000))` (vô hiệu hóa hoàn toàn `autojunk` cho mọi vùng chỉnh sửa $\le 8.000$ token, vừa đảm bảo độ chính xác tuyệt đối cho 300–4.000 từ lặp vừa bảo vệ Web Worker trước dữ liệu đối kháng cực lớn).

---

### Nghiên cứu 5: Kiểm tra đầy đủ tham số điều khiển chất lượng chữ viết trong WriteOptions

#### Bối cảnh & Vấn đề
- `WriteOptions.validate()` hiện chưa kiểm tra `letter_gap`, `target_xh`, `pen_clearance_factor` và chưa kiểm tra kiểu cho các cờ Boolean.
- Trong Python, `isinstance(True, int)` là `True` và `math.isfinite(True)` là `True` (`float(True) == 1.0`). Do đó nếu chỉ dùng `math.isfinite(val)` mà không kiểm tra `isinstance(val, (int, float)) and not isinstance(val, bool)`, giá trị `True`/`False` sẽ lọt qua tất cả các trường số học!

#### Quyết định Thiết kế
1. **Hàm kiểm tra số thực/số nguyên an toàn trong `WriteOptions.validate()`**:
   - Mọi trường số học (`scale`, `line`, `width`, `space`, `jitter`, `wscale`, `paper_width`, `paper_height`, `margin_left`, `margin_right`, `margin_top`, `margin_bottom`, `background_spacing`, `background_margin`, `letter_gap`, `target_xh`, `pen_clearance_factor`) PHẢI kiểm tra `isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val)`.
   - Miền giá trị cho 3 tham số chất lượng chữ:
     - `letter_gap`: $0.0 \le \text{letter\_gap} \le 10.0$
     - `target_xh`: $0.0 < \text{target\_xh} \le 100.0$
     - `pen_clearance_factor`: $0.0 \le \text{pen\_clearance\_factor} \le 10.0$
2. **Kiểm tra nghiêm ngặt các cờ Boolean**:
   - `auto_xh`, `stable_variants`, `assemble_letters`, `snap_to_ruling`, `strict_case`, `missing_grid`: phải thỏa mãn `isinstance(val, bool)`, nếu sai ném `ValueError` nêu rõ tên trường.

---

### Nghiên cứu 6: Tối ưu hóa Tab Kho mẫu qua API Snapshot một lượt & Đồng bộ Worker Recovery

#### Bối cảnh & Vấn đề
- `webapp/js/bank.js` (`refreshBankView`) hiện gọi tuần tự 4 API tới Pyodide Web Worker (`get_stats`, `list_letters`, `list_category_items("symbols")`, `list_category_items("marks")`) và bỏ qua lỗi bằng `catch (_) {}`.
- Trong kiến trúc Web Worker của dự án, `webapp/js/worker/py-worker.js` phân luồng tường minh từng `method` qua chuỗi `if (method === "...")`. Do đó mọi phương thức mới trên `BrowserBridge` bắt buộc phải được đăng ký nhánh điều phối trong `py-worker.js`.
- Ngoài ra, khi Worker bị khởi động lại qua `recoverWorker()` (trong `webapp/js/app.js`) hoặc khi người dùng chuyển đổi hồ sơ kho mẫu (profile), bộ đếm `bank_revision` trong Worker mới sẽ khởi tạo lại từ đầu. Nếu `bank.js` chỉ so sánh `snapshot.revision === lastLoadedRevision` mà không gắn kèm định danh hồ sơ hoặc cờ ép làm mới, giao diện có thể bỏ qua việc cập nhật khi trùng số `revision` sau khi đổi kho!

#### Quyết định Thiết kế
1. **Thêm `get_bank_snapshot()` vào `BrowserBridge` (`chuviettay/browser/bridge.py`) và đăng ký trong `webapp/js/worker/py-worker.js`**:
   - `BrowserBridge` duy trì thuộc tính `self.bank_revision: int = 1`, tự động tăng `self.bank_revision += 1` khi thực hiện thành công `init`, `load_bank`, `teach_sample`, `teach_char`, `import_grid`, `drop_label`, `drop_chars`, `drop_label_samples`.
   - `get_bank_snapshot()` trả về `{ "ok": True, "data": { "revision": self.bank_revision, "stats": ..., "letters": ..., "digits": ..., "punct": ..., "symbols": ..., "marks": ... } }`.
2. **Cập nhật `webapp/js/bank.js`**:
   - `refreshBankView(options = {})` gọi 1 lần `sendWorkerFn("get_bank_snapshot")`.
   - Kết hợp khóa bộ nhớ đệm `(snapshot.revision, activeProfileId)` (và hỗ trợ `options.force = true` khi xóa/thêm mẫu hoặc đổi hồ sơ) để quyết định bỏ qua dựng lại lưới thẻ DOM khi dữ liệu thực sự chưa thay đổi.
   - Hiển thị thông báo lỗi rõ ràng trên giao diện khi `get_bank_snapshot` trả về lỗi hoặc ngoại lệ, loại bỏ hoàn toàn các khối `catch (_) {}` nuốt lỗi.

---

### Nghiên cứu 7: Phân tách Kiểm thử Hồi quy Hiệu năng (Deterministic CI Tests vs Benchmark Suite)

#### Bối cảnh & Vấn đề
- Trong `.github/workflows/ci.yml`, lệnh chạy pytest là `python -m pytest -vv -s --timeout=60 -m "not benchmark"`.
- Nếu đánh dấu `@pytest.mark.benchmark` cho toàn bộ `tests/test_performance_regression.py`, các bài kiểm thử này sẽ bị bỏ qua trên CI; ngược lại, nếu không đánh dấu và đặt ngưỡng thời gian cứng quá hẹp (như `< 15ms` hay `< 50ms`), CI trên các máy ảo dùng chung sẽ bị lỗi chập chờn (flaky).

#### Quyết định Thiết kế
- Thiết kế `tests/test_performance_regression.py` gồm 2 nhóm:
  1. **Nhóm kiểm thử bất biến hiệu năng & cấu trúc (chạy mặc định trong CI, không gắn cờ `benchmark`)**: Kiểm tra tính đúng đắn 100% của `align_document_seeds` trên 300–1.000 từ lặp (kèm ngưỡng an toàn rộng `< 2.0s`), kiểm tra `get_bank_snapshot` giảm số lượt gọi Worker từ 4 xuống 1, và kiểm tra parser Markdown xử lý tài liệu lớn không gặp độ phức tạp bậc hai.
  2. **Nhóm đo kiểm chuyên sâu (`@pytest.mark.benchmark`)**: Đo chi tiết thời gian và bộ nhớ cho Markdown (10 KB, 100 KB, 1 MB), seed alignment và bank snapshot phục vụ kiểm chuẩn hiệu năng định kỳ.
