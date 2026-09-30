"""Quy tắc kiến trúc MVC, được kiểm tra TỰ ĐỘNG bằng cách đọc import trong mã nguồn.

Vì sao có test này: MVC chỉ có giá trị khi các ranh giới được GIỮ THEO THỜI GIAN. Sau vài lần
sửa vội, rất dễ có người `import tkinter` vào Model hay `print()` vào Controller và cấu trúc
mục ruỗng dần. Test này biến các quy tắc trong README thành thứ máy kiểm tra được -- vi phạm
là test đỏ ngay, kèm chỉ đúng file/dòng.

Sơ đồ phụ thuộc (mũi tên = "được phép import"):
    cli.py, gui.py, view/  ->  controller/  ->  model/
"""
import ast
import pathlib

import pytest

PKG = pathlib.Path(__file__).resolve().parent.parent / "chuviettay"


def py_files(sub=None):
    base = PKG / sub if sub else PKG
    return sorted(base.glob("*.py"))


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
    return found


def violations(files, forbidden_prefixes):
    bad = []
    for f in files:
        for mod, line in imported_modules(f):
            if any(mod == p or mod.startswith(p + ".") for p in forbidden_prefixes):
                bad.append("%s:%d import %s" % (f.relative_to(PKG.parent), line, mod))
    return bad


def print_calls(files):
    bad = []
    for f in files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("print", "input"):
                bad.append("%s:%d gọi %s()" % (f.relative_to(PKG.parent), node.lineno, node.func.id))
    return bad


UI_AND_ENTRY = ["chuviettay.view", "chuviettay.cli", "chuviettay.gui"]


def test_model_khong_biet_gi_ve_giao_dien_hay_controller():
    bad = violations(py_files("model"),
                     ["tkinter", "argparse", "chuviettay.controller", "chuviettay.formatting"] + UI_AND_ENTRY)
    assert not bad, "Model phải độc lập:\n  " + "\n  ".join(bad)


def test_controller_khong_biet_gi_ve_tkinter_argparse_view_cli():
    bad = violations(py_files("controller"), ["tkinter", "argparse"] + UI_AND_ENTRY)
    assert not bad, "Controller không được phụ thuộc giao diện:\n  " + "\n  ".join(bad)


def test_chi_view_va_gui_duoc_import_tkinter():
    others = [f for f in py_files() + py_files("model") + py_files("controller")
              if f.name != "gui.py"]
    bad = violations(others, ["tkinter"])
    assert not bad, "Chỉ view/ (và gui.py) được import tkinter:\n  " + "\n  ".join(bad)


def test_view_chi_noi_chuyen_voi_controller_khong_cham_vao_model():
    bad = violations(py_files("view"), ["chuviettay.model", "argparse"])
    assert not bad, "View chỉ được gọi Controller, không đụng Model:\n  " + "\n  ".join(bad)


def test_cli_chi_noi_chuyen_voi_controller_khong_cham_vao_model_hay_view():
    bad = violations([PKG / "cli.py"], ["chuviettay.model", "tkinter"] + ["chuviettay.view", "chuviettay.gui"])
    assert not bad, "cli.py chỉ được gọi Controller:\n  " + "\n  ".join(bad)


def test_khong_print_hay_input_trong_cac_lop_loi():
    core_files = (
        py_files("model")
        + py_files("controller")
        + py_files("view")
        + py_files("document")
        + py_files("importer")
        + py_files("layout")
        + py_files("math")
        + py_files("fidelity")
    )
    bad = print_calls(core_files)
    assert not bad, ("Chỉ cli.py được in ra màn hình; các lớp còn lại trả dữ liệu / ghi log:\n  "
                     + "\n  ".join(bad))


def test_khong_dung_sys_exit_trong_cac_lop_loi():
    bad = []
    core_files = (
        py_files("model")
        + py_files("controller")
        + py_files("view")
        + py_files("document")
        + py_files("importer")
        + py_files("layout")
        + py_files("math")
        + py_files("fidelity")
    )
    for f in core_files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Attribute) and node.attr == "exit"
                    and isinstance(node.value, ast.Name) and node.value.id == "sys"):
                bad.append("%s:%d sys.exit" % (f.relative_to(PKG.parent), node.lineno))
    assert not bad, "Thoát chương trình là việc của cli.py/hw_*.py, không phải của lõi:\n  " + "\n  ".join(bad)


def test_fidelity_khong_phu_thuoc_view_hay_cli():
    """Tầng fidelity/ không được phụ thuộc vào giao diện (view), CLI hay tkinter."""
    bad = violations(py_files("fidelity"), ["tkinter"] + UI_AND_ENTRY)
    assert not bad, "Fidelity không được phụ thuộc View/CLI/Tkinter:\n  " + "\n  ".join(bad)


@pytest.mark.parametrize("name", ["hw_note.py", "hw_gui.py"])
def test_file_khoi_chay_o_thu_muc_goc_chi_la_lop_mong(name):
    src = (PKG.parent / name).read_text(encoding="utf-8")
    assert len(src.splitlines()) < 40, "%s phải chỉ là lối vào mỏng, logic để trong chuviettay/" % name


def test_view_khong_truy_cap_truc_tiep_ctl_bank():
    """Tầng view/ không được truy cập trực tiếp ctl.bank (phải qua các method/property được expose)."""
    bad = []
    for f in py_files("view"):
        tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "bank":
                bad.append("%s:%d truy cập .bank" % (f.relative_to(PKG.parent), node.lineno))
    assert not bad, "View không được truy cập trực tiếp ctl.bank:\n  " + "\n  ".join(bad)


def test_document_ir_hoan_toan_doc_lap():
    """Tầng document/ (IR) là cấu trúc dữ liệu thuần, không phụ thuộc controller, view, model hay layout."""
    bad = violations(
        py_files("document"),
        ["chuviettay.controller", "chuviettay.model", "chuviettay.layout", "chuviettay.importer"] + UI_AND_ENTRY,
    )
    assert not bad, "Document IR phải hoàn toàn độc lập:\n  " + "\n  ".join(bad)


def test_math_package_doc_lap_voi_giao_dien_va_model():
    """Tầng math/ (AST, parser) không phụ thuộc model, controller hay view."""
    bad = violations(
        py_files("math"),
        ["chuviettay.controller", "chuviettay.model", "chuviettay.layout", "chuviettay.importer"] + UI_AND_ENTRY,
    )
    assert not bad, "Math package phải hoàn toàn độc lập với UI/Model/Controller:\n  " + "\n  ".join(bad)


def test_importer_khong_phu_thuoc_view_hay_cli():
    """Tầng importer/ không được phụ thuộc vào giao diện (view) hay CLI."""
    bad = violations(py_files("importer"), ["chuviettay.controller"] + UI_AND_ENTRY)
    assert not bad, "Importer không được phụ thuộc View/CLI/Controller:\n  " + "\n  ".join(bad)


def test_layout_engine_khong_phu_thuoc_view_cli_controller_hay_importer():
    """Tầng layout/ không được phụ thuộc vào giao diện người dùng, CLI, Controller hay các bộ importer."""
    bad = violations(py_files("layout"), ["chuviettay.controller", "chuviettay.importer"] + UI_AND_ENTRY)
    assert not bad, "Layout Engine không được phụ thuộc View/CLI/Controller/Importer:\n  " + "\n  ".join(bad)
