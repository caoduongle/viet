"""Kiểm thử tính toàn vẹn và sạch sẽ của bản build tĩnh (scripts/build_web.py)."""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "webapp" / "dist"


def test_build_web_output_integrity():
    # Chạy build script
    res = subprocess.run(
        [sys.executable, str(ROOT_DIR / "scripts" / "build_web.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode == 0, f"build_web.py thất bại:\n{res.stderr}"

    # Kiểm tra version.json
    v_file = DIST_DIR / "version.json"
    assert v_file.exists()
    v_data = json.loads(v_file.read_text(encoding="utf-8"))
    assert "version" in v_data
    assert "pyodide_version" in v_data
    assert v_data["pyodide_version"] == "314.0.7"

    # Kiểm tra runtime Pyodide
    pyodide_dir = DIST_DIR / "pyodide"
    assert (pyodide_dir / "pyodide.js").exists()
    assert (pyodide_dir / "pyodide.asm.wasm").exists()
    assert (pyodide_dir / "python_stdlib.zip").exists()

    # Kiểm tra vendor wheels
    wheels_dir = pyodide_dir / "wheels"
    assert wheels_dir.exists()
    wheels = [f.name for f in wheels_dir.glob("*.whl")]
    assert any("markdown_it_py" in w for w in wheels)
    assert any("mdit_py_plugins" in w for w in wheels)
    assert any("mdurl" in w for w in wheels)
    assert any("python_docx" in w for w in wheels)
    assert any("lxml" in w for w in wheels)

    # Kiểm tra chuviettay.zip không chứa mã cấm
    zip_path = pyodide_dir / "chuviettay.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "chuviettay/browser/bridge.py" in namelist
        assert "chuviettay/controller/app_controller.py" in namelist
        assert "chuviettay/controller/teach_geometry.py" in namelist
        assert "chuviettay/model/bank.py" in namelist

        # Cấm view, gui, cli, fidelity
        for name in namelist:
            assert not name.startswith("chuviettay/view"), f"Chứa view: {name}"
            assert not name.startswith("chuviettay/fidelity"), f"Chứa fidelity: {name}"
            assert not name.endswith("gui.py"), f"Chứa gui.py: {name}"
            assert not name.endswith("cli.py"), f"Chứa cli.py: {name}"

    # Quét sạch dist: không file kho mẫu *.json.gz, không thư mục test
    for f in DIST_DIR.rglob("*"):
        assert not f.name.endswith(".json.gz"), f"File kho mẫu bị lọt vào dist: {f}"
        assert f.name != "tests", f"Thư mục tests bị lọt vào dist: {f}"
        assert f.name != "specs", f"Thư mục specs bị lọt vào dist: {f}"
