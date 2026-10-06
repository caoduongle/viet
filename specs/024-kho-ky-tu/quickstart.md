# Quickstart & Verification Guide: Thuần Ký Tự & Nạp Lưới

**Feature**: `specs/024-kho-ky-tu`

---

## 1. Prerequisites
- Python 3.10+ đã cài đặt `pytest`, `pytest-timeout`.
- Node.js & Playwright (đối với E2E web client).

---

## 2. Test Verification Scenarios

### Kịch bản 1: Kiểm thử Unit & Regression (Python)
Kiểm tra toàn bộ logic phân loại ký tự, catalog, bearing và nạp lưới:

```bash
# Chạy bộ test đơn vị cho grid & char bank:
pytest tests/test_char_catalog.py tests/test_grid_import.py -v

# Chạy toàn bộ test suite để đảm bảo không hồi quy:
pytest -v
```
**Kỳ vọng**: 100% test pass, không phát sinh lỗi MVC kiến trúc (`tests/test_architecture.py`).

---

### Kịch bản 2: CLI - Sinh lưới & Nạp lưới vào kho
Kiểm thử chu trình CLI:

```bash
# 1. Sinh file lưới cơ bản
python -m chuviettay.cli grid --set co_ban -o temp_luoi.xopp

# 2. Dùng helper giả lập viết nét mực vào các ô
python -c "
from tests.helpers import fill_grid_with_ink
fill_grid_with_ink('temp_luoi.xopp', 'temp_luoi_ink.xopp')
"

# 3. Nạp lưới vào kho mới
python -m chuviettay.cli learn --grid temp_luoi_ink.xopp -k temp_kho.json.gz

# 4. Kiểm tra xuất văn bản bằng kho vừa tạo (luôn tự ghép từ ký tự)
python -m chuviettay.cli write -t "Xin chào Việt Nam 2026" -k temp_kho.json.gz -o output.xopp
```
**Kỳ vọng**:
- Console in kết quả nạp lưới đầy đủ số liệu.
- File `output.xopp` được tạo thành công, các ký tự không bị giãn 10 lần (F2 đã khắc phục).

---

### Kịch bản 3: Web Client E2E (Playwright)
Kiểm thử trên giao diện Web:

```bash
npm run test:e2e
```
**Kỳ vọng**:
- Test case `grid-import.spec.ts` nạp file `.xopp` thành công, bảng thông báo modal hiển thị thống kê ô thêm/ô trùng.
- Không còn nút "Từ thông dụng" hay các ô dạy từ đơn lẻ.
- Viết văn bản tiếng Việt hiển thị mượt mà trên SVG canvas mà không báo lỗi thiếu từ.
