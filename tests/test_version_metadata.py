"""Kiểm thử tính đồng bộ và toàn vẹn của metadata phiên bản (Contract CTR-039-RELEASE-METADATA)."""
from __future__ import annotations

import json
from pathlib import Path

import chuviettay


ROOT_DIR = Path(__file__).resolve().parent.parent


def test_version_consistency_pyproject():
    """pyproject.toml phải khai báo số phiên bản khớp 100% với chuviettay.__version__."""
    pyproject_path = ROOT_DIR / "pyproject.toml"
    assert pyproject_path.exists()

    content = pyproject_path.read_text(encoding="utf-8")
    expected_line = f'version = "{chuviettay.__version__}"'
    assert expected_line in content, (
        f"pyproject.toml không chứa phiên bản '{chuviettay.__version__}' của chuviettay!"
    )


def test_version_consistency_package_json():
    """package.json của web client phải khai báo số phiên bản khớp 100% với chuviettay.__version__."""
    pkg_json_path = ROOT_DIR / "package.json"
    assert pkg_json_path.exists()

    with open(pkg_json_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    assert pkg.get("version") == chuviettay.__version__, (
        f"package.json ghi phiên bản '{pkg.get('version')}', lệch với chuviettay.__version__ ('{chuviettay.__version__}')!"
    )


def test_version_changelog_latest_release():
    """CHANGELOG.md phải có ghi nhận mục phát hành cho phiên bản chuviettay.__version__."""
    changelog_path = ROOT_DIR / "CHANGELOG.md"
    assert changelog_path.exists()

    content = changelog_path.read_text(encoding="utf-8")
    assert f"[{chuviettay.__version__}]" in content or f"## {chuviettay.__version__}" in content, (
        f"CHANGELOG.md chưa ghi nhận phiên bản '{chuviettay.__version__}'!"
    )


def test_build_web_generates_matching_version_json(tmp_path):
    """Hàm generate_version_json() trong build_web.py phải sinh trường 'version' khớp với chuviettay.__version__."""
    import importlib.util

    build_script = ROOT_DIR / "scripts" / "build_web.py"
    spec = importlib.util.spec_from_file_location("build_web", build_script)
    assert spec is not None and spec.loader is not None
    build_web = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_web)

    build_web.generate_version_json(tmp_path)

    version_json = tmp_path / "version.json"
    assert version_json.exists()

    with open(version_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("version") == chuviettay.__version__, (
        f"version.json do build sinh ra ghi '{data.get('version')}', không khớp với '{chuviettay.__version__}'!"
    )


def test_python_version_file_format():
    """[057-fix-ci-python-version] .python-version phải khai báo dòng minor '3.13' hợp lệ, không ghim bản vá vi mô."""
    import re

    py_ver_path = ROOT_DIR / ".python-version"
    assert py_ver_path.exists(), ".python-version không tồn tại!"

    content = py_ver_path.read_text(encoding="utf-8").strip()
    assert re.match(r"^\d+\.\d+$", content), (
        f".python-version phải có định dạng Major.Minor (ví dụ 3.13), nhưng nhận được: '{content}'"
    )
    assert content == "3.13", f".python-version phải là '3.13', nhưng nhận được '{content}'!"


def test_render_yaml_python_version():
    """[057-fix-ci-python-version] render.yaml phải đồng bộ biến PYTHON_VERSION khớp với .python-version ('3.13')."""
    import re

    render_yaml_path = ROOT_DIR / "render.yaml"
    py_ver_path = ROOT_DIR / ".python-version"
    assert render_yaml_path.exists(), "render.yaml không tồn tại!"
    assert py_ver_path.exists(), ".python-version không tồn tại!"

    expected_ver = py_ver_path.read_text(encoding="utf-8").strip()

    content = render_yaml_path.read_text(encoding="utf-8")
    assert "key: PYTHON_VERSION" in content
    m = re.search(r"key:\s*PYTHON_VERSION\s*\n\s*value:\s*([^\n\r]+)", content)
    assert m, "Không tìm thấy cấu hình value cho PYTHON_VERSION trong render.yaml!"
    val = m.group(1).strip().strip('"').strip("'")
    assert val == expected_ver, (
        f"PYTHON_VERSION trong render.yaml ({val}) phải khớp với .python-version ({expected_ver})!"
    )
    assert val == "3.13", f"PYTHON_VERSION trong render.yaml phải là '3.13', nhưng nhận được '{val}'!"
