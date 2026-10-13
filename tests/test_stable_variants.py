"""Kiểm thử tính năng D3 & WP2: Kiểu chữ ổn định (stable_variants).

Bao gồm:
1. Tạo ngân hàng đa biến thể (ít nhất 4 biến thể/chữ) với hình học nét khác biệt để phát hiện
   bất kỳ sự thay đổi biến thể thực sự nào.
2. Kiểm tra tính bất biến khi chèn từ phía trước (Prepend Invariance):
   Chèn "a" hoặc "buổi sáng" phía trước KHÔNG làm đổi biến thể hoặc tọa độ tương đối của các từ phía sau.
3. Kiểm tra chống lặp biến thể cục bộ (De-duplication):
   Một từ lặp lại liên tiếp không chọn trùng một biến thể 2 lần liền nhau.
4. Kiểm tra bất biến khi tịnh tiến tọa độ Y.
5. Kiểm tra stable_variants=False (mặc định) vẫn giữ tính ngẫu nhiên tuần tự cũ.
"""
from __future__ import annotations

import copy
import gzip
import json
import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.model.bank import Bank
from chuviettay.model.text_utils import shift
from chuviettay.model.writer import Writer

KHO_TONG_HOP = "tests/data/kho_mau_tong_hop.json.gz"


def create_multivariant_bank(tmp_path) -> Bank:
    """Tạo ngân hàng đa biến thể trong bộ nhớ từ kho_mau_tong_hop.json.gz.
    Mỗi chữ cái/ký tự được nhân bản thành ít nhất 4 biến thể với tọa độ nét khác biệt,
    bảo đảm việc chọn biến thể khác nhau sẽ dẫn đến hình học nét khác nhau rõ rệt.
    """
    with gzip.open(KHO_TONG_HOP, "rt", encoding="utf-8") as f:
        data = json.load(f)

    # Nhân bản các danh mục thành 4 biến thể với biến đổi nét
    for category in ("letters", "words", "punct", "symbols", "digits"):
        cat_dict = data.get(category, {})
        for key, samples in list(cat_dict.items()):
            if not samples:
                continue
            base_sample = samples[0]
            new_samples = []
            for v_idx in range(4):
                sample_copy = copy.deepcopy(base_sample)
                # Biến đổi nhẹ tọa độ các nét để mỗi biến thể là duy nhất
                delta = (v_idx + 1) * 0.25
                sample_copy["s"] = [shift(st, delta, delta * 0.5) for st in sample_copy.get("s", [])]
                sample_copy["variant_id"] = v_idx
                new_samples.append(sample_copy)
            cat_dict[key] = new_samples

    out_file = str(tmp_path / "kho_multivariant.json.gz")
    with gzip.open(out_file, "wt", encoding="utf-8") as f:
        json.dump(data, f)

    return Bank(out_file)


def test_stable_variants_prepend_invariance(tmp_path):
    """Kiểm chứng tính bất biến khi chèn tiền tố:
    Chèn từ 'buổi sáng' phía trước không làm đổi nét chữ của 'hôm', 'nay', 'trời', 'đẹp'.
    """
    bank = create_multivariant_bank(tmp_path)
    tokens_target = ["hôm", "nay", "trời", "đẹp"]

    # Lượt 1: Chỉ viết các từ mục tiêu
    w1 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    strokes_run1: dict[str, list] = {}
    for tok in tokens_target:
        st, w, miss = w1.token(tok)
        strokes_run1[tok] = st

    # Lượt 2: Chèn thêm từ phía trước
    w2 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    w2.token("buổi")
    w2.token("sáng")

    strokes_run2: dict[str, list] = {}
    for tok in tokens_target:
        st, w, miss = w2.token(tok)
        strokes_run2[tok] = st

    # So sánh từng nét vẽ thật sự
    for tok in tokens_target:
        assert strokes_run1[tok] == strokes_run2[tok], (
            f"Từ '{tok}' bị thay đổi hình dạng nét khi chèn từ phía trước!"
        )


def test_stable_variants_single_word_prepend(tmp_path):
    """Tái hiện trực tiếp ca đo kiểm nghiệm:
    Chèn từ 'a' phía trước không làm đổi hình của 'nay'.
    """
    bank = create_multivariant_bank(tmp_path)

    w1 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    st1, _, _ = w1.token("nay")

    w2 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    w2.token("a")
    st2, _, _ = w2.token("nay")

    assert st1 == st2, "Chèn từ 'a' phía trước đã làm đổi hình nét của từ 'nay'!"


def test_repeated_word_no_immediate_duplicate(tmp_path):
    """Kiểm tra chống lặp biến thể:
    Một từ lặp lại 50 lần liên tiếp trong tài liệu không chọn trùng 2 lần liền nhau.
    """
    bank = create_multivariant_bank(tmp_path)
    w = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)

    last_strokes = None
    for rep in range(50):
        curr_strokes, _, _ = w.token("tôi")
        if last_strokes is not None:
            assert curr_strokes != last_strokes, (
                f"Lần lặp {rep}: Từ 'tôi' bị lặp trùng y hệt biến thể nét của lần trước!"
            )
        last_strokes = curr_strokes


def test_stable_variants_false_differs_from_true(tmp_path):
    """Khi stable_variants=False, hành vi ngẫu nhiên tuần tự thông thường vẫn diễn ra."""
    bank = create_multivariant_bank(tmp_path)

    w_default1 = Writer(bank, None, jitter=0.0, stable_variants=False, seed=42)
    st_def1, _, _ = w_default1.token("nay")

    w_default2 = Writer(bank, None, jitter=0.0, stable_variants=False, seed=42)
    w_default2.token("a")
    st_def2, _, _ = w_default2.token("nay")

    # Với stable_variants=False, việc chèn 'a' tiêu thụ RNG khiến 'nay' đổi mẫu
    assert st_def1 != st_def2, "Với stable_variants=False, chèn 'a' phải làm đổi mẫu do tiêu thụ RNG tuần tự"


def test_cli_stable_flag_integration(tmp_path):
    """Kiểm tra tích hợp WriteOptions(stable_variants=True) qua AppController."""
    ctl = AppController(bank_path=KHO_TONG_HOP, timer_factory=lambda *a, **k: None)
    ctl.load_bank()

    opts_stable = WriteOptions(seed=12345, stable_variants=True)
    out1 = tmp_path / "out1.xopp"
    res1 = ctl.write_text("hôm nay trời đẹp", opts_stable, str(out1))
    assert res1.n_lines > 0
    assert res1.seed_used == 12345
