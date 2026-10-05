"""Kiểm thử nghiệm thu định lượng chất lượng nét mực và ghép chữ (Quantitative Acceptance Suite).

Sử dụng kho chữ cái tổng hợp chuẩn (build_synthetic_letter_bank) và tệp văn bản nghiệm thu
tests/data/accept_sample.txt với các cờ ghép chữ: --assemble --auto-xh.
Các chỉ số được đo lường bằng tools/measure_ink.measure_ink_metrics:
1. 0 từ thiếu (result.n_missing_tokens == 0)
2. min_stroke_clearance_pen >= 0.8
3. max_bbox_overlap_pct <= 10.0
4. median_x_height trong khoảng 7.94 pt ± 10% (7.15 đến 8.73 pt)
5. pen_to_xh_ratio trong khoảng [0.15, 0.20]
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from chuviettay.controller.app_controller import AppController
from chuviettay.model.composer import WriteOptions
from scripts.gen_synthetic_bank import build_synthetic_letter_bank
from tools.measure_ink import measure_ink_metrics


def test_quantitative_acceptance_metrics(tmp_path):
    # 1. Dựng kho chữ tổng hợp
    bank_dict = build_synthetic_letter_bank(seed=42)
    bank_path = tmp_path / "synthetic_letter_bank.json.gz"
    with gzip.open(bank_path, "wt", encoding="utf-8") as gf:
        json.dump(bank_dict, gf)

    ctl = AppController(str(bank_path))
    ctl.load_bank()

    # 2. Đọc tệp mẫu nghiệm thu
    sample_text_path = Path("tests") / "data" / "accept_sample.txt"
    assert sample_text_path.exists(), f"Không tìm thấy {sample_text_path}"
    sample_text = sample_text_path.read_text(encoding="utf-8")

    out_xopp = str(tmp_path / "accept_result.xopp")
    opts = WriteOptions(
        seed=42,
        assemble_letters=True,
        auto_xh=True,
        target_xh=7.94,
        letter_gap=1.0,
        pen_clearance_factor=0.8,
    )
    result = ctl.write_text(sample_text, opts, out_xopp)

    # Khẳng định 1: Không có từ nào bị thiếu mẫu
    assert result.n_missing_tokens == 0, f"Còn từ thiếu mẫu: {result.missing}"

    # 3. Đo lường định lượng các chỉ số nét mực
    metrics = measure_ink_metrics(out_xopp)

    # Khẳng định 2: Khe hở nét tối thiểu >= 0.8 lần độ dày bút
    min_clearance_pen = float(metrics["min_stroke_clearance_pen"])
    assert min_clearance_pen >= 0.8, (
        f"Khe hở nét bút quá nhỏ: {min_clearance_pen:.2f} < 0.80 lần bề dày bút"
    )

    # Khẳng định 3: Bounding box overlap tối đa <= 10.0%
    max_overlap_pct = float(metrics["max_bbox_overlap_pct"])
    assert max_overlap_pct <= 10.0, (
        f"Chồng lấn bounding box quá lớn: {max_overlap_pct:.2f}% > 10.0%"
    )

    # Khẳng định 4: Median x-height nằm trong 7.94 ± 10% (7.15 đến 8.73 pt)
    med_xh = float(metrics["median_x_height"])
    assert 7.15 <= med_xh <= 8.73, (
        f"x-height trung vị lệch chuẩn: {med_xh:.2f} pt (kỳ vọng [7.15, 8.73])"
    )

    # Khẳng định 5: Tỉ lệ nét bút / x-height nằm trong [0.15, 0.20] (chuẩn sổ tay 0.178)
    pen_ratio = float(metrics["pen_to_xh_ratio"])
    assert 0.15 <= pen_ratio <= 0.20, (
        f"Tỉ lệ nét bút / x-height không tự nhiên: {pen_ratio:.3f} (kỳ vọng [0.15, 0.20])"
    )
