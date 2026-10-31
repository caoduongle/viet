"""Kịch bản thực nghiệm benchmark độc lập: Tái lập so sánh hiệu năng và bộ nhớ PUA.

Sử dụng 100% thư viện chuẩn của Python (re, tracemalloc, time, platform, sys, gc, argparse).
Đo đạc định lượng 3 phương án:
1. Baseline: set(text)
2. Regex: findall(text)
3. Triển khai thực tế: _PUA_RE.finditer(text) (MarkdownImporter._collect_used_pua_codepoints)

Hỗ trợ chạy từ CLI:
    python scripts/benchmark_pua_memory.py
    python scripts/benchmark_pua_memory.py --rounds 10
    python scripts/benchmark_pua_memory.py --json
"""

from __future__ import annotations

import argparse
from datetime import datetime
import gc
import json
from pathlib import Path
import platform
import sys
import time
import tracemalloc

# Tự động bootstrap sys.path để có thể chạy script độc lập từ bất kỳ vị trí nào
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chuviettay.importer.markdown_importer import (  # noqa: E402
    _FAKE_CLOSE_PUA_END,
    _FAKE_CLOSE_PUA_START,
    _PUA_RE,
    MarkdownImporter,
)


def get_environment_info() -> dict[str, str]:
    """Thu thập siêu dữ liệu môi trường thực thi."""
    bitness = "64-bit" if sys.maxsize > 2**32 else "32-bit"
    return {
        "python_version": f"{platform.python_version()} ({platform.python_implementation()}, {bitness})",
        "os_platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "processor": platform.processor() or "Unknown CPU",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def make_multilingual_text(target_length: int = 510000) -> str:
    """Sinh chuỗi văn bản mẫu đa ngữ kết hợp 4 hệ chữ Unicode thực sự và ký tự PUA U+E000:
    - CJK Unified Ideographs (chữ Hán/Nôm): U+4E00..U+6D3F (8.000 ký tự)
    - Cyrillic (bảng chữ cái Slav): U+0410..U+0603 (500 ký tự)
    - Greek & Coptic (chữ Hy Lạp toán học): U+0391..U+0584 (500 ký tự)
    - Mathematical Operators (toán tử toán học): U+2200..U+25E7 (1.000 ký tự)
    - Private Use Area: U+E000 (1 ký tự va chạm)
    """
    cjk = "".join(chr(0x4E00 + i) for i in range(8000))
    cyrillic = "".join(chr(0x0410 + i) for i in range(500))
    greek = "".join(chr(0x0391 + i) for i in range(500))
    math_syms = "".join(chr(0x2200 + i) for i in range(1000))
    alphabet = cjk + cyrillic + greek + math_syms

    repeat_count = (target_length // len(alphabet)) + 1
    return (alphabet * repeat_count)[:target_length] + chr(_FAKE_CLOSE_PUA_START)


def benchmark_method(
    name: str,
    fn,
    text: str,
    rounds: int,
) -> dict[str, float | int | str]:
    """Đo thời gian chạy trung bình và bộ nhớ đỉnh phân bổ của một hàm xử lý."""
    # 1. Đo bộ nhớ đỉnh bằng tracemalloc
    gc.collect()
    tracemalloc.start()
    try:
        res = fn(text)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    elements_found = len(res)

    # 2. Đo thời gian phân giải cao qua nhiều vòng lặp
    gc.collect()
    t0 = time.perf_counter()
    for _ in range(rounds):
        fn(text)
    total_time = time.perf_counter() - t0
    avg_time_ms = (total_time / rounds) * 1000.0

    return {
        "name": name,
        "avg_time_ms": round(avg_time_ms, 2),
        "peak_memory_kb": round(peak_bytes / 1024.0, 2),
        "elements": elements_found,
    }


def run_benchmarks(rounds: int = 5) -> dict[str, object]:
    """Thực thi đầy đủ các kịch bản benchmark."""
    env_info = get_environment_info()

    # --- Kịch bản 1: Văn bản đa ngữ lớn (4 hệ chữ Unicode, 1 PUA) ---
    text_multi = make_multilingual_text(target_length=510000)
    utf8_bytes = len(text_multi.encode("utf-8"))
    size_human = f"{utf8_bytes / (1024 * 1024):.2f} MB"

    # Các hàm đại diện
    def run_set_text(txt: str) -> set[int]:
        return {ord(c) for c in set(txt) if _FAKE_CLOSE_PUA_START <= ord(c) <= _FAKE_CLOSE_PUA_END}

    def run_regex_findall(txt: str) -> set[int]:
        return {ord(c) for c in _PUA_RE.findall(txt)}

    def run_regex_finditer(txt: str) -> set[int]:
        return MarkdownImporter._collect_used_pua_codepoints(txt)

    results_main = [
        benchmark_method("1. set(text)", run_set_text, text_multi, rounds),
        benchmark_method("2. regex findall()", run_regex_findall, text_multi, rounds),
        benchmark_method("3. regex finditer()", run_regex_finditer, text_multi, rounds),
    ]

    base_time = float(results_main[0]["avg_time_ms"])
    for r in results_main:
        t = float(r["avg_time_ms"])
        r["speedup_vs_baseline"] = f"{base_time / max(t, 0.01):.2f}x"

    # --- Kịch bản 2: Văn bản đối kháng lặp 100.000 ký tự PUA (Áp dụng rounds nhất quán) ---
    text_pua_heavy = chr(_FAKE_CLOSE_PUA_START) * 100000
    results_stress = [
        benchmark_method("2. regex findall()", run_regex_findall, text_pua_heavy, rounds=rounds),
        benchmark_method("3. regex finditer()", run_regex_finditer, text_pua_heavy, rounds=rounds),
    ]

    mem_findall = float(results_stress[0]["peak_memory_kb"])
    mem_finditer = float(results_stress[1]["peak_memory_kb"])
    mem_reduction = f"{mem_findall / max(mem_finditer, 0.01):.1f}x"

    return {
        "environment": env_info,
        "dataset_main": {
            "text_length": len(text_multi),
            "text_bytes": utf8_bytes,
            "text_size_human": size_human,
            "distinct_characters": len(set(text_multi)),
            "character_families": [
                "Han/Nom (CJK Unified Ideographs)",
                "Cyrillic",
                "Greek & Coptic",
                "Mathematical Operators",
                "Private Use Area (PUA)",
            ],
            "pua_characters_in_text": 1,
            "rounds": rounds,
        },
        "results_main": results_main,
        "dataset_stress": {
            "text_length": len(text_pua_heavy),
            "description": "100,000 repeated PUA characters (Adversarial stress test)",
            "rounds": rounds,
            "memory_reduction_ratio": mem_reduction,
        },
        "results_stress": results_stress,
    }


def print_markdown_report(data: dict[str, object]) -> None:
    """In báo cáo định dạng Markdown trực quan ra stdout."""
    env = data["environment"]  # type: ignore
    ds = data["dataset_main"]  # type: ignore
    stress_ds = data["dataset_stress"]  # type: ignore

    print("=" * 88)
    print("PUA MEMORY & PERFORMANCE REPRODUCIBILITY BENCHMARK")
    print("=" * 88)
    print("Environment:")
    print(f"  - Python:       {env['python_version']}")
    print(f"  - Platform:     {env['os_platform']}")
    print(f"  - Processor:    {env['processor']}")
    print(f"  - Timestamp:    {env['timestamp']}")
    print("\nDataset (Multilingual):")
    print(f"  - Text Length:         {ds['text_length']:,} characters ({ds['text_bytes']:,} bytes ~ {ds['text_size_human']} UTF-8)")
    print(f"  - Distinct Characters: {ds['distinct_characters']:,} characters ({', '.join(ds['character_families'])})")
    print(f"  - PUA Target:          {ds['pua_characters_in_text']} collision character (U+E000)")
    print(f"  - Measurement Rounds:  {ds['rounds']}")
    print("\nResults Summary:")
    print("| Method              | Avg Time (ms) | Peak Memory (KB) | Elements | Speedup vs Baseline |")
    print("| :------------------ | ------------: | ---------------: | -------: | ------------------: |")
    for r in data["results_main"]:  # type: ignore
        print(
            f"| {r['name']:<19} | {r['avg_time_ms']:>13.2f} | {r['peak_memory_kb']:>16.2f} | {r['elements']:>8} | {r['speedup_vs_baseline']:>19} |"
        )

    print("\nAdversarial Stress Test (100,000 PUA repeated chars):")
    print(f"  - Rounds:           {stress_ds['rounds']}")
    print(f"  - Memory Reduction: finditer() consumes {stress_ds['memory_reduction_ratio']} less peak memory than findall()")
    print("| Method              | Avg Time (ms) | Peak Memory (KB) | Memory Behavior                     |")
    print("| :------------------ | ------------: | ---------------: | :---------------------------------- |")
    for r in data["results_stress"]:  # type: ignore
        behavior = (
            "Allocates intermediate 100k-element list"
            if "findall" in r["name"]
            else "Streaming match iterator, no list allocated"
        )
        print(f"| {r['name']:<19} | {r['avg_time_ms']:>13.2f} | {r['peak_memory_kb']:>16.2f} | {behavior:<35} |")
    print("=" * 88)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark tái lập hiệu năng và bộ nhớ PUA (Feature 066).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="Số lượt đo lặp lại cho mỗi phương pháp trên cả kịch bản chính và đối kháng (Mặc định: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Xuất kết quả ở định dạng JSON thay vì bảng Markdown",
    )

    args = parser.parse_args()

    data = run_benchmarks(rounds=max(args.rounds, 1))

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_markdown_report(data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
