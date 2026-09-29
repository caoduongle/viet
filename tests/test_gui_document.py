"""Kiểm thử tính năng mở tài liệu đa định dạng và hiển thị thông số trên GUI."""
import os
import pytest

from tests import conftest

if not conftest.is_tk_usable():
    pytest.skip(f"Môi trường Tk/Tcl không khả dụng ({conftest._tk_unusable_reason}). Trên Linux hãy chạy: xvfb-run -a pytest", allow_module_level=True)

pytestmark = [pytest.mark.gui]

from tkinter import filedialog, messagebox  # noqa: E402
from tests.test_gui import Dialogs  # noqa: E402
from chuviettay.controller.app_controller import AppController  # noqa: E402
from chuviettay.view.app_window import MainWindow  # noqa: E402


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


def test_gui_write_tab_paper_and_background_options(app, tmp_path, monkeypatch, dlg):
    """Kiểm tra thay đổi khổ giấy, chiều giấy và nền trên GUI được áp dụng vào file xuất ra."""
    out_xopp = tmp_path / "gui_out.xopp"
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: str(out_xopp))

    app.write_tab.text.delete("1.0", "end")
    app.write_tab.text.insert("1.0", "Thử nghiệm từ giao diện GUI")

    app.write_tab.v_paper.set("A3 (297×420 mm)")
    app.write_tab.v_orientation.set("Ngang (Landscape)")
    app.write_tab.v_background.set("Ô li (Graph)")
    app.write_tab.v_spacing.set("5.0")

    opts = app.write_tab.read_options()
    assert opts.paper == "a3"
    assert opts.orientation == "landscape"
    assert opts.background == "graph"
    assert opts.background_spacing == 14.17

    app.write_tab.do_write()
    assert out_xopp.exists()

    import gzip
    raw = gzip.decompress(open(out_xopp, "rb").read()).decode("utf-8")
    assert '<page width="1190.55" height="841.89">' in raw
    assert 'style="graph"' in raw
    assert 'config="r1=14.17"' in raw


def test_gui_custom_paper_dialog(app, monkeypatch):
    """Kiểm tra hộp thoại khổ giấy tùy chỉnh tính toán và lưu kích thước PostScript points chuẩn xác."""
    from chuviettay.view.write_tab import CustomPaperDialog

    # Khởi tạo CustomPaperDialog
    dlg = CustomPaperDialog(app, initial_w=150.0, initial_h=200.0)
    dlg.v_w.set("150")
    dlg.v_h.set("200")
    dlg.v_unit.set("mm")
    dlg._on_ok()

    assert dlg.result is not None
    # 150mm ~ 425.20 pt, 200mm ~ 566.93 pt
    assert dlg.result[0] == 425.20
    assert dlg.result[1] == 566.93

