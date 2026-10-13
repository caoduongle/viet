"""Quy tắc kiến trúc cho Web-only HandWrite (chuviettay).

Được kiểm tra TỰ ĐỘNG bằng AST phân tích import và lời gọi hàm.
Bảo đảm ranh giới kiến trúc:
- Tuyệt đối cấm tkinter trên toàn bộ repository (chuviettay, tests, scripts).
- Không tồn tại mã nguồn Desktop GUI hay CLI (chuviettay.view, gui.py, cli.py, hw_*.py, v.v.).
- Browser bridge chỉ giao tiếp qua Controller, không chạm Model hay Fidelity.
- Model, Controller, Layout, Document, Math hoàn toàn độc lập, không phụ thuộc Browser/Pyodide.
"""
import ast
import pathlib

PKG = pathlib.Path(__file__).resolve().parent.parent / "chuviettay"


def py_files(sub=None, recursive=False):
    base = PKG / sub if sub else PKG
    if not base.exists():
        return []
    pattern = "**/*.py" if recursive else "*.py"
    return sorted(base.glob(pattern))


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


def test_tuyet_doi_khong_import_tkinter_toan_repo():
    """Tất cả các tệp Python trong chuviettay/, tests/, scripts/ tuyệt đối KHÔNG được import tkinter."""
    repo_root = PKG.parent
    all_files = (
        sorted((repo_root / "chuviettay").glob("**/*.py"))
        + sorted((repo_root / "tests").glob("**/*.py"))
        + sorted((repo_root / "scripts").glob("**/*.py"))
    )
    bad = violations(all_files, ["tkinter"])
    assert not bad, "Tkinter đã bị loại bỏ hoàn toàn khỏi dự án:\n  " + "\n  ".join(bad)


def test_cac_module_va_tap_tin_desktop_cli_khong_con_ton_tai():
    """Xác nhận các thành phần Desktop Tkinter và CLI đã được dọn sạch hoàn toàn."""
    repo_root = PKG.parent
    deleted_paths = [
        repo_root / "chuviettay" / "view",
        repo_root / "chuviettay" / "gui.py",
        repo_root / "chuviettay" / "cli.py",
        repo_root / "chuviettay" / "__main__.py",
        repo_root / "hw_gui.py",
        repo_root / "hw_note.py",
        repo_root / "hw_gui.spec",
        repo_root / "build_windows.bat",
        repo_root / "build_linux_mac.sh",
        repo_root / "requirements-build.txt",
    ]
    for p in deleted_paths:
        assert not p.exists(), f"Đường dẫn đã loại bỏ nhưng vẫn tồn tại: {p}"


def test_model_khong_biet_gi_ve_controller_hay_ui():
    bad = violations(
        py_files("model"),
        ["tkinter", "argparse", "chuviettay.controller", "chuviettay.formatting"] + UI_AND_ENTRY,
    )
    assert not bad, "Model phải độc lập:\n  " + "\n  ".join(bad)


def test_controller_khong_biet_gi_ve_tkinter_argparse_view_cli():
    bad = violations(py_files("controller"), ["tkinter", "argparse"] + UI_AND_ENTRY)
    assert not bad, "Controller không được phụ thuộc giao diện Desktop/CLI:\n  " + "\n  ".join(bad)


def test_khong_print_hay_input_trong_cac_lop_loi():
    core_files = (
        py_files("model")
        + py_files("controller")
        + py_files("document", recursive=True)
        + py_files("importer", recursive=True)
        + py_files("layout", recursive=True)
        + py_files("math", recursive=True)
        + py_files("fidelity", recursive=True)
        + py_files("browser", recursive=True)
    )
    bad = print_calls(core_files)
    assert not bad, ("Các lớp lõi không được in ra màn hình; phải trả dữ liệu hoặc ghi log:\n  "
                     + "\n  ".join(bad))


def test_khong_dung_sys_exit_trong_cac_lop_loi():
    bad = []
    core_files = (
        py_files("model")
        + py_files("controller")
        + py_files("document", recursive=True)
        + py_files("importer", recursive=True)
        + py_files("layout", recursive=True)
        + py_files("math", recursive=True)
        + py_files("fidelity", recursive=True)
        + py_files("browser", recursive=True)
    )
    for f in core_files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Attribute) and node.attr == "exit"
                    and isinstance(node.value, ast.Name) and node.value.id == "sys"):
                bad.append("%s:%d sys.exit" % (f.relative_to(PKG.parent), node.lineno))
    assert not bad, "Lõi không được gọi sys.exit:\n  " + "\n  ".join(bad)


def test_browser_khong_phu_thuoc_model_fidelity_tkinter_argparse():
    """Tầng browser/ chỉ giao tiếp qua Controller, cấm chạm trực tiếp Model, Fidelity, Tkinter."""
    forbidden = [
        "chuviettay.model",
        "chuviettay.fidelity",
        "tkinter",
        "argparse",
    ] + UI_AND_ENTRY
    bad = violations(py_files("browser", recursive=True), forbidden)
    assert not bad, "Browser bridge phải độc lập với Model, Fidelity, Tkinter:\n  " + "\n  ".join(bad)


def test_model_va_controller_khong_phu_thuoc_browser_pyodide_js():
    """Model và Controller là lõi thuần túy, tuyệt đối không biết gì về Pyodide, JS hay Browser bridge."""
    forbidden = ["js", "pyodide", "pyodide_js", "chuviettay.browser"]
    bad = violations(py_files("model") + py_files("controller"), forbidden)
    assert not bad, "Model và Controller không được phụ thuộc vào môi trường Browser/Pyodide:\n  " + "\n  ".join(bad)


def test_fidelity_khong_phu_thuoc_view_hay_cli():
    """Tầng fidelity/ không được phụ thuộc vào giao diện (view), CLI hay tkinter."""
    bad = violations(py_files("fidelity"), ["tkinter"] + UI_AND_ENTRY)
    assert not bad, "Fidelity không được phụ thuộc View/CLI/Tkinter:\n  " + "\n  ".join(bad)


def test_document_ir_hoan_toan_doc_lap():
    """Tầng document/ (IR) là cấu trúc dữ liệu thuần, không phụ thuộc controller, model hay layout."""
    bad = violations(
        py_files("document"),
        ["chuviettay.controller", "chuviettay.model", "chuviettay.layout", "chuviettay.importer"] + UI_AND_ENTRY,
    )
    assert not bad, "Document IR phải hoàn toàn độc lập:\n  " + "\n  ".join(bad)


def test_math_package_doc_lap_voi_giao_dien_va_model():
    """Tầng math/ (AST, parser) không phụ thuộc model, controller hay layout."""
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
