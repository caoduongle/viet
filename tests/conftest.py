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
        "symbols": {},
        "letters": {
            "x": [_inst(2.5, [[0, 0, 2.5, -5]])],
            "i": [_inst(1.5, [[0, 0, 1.5, -5]])],
            "n": [_inst(3.0, [[0, 0, 3.0, -5]])],
            "b": [_inst(3.5, [[0, 0, 3.5, -7]])],
            "a": [_inst(3.0, [[0, 0, 3.0, -5]])],
            "c": [_inst(2.5, [[0, 0, 2.5, -5]])],
            "h": [_inst(3.5, [[0, 0, 3.5, -7]])],
            "o": [_inst(3.0, [[0, 0, 3.0, -5]])],
        },
        "marks": {},
    }


def generate_large_synthetic_bank_dict(n_samples: int = 5000) -> dict:
    """Tạo nhanh kho mẫu tổng hợp có số lượng mẫu lớn (mặc định 5,000) phục vụ benchmark.
    Bao gồm các từ có dấu thanh để kiểm thử chỉ mục _raw_marks và lọc phân vị."""
    tones_list = ["", "\u0300", "\u0301", "\u0303", "\u0309", "\u0323"]
    words_dict = {}
    samples_per_word = 10
    num_words = max(1, n_samples // samples_per_word)

    for w_idx in range(num_words):
        t = tones_list[w_idx % len(tones_list)]
        word_label = f"word_{w_idx}" if not t else f"word_{w_idx}{t}"
        samples = []
        for s_idx in range(samples_per_word):
            ti = 1 if t else -1
            vi = 2 if t else -1
            strokes = [[0.0, 0.0, 5.0, -5.0, 10.0, 0.0]]
            if t:
                strokes.append([5.0, -10.0 + s_idx * 0.05, 7.0, -8.0 + s_idx * 0.05])
            samples.append({"w": 12.0 + (s_idx * 0.1), "s": strokes, "T": t, "vi": vi, "ti": ti})
        words_dict[word_label] = samples

    return {
        "schema_version": 2,
        "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0, "v": 1,
        "x0": 78.0, "width": 500.0, "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": words_dict,
        "digits": {"1": [{"w": 3.0, "s": [[0, 0, 1, -6]]}]},
        "punct": {".": [{"w": 1.0, "s": [[0, 0, 0.5, 0.5]]}]},
        "tombstones": {},
        "generation": 1,
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


def make_corrupt_bank(path: str, mode: str = "bad_gzip") -> str:
    """Tạo file kho mẫu bị hỏng ở path:
    - 'bad_gzip': header/payload gzip không hợp lệ
    - 'bad_json': gzip hợp lệ nhưng bên trong là JSON sai cú pháp
    - 'empty': file 0 bytes
    """
    if mode == "empty":
        with open(path, "wb"):
            pass
    elif mode == "bad_gzip":
        with open(path, "wb") as f:
            f.write(b"not-a-gzip-stream-at-all\x00\x01\x02\x03")
    elif mode == "bad_json":
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write("{invalid-json-content: 123,")
    return path


_tk_usable_cached: bool | None = None
_tk_unusable_reason: str = ""


def is_tk_usable() -> bool:
    """Kiểm tra xem Tkinter và runtime Tcl/Tk có hoạt động đầy đủ hay không.
    Thẩm tra toàn diện:
    1. Import tkinter và ttk.
    2. Khởi tạo root = tk.Tk().
    3. Thẩm tra và nạp trực tiếp script Tcl cốt lõi ($tk_library/listbox.tcl, tk.tcl).
    4. Thử nghiệm khởi tạo các widget phức hợp mà MainWindow sử dụng (Notebook, Listbox, Button, Canvas).
    5. Thực thi chu kỳ sự kiện (update_idletasks, update) để bắt mọi TclError tiềm ẩn.
    """
    global _tk_usable_cached, _tk_unusable_reason
    if _tk_usable_cached is not None:
        return _tk_usable_cached
    root = None
    try:
        import tkinter as tk
        from tkinter import ttk

        root = tk.Tk()
        root.withdraw()

        # 1. Thẩm tra tệp script Tcl cốt lõi (init.tcl)
        try:
            tcl_lib = root.tk.eval("set tcl_library")
            init_script = os.path.join(tcl_lib, "init.tcl")
            if not os.path.exists(init_script):
                root.tk.eval("source [file join $tcl_library init.tcl]")
        except Exception as tcl_err:  # noqa: BLE001
            raise RuntimeError(f"Thiếu hoặc không thể nạp tệp thư viện Tcl init.tcl ({tcl_err})") from tcl_err

        # 2. Thẩm tra tệp script Tk cốt lõi (ngăn chặn lỗi thiếu listbox.tcl trên Windows)
        try:
            tk_lib = root.tk.eval("set tk_library")
            for req_script in ("tk.tcl", "listbox.tcl", "button.tcl", "entry.tcl"):
                script_path = os.path.join(tk_lib, req_script)
                if not os.path.exists(script_path):
                    # Thử xem Tcl có nạp được từ VFS/zip không qua lệnh source
                    root.tk.eval(f"source [file join $tk_library {req_script}]")
        except Exception as script_err:  # noqa: BLE001
            raise RuntimeError(f"Thiếu hoặc không thể nạp tệp thư viện Tk ({script_err})") from script_err

        # 3. Khởi tạo các widget và kích hoạt chu trình cập nhật giao diện
        ttk.Notebook(root)
        ttk.Button(root)
        lb = tk.Listbox(root)
        lb.insert(0, "test")
        tk.Canvas(root)
        root.update_idletasks()
        root.update()

        _tk_usable_cached = True
        _tk_unusable_reason = ""
    except Exception as e:  # noqa: BLE001
        _tk_usable_cached = False
        _tk_unusable_reason = str(e)
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:  # noqa: BLE001, S110
                pass
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


@pytest.fixture(autouse=True)
def _safe_gui_dialogs(monkeypatch):
    """Bảo đảm mọi hộp thoại Tkinter (messagebox, simpledialog) không mở popup chặn tiến trình khi test trên headless/xvfb."""
    try:
        from tkinter import messagebox, simpledialog
    except (ImportError, Exception):  # noqa: BLE001
        return

    # Mock các hộp thoại thông báo và xác nhận để không treo modal loop trên xvfb
    for name in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, name, lambda *a, **kw: "ok")
    for name in ("askokcancel", "askyesno", "askyesnocancel", "askretrycancel"):
        monkeypatch.setattr(messagebox, name, lambda *a, **kw: True)
    monkeypatch.setattr(messagebox, "askquestion", lambda *a, **kw: "yes")

    # Mock các hộp thoại nhập liệu đơn giản
    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **kw: "")
    monkeypatch.setattr(simpledialog, "askinteger", lambda *a, **kw: 0)
    monkeypatch.setattr(simpledialog, "askfloat", lambda *a, **kw: 0.0)


@pytest.fixture
def legacy_words_only_bank_path(tmp_path):
    """Kho mẫu chỉ chứa từ nguyên khối cũ (words) và hoàn toàn không có letters."""
    p = tmp_path / "legacy_bank.json.gz"
    d = {
        "schema_version": 1,
        "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0, "v": 1,
        "x0": 78.0, "width": 500.0, "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": {
            "xin": [{"w": 9.0, "s": [[0, 0, 3, -5, 6, 0, 9, -5]]}],
            "chào": [{"w": 14.0, "s": [[0, 0, 5, -6, 10, 0, 14, -5], [7, -11, 9, -9]], "T": "\u0300", "vi": 2, "ti": 1}],
        },
        "digits": {}, "punct": {}, "symbols": {}, "letters": {}, "marks": {},
    }
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    return str(p)


@pytest.fixture
def legacy_words_only_bank(legacy_words_only_bank_path):
    from chuviettay.model.bank import Bank
    return Bank(legacy_words_only_bank_path)


