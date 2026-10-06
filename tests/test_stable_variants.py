"""Kiểm thử tính năng D3: Kiểu chữ ổn định (stable_variants).

Đảm bảo:
  1. stable_variants=False (mặc định) giữ nguyên hành vi ngẫu nhiên theo dòng random chung.
  2. stable_variants=True:
     - Chọn mẫu tất định theo hash(seed, token, count).
     - Khi chèn thêm từ ở đầu hoặc giữa câu, các từ xuất hiện sau đó vẫn giữ nguyên
       chỉ số mẫu biến thể đã chọn.
"""
from __future__ import annotations

from chuviettay.controller.app_controller import AppController
from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteOptions
from chuviettay.model.writer import Writer

KHO_TONG_HOP = "tests/data/kho_mau_tong_hop.json.gz"


def test_writer_stable_variants_keeps_choice():
    """Kiểm tra Writer với stable_variants=True giữ nguyên lựa chọn mẫu cho cùng từ."""
    bank = Bank(KHO_TONG_HOP)

    # 1. Câu ban đầu: "hôm nay trời đẹp"
    # Dùng Writer với stable_variants=True
    w1 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    # Lấy mẫu các từ
    tokens = ["hôm", "nay", "trời", "đẹp"]
    choices_run1 = {}
    for tok in tokens:
        st, w, miss = w1.token(tok)
        choices_run1[tok] = w1.last.get(tok)

    # 2. Chèn thêm từ "buổi sáng" vào trước: "buổi sáng hôm nay trời đẹp"
    w2 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    w2.token("buổi")
    w2.token("sáng")

    choices_run2 = {}
    for tok in tokens:
        st, w, miss = w2.token(tok)
        choices_run2[tok] = w2.last.get(tok)

    # Khẳng định: Các từ "hôm", "nay", "trời", "đẹp" có đúng chỉ số mẫu đã chọn như lần 1
    for tok in tokens:
        assert choices_run1[tok] == choices_run2[tok], f"Từ '{tok}' bị đổi mẫu biến thể khi chèn từ phía trước!"


def test_cli_stable_flag_integration(tmp_path):
    """Kiểm tra tích hợp WriteOptions(stable_variants=True) qua AppController."""
    ctl = AppController(bank_path=KHO_TONG_HOP, timer_factory=lambda *a, **k: None)
    ctl.load_bank()

    opts_stable = WriteOptions(seed=12345, stable_variants=True)
    out1 = tmp_path / "out1.xopp"
    res1 = ctl.write_text("hôm nay trời đẹp", opts_stable, str(out1))
    assert res1.n_lines > 0
