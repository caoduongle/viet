"""Bài kiểm thử tự động (Smoke Test) cho kịch bản benchmark độc lập PUA.

[Feature 066 - US2]
Kiểm chứng khả năng thực thi từ đầu đến cuối của scripts/benchmark_pua_memory.py:
- Chạy với cờ --rounds 1 --json qua subprocess.
- Xác nhận mã thoát tiến trình bằng 0.
- Xác nhận đầu ra stdout là JSON hợp lệ.
- Kiểm tra tính đầy đủ của các trường cấu trúc và tính nhất quán của số lượt đo.
- Tuyệt đối không so sánh ngưỡng thời gian mili-giây tuyệt đối để tránh flaky trên CI.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_benchmark_pua_script_smoke_execution():
    """Xác nhận scripts/benchmark_pua_memory.py thực thi thành công từ CLI và xuất JSON chuẩn."""
    repo_root = Path(__file__).resolve().parent.parent
    script_path = repo_root / "scripts" / "benchmark_pua_memory.py"
    assert script_path.is_file(), f"Không tìm thấy kịch bản benchmark tại: {script_path}"

    cmd = [sys.executable, str(script_path), "--rounds", "1", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    assert proc.returncode == 0, f"Benchmark script thất bại với mã lỗi {proc.returncode}:\n{proc.stderr}"
    assert proc.stdout.strip().startswith("{"), "Đầu ra không bắt đầu bằng dấu ngoặc nhọn JSON"

    data = json.loads(proc.stdout)

    # 1. Kiểm tra 5 nhóm khóa bắt buộc
    for key in ("environment", "dataset_main", "results_main", "dataset_stress", "results_stress"):
        assert key in data, f"Thiếu trường bắt buộc '{key}' trong dữ liệu JSON"

    # 2. Kiểm tra siêu dữ liệu môi trường
    env = data["environment"]
    for env_key in ("python_version", "os_platform", "processor", "timestamp"):
        assert env_key in env, f"Thiếu trường môi trường '{env_key}'"
        assert len(str(env[env_key])) > 0

    # 3. Kiểm tra thông số tập dữ liệu chính (4 họ chữ Unicode và tính toán byte động)
    ds_main = data["dataset_main"]
    assert ds_main["rounds"] == 1
    assert ds_main["text_length"] == 510001
    assert ds_main["text_bytes"] > 1_000_000
    assert "MB" in ds_main["text_size_human"]
    assert len(ds_main["character_families"]) >= 4

    # 4. Kiểm tra danh sách kết quả chính (3 phương án)
    res_main = data["results_main"]
    assert len(res_main) == 3
    methods_main = [r["name"] for r in res_main]
    assert any("set(text)" in m for m in methods_main)
    assert any("findall" in m for m in methods_main)
    assert any("finditer" in m for m in methods_main)

    # 5. Kiểm tra kịch bản đối kháng (2 phương án, rounds nhất quán)
    ds_stress = data["dataset_stress"]
    assert ds_stress["rounds"] == 1
    assert ds_stress["text_length"] == 100000

    res_stress = data["results_stress"]
    assert len(res_stress) == 2
    methods_stress = [r["name"] for r in res_stress]
    assert any("findall" in m for m in methods_stress)
    assert any("finditer" in m for m in methods_stress)
