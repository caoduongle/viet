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


def test_sw_precache_and_lazy_urls_separation(built_dist: Path):
    """sw.js phân tách đúng PRECACHE_URLS (core) và OPTIONAL_LAZY_URLS (lazy wheels) và có băm 12 ký tự."""
    sw_file = built_dist / "sw.js"
    assert sw_file.exists()
    content = sw_file.read_text(encoding="utf-8")

    import re

    cache_match = re.search(r'const\s+CACHE_NAME\s*=\s*"([^"]+)";', content)
    assert cache_match, "Không tìm thấy CACHE_NAME trong sw.js"
    cache_name = cache_match.group(1)
    assert re.match(r"^chuviettay-cache-[a-f0-9]{12}$", cache_name), f"CACHE_NAME sai định dạng băm: {cache_name}"

    precache_match = re.search(r"const\s+PRECACHE_URLS\s*=\s*(\[[\s\S]*?\]);", content)
    assert precache_match, "Không tìm thấy PRECACHE_URLS trong sw.js"
    precache_urls = json.loads(precache_match.group(1))

    lazy_match = re.search(r"const\s+OPTIONAL_LAZY_URLS\s*=\s*(\[[\s\S]*?\]);", content)
    assert lazy_match, "Không tìm thấy OPTIONAL_LAZY_URLS trong sw.js"
    lazy_urls = json.loads(lazy_match.group(1))

    # Core files bắt buộc có trong PRECACHE_URLS
    assert "./" in precache_urls
    assert any("pyodide.asm.wasm" in u for u in precache_urls)
    assert any("python_stdlib.zip" in u for u in precache_urls)
    assert any("chuviettay.zip" in u for u in precache_urls)

    # Startup wheels phải nằm trong PRECACHE_URLS
    assert any("markdown_it_py" in u for u in precache_urls)
    assert any("mdit_py_plugins" in u for u in precache_urls)
    assert any("mdurl" in u for u in precache_urls)

    # Lazy wheels (docx, lxml, typing_extensions) KHÔNG được nằm trong PRECACHE_URLS
    assert not any("python_docx" in u for u in precache_urls), "python_docx không được nằm trong PRECACHE_URLS"
    assert not any("lxml" in u for u in precache_urls), "lxml không được nằm trong PRECACHE_URLS"
    assert not any("typing_extensions" in u for u in precache_urls), "typing_extensions không được nằm trong PRECACHE_URLS"

    # Lazy wheels PHẢI nằm trong OPTIONAL_LAZY_URLS
    assert any("python_docx" in u for u in lazy_urls), "python_docx phải nằm trong OPTIONAL_LAZY_URLS"
    assert any("lxml" in u for u in lazy_urls), "lxml phải nằm trong OPTIONAL_LAZY_URLS"
    assert any("typing_extensions" in u for u in lazy_urls), "typing_extensions phải nằm trong OPTIONAL_LAZY_URLS"

    # Hai tập URL này phải rời nhau
    overlap = set(precache_urls).intersection(set(lazy_urls))
    assert len(overlap) == 0, f"PRECACHE_URLS và OPTIONAL_LAZY_URLS bị trùng lặp: {overlap}"

    # [055-parser-table-build-hardening] Marker an toàn và tệp ẩn KHÔNG được nằm trong sw.js hay PRECACHE_URLS
    from scripts.build_web import BUILD_MARKER_NAME
    assert BUILD_MARKER_NAME not in content, f"{BUILD_MARKER_NAME} bị lọt vào nội dung sw.js"
    assert not any(BUILD_MARKER_NAME in u for u in precache_urls), f"{BUILD_MARKER_NAME} bị lọt vào PRECACHE_URLS"
    assert not any("/." in u for u in precache_urls), "Tệp ẩn bị lọt vào PRECACHE_URLS"


def test_generate_sw_js_excludes_hidden_directories(tmp_path: Path):
    """[056] Kiểm tra generate_sw_js cắt tỉa thư mục ẩn (.internal/) không đưa vào PRECACHE_URLS."""
    from scripts import build_web

    dist = tmp_path / "dist_with_hidden"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>Test</h1>", encoding="utf-8")

    # Tạo thư mục ẩn chứa tệp
    hidden_dir = dist / ".internal"
    hidden_dir.mkdir()
    (hidden_dir / "secret.js").write_text("console.log('secret');", encoding="utf-8")

    build_web.generate_sw_js(dist)
    sw_content = (dist / "sw.js").read_text(encoding="utf-8")

    import json
    import re
    m = re.search(r"const\s+PRECACHE_URLS\s*=\s*(\[[^\]]+\]);", sw_content)
    assert m, "Không tìm thấy PRECACHE_URLS trong sw.js"
    precache_urls = json.loads(m.group(1))

    assert not any("secret.js" in u for u in precache_urls), "Tệp trong thư mục ẩn bị lọt vào PRECACHE_URLS"
    assert not any(".internal" in u for u in precache_urls), "Thư mục ẩn bị lọt vào PRECACHE_URLS"
    assert not any("/." in u for u in precache_urls)



