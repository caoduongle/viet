# Quickstart & Verification Guide: Post-Review Hardening

**Branch**: `039-post-review-hardening` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

Tài liệu này cung cấp các kịch bản kiểm chứng nhanh (runnable validation scenarios) độc lập để xác nhận 5 nhóm yêu cầu của feature hoạt động chính xác sau khi triển khai.

---

## 1. Yêu cầu Tiền đề (Prerequisites)

- Python >= 3.10
- Node.js >= 18
- Thư viện kiểm thử: `pytest`, `playwright`

---

## 2. Kịch bản 1: Kiểm chứng Cắt lát trên `RenderItem` (RenderItem Slice Support)

**Mục tiêu**: Xác nhận `RenderItem.__getitem__()` hỗ trợ các biểu thức cắt lát như `item[:3]` và chỉ số âm mà không gây `IndexError`.

**Lệnh thực thi**:
```bash
pytest tests/test_render_item.py -v
```

**Kết quả mong đợi**:
- `item[:3]` trả về đúng bộ 3 phần tử `(start, strokes, width)`.
- `item[1:4]` trả về `(strokes, width, missing)`.
- `item[-1]` trả về trường `occurrence`.
- Không phát sinh lỗi ngoại lệ nào.

---

## 3. Kịch bản 2: Kiểm chứng Biến thể Độc lập cho Công thức Toán lặp lại

**Mục tiêu**: Xác nhận 2 lần xuất hiện của cùng một công thức toán (ví dụ: `$x + 1$`) sở hữu các nét viết tay tự nhiên độc lập nhau khi `stable_variants=True`.

**Lệnh thực thi**:
```bash
pytest tests/test_stable_variants.py -k "test_repeated_math_formula_independent_variants" -v
```

**Kết quả mong đợi**:
- Hai công thức toán giống nhau có hạt giống nội bộ khác nhau (`math_seed` khác nhau do `occurrence` khác nhau).
- Tọa độ nét viết tay của lần xuất hiện thứ hai không bị trùng lặp 100% với lần xuất hiện thứ nhất.

---

## 4. Kịch bản 3: Kiểm chứng Khóa RNG Phân biệt Loại Nội dung & Prepend Invariance

**Mục tiêu**: Xác nhận việc sử dụng `token_id` có tiền tố (`text:`, `sym:`, `cell:`) ngăn ngừa va chạm giữa các khối và bảo toàn tính bất biến khi chèn từ phía trước kèm `jitter=1.0`.

**Lệnh thực thi**:
```bash
pytest tests/test_stable_variants.py -k "test_render_pipeline_prepend_invariance_with_jitter" -v
pytest tests/test_stable_variants.py -k "test_cross_block_rng_independence" -v
```

**Kết quả mong đợi**:
- Từ xuất hiện trong bảng và từ xuất hiện ngoài đoạn văn không bị gán trùng khóa jitter.
- Thao tác chèn từ mới ở đầu văn bản không làm thay đổi hình dạng nét của các đoạn văn phía sau.

---

## 5. Kịch bản 4: Kiểm chứng Đồng bộ hóa Metadata Phiên bản

**Mục tiêu**: Xác nhận toàn bộ tệp cấu hình và bản build web đều khai báo thống nhất phiên bản `2.1.0`.

**Lệnh thực thi**:
```bash
pytest tests/test_version_metadata.py -v
```

**Kết quả mong đợi**:
- `chuviettay.__version__ == "2.1.0"`.
- `pyproject.toml` có `version = "2.1.0"`.
- `package.json` có `"version": "2.1.0"`.
- Tiêu đề mới nhất trong `CHANGELOG.md` ghi `2.1.0`.

---

## 6. Kịch bản 5: Đóng gói Web Client và Kiểm tra An toàn Phân phối

**Mục tiêu**: Chạy quy trình đóng gói Web tĩnh và kiểm tra tệp `version.json` cùng độ an toàn phân phối.

**Lệnh thực thi**:
```bash
python scripts/build_web.py
```

**Kết quả mong đợi**:
- Quá trình build hoàn tất thành công.
- Tệp `webapp/dist/version.json` ghi nhận chính xác `"version": "2.1.0"`.
- Không có tệp cấm hoặc module `fidelity/` trong `webapp/dist/`.
- Kiểm thử đơn vị Web qua `npm run test:unit` đạt 100% thành công.
