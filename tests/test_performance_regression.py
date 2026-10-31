"""Bộ kiểm thử hồi quy hiệu năng tự động (067-content-seed-bank-hardening).

Tách biệt rõ ràng thành hai nhóm:
1. CI Invariant Tests (không gắn marker benchmark):
   - Kiểm tra các ràng buộc thuật toán bất biến (thời gian < 200ms, bộ nhớ <= 50KB).
   - Luôn chạy tự động trong CI thông thường (`pytest tests/`).
2. Benchmark Tests (gắn marker @pytest.mark.benchmark):
   - Đo kiểm chi tiết thông lượng (throughput) và độ trễ trên dữ liệu lớn (10 KB, 100 KB, 1 MB).
   - Chạy thủ công hoặc trong luồng profiling riêng biệt: `pytest -m benchmark`.
"""
from __future__ import annotations

import gc
import time
import tracemalloc
import pytest

from chuviettay.browser.bridge import BrowserBridge
from chuviettay.document.ir import Document, Paragraph, Text, align_document_seeds
from chuviettay.importer.markdown_importer import MarkdownImporter


@pytest.fixture
def bridge_with_tiny_bank(tmp_path, tiny_bank_path):
    bridge = BrowserBridge(bank_path=tiny_bank_path)
    bridge.init()
    return bridge


# ==============================================================================
# 1. CI Invariant Tests (chạy tự động trong CI thường, kiểm tra ngưỡng chặn)
# ==============================================================================

def test_ci_invariant_seed_alignment_repetitive_words():
    """[CI-Invariant] Đảm bảo đối chiếu 1.000 từ lặp lại hoàn tất < 200ms (SC-007)."""
    words = ["là"] * 1000
    base_text = " ".join(words)
    base_doc = Document(blocks=[Paragraph(inlines=[Text(base_text)])])
    base_aligned = align_document_seeds(base_doc, base_doc)

    edited_words = words[:500] + ["chèn", "nội", "dung"] + words[500:]
    edited_text = " ".join(edited_words)
    edited_doc = Document(blocks=[Paragraph(inlines=[Text(edited_text)])])

    t0 = time.perf_counter()
    res_doc = align_document_seeds(base_aligned, edited_doc)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 200.0, f"align_document_seeds 1.000 từ lặp vượt ngưỡng 200ms: {elapsed_ms:.2f} ms"

    # Kiểm tra tính toàn vẹn của kết quả
    text_node = res_doc.blocks[0].inlines[0]
    token_occs = getattr(text_node, "token_occurrences", None)
    assert token_occs is not None and len(token_occs) == len(edited_words)
    assert token_occs[0] == 0
    assert token_occs[499] == 499
    assert token_occs[503] == 500


def test_ci_invariant_pua_collection_bounded_memory():
    """[CI-Invariant] Kiểm tra bộ nhớ phụ khi quét PUA khống chế <= 50KB (SC-004)."""
    han_nom_chars = "".join(chr(0x4E00 + i) for i in range(10000))
    # Văn bản lớn chứa 10.000 ký tự Hán Nôm, ký tự PUA và HTML entity
    large_text = f"{han_nom_chars}\ue000&#xE001;&#57346;" * 5

    gc.collect()
    tracemalloc.start()
    try:
        used_cps = MarkdownImporter._collect_used_pua_codepoints(large_text)
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    peak_kb = peak_memory / 1024
    assert peak_kb <= 50.0, f"Bộ nhớ đỉnh quét PUA vượt ngưỡng 50 KB: {peak_kb:.2f} KB"
    assert {0xE000, 0xE001, 0xE002}.issubset(used_cps)


def test_ci_invariant_bank_snapshot_latency(bridge_with_tiny_bank):
    """[CI-Invariant] Kiểm tra độ trễ tạo snapshot kho mẫu < 100ms (SC-006)."""
    # Lần gọi đầu làm nóng cache/nạp dữ liệu
    bridge_with_tiny_bank.get_bank_snapshot()

    t0 = time.perf_counter()
    snapshot = bridge_with_tiny_bank.get_bank_snapshot(profile_id="benchmark_profile")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert snapshot["ok"] is True
    assert elapsed_ms < 100.0, f"get_bank_snapshot vượt ngưỡng 100ms: {elapsed_ms:.2f} ms"


