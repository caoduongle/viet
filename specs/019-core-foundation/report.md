# Báo cáo Thực thi P1 — Core Foundation & Ecosystem Harmonization

**Nhánh**: `refactor/phase1-foundation`  
**Ngày bắt đầu**: 2026-10-05  
**Môi trường thực thi**: Windows, Python 3.12 (`py -3.12`)  

---

## 1. Baseline & Lưới an toàn (Phase 1: Setup)

### T001: Trạng thái Git
- Nhánh: `refactor/phase1-foundation`
- Working tree sạch hoàn toàn trước khi bắt đầu (chỉ có thư mục spec `specs/019-core-foundation/`).

### T002: Kiểm tra nghiệm thu P0
Lệnh: `py -3.12 repro_viet_baseline.py --repo . --only D1a D1b D2 D3 D4a D4b D5`
Kết quả:
```text
[ĐÃ SỬA  ] D1a  Xoá CHỮ CÁI 'a' rồi lưu có hợp nhất làm mất luôn TỪ 'a'
           sau hợp nhất: words['a']=1 (kỳ vọng 1), letters['a']=0 (kỳ vọng 0)
[ĐÃ SỬA  ] D1b  Chọn TỪ 'a' ở tab Kho mẫu rồi xoá lại xoá nhầm CHỮ CÁI 'a'
           sau drop_words(['a']): words['a']=0 (kỳ vọng 0), letters['a']=1 (kỳ vọng 1)
[ĐÃ SỬA  ] D2   Xoá ký hiệu rồi dạy lại bằng add_symbol_sample: mẫu mới mất sau lần hợp nhất kế
           mẫu π sau hợp nhất: trong RAM=1, trên đĩa=1 (kỳ vọng 1)
[ĐÃ SỬA  ] D3   learn không idempotent: lưu lại cùng tờ lưới (header gzip đổi) bị học trùng
           số mẫu 'khoai': sau lần học 1 = 1, sau lần học 2 (cùng nội dung) = 1 (kỳ vọng vẫn 1)
[ĐÃ SỬA  ] D4a  WriteOptions(missing_grid=False) bị bỏ qua ở chế độ Semantic; CLI không có --no-missing-grid
           _thieu.xopp vẫn được tạo khi tắt cờ: False | CLI có --no-missing-grid: True
[ĐÃ SỬA  ] D4b  Chạy lại write ghi đè ra_thieu.xopp, mất nét người dùng đã viết dở
           nét người dùng trong ra_thieu.xopp: trước=1, sau khi chạy lại write=1 (kỳ vọng vẫn 1)
[ĐÃ SỬA  ] D5   Lưu hoãn trên luồng Timer: RuntimeError 'dictionary changed size during iteration'
           0/8 vòng làm luồng Timer ném lỗi

Tổng: 7 mục | BUG: 0 | ĐÃ SỬA: 7 | LỖI-CHẠY: 0 | BỎ-QUA: 0
```

### T003: Cổng chất lượng (GATE) ban đầu
- `ruff check .` -> All checks passed!
- `pytest -q --timeout=90 -p no:cacheprovider` -> 1104 passed in 63.04s.
- `pytest -q tests/test_golden_master_real_path.py tests/test_architecture.py -p no:cacheprovider` -> 23 passed in 1.62s.

### T004: Tái hiện lỗi F4 (Pip installation bug)
Lệnh: `py -3.12 repro_viet_baseline.py --repo . --with-pip --only F4`
Kết quả:
```text
[BUG     ] F4   Cài bằng pip: kho/log mặc định nằm trong site-packages, `hw-note stats` báo không thấy kho
           kho mặc định = C:\Users\LE\AppData\Local\Temp\tmp0f7gzy0m\site\chu_cua_ban.json.gz

Tổng: 1 mục | BUG: 1 | ĐÃ SỬA: 0 | LỖI-CHẠY: 0 | BỎ-QUA: 0
```
Xác nhận F4 được tái hiện chính xác 100% trước khi sửa.

---

## 2. Ghi chú chung & Quyết định thiết kế
- `docs/img/after_fix.png` là ảnh cũ (trước `d17a142`), chủ repo cần sinh lại từ kho riêng — KHÔNG tự ý sinh lại bằng kho tổng hợp.

---

## 3. Giai đoạn 1: Nền tảng (P1)

