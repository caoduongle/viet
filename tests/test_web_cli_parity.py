"""Kiểm thử tính tương đương (Parity) giữa đầu ra của Web Bridge và CLI / Controller lõi.

Đảm bảo:
  1. Với cùng một văn bản và WriteOptions (seed, scale, line, v.v.), file .xopp tạo ra
     từ BrowserBridge hoàn toàn trùng khớp từng byte nội dung XML với CLI/AppController.
  2. Định dạng Markdown có công thức toán $...$ hoặc bảng biểu sinh ra kết quả tương đương 100%.
  3. Cú pháp ngắt trang <!-- pagebreak --> và \\pagebreak sinh ra đúng số trang.
"""
from __future__ import annotations

import base64
import gzip
import tempfile
from pathlib import Path

import pytest

from chuviettay.browser.bridge import BrowserBridge
from chuviettay.controller.app_controller import AppController
from chuviettay.importer.markdown_importer import MarkdownImporter
from chuviettay.model.composer import WriteOptions

KHO_TONG_HOP = Path(__file__).resolve().parent / "data" / "kho_mau_tong_hop.json.gz"


def _read_xopp_xml(xopp_bytes: bytes) -> str:
    """Giải nén và đọc chuỗi XML từ file .xopp (gzipped .xoj)."""
    return gzip.decompress(xopp_bytes).decode("utf-8")


@pytest.fixture
def bank_bytes() -> bytes:
    with open(KHO_TONG_HOP, "rb") as f:
        return f.read()


def test_plain_text_parity(bank_bytes: bytes, tmp_path: Path):
    """Kiểm tra văn bản thuần qua Bridge vs AppController trực tiếp."""
    # 1. Setup AppController trực tiếp (như CLI làm)
    bank_path = tmp_path / "bank.json.gz"
    bank_path.write_bytes(bank_bytes)
    ctl = AppController(bank_path=str(bank_path), timer_factory=lambda *a, **k: None)
    ctl.load_bank()

    opts = WriteOptions(seed=42, scale=1.0, width=0.8, color="#000000ff")
    cli_out = tmp_path / "cli_out.xopp"
    text = "Xin chào các bạn, đây là bài kiểm tra độ đồng nhất giữa Web và CLI."
    cli_result = ctl.write_text(text, opts, str(cli_out))

    with open(cli_out, "rb") as f:
        cli_xml = _read_xopp_xml(f.read())

    # 2. Setup BrowserBridge
    bridge = BrowserBridge(bank_path=str(tmp_path / "bridge_bank.json.gz"))
    load_res = bridge.load_bank(bank_bytes)
    assert load_res["ok"] is True

    bridge_res = bridge.write_text(
        text,
        options={"seed": 42, "scale": 1.0, "width": 0.8, "color": "#000000ff"},
        fmt="txt",
    )
    assert bridge_res["ok"] is True
    bridge_xml = _read_xopp_xml(base64.b64decode(bridge_res["xopp_base64"]))

    # 3. So khớp từng byte nội dung XML
    assert bridge_xml == cli_xml
    assert bridge_res["n_pages"] == cli_result.n_pages
    assert bridge_res["n_strokes"] == cli_result.n_strokes
    assert bridge_res["n_lines"] == cli_result.n_lines


def test_markdown_parity(bank_bytes: bytes, tmp_path: Path):
    """Kiểm tra văn bản Markdown có công thức toán qua Bridge vs CLI/MarkdownImporter."""
    bank_path = tmp_path / "bank.json.gz"
    bank_path.write_bytes(bank_bytes)
    ctl = AppController(bank_path=str(bank_path), timer_factory=lambda *a, **k: None)
    ctl.load_bank()

    md_text = (
        "# Tiêu đề bài viết\n\n"
        "Phương trình bậc hai: $ax^2 + bx + c = 0$\n\n"
        "Công thức tích phân: $\\int_0^1 x dx$\n"
    )

    importer = MarkdownImporter()
    doc_res = importer.import_text(md_text)
    opts = WriteOptions(seed=123, scale=1.1, line=25.0)

    cli_out = tmp_path / "cli_md.xopp"
    cli_result = ctl.write_document(doc_res.document, opts, str(cli_out))
    with open(cli_out, "rb") as f:
        cli_xml = _read_xopp_xml(f.read())

    # Qua bridge
    bridge = BrowserBridge(bank_path=str(tmp_path / "bridge_bank.json.gz"))
    bridge.load_bank(bank_bytes)
    bridge_res = bridge.write_text(
        md_text,
        options={"seed": 123, "scale": 1.1, "line": 25.0},
        fmt="md",
    )
    assert bridge_res["ok"] is True
    bridge_xml = _read_xopp_xml(base64.b64decode(bridge_res["xopp_base64"]))

    assert bridge_xml == cli_xml
    assert bridge_res["n_pages"] == cli_result.n_pages
    assert bridge_res["n_strokes"] == cli_result.n_strokes


def test_pagebreak_parity(bank_bytes: bytes, tmp_path: Path):
    """Kiểm tra xử lý ngắt trang <!-- pagebreak --> và \\pagebreak."""
    bridge = BrowserBridge(bank_path=str(tmp_path / "bridge_bank.json.gz"))
    bridge.load_bank(bank_bytes)

    text_with_breaks = (
        "Trang 1: Nội dung dòng đầu tiên.\n"
        "<!-- pagebreak -->\n"
        "Trang 2: Nội dung của trang hai.\n"
        "\\pagebreak\n"
        "Trang 3: Nội dung của trang ba."
    )

    res = bridge.write_text(text_with_breaks, options={"seed": 999}, fmt="md")
    assert res["ok"] is True
    assert res["n_pages"] == 3
