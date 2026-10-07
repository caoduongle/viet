# Quickstart & Verification Guide: Punctuation Spacing & Digit Spacing

**Feature**: `030-punctuation-spacing-alignment`  
**Date**: 2026-10-07

## 1. Quick Verification via Automated Tests

### Chạy toàn bộ test kiểm thử typography & spacing
```bash
pytest tests/test_writer.py tests/test_digits_and_punct.py tests/test_letter_assembly.py -v
```

### Chạy test kiểm chứng hiện tượng dính nét dấu câu và rời rạc chữ số
```bash
pytest tests/test_punctuation_spacing.py -v
```
*(File test mới sẽ được tạo trong pha implementation để bao phủ 100% các ca: `đổi:`, `(bằng`, `0,12`, `184,05`, `181`, `00144`)*.

---

## 2. E2E CLI Verification

### Xuất tài liệu mẫu kiểm tra hình ảnh trực quan
Tạo file test Markdown `sample_test.md`:
```markdown
### BÀI 1: Tự tính Pearson r trên mẫu chim cánh cụt

**1. Tính \bar{x} và \bar{y}:**

* \bar{x} = \frac{39,1 + 39,5 + 40,3 + 36,7 + 39,3}{5} = \frac{194,9}{5} = 38,98\text{ mm}
* \bar{y} = \frac{181 + 186 + 195 + 193 + 190}{5} = \frac{945}{5} = 189\text{ mm}

**2. Bảng tính 5 cột:**
| i | x_i | y_i |
|---|---|---|
| 1 | 0,12 | -8 |
| 2 | 0,52 | -3 |
| 3 | 132 | 6 |
| 4 | -228 | 4 |
```

Chạy lệnh render:
```bash
python -m chuviettay.cli write sample_test.md -o output_test.xopp --bank chu_cua_ban.json.gz
```

**Tiêu chí kiểm chứng**:
1. Trong cụm từ `**1. Tính \bar{x} và \bar{y}:**`, dấu `:` nằm cách chữ `y` một khoảng hở rõ ràng, không chạm nét.
2. Trong các số `39,1`, `38,98`, `181`, `186`, `0,12`, `-228`, các chữ số đi liền nhau mạch lạc, không bị giãn cách toác ra như các chữ số rời.
3. Không có cảnh báo lỗi hoặc sụp đổ luồng xử lý.