### Q3 — Đồng bộ Schema v4 làm nguồn sự thật duy nhất và sửa tài liệu lưới chữ

#### Bằng chứng kiểm thử ĐỎ (T005 - T008)
Lệnh: `py -3.12 -m pytest -v tests/test_migrate_letter_bank.py::test_migrate_schema_version_v4_and_strict_validation tests/test_synthetic_bank.py::test_generate_synthetic_bank_schema_version_v4_strict tests/test_schema.py::test_bank_schema_docstring_matches_current_version`
Kết quả:
```text
FAILED tests/test_migrate_letter_bank.py::test_migrate_schema_version_v4_and_strict_validation - AssertionError: assert 3 == 4
FAILED tests/test_synthetic_bank.py::test_generate_synthetic_bank_schema_version_v4_strict - AssertionError: assert 2 == 4
FAILED tests/test_schema.py::test_bank_schema_docstring_matches_current_version - AssertionError: Docstring vẫn tham chiếu schema_version = 2 lỗi thời
3 failed in 1.01s
```

#### Bằng chứng kiểm thử XANH (T015)
- `tests/test_migrate_letter_bank.py`: PASSED
- `tests/test_synthetic_bank.py`: PASSED
- `tests/test_schema.py`: PASSED
- `ruff check .`: All checks passed!
- `test_golden_master_real_path.py & test_architecture.py`: 23 passed in 1.68s.
- **Commit**: `1f1e9f4` — `docs(schema): đồng bộ schema v4 làm nguồn sự thật và sửa tài liệu lưới chữ [Q3]`

---

### Q2 — Chuyển test sang đường thật và dọn dẹp composer cũ

#### Bảng ánh xạ test cũ sang đường thật (T019)
| Tên test | Đường cũ | Đường thật (`AppController.write_text`) | Khẳng định & Lý do |
|---|---|---|---|
| `test_van_ban_don_gian` | `compose_document` | `ctl.write_text` | Giữ nguyên: (n_lines=1, n_tokens=2, n_missing=0, n_strokes=2), `missing={}`. Đổi: `parts[0]==HEAD` -> XML `startswith('<?xml') and endswith('</xournal>')`. |
| `test_token_thieu_mau_duoc_dem_dung` | `compose_document` | `ctl.write_text` | Giữ nguyên 100%: n_tokens=4, n_missing_tokens=2, missing={'zzz': 2}. |
| `test_xuong_dong_khi_qua_be_rong` | `compose_document` | `ctl.write_text` | Giữ nguyên 100%: width=20 làm văn bản dài ngắt thành 3 dòng (n_lines=3). |
| `test_dong_trong_duoc_giu` | `compose_document` | `ctl.write_text` | Đổi: `r.n_lines=2` (DocumentLayoutEngine đếm số dòng có text thực sự); bổ sung đo khoảng cách tọa độ y: $\Delta y_{\text{gap}} > \Delta y_{\text{nogap}}$ chứng minh dòng trống được giữ nguyên trên trang. |
| `test_chia_trang` | `compose_document` (`line=1000` trên trang 200 pt) | `ctl.write_text` (`line=500` trên trang A4 841.89 pt) | Đổi: dòng 1 base 540 pt, dòng 2 cần thêm 500 pt vượt quá chiều cao khả dụng 761.89 pt nên ngắt sang trang 2 (`xml.count('<page ') == 2`). |
| `test_cung_seed_cung_ket_qua_khac_seed_khac_ket_qua` | `compose_document` | `ctl.write_text` | Giữ nguyên 100%: cùng seed ra XML giống nhau từng byte, khác seed ra XML khác nhau. |
| `test_jitter_0_thi_khong_con_ngau_nhien_ve_hinh_dang` | `compose_document` | `ctl.write_text` | Giữ nguyên 100%: jitter=0 cho tọa độ nét giống nhau giữa các seed; jitter=1.0 cho tọa độ khác nhau. |
| `test_mau_muc_va_do_day` | `compose_document` | `ctl.write_text` | Giữ nguyên 100%: `color="#1a237e"` xuất hiện trong thẻ `<stroke>` XML. |
| `test_write_document_ghi_file_va_file_luoi_o_khi_thieu` | `composer.write_document` | `ctl.write_text` | Giữ nguyên 100%: sinh file `.xopp` và file `_thieu.xopp` chứa nhãn 'zzz'. |
| `test_write_document_khong_thieu_thi_khong_tao_file_luoi_o` | `composer.write_document` | `ctl.write_text` | Giữ nguyên 100%: không sinh file `_thieu.xopp` khi không có từ thiếu. |
| `test_write_document_co_the_tat_file_luoi_o` | `composer.write_document` | `ctl.write_text(missing_grid=False)` | Giữ nguyên 100%: missing ghi nhận nhưng không sinh `_thieu.xopp`. |
| `test_strict_case_anh_huong_danh_sach_thieu` | `compose_document` | `ctl.write_text` | Giữ nguyên 100%: strict_case=False không thiếu, strict_case=True thiếu 'Xin'. |
| `test_auto_xh_and_dynamic_stroke_scaling` | `compose_document` | `ctl.write_text` | Giữ nguyên 100%: res.n_strokes > 0 và `width=` được bù trừ theo auto-xh trong XML. |

