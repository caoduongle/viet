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
# Fixture kho mẫu tổng hợp độc lập (sinh bởi scripts/gen_synthetic_bank.py), hoàn toàn
# không chứa dữ liệu cá nhân nhưng có đầy đủ dấu thanh, từ mốc, chữ số và dấu câu.
REAL_BANK = os.path.join(HERE, "data", "kho_mau_tong_hop.json.gz")


@pytest.fixture(autouse=True)
def _no_log_file(monkeypatch):
    """Không để test tạo file chuviettay.log trong thư mục dự án."""
    from chuviettay import logging_setup
    monkeypatch.setattr(logging_setup, "_configured", True)


@pytest.fixture
def real_bank_path(tmp_path):
    """Bản sao (trong thư mục tạm) của fixture kho mẫu tổng hợp."""
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


_tk_usable_cached: bool | None = None
_tk_unusable_reason: str = ""


def is_tk_usable() -> bool:
    """Kiểm tra xem Tkinter và runtime Tcl/Tk có hoạt động đầy đủ hay không."""
    global _tk_usable_cached, _tk_unusable_reason
    if _tk_usable_cached is not None:
        return _tk_usable_cached
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.withdraw()
        # Thử khởi tạo widget cơ bản và ttk để nạp file script Tcl (init.tcl, listbox.tcl)
        ttk.Button(root)
        tk.Listbox(root)
        root.destroy()
        _tk_usable_cached = True
        _tk_unusable_reason = ""
    except Exception as e:  # noqa: BLE001
        _tk_usable_cached = False
        _tk_unusable_reason = str(e)
    return _tk_usable_cached


def pytest_collection_modifyitems(config, items):
    """Tự động đánh dấu skip các test GUI nếu môi trường Tk/Tcl bị lỗi hoặc thiếu."""
    if not is_tk_usable():
        reason = f"Tk/Tcl không khả dụng hoặc runtime bị lỗi ({_tk_unusable_reason}). Trên Linux hãy chạy: xvfb-run -a pytest"
        skip_tk = pytest.mark.skip(reason=reason)
        for item in items:
            if "gui" in item.keywords:
                item.add_marker(skip_tk)


@pytest.fixture
def tk_root():
    """Cửa sổ Tk ẩn. Không có màn hình hoặc lỗi Tk thì bỏ qua test (Linux: chạy `xvfb-run -a pytest`)."""
    if not is_tk_usable():
        pytest.skip(f"Môi trường Tk/Tcl không khả dụng ({_tk_unusable_reason}). Trên Linux hãy chạy: xvfb-run -a pytest")
    import tkinter as tk
    try:
        root = tk.Tk()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Không tạo được cửa sổ Tk ({e}). Trên Linux hãy chạy: xvfb-run -a pytest")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:  # noqa: BLE001, S110
        pass
