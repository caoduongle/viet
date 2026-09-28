"""Fixture dùng chung cho toàn bộ bộ kiểm thử.

Nguyên tắc: test KHÔNG BAO GIỜ đụng vào kho mẫu thật của người dùng -- dùng bản chụp cố định
trong tests/data/, và luôn làm việc trên BẢN SAO trong thư mục tạm (real_bank_path). Với các test cần kết quả tất định, dùng kho
mẫu nhỏ tự dựng (tiny_bank_path) để tự tính tay được đáp án.
"""
import gzip
import json
import os
import shutil

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
# Bản CHỤP CỐ ĐỊNH của một kho mẫu thật (362 từ / 859 mẫu, chụp lúc tái cấu trúc). Test dùng bản này
# thay vì chu_cua_ban.json.gz của người dùng, để (1) kết quả không đổi khi bạn dạy thêm từ mới và
# (2) test không bao giờ đọc/ghi dữ liệu thật của bạn.
REAL_BANK = os.path.join(HERE, "data", "kho_mau_chup_lai.json.gz")


@pytest.fixture(autouse=True)
def _no_log_file(monkeypatch):
    """Không để test tạo file chuviettay.log trong thư mục dự án."""
    from chuviettay import logging_setup
    monkeypatch.setattr(logging_setup, "_configured", True)


@pytest.fixture
def real_bank_path(tmp_path):
    """Bản sao (trong thư mục tạm) của bản chụp kho mẫu thật: 362 từ / 859 mẫu."""
    dst = tmp_path / "bank.json.gz"
    shutil.copy(REAL_BANK, dst)
    return str(dst)


@pytest.fixture
def real_bank(real_bank_path):
    from chuviettay.model.bank import Bank
    return Bank(real_bank_path)


def _inst(w, strokes, T="", vi=-1, ti=-1):
    return {"w": w, "s": strokes, "T": T, "vi": vi, "ti": ti}


def tiny_bank_dict():
    """Kho mẫu nhỏ, tự dựng, đủ để chạm mọi nhánh chính của thuật toán:
    - "xin": 5 mẫu, độ rộng ổn định -> ứng viên từ mốc hiệu chỉnh cỡ tay
    - "ba": không dấu -> làm thân chữ khi ghép "bà"/"bá"...
    - "chào": có dấu huyền (nét dấu là nét số 1) -> cung cấp nét dấu thanh rời để ghép
    - chữ số 1, 2 và dấu , . cho nhánh số / dấu câu
    """
    xin = [_inst(w, [[0, 0, 3, -5, 6, 0, 9, -5]]) for w in (9.0, 9.2, 8.8, 9.1, 8.9)]
    return {
        "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0, "v": 1,
        "x0": 78.0, "width": 500.0, "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": {
            "xin": xin,
            "ba": [_inst(8.0, [[0, 0, 4, -5, 8, 0]]), _inst(8.4, [[0, 0, 4, -5.5, 8.4, 0]])],
            "chào": [
                _inst(14.0, [[0, 0, 5, -6, 10, 0, 14, -5], [7, -11, 9, -9]], T="\u0300", vi=2, ti=1),
                _inst(14.4, [[0, 0, 5, -6, 10, 0, 14.4, -5], [7.4, -11.5, 9.4, -9.5]], T="\u0300", vi=2, ti=1),
            ],
        },
        "digits": {"1": [_inst(3.0, [[0, 0, 1, -6]])], "2": [_inst(4.0, [[0, -6, 3, -6, 0, 0, 4, 0]])]},
        "punct": {",": [{"w": 1.0, "s": [[0, 0, 0.5, 1.5]]}], ".": [{"w": 1.0, "s": [[0, 0, 0.5, 0.5]]}]},
    }


@pytest.fixture
def tiny_bank_path(tmp_path):
    p = tmp_path / "tiny.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(tiny_bank_dict(), f, ensure_ascii=False)
    return str(p)


@pytest.fixture
def tiny_bank(tiny_bank_path):
    from chuviettay.model.bank import Bank
    return Bank(tiny_bank_path)


@pytest.fixture
def tk_root():
    """Cửa sổ Tk ẩn. Không có màn hình thì bỏ qua test (Linux: chạy `xvfb-run -a pytest`)."""
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError as e:
        pytest.skip("Không tạo được cửa sổ Tk (%s). Trên Linux hãy chạy: xvfb-run -a pytest" % e)
    root.withdraw()
    yield root
    root.destroy()
