"""Kiểm thử tính toàn vẹn và sạch sẽ của bản build tĩnh (scripts/build_web.py)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
REAL_DIST_DIR = ROOT_DIR / "webapp" / "dist"
PYODIDE_EXISTS = (ROOT_DIR / "node_modules" / "pyodide" / "package.json").exists()
REQUIRE_WEB_BUILD = os.environ.get("REQUIRE_WEB_BUILD") == "1"

pytestmark = [
    pytest.mark.web,
    pytest.mark.timeout(300),
]


def check_pyodide_available():
    """Kiểm tra sự tồn tại của node_modules/pyodide; fail nếu REQUIRE_WEB_BUILD=1, skip nếu không."""
    pyodide_exists = (ROOT_DIR / "node_modules" / "pyodide" / "package.json").exists()
    require_web_build = os.environ.get("REQUIRE_WEB_BUILD") == "1"
    if not pyodide_exists:
        if require_web_build:
            pytest.fail("REQUIRE_WEB_BUILD=1 nhưng không tìm thấy node_modules/pyodide. Hãy chạy 'npm ci'!")
        else:
            pytest.skip("Bỏ qua test web vì chưa cài node_modules/pyodide (chạy npm ci để kích hoạt).")


@pytest.fixture(scope="module")
def built_dist(tmp_path_factory) -> Path:
    """Build bản web vào thư mục tạm bằng --dist, đảm bảo không đụng đến webapp/dist thật."""
    check_pyodide_available()

    tmp_dist = tmp_path_factory.mktemp("web_dist")

    # Ghi nhận mtime của version.json thật (nếu có) để assert không bị đụng chạm
    real_v_file = REAL_DIST_DIR / "version.json"
    real_mtime_before = real_v_file.stat().st_mtime if real_v_file.exists() else None

    build_script = ROOT_DIR / "scripts" / "build_web.py"
    res = subprocess.run(
        [sys.executable, str(build_script), "--dist", str(tmp_dist)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert res.returncode == 0, f"build_web.py thất bại:\nSTDERR:\n{res.stderr}\nSTDOUT:\n{res.stdout}"

    # Khẳng định webapp/dist không bị đụng chạm
    if real_mtime_before is not None:
        assert real_v_file.stat().st_mtime == real_mtime_before, "webapp/dist/version.json bị sửa đổi bởi test!"

    return tmp_dist


def test_version_json_matches_package_json(built_dist: Path):
    """version.json phải khớp với pyodide trong package.json."""
    v_file = built_dist / "version.json"
    assert v_file.exists()
    v_data = json.loads(v_file.read_text(encoding="utf-8"))
    assert "version" in v_data
    assert "pyodide_version" in v_data

    pkg_json_file = ROOT_DIR / "package.json"
    if pkg_json_file.exists():
        pkg_data = json.loads(pkg_json_file.read_text(encoding="utf-8"))
        expected_pyodide = pkg_data.get("devDependencies", {}).get("pyodide")
        if expected_pyodide:
            assert v_data["pyodide_version"] == expected_pyodide


def test_runtime_and_wheels_integrity(built_dist: Path):
    """Kiểm tra runtime Pyodide và các vendor wheels bắt buộc."""
    pyodide_dir = built_dist / "pyodide"
    assert (pyodide_dir / "pyodide.js").exists()
    assert (pyodide_dir / "pyodide.asm.wasm").exists()
    assert (pyodide_dir / "python_stdlib.zip").exists()

    wheels_dir = pyodide_dir / "wheels"
    assert wheels_dir.exists()
    wheels = [f.name for f in wheels_dir.glob("*.whl")]
    assert any("markdown_it_py" in w for w in wheels)
    assert any("mdit_py_plugins" in w for w in wheels)
    assert any("mdurl" in w for w in wheels)
    assert any("python_docx" in w for w in wheels)
    assert any("typing_extensions" in w for w in wheels)
    assert any("lxml" in w for w in wheels)


def test_clean_chuviettay_zip(built_dist: Path):
    """chuviettay.zip chỉ chứa core, cấm view, gui, cli, fidelity."""
    zip_path = built_dist / "pyodide" / "chuviettay.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "chuviettay/browser/bridge.py" in namelist
        assert "chuviettay/controller/app_controller.py" in namelist
        assert "chuviettay/controller/teach_geometry.py" in namelist
        assert "chuviettay/model/bank.py" in namelist

        for name in namelist:
            assert not name.startswith("chuviettay/view"), f"Chứa view: {name}"
            assert not name.startswith("chuviettay/fidelity"), f"Chứa fidelity: {name}"
            assert not name.endswith("gui.py"), f"Chứa gui.py: {name}"
            assert not name.endswith("cli.py"), f"Chứa cli.py: {name}"


def test_dist_forbidden_files_clean(built_dist: Path):
    """dist sạch tuyệt đối không chứa file cấm, kho cá nhân, tests hay specs."""
    for f in built_dist.rglob("*"):
        assert not f.name.endswith(".json.gz"), f"File kho mẫu bị lọt vào dist: {f}"
        assert f.name != "tests", f"Thư mục tests bị lọt vào dist: {f}"
        assert f.name != "specs", f"Thư mục specs bị lọt vào dist: {f}"
        assert f.name != "docs", f"Thư mục docs bị lọt vào dist: {f}"
        assert f.name != "__pycache__", f"__pycache__ bị lọt vào dist: {f}"


def test_prepare_dist_dir_safety(monkeypatch, tmp_path: Path):
    """Kiểm tra hàm prepare_dist_dir từ chối an toàn các đường dẫn nguy hiểm."""
    from scripts import build_web

    # Giả lập môi trường test trong tmp_path
    mock_root = tmp_path / "mock_repo"
    mock_webapp = mock_root / "webapp"
    mock_default_dist = mock_webapp / "dist"
    mock_webapp.mkdir(parents=True)

    monkeypatch.setattr(build_web, "ROOT_DIR", mock_root)
    monkeypatch.setattr(build_web, "DEFAULT_DIST_DIR", mock_default_dist)

    # 1. Trùng ROOT_DIR -> SystemExit
    with pytest.raises(SystemExit) as exc:
        build_web.prepare_dist_dir(mock_root)
    assert "trùng với thư mục gốc" in str(exc.value)

    # 2. Tổ tiên của ROOT_DIR -> SystemExit
    with pytest.raises(SystemExit) as exc:
        build_web.prepare_dist_dir(tmp_path)
    assert "là tổ tiên" in str(exc.value)

    # 3. Nằm trong webapp nhưng không phải webapp/dist -> SystemExit
    unsafe_sub = mock_webapp / "js"
    unsafe_sub.mkdir()
    with pytest.raises(SystemExit) as exc:
        build_web.prepare_dist_dir(unsafe_sub)
    assert "nằm trong webapp/" in str(exc.value)

    # 4. Hợp lệ: mock_default_dist -> thành công
    build_web.prepare_dist_dir(mock_default_dist)
    assert mock_default_dist.exists()
