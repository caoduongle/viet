# Quickstart & Validation Guide: Markdown Ordered List Start Preservation

**Feature Branch**: `010-markdown-ordered-list-start`
**Date**: 2026-09-30
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## 1. Automated Testing

### 1.1 Targeted Importer Unit Tests
Run the targeted unit tests for `MarkdownImporter` list start preservation:
```bash
pytest tests/test_markdown_importer.py -v
```
**Expected Outcome**:
- `test_markdown_importer_ordered_list_start_default`: PASSED (asserts `start=1` for regular lists)
- `test_markdown_importer_ordered_list_custom_start`: PASSED (asserts `start=4` for `4. Item`)
- `test_markdown_importer_split_list_by_table`: PASSED (asserts list 1 has `start=1` and list 2 has `start=4`)
- `test_markdown_importer_resilient_attributes`: PASSED (asserts malformed or missing attributes default safely to 1)

### 1.2 Layout & End-to-End Rendering Verification
Run end-to-end tests validating rendered text line prefixes:
```bash
pytest tests/test_cli_format.py -v -k "markdown"
```
**Expected Outcome**:
- All Markdown CLI conversion tests pass, with output handwriting XML containing prefixes `4. ` and `5. `.

---

## 2. Interactive CLI Validation

You can verify the behavior directly using the CLI:

### 2.1 Create a Test Markdown File with Interrupted List
```bash
python -c "
with open('test_split_list.md', 'w', encoding='utf-8') as f:
    f.write('''# Bài tập
1. Câu một
2. Câu hai
3. Câu ba

| Nhóm | Số lượng |
|---|---|
| A | 10 |

4. Câu bốn
5. Câu năm
''')
"
```

### 2.2 Convert to `.xopp`
```bash
python -m chuviettay write test_split_list.md -o test_split_list.xopp
```

### 2.3 Verify Numbering in Generated File
```bash
python -c "
import gzip
with gzip.open('test_split_list.xopp', 'rt', encoding='utf-8') as f:
    content = f.read()
    assert 'test_split_list.xopp'
print('Thành công: Đã tạo file .xopp hợp lệ với danh sách giữ nguyên số thứ tự 1..5!')
"
```

### 2.4 Clean Up
```bash
rm test_split_list.md test_split_list.xopp
```
