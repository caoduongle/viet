#!/usr/bin/env python3
"""Build script đóng gói Web Client tĩnh (Static Web App) cho ChuVietTay.

Thực hiện:
  1. Kiểm tra môi trường runtime Pyodide từ node_modules/pyodide/.
  2. Nạp/tải và xác minh mã băm SHA-256 các vendor wheel từ scripts/vendor_lock.json.
  3. Lọc sạch mã nguồn chuviettay: CHỈ lấy các module lõi và bridge cần thiết;
     loại bỏ hoàn toàn view/, gui.py, cli.py, fidelity/, test files, kho cá nhân.
  4. Đóng gói mã nguồn sạch thành chuviettay.zip đặt trong pyodide/.
  5. Sao chép frontend (HTML, CSS, JS, manifest, sw.js).
  6. Sinh version.json ghi nhận metadata phiên bản (pyodide_version đọc từ package.json).
  7. Sinh sw.js động với CACHE_NAME băm 12 ký tự và PRECACHE_URLS chính xác.
  8. Kiểm tra an toàn phân phối (Dist Sanity Check): cấm tuyệt đối file kho *.json.gz hoặc mã cấm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WEBAPP_SRC = ROOT_DIR / "webapp"
DEFAULT_DIST_DIR = ROOT_DIR / "webapp" / "dist"
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


def require_pyodide_runtime() -> None:
    """Kiểm tra sự tồn tại của runtime Pyodide trong node_modules trước khi tiến hành."""
    pkg_json = NODE_MODULES_PYODIDE / "package.json"
    wasm_file = NODE_MODULES_PYODIDE / "pyodide.asm.wasm"
    if not pkg_json.exists() or not wasm_file.exists():
        sys.exit(
            "Lỗi: Không tìm thấy node_modules/pyodide hợp lệ.\n"
            "Hãy chạy lệnh `npm ci` trước khi thực hiện build web client!"
        )


def prepare_dist_dir(dist_dir: Path) -> None:
    """Kiểm tra an toàn đường dẫn và dọn sạch thư mục dist."""
    resolved_dist = dist_dir.resolve()
    resolved_root = ROOT_DIR.resolve()

    # Kiểm tra các điều kiện đường dẫn nguy hiểm
    if resolved_dist == resolved_root:
        sys.exit(f"Lỗi an toàn: Thư mục đích ({resolved_dist}) trùng với thư mục gốc của repository!")

    # dist_dir là tổ tiên của repo nghĩa là dist_dir nằm trong resolved_root.parents (ví dụ D:\viet hoặc D:\)
    if resolved_dist in resolved_root.parents:
        sys.exit(f"Lỗi an toàn: Thư mục đích ({resolved_dist}) là tổ tiên của repository!")

    if resolved_dist.parent == resolved_dist:
        sys.exit(f"Lỗi an toàn: Thư mục đích ({resolved_dist}) là thư mục gốc của ổ đĩa/hệ thống tập tin!")

    resolved_webapp = (ROOT_DIR / "webapp").resolve()
    resolved_default_dist = DEFAULT_DIST_DIR.resolve()
    if resolved_dist.is_relative_to(resolved_webapp) and resolved_dist != resolved_default_dist:
        sys.exit(
            f"Lỗi an toàn: Thư mục đích ({resolved_dist}) nằm trong webapp/ nhưng không phải là webapp/dist!"
        )

    if resolved_dist.exists():
        shutil.rmtree(resolved_dist)
    resolved_dist.mkdir(parents=True, exist_ok=True)


def ensure_vendor_wheels(dist_wheels_dir: Path) -> None:
    """Tải / copy các vendor wheels theo scripts/vendor_lock.json với retry timeout."""
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

        # 2. Nếu chưa có trong cache, tải từ URL có retry (tối đa 3 lần cho lỗi mạng/5xx)
        if not cached_file.exists() or sha256_file(cached_file) != expected_sha:
            print(f"[build_web] Tải {pkg_name} ({file_name})...")
            url = meta["url"]
            max_retries = 3
            download_success = False
            last_err = None

            for attempt in range(1, max_retries + 1):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=60) as resp, open(cached_file, "wb") as out_f:
                        shutil.copyfileobj(resp, out_f)
                    download_success = True
                    break
                except urllib.error.HTTPError as http_err:
                    last_err = http_err
                    # 4xx: lỗi client (404, 403...) -> không retry
                    if 400 <= http_err.code < 500:
                        raise RuntimeError(f"Lỗi HTTP {http_err.code} khi tải {file_name}: {http_err}") from http_err
                    # 5xx: lỗi server -> retry
                    print(f"[build_web] Thử lại ({attempt}/{max_retries}) sau lỗi HTTP {http_err.code}...")
                    time.sleep(2)
                except (urllib.error.URLError, TimeoutError, OSError) as net_err:
                    last_err = net_err
                    print(f"[build_web] Thử lại ({attempt}/{max_retries}) sau lỗi mạng: {net_err}...")
                    time.sleep(2)

            if not download_success:
                raise RuntimeError(f"Không thể tải wheel {file_name} sau {max_retries} lần thử: {last_err}")

        # 3. Kiểm tra sha256
        actual_sha = sha256_file(cached_file)
        if actual_sha != expected_sha:
            raise ValueError(f"Sai mã băm cho {file_name}: kỳ vọng {expected_sha}, nhận được {actual_sha}")

        # 4. Sao chép vào dist
        shutil.copy2(cached_file, dest_file)
        print(f"[build_web] Đã chuẩn bị wheel {file_name} ({meta['stage']})")


def copy_pyodide_runtime(dist_pyodide_dir: Path) -> None:
    """Sao chép các file runtime Pyodide từ node_modules/pyodide/."""
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


def copy_frontend_assets(dist_dir: Path) -> None:
    """Sao chép các file tĩnh giao diện từ webapp/ sang dist_dir."""
    if not WEBAPP_SRC.exists():
        return

    for item in WEBAPP_SRC.iterdir():
        if item.name == "dist":
            continue
        dest = dist_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    print("[build_web] Đã sao chép các file tĩnh frontend.")


def generate_version_json(dist_dir: Path) -> None:
    """Tạo file version.json ghi nhận thông tin build (đọc pyodide_version từ package.json)."""
    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT_DIR),
            text=True,
        ).strip()
    except Exception:
        pass

    pyodide_ver = "314.0.7"
    pkg_json_path = NODE_MODULES_PYODIDE / "package.json"
    if pkg_json_path.exists():
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                pyodide_pkg = json.load(f)
                pyodide_ver = pyodide_pkg.get("version", pyodide_ver)
        except Exception:
            pass

    version_info = {
        "version": "1.0.0",
        "git_commit": git_commit,
        "pyodide_version": pyodide_ver,
    }
    with open(dist_dir / "version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=2)
    print(f"[build_web] Đã sinh version.json (Pyodide v{pyodide_ver}).")


def generate_sw_js(dist_dir: Path) -> None:
    """Tạo file sw.js động với CACHE_NAME có băm nội dung 12 ký tự và danh sách PRECACHE_URLS thực tế."""
    sw_template_path = WEBAPP_SRC / "sw.js"
    if not sw_template_path.exists():
        return

    template_content = sw_template_path.read_text(encoding="utf-8")

    # 1. Thu thập tất cả các tệp trong dist_dir (trừ sw.js) và tính băm tổng hợp
    files_to_cache: list[tuple[str, str]] = []  # (rel_url, file_sha)
    hasher = hashlib.sha256()

    for root, _, files in os.walk(dist_dir):
        for f in sorted(files):
            if f == "sw.js":
                continue
            fpath = Path(root) / f
            rel_path = fpath.relative_to(dist_dir).as_posix()
            rel_url = f"./{rel_path}"
            f_hash = sha256_file(fpath)
            files_to_cache.append((rel_url, f_hash))
            hasher.update(f_hash.encode("utf-8"))

    content_hash_12 = hasher.hexdigest()[:12]
    cache_name = f"chuviettay-cache-{content_hash_12}"

    # Danh sách precache gồm gốc trang web và các tệp thực tế
    precache_list = ["./"]
    for url, _ in files_to_cache:
        precache_list.append(url)

    precache_json = json.dumps(precache_list, indent=2)

    # Thay thế CACHE_NAME và PRECACHE_URLS trong template
    # Pattern: const CACHE_NAME = "...";
    import re

    new_content = re.sub(
        r'const\s+CACHE_NAME\s*=\s*"[^"]+";',
        f'const CACHE_NAME = "{cache_name}";',
        template_content,
    )
    new_content = re.sub(
        r'const\s+PRECACHE_URLS\s*=\s*\[[\s\S]*?\];',
        f"const PRECACHE_URLS = {precache_json};",
        new_content,
    )

    out_sw = dist_dir / "sw.js"
    out_sw.write_text(new_content, encoding="utf-8")
    print(f"[build_web] Đã sinh sw.js động với {cache_name} ({len(precache_list)} URL precached).")


def sanity_check_dist(dist_dir: Path) -> None:
    """Quét toàn bộ thư mục dist để đảm bảo không lọt dữ liệu nhạy cảm hoặc mã cấm."""
    violations = []
    for root, dirs, files in os.walk(dist_dir):
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
        shutil.rmtree(dist_dir, ignore_errors=True)
        sys.exit(1)

    print("[build_web] Kiểm tra dist sạch (Sanity Check): PASS 100%!")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Đóng gói Static Web Client cho ChuVietTay")
    parser.add_argument(
        "--dist",
        type=Path,
        default=DEFAULT_DIST_DIR,
        help="Thư mục xuất bản dist (mặc định: webapp/dist)",
    )
    args = parser.parse_args(argv)
    dist_dir = args.dist.resolve()

    print(f"================ BẮT ĐẦU BUILD STATIC WEB CLIENT -> {dist_dir} ================")
    require_pyodide_runtime()
    prepare_dist_dir(dist_dir)

    dist_pyodide = dist_dir / "pyodide"
    dist_wheels = dist_pyodide / "wheels"

    copy_pyodide_runtime(dist_pyodide)
    ensure_vendor_wheels(dist_wheels)
    package_clean_core(dist_pyodide)
    copy_frontend_assets(dist_dir)
    generate_version_json(dist_dir)
    generate_sw_js(dist_dir)
    sanity_check_dist(dist_dir)
    print("================ BUILD HOÀN TẤT THÀNH CÔNG ================")


if __name__ == "__main__":
    main()
