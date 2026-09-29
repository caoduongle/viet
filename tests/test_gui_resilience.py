"""Kiểm thử tính năng cô lập và tự động bỏ qua (skip) an toàn khi môi trường Tk/Tcl thiếu hoặc lỗi."""
import pytest

from tests import conftest


def test_is_tk_usable_returns_bool():
    """Hàm probe môi trường Tk phải trả về bool mà không văng ngoại lệ ra ngoài."""
    res = conftest.is_tk_usable()
    assert isinstance(res, bool)


def test_is_tk_usable_handles_tcl_error_gracefully(monkeypatch):
    """Khi khởi tạo Tk văng lỗi TclError (ví dụ thiếu init.tcl hoặc listbox.tcl), probe phải trả về False."""
    pytest.importorskip("tkinter")
    import tkinter as tk

    monkeypatch.setattr(conftest, "_tk_usable_cached", None)

    def mock_tk_init(*args, **kwargs):
        raise tk.TclError("Can't find a usable init.tcl in the following directories")

    monkeypatch.setattr(tk, "Tk", mock_tk_init)
    assert conftest.is_tk_usable() is False
    assert "init.tcl" in conftest._tk_unusable_reason

    # Khôi phục cache sau test
    monkeypatch.setattr(conftest, "_tk_usable_cached", None)


def test_tk_root_skips_when_tk_unusable(monkeypatch):
    """Fixture tk_root phải gọi pytest.skip thay vì để văng TclError ra ngoài làm hỏng test runner."""
    monkeypatch.setattr(conftest, "is_tk_usable", lambda: False)
    monkeypatch.setattr(conftest, "_tk_unusable_reason", "Giả lập thiếu init.tcl")

    with pytest.raises(pytest.skip.Exception) as exc_info:
        # Gọi qua __wrapped__ để không vi phạm quy tắc pytest 9 cấm gọi fixture trực tiếp
        gen = conftest.tk_root.__wrapped__()
        next(gen)

    assert "Môi trường Tk/Tcl không khả dụng" in str(exc_info.value)