def test_ci_invariant_markdown_import_moderate():
    """[CI-Invariant] Kiểm tra nạp tài liệu Markdown kích thước trung bình 10 KB < 100ms."""
    importer = MarkdownImporter()
    # 10 KB văn bản kết hợp tiêu đề, danh sách, công thức và bảng
    paragraph_chunk = (
        "## Tiêu đề phân đoạn\n\n"
        "Đoạn văn bản tiếng Việt có chứa công thức inline $E = mc^2$ và ký hiệu toán.\n\n"
        "- Mục danh sách một với từ ngữ tự nhiên\n"
        "- Mục danh sách hai có số liệu $x_1 + x_2 = 10$\n\n"
        "| Tham số | Giá trị | Ghi chú |\n"
        "|---|---|---|\n"
        "| Alpha | 1.0 | Hệ số chuẩn hóa |\n"
        "| Beta | 2.5 | Hệ số dải nét |\n\n"
    )
    content = paragraph_chunk * 25  # ~10 KB

    t0 = time.perf_counter()
    res = importer.import_text(content)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert res.document is not None
    assert len(res.document.blocks) > 0
    assert elapsed_ms < 100.0, f"import_text 10KB Markdown vượt ngưỡng 100ms: {elapsed_ms:.2f} ms"


# ==============================================================================
# 2. Benchmark Tests (@pytest.mark.benchmark, đo kiểm chuyên sâu)
# ==============================================================================

@pytest.mark.benchmark
@pytest.mark.parametrize(
    ("size_label", "repeat_count"),
    [
        ("10 KB", 25),
        ("100 KB", 250),
        ("1 MB", 2500),
    ],
)
def test_benchmark_markdown_importer_throughput(size_label: str, repeat_count: int):
    """[Benchmark] Đo thông lượng xử lý cú pháp Markdown với các tải 10 KB, 100 KB, 1 MB."""
    importer = MarkdownImporter()
    chunk = (
        "Đoạn văn bản kiểm thử hiệu năng với công thức toán $\\alpha + \\beta = \\gamma$.\n"
        "- Danh mục thứ nhất trong danh sách kiểm tra\n"
        "| Cột 1 | Cột 2 |\n|---|---|\n| Dữ liệu A | Dữ liệu B |\n\n"
    )
    content = chunk * repeat_count
    actual_kb = len(content.encode("utf-8")) / 1024

    t0 = time.perf_counter()
    res = importer.import_text(content)
    elapsed_s = time.perf_counter() - t0

    throughput_kb_s = actual_kb / elapsed_s if elapsed_s > 0 else 0
    print(f"\n[Benchmark Markdown] {size_label} ({actual_kb:.1f} KB): {elapsed_s:.3f} s ({throughput_kb_s:.1f} KB/s)")
    assert res.document is not None


@pytest.mark.benchmark
def test_benchmark_seed_alignment_scaling():
    """[Benchmark] Đo tốc độ căn chỉnh seed trên 1.000 và 2.000 từ lặp."""
    for n_words in (1000, 2000):
        words = ["học"] * n_words
        base_doc = Document(blocks=[Paragraph(inlines=[Text(" ".join(words))])])
        base_aligned = align_document_seeds(base_doc, base_doc)

        edited_words = words[: n_words // 2] + ["và", "tập"] + words[n_words // 2 :]
        edited_doc = Document(blocks=[Paragraph(inlines=[Text(" ".join(edited_words))])])

        t0 = time.perf_counter()
        res_doc = align_document_seeds(base_aligned, edited_doc)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        print(f"\n[Benchmark Seed Alignment] {n_words} từ lặp: {elapsed_ms:.2f} ms")
        assert res_doc is not None


@pytest.mark.benchmark
def test_benchmark_bank_snapshot_throughput(bridge_with_tiny_bank):
    """[Benchmark] Đo thông lượng 100 lượt gọi liên tiếp get_bank_snapshot."""
    bridge_with_tiny_bank.get_bank_snapshot()

    n_calls = 100
    t0 = time.perf_counter()
    for _ in range(n_calls):
        res = bridge_with_tiny_bank.get_bank_snapshot(profile_id="default")
        assert res["ok"] is True
    elapsed_ms = (time.perf_counter() - t0) * 1000
    avg_ms = elapsed_ms / n_calls

    print(f"\n[Benchmark Bank Snapshot] {n_calls} calls: {elapsed_ms:.2f} ms (trung bình {avg_ms:.2f} ms/call)")