def test_deterministic_sw_cache_and_path_sensitivity(tmp_path: Path):
    """[054-repo-audit-hardening] Kiểm tra tính tái lập của khóa cache Service Worker và độ nhạy khi đổi đường dẫn."""
    from scripts import build_web

    dist1 = tmp_path / "dist1"
    dist1.mkdir()
    (dist1 / "a.js").write_text("console.log('hello');", encoding="utf-8")
    (dist1 / "b.css").write_text("body { color: red; }", encoding="utf-8")

    # Giả lập template sw.js
    sw_template = build_web.WEBAPP_SRC / "sw.js"
    assert sw_template.exists()

    build_web.generate_sw_js(dist1)
    sw1 = (dist1 / "sw.js").read_text(encoding="utf-8")
    import re
    match1 = re.search(r'const\s+CACHE_NAME\s*=\s*"([^"]+)";', sw1)
    assert match1
    cache1 = match1.group(1)

    # Chạy lần 2 trên cùng cấu trúc -> hash phải trùng khớp 100%
    build_web.generate_sw_js(dist1)
    sw2 = (dist1 / "sw.js").read_text(encoding="utf-8")
    match2 = re.search(r'const\s+CACHE_NAME\s*=\s*"([^"]+)";', sw2)
    assert match2
    assert match2.group(1) == cache1, "Cùng dữ liệu đầu vào phải cho ra cùng CACHE_NAME"

    # Đổi đường dẫn tệp (đổi tên b.css -> sub/c.css với nội dung giữ nguyên)
    (dist1 / "b.css").unlink()
    sub_dir = dist1 / "sub"
    sub_dir.mkdir()
    (sub_dir / "c.css").write_text("body { color: red; }", encoding="utf-8")

    build_web.generate_sw_js(dist1)
    sw3 = (dist1 / "sw.js").read_text(encoding="utf-8")
    match3 = re.search(r'const\s+CACHE_NAME\s*=\s*"([^"]+)";', sw3)
    assert match3
    assert match3.group(1) != cache1, "Đổi đường dẫn tệp phải làm thay đổi CACHE_NAME"


def test_prepare_dist_dir_external_safety(monkeypatch, tmp_path: Path):
    """[054-repo-audit-hardening] Kiểm tra bảo vệ thư mục ngoài không rỗng khi thiếu --force-clean."""
    from scripts import build_web

    mock_root = tmp_path / "repo"
    mock_root.mkdir()
    mock_webapp = mock_root / "webapp"
    mock_default_dist = mock_webapp / "dist"
    mock_default_dist.mkdir(parents=True)

    monkeypatch.setattr(build_web, "ROOT_DIR", mock_root)
    monkeypatch.setattr(build_web, "DEFAULT_DIST_DIR", mock_default_dist)

    external_dir = tmp_path / "user_important_data"
    external_dir.mkdir()
    secret_file = external_dir / "important_document.txt"
    secret_file.write_text("Dữ liệu quan trọng của người dùng", encoding="utf-8")

    # 1. Thư mục ngoài có dữ liệu, không có force_clean -> Chặn và ném SystemExit
    with pytest.raises(SystemExit) as exc:
        build_web.prepare_dist_dir(external_dir, force_clean=False)
    assert "nằm ngoài phạm vi mặc định" in str(exc.value)
    assert secret_file.exists(), "Tệp quan trọng của người dùng không được phép bị xóa"

    # 2. Thư mục ngoài có dữ liệu nhưng có cờ force_clean=True -> Cho phép dọn dẹp
    build_web.prepare_dist_dir(external_dir, force_clean=True)
    assert external_dir.exists()
    assert not secret_file.exists(), "Tệp cũ đã được dọn sạch khi có force_clean"
    assert not (external_dir / build_web.BUILD_MARKER_NAME).exists(), "Thư mục xuất xưởng sạch, không tạo marker nội bộ"

    # 3. Sau khi build, người dùng lưu thêm tệp mới vào external_dir
    user_new_file = external_dir / "user_new_document.pdf"
    user_new_file.write_text("Tài liệu mới của người dùng", encoding="utf-8")

    # Lần build tiếp theo vào external_dir có chứa dữ liệu mà không có force_clean -> BẮT BUỘC chặn và ném SystemExit
    with pytest.raises(SystemExit) as exc2:
        build_web.prepare_dist_dir(external_dir, force_clean=False)
    assert "nằm ngoài phạm vi mặc định" in str(exc2.value)
    assert user_new_file.exists(), "Tệp mới của người dùng không bao giờ bị xóa chỉ vì thư mục từng được build trước đó"

    # 4. Khi external_dir hoàn toàn rỗng -> Cho phép chuẩn bị build mà không cần force_clean
    user_new_file.unlink()
    assert not any(external_dir.iterdir())
    build_web.prepare_dist_dir(external_dir, force_clean=False)
    assert external_dir.exists()
