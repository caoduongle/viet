"""Kiểm thử tính năng mở tài liệu đa định dạng và hiển thị thông số trên GUI."""
import os
import pytest
from tkinter import filedialog, messagebox

from tests import conftest
from tests.test_gui import Dialogs

if not conftest.is_tk_usable():
    pytest.skip(f"Tk/Tcl không khả dụng ({conftest._tk_unusable_reason})", allow_module_level=True)

pytestmark = [pytest.mark.gui]

from chuviettay.controller.app_controller import AppController
from chuviettay.view.app_window import MainWindow


@pytest.fixture
def dlg(monkeypatch):
    return Dialogs(monkeypatch)


@pytest.fixture
def app(tk_root, tiny_bank_path, dlg):
    tk_root.destroy()
    w = MainWindow(AppController(tiny_bank_path))
    w.withdraw()
    w.update()
    yield w
    try:
        w.destroy()
    except Exception:
        pass


def test_gui_open_markdown_document(app, tmp_path, monkeypatch, dlg):
    pytest.importorskip("markdown_it", reason="Cần cài đặt markdown-it-py để chạy kiểm thử định dạng Markdown")
    md_file = tmp_path / "test.md"
    md_file.write_text("# Tiêu đề A\n\nNội dung B", encoding="utf-8")

    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: str(md_file))
    app.write_tab.open_document()

    assert app.write_tab.current_doc is not None
    assert len(app.write_tab.current_doc.blocks) == 2
    status_text = app.write_tab.status.get("1.0", "end")
    assert "Đã mở tài liệu: test.md (2 khối)" in status_text


def test_gui_open_docx_document(app, tmp_path, monkeypatch, dlg):
    pytest.importorskip("docx", reason="Cần cài đặt python-docx để chạy kiểm thử định dạng Word")
    import docx
    docx_file = tmp_path / "test.docx"
    doc = docx.Document()
    doc.add_paragraph("Đoạn văn Word")
    doc.save(str(docx_file))

    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: str(docx_file))
    app.write_tab.open_document()

    assert app.write_tab.current_doc is not None
    assert len(app.write_tab.current_doc.blocks) == 1


def test_gui_write_document_flow(app, tmp_path, monkeypatch, dlg):
    pytest.importorskip("markdown_it", reason="Cần cài đặt markdown-it-py để chạy kiểm thử định dạng Markdown")
    md_file = tmp_path / "input.md"
    md_file.write_text("xin chào", encoding="utf-8")
    out_xopp = tmp_path / "out.xopp"

    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: str(md_file))
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: str(out_xopp))

    app.write_tab.open_document()
    assert app.write_tab.current_doc is not None

    app.write_tab.do_write()
    assert out_xopp.exists()
    status_text = app.write_tab.status.get("1.0", "end")
    assert "Xong" in status_text or "out.xopp" in status_text


def test_gui_error_handling_does_not_block_headless_dialog(app, tmp_path, monkeypatch, dlg):
    """Xác nhận lỗi khi mở hoặc xử lý tài liệu không làm treo giao diện trên xvfb."""
    corrupt_file = tmp_path / "corrupt.docx"
    corrupt_file.write_text("not a docx zip file", encoding="utf-8")

    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: str(corrupt_file))
    # open_document sẽ gọi report_error khi không đọc được tài liệu
    app.write_tab.open_document()

    # Hộp thoại showerror phải được ghi nhận mà không mở modal loop treo máy
    assert "showerror" in dlg.kinds()
    assert app.write_tab.current_doc is None