#### Bằng chứng kiểm thử ĐỎ hồi quy (T020)
- `tests/test_composer.py::test_composer_module_exports_contracts_and_no_legacy`: FAILED với `AssertionError: assert not True (hasattr(composer, 'compose_document'))`.

#### Bằng chứng kiểm thử XANH sau dọn dẹp mã (T024)
- Xoá `tests/test_golden_master.py` (toàn bộ kiểm định đối chứng kế thừa chuyển sang `tests/test_golden_master_real_path.py` của đường thật). Hằng `GOLDEN` cũ mất theo file đã xóa; hằng `GOLDEN_REAL` giữ nguyên vẹn 100%.
- Cắt bỏ `compose_document`, `composer.write_document`, `_missing_grid_path` và toàn bộ import thừa (`random`, `MAXH`, `xopp`, `Bank`, `Stroke`, `place`, `fmt`, `Writer`, `os`).
- `tests/test_composer.py`: 38 passed.
- `tests/test_letter_assembly_quality.py`: 6 passed.
- `ruff check .`: All checks passed!
- `test_golden_master_real_path.py & test_architecture.py`: 23 passed in 1.73s.
- **Commit**: `a3a3ff2` — `refactor(layout): chuyển toàn bộ test sang đường thật và dọn dẹp composer cũ [Q2]`

---

### Q4 — Kho chữ tổng hợp và kiểm thử nghiệm thu định lượng

#### Bằng chứng kiểm thử ĐỎ (T027)
Lệnh: `py -3.12 -m pytest tests/test_synthetic_bank.py::test_build_synthetic_letter_bank_contract tests/test_acceptance_metrics.py`
Kết quả:
```text
ImportError while importing test module 'D:\viet\app\tests\test_acceptance_metrics.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
tests\test_acceptance_metrics.py:20: in <module>
    from scripts.gen_synthetic_bank import build_synthetic_letter_bank
E   ImportError: cannot import name 'build_synthetic_letter_bank' from 'scripts.gen_synthetic_bank' (D:\viet\app\scripts\gen_synthetic_bank.py)
ERROR tests/test_acceptance_metrics.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
============================== 1 error in 0.78s ===============================
```

#### Bằng chứng kiểm thử XANH & Bảng chỉ số đo được (T030)
Lệnh: `py -3.12 -m pytest tests/test_synthetic_bank.py::test_build_synthetic_letter_bank_contract tests/test_acceptance_metrics.py`
Kết quả: `2 passed in 0.95s`

Bảng kết quả đo lường định lượng từ `tools/measure_ink.measure_ink_metrics` trên `tests/data/accept_sample.txt` (`--assemble --auto-xh`):

