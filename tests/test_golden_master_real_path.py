"""Golden-master cho đường thật (AppController.write_text / write_document -> DocumentLayoutEngine).

Đầu ra của đường thật là trang A4 chuẩn (595.28 x 841.89 pt).
Toàn bộ mã băm dưới đây là SHA-256 của XML đã giải nén (cả .xopp lẫn _thieu.xopp nếu có)
được ghi nhận từ mã nguồn chưa sửa tại commit e517636.
"""
from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.importer.markdown_importer import MarkdownImporter
from tests.test_letter_assembly_quality import _create_quality_test_bank

GOLDEN_REAL = {
    "co_ban": {
        "xopp": "83e0967e609a5aaad50e3345ab0e19d8ae61c047c66802dfb70dd6fb153b5efe",
        "thieu": "000440af2e0670beecdb7921c22d67440405fc3d28c37883c38785923f6ec333",
    },
    "tuy_chon": {
        "xopp": "190b4e1c1bf0cda0aa31d11b449d29240561a9e59b443864dbeb0f4e12b130e0",
    },
    "nhieu_trang": {
        "xopp": "90a2aaf90eabae2564473afdfe10dff519866c1a3cfe4702235510c108eff40f",
    },
    "strict_case": {
        "xopp": "8ae4fe97061895859183839e788139d9823a9d7d2262bb3991cd9b184fbecea8",
        "thieu": "ef93eae81ec0187f34ad86ef1874380a6085d6e9cd3e84d6001f38b20515a17f",
    },
    "assemble_letters": {
        "xopp": "1d71a384018f13878f4da6abea651407b2af413b17d171c9b72ef6895a2fd589",
    },
    "math": {
        "xopp": "e20f2e35fd52edf5500bfa9103b9bceab4743431d0850df10350f175b6ccd482",
    },
    "table": {
        "xopp": "9239b2e3e2c825a99b4d34537170690b263ad27f93711a55a9276879054c2c82",
    },
    "markdown_list": {
        "xopp": "87a0e193035427d12e2b342b23cfd8c60117a09876a991581d6474640943a4c0",
        "thieu": "3636548df75c288757d6f28fadf3b87a13b6cda61b4bfa154148323d637b13c9",
    },
}

CASES = {
    "co_ban": ("xin ba bà chào Xin 12 1,2 xin. (xin) zzz bá", WriteOptions(seed=7)),
    "tuy_chon": (
        "xin ba bà chào\n\nxin xin xin ba ba 12 1,2 xin",
        WriteOptions(width=60, scale=1.3, space=1.2, jitter=0.5, seed=21, color="#1a237e", wscale=1.4),
    ),
    "nhieu_trang": ("\n".join(["xin ba bà"] * 7), WriteOptions(line=1000, seed=3)),
    "strict_case": ("Xin Ba xin", WriteOptions(strict_case=True, seed=1)),
}


def sha(path: str) -> str:
    return hashlib.sha256(gzip.decompress(Path(path).read_bytes())).hexdigest()


@pytest.mark.parametrize("name", sorted(CASES))
def test_real_path_standard_cases(name, tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    text, opts = CASES[name]
    out = str(tmp_path / (name + ".xopp"))
    result = ctl.write_text(text, opts, out)

    actual_xopp_sha = sha(out)
    assert actual_xopp_sha == GOLDEN_REAL[name]["xopp"], (
        f"{name}: file .xopp khác bản gốc đường thật. Mã băm mới: {actual_xopp_sha}"
    )

    if "thieu" in GOLDEN_REAL[name]:
        assert result.missing_grid_path, f"{name}: kỳ vọng có file _thieu.xopp nhưng không có"
        actual_thieu_sha = sha(result.missing_grid_path)
        assert actual_thieu_sha == GOLDEN_REAL[name]["thieu"], (
            f"{name}: file _thieu.xopp khác bản gốc đường thật. Mã băm mới: {actual_thieu_sha}"
        )
    else:
        assert result.missing_grid_path is None, f"{name}: kỳ vọng không có _thieu.xopp"


def test_real_path_assemble_letters(tmp_path):
    qbank = _create_quality_test_bank(tmp_path)
    qbank.save()
    ctl = AppController(qbank.path)
    ctl.load_bank()
    out = str(tmp_path / "assemble_letters.xopp")
    result = ctl.write_text("pipeline", WriteOptions(seed=42, assemble_letters=True, auto_xh=True), out)

    actual_xopp_sha = sha(out)
    assert actual_xopp_sha == GOLDEN_REAL["assemble_letters"]["xopp"], (
        f"assemble_letters: file .xopp khác bản gốc đường thật. Mã băm mới: {actual_xopp_sha}"
    )
    assert result.missing_grid_path is None


def test_real_path_math(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    doc = MarkdownImporter().import_text("xin ba $1,2$\n\n$$\\frac{1}{2}$$").document
    out = str(tmp_path / "math.xopp")
    result = ctl.write_document(doc, WriteOptions(seed=13), out)

    actual_xopp_sha = sha(out)
    assert actual_xopp_sha == GOLDEN_REAL["math"]["xopp"], (
        f"math: file .xopp khác bản gốc đường thật. Mã băm mới: {actual_xopp_sha}"
    )
    assert result.missing_grid_path is None


def test_real_path_table(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    doc = MarkdownImporter().import_text("| xin | ba |\n|---|---|\n| 1 | 2 |").document
    out = str(tmp_path / "table.xopp")
    result = ctl.write_document(doc, WriteOptions(seed=17), out)

    actual_xopp_sha = sha(out)
    assert actual_xopp_sha == GOLDEN_REAL["table"]["xopp"], (
        f"table: file .xopp khác bản gốc đường thật. Mã băm mới: {actual_xopp_sha}"
    )
    assert result.missing_grid_path is None


def test_real_path_markdown_list(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    doc = MarkdownImporter().import_text("# xin\n\n- ba\n- chào\n\n1. xin\n2. ba").document
    out = str(tmp_path / "markdown_list.xopp")
    result = ctl.write_document(doc, WriteOptions(seed=19), out)

    actual_xopp_sha = sha(out)
    assert actual_xopp_sha == GOLDEN_REAL["markdown_list"]["xopp"], (
        f"markdown_list: file .xopp khác bản gốc đường thật. Mã băm mới: {actual_xopp_sha}"
    )
    assert result.missing_grid_path, "markdown_list: kỳ vọng có file _thieu.xopp nhưng không có"
    actual_thieu_sha = sha(result.missing_grid_path)
    assert actual_thieu_sha == GOLDEN_REAL["markdown_list"]["thieu"], (
        f"markdown_list: file _thieu.xopp khác bản gốc đường thật. Mã băm mới: {actual_thieu_sha}"
    )
