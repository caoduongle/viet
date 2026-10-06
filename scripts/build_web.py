#!/usr/bin/env python3
"""Build script đóng gói Web Client tĩnh (Static Web App) cho ChuVietTay.

Thực hiện:
  1. Chuẩn bị runtime Pyodide từ node_modules/pyodide/.
  2. Nạp/tải và xác minh mã băm SHA-256 các vendor wheel từ scripts/vendor_lock.json.
  3. Lọc sạch mã nguồn chuviettay: CHỈ lấy các module lõi và bridge cần thiết;
     loại bỏ hoàn toàn view/, gui.py, cli.py, fidelity/, test files, kho cá nhân.
  4. Đóng gói mã nguồn sạch thành chuviettay.zip đặt trong webapp/dist/pyodide/.
  5. Sao chép frontend (HTML, CSS, JS, manifest, sw.js) sang webapp/dist/.
  6. Sinh version.json ghi nhận metadata phiên bản.
  7. Kiểm tra an toàn phân phối (Dist Sanity Check): cấm tuyệt đối file kho *.json.gz hoặc mã cấm.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WEBAPP_SRC = ROOT_DIR / "webapp"
DIST_DIR = ROOT_DIR / "webapp" / "dist"
VENDOR_LOCK_PATH = ROOT_DIR / "scripts" / "vendor_lock.json"
NODE_MODULES_PYODIDE = ROOT_DIR / "node_modules" / "pyodide"
CACHE_WHEEL_DIR = ROOT_DIR / ".cache" / "wheels"

# Các thư mục con của chuviettay được phép đưa vào bản web
ALLOWED_PACKAGES = {
    "browser",
    "controller",
    "model",
    "document",
    "importer",
    "layout",
    "math",
}

# Các file gốc của chuviettay được phép
ALLOWED_ROOT_FILES = {
    "__init__.py",
    "config.py",
    "paths.py",
}

# Các file / mẫu bị cấm tuyệt đối trong bản phân phối dist
FORBIDDEN_PATTERNS = [
    "*.json.gz",
    "*.pyc",
    "__pycache__",
    "tests",
    "specs",
    "docs",
    "view",
    "gui.py",
    "cli.py",
    "fidelity",
    "logging_setup.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def ensure_vendor_wheels(dist_wheels_dir: Path) -> None:
    """Tải / copy các vendor wheels theo scripts/vendor_lock.json."""
    dist_wheels_dir.mkdir(parents=True, exist_ok=True)
    CACHE_WHEEL_DIR.mkdir(parents=True, exist_ok=True)

    with open(VENDOR_LOCK_PATH, "r", encoding="utf-8") as f:
        lock_data = json.load(f)

    for pkg_name, meta in lock_data.get("packages", {}).items():
        file_name = meta["file_name"]
        expected_sha = meta["sha256"]
        cached_file = CACHE_WHEEL_DIR / file_name
        dest_file = dist_wheels_dir / file_name

        # 1. Kiểm tra trong node_modules/pyodide/ trước (ví dụ lxml wasm wheel)
        node_module_wheel = NODE_MODULES_PYODIDE / file_name
        if node_module_wheel.exists():
            shutil.copy2(node_module_wheel, cached_file)

        # 2. Nếu chưa có trong cache, tải từ URL
        if not cached_file.exists() or sha256_file(cached_file) != expected_sha:
            print(f"[build_web] Tải {pkg_name} ({file_name})...")
            req = urllib.request.Request(meta["url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(cached_file, "wb") as out_f:
                shutil.copyfileobj(resp, out_f)

        # 3. Kiểm tra sha256
        actual_sha = sha256_file(cached_file)
        if actual_sha != expected_sha:
            raise ValueError(f"Sai mã băm cho {file_name}: kỳ vọng {expected_sha}, nhận được {actual_sha}")

        # 4. Sao chép vào dist
        shutil.copy2(cached_file, dest_file)
        print(f"[build_web] Đã chuẩn bị wheel {file_name} ({meta['stage']})")


def copy_pyodide_runtime(dist_pyodide_dir: Path) -> None:
    """Sao chép các file runtime Pyodide từ node_modules/pyodide/."""
    if not NODE_MODULES_PYODIDE.exists():
        raise RuntimeError("Không tìm thấy node_modules/pyodide. Hãy chạy `npm install` trước khi build.")

    dist_pyodide_dir.mkdir(parents=True, exist_ok=True)

    files_to_copy = [
        "pyodide.js",
        "pyodide.js.map",
        "pyodide.mjs",
        "pyodide.mjs.map",
        "pyodide.asm.js",
        "pyodide.asm.mjs",
        "pyodide.asm.wasm",
        "python_stdlib.zip",
        "pyodide-lock.json",
    ]

    for fname in files_to_copy:
        src = NODE_MODULES_PYODIDE / fname
        if src.exists():
            shutil.copy2(src, dist_pyodide_dir / fname)
    print("[build_web] Đã sao chép runtime Pyodide.")


def package_clean_core(dist_pyodide_dir: Path) -> None:
    """Đóng gói mã nguồn chuviettay sạch thành chuviettay.zip."""
    pkg_src = ROOT_DIR / "chuviettay"
    zip_dest = dist_pyodide_dir / "chuviettay.zip"

    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pkg_src):
            rel_dir = Path(root).relative_to(pkg_src)
            top_level = rel_dir.parts[0] if rel_dir.parts else ""

            # Bỏ qua các thư mục không được phép hoặc thư mục tạm
            if top_level and top_level not in ALLOWED_PACKAGES:
                continue
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")

            for file in files:
                if not file.endswith(".py"):
                    continue
                if not rel_dir.parts and file not in ALLOWED_ROOT_FILES:
                    continue

                full_path = Path(root) / file
                archive_name = Path("chuviettay") / rel_dir / file
                zf.write(full_path, str(archive_name).replace("\\", "/"))

    print(f"[build_web] Đã đóng gói mã nguồn sạch vào {zip_dest.name} ({zip_dest.stat().st_size // 1024} KB)")


def copy_frontend_assets() -> None:
    """Sao chép các file tĩnh giao diện từ webapp/ sang webapp/dist/."""
    if not WEBAPP_SRC.exists():
        return

    for item in WEBAPP_SRC.iterdir():
        if item.name == "dist":
            continue
        dest = DIST_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    print("[build_web] Đã sao chép các file tĩnh frontend.")


def generate_version_json() -> None:
    """Tạo file version.json ghi nhận thông tin build."""
    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT_DIR),
            text=True,
        ).strip()
    except Exception:
        pass

    version_info = {
        "version": "1.0.0",
        "git_commit": git_commit,
        "pyodide_version": "314.0.7",
    }
    with open(DIST_DIR / "version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=2)
    print("[build_web] Đã sinh version.json.")


def sanity_check_dist() -> None:
    """Quét toàn bộ thư mục dist để đảm bảo không lọt dữ liệu nhạy cảm hoặc mã cấm."""
    violations = []
    for root, dirs, files in os.walk(DIST_DIR):
        for pattern in FORBIDDEN_PATTERNS:
            # Kiểm tra tên thư mục
            for d in list(dirs):
                if d == pattern or d == f"{pattern}/" or d.startswith(pattern):
                    violations.append(f"Thư mục cấm: {Path(root) / d}")
            # Kiểm tra file
            for f in files:
                if pattern.startswith("*") and f.endswith(pattern[1:]):
                    violations.append(f"File cấm: {Path(root) / f}")
                elif f == pattern:
                    violations.append(f"File cấm: {Path(root) / f}")

    if violations:
        print("[build_web] LỖI BẢO MẬT: Phát hiện file cấm trong bản build dist:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        shutil.rmtree(DIST_DIR, ignore_errors=True)
        sys.exit(1)

    print("[build_web] Kiểm tra dist sạch (Sanity Check): PASS 100%!")


def main() -> None:
    print("================ BẮT ĐẦU BUILD STATIC WEB CLIENT ================")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    dist_pyodide = DIST_DIR / "pyodide"
    dist_wheels = dist_pyodide / "wheels"

    copy_pyodide_runtime(dist_pyodide)
    ensure_vendor_wheels(dist_wheels)
    package_clean_core(dist_pyodide)
    copy_frontend_assets()
    generate_version_json()
    sanity_check_dist()
    print("================ BUILD HOÀN TẤT THÀNH CÔNG ================")


if __name__ == "__main__":
    main()