| Chỉ số hình học nét mực | Kết quả thực đo | Ngưỡng nghiệm thu kỳ vọng | Kết luận |
|---|---|---|---|
| Số token thiếu mẫu (`n_missing_tokens`) | **0** | **== 0** | **ĐẠT** |
| Khe hở nét tối thiểu theo độ dày bút (`min_stroke_clearance_pen`) | **0.85x** | **$\ge$ 0.80x** | **ĐẠT** |
| Khe hở nét tối thiểu tuyệt đối (`min_stroke_clearance_pt`) | **1.20 pt** | $\ge 1.13$ pt | **ĐẠT** |
| Tỉ lệ chồng lấn bounding box tối đa (`max_bbox_overlap_pct`) | **0.0%** | **$\le$ 10.0%** | **ĐẠT** |
| Trung vị x-height (`median_x_height`) | **8.06 pt** | **[7.15, 8.73] pt** (7.94 ± 10%) | **ĐẠT** |
| Độ lệch chuẩn x-height (`xh_std_dev`) | **1.34 pt** | Ổn định | **ĐẠT** |
| Tỉ lệ bề dày bút / x-height (`pen_to_xh_ratio`) | **0.175** | **[0.15, 0.20]** (chuẩn sổ tay 0.178) | **ĐẠT** |
| Khoảng cách giữa các chữ trong từ (`median_letter_gap`) | **2.20 pt** | Phù hợp tỉ lệ quang học | **ĐẠT** |
| Khoảng cách giữa các từ (`median_word_gap`) | **11.43 pt** | Rõ ràng, dễ đọc | **ĐẠT** |
| Tổng số nét phân tích (`stroke_count`) | **186 nét** | Đầy đủ văn bản | **ĐẠT** |

*Ghi chú quan trọng*: Kiểm thử này chứng minh cơ chế lắp ghép chữ cái dual-path, bộ lọc tự động co giãn x-height (auto-xh) và sàn khe hở vật lý (clearance floor) hoạt động chuẩn xác theo thiết kế; kiểm thử không đại diện cho tính thẩm mỹ hay nét chữ viết tay nghệ thuật.

- `ruff check .`: All checks passed!
- `test_golden_master_real_path.py & test_architecture.py`: 23 passed in 4.40s.
- **Commit**: `5683067` — `feat(test): bổ sung kho chữ tổng hợp và bộ test nghiệm thu định lượng [Q4]`

---

### F3 — Lưới chữ cái hw3 có f, j, w, z và bộ lọc nhãn chữ cái

#### Bằng chứng kiểm thử ĐỎ (T034)
Lệnh: `py -3.12 -m pytest tests/test_grid_hw3.py::test_export_letter_grid_85_cells tests/test_learning.py::test_learn_hw3_filter_letters_only`
Kết quả:
```text
FAILED tests/test_grid_hw3.py::test_export_letter_grid_85_cells - AssertionError: Kỳ vọng 85 ô nhãn, thực tế có 77: ['a', 'ă', 'â', ... 'X', 'Y', 'ng', ... 'dấu nặng']
FAILED tests/test_learning.py::test_learn_hw3_filter_letters_only - AssertionError: assert '1' not in {'1': [{'w': 5.0, 's': ...}]}
2 failed in 0.82s
```

#### Bằng chứng kiểm thử XANH sau khi hiện thực (T037)
Lệnh: `py -3.12 -m pytest tests/test_grid_hw3.py tests/test_learning.py`
Kết quả: `19 passed in 1.02s`

Các điểm đã hoàn thành:
1. `export_letter_grid`: Bổ sung `f, j, w, z` và `F, J, W, Z` vào `standard_letters` -> Lưới sinh đúng 85 ô nhãn (66 chữ cái + 14 digraphs + 5 dấu thanh).
2. Tương thích ngược: `test_learn_from_77_cells_legacy_grid_backward_compatibility` khẳng định đọc chính xác lưới 77 ô cũ từ `HEAD~` không bị lệch ô.
3. Lọc ký tự khi học (`learning.py`): Điều kiện `(len(r.label) == 1 and r.label.isalpha()) or r.label in xopp.VIETNAMESE_DIGRAPHS` đảm bảo các nhãn chữ số `"1"`, dấu câu `","`, ký hiệu `"+"` không bao giờ bị ghi đè vào `bank.letters`.
4. Ảnh minh hoạ `docs/img/luoi_hw3.png`: Là ảnh kết xuất đồ hoạ giao diện thực tế của tờ lưới cũ (77 ô). Giữ nguyên file ảnh trên đĩa để tránh sinh giả lập; chủ repo có thể kết xuất lại ảnh lưới 85 ô từ Xournal++ khi cần.
5. Cập nhật `README.md`: Nâng mô tả lưới hw3 từ 77 ô lên 85 ô kèm giải thích 4 chữ cái Latin mượn.
- `ruff check .`: All checks passed!
- `test_golden_master_real_path.py & test_architecture.py`: 23 passed in 2.16s.


