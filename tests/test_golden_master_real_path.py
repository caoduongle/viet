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
        "xopp": "001683a9d8e219fb798fafddf311ea6af174f3c10f24f383c2685c2b4abe35bd",
        "thieu": "6b336106a6ca50e7ca62fe93179cc3a2530c29c5669cd15be7b73102d9fbfde3",
    },
    "tuy_chon": {
        "xopp": "ff88562804ff4f74b93cc6b676436e19b35371c787045b78b3c75e68d8f99c5a",
    },
    "nhieu_trang": {
        "xopp": "5552508f031d160fe23819e28693bf71ac2835e814639b9e0598faf7549a4542",
    },
    "strict_case": {
        "xopp": "04beeac960da1920fc69912d9fc4872a62b56a84d3d3b37d02e68431beea7e7e",
        "thieu": "acb51aba82031bdbdb376ab26d802b51292874722e59185c924aaf40774afa36",
    },
    "assemble_letters": {
        "xopp": "1d71a384018f13878f4da6abea651407b2af413b17d171c9b72ef6895a2fd589",
    },
    "math": {
        "xopp": "7f4bc6d8f7f25b94817585958a55a9ef6bf31dd0ceb8c41cd061dcea17694d5b",
    },
    "table": {
        "xopp": "bfa7b717d444908e1107ebc5cd6055963957ef2a047a9a3758671936ecd7b2ec",
    },
    "markdown_list": {
        "xopp": "1537d84d1f21318955ec43ea1e8db44257f79ef0f12933142ede3978d3bbdbe2",
        "thieu": "6364a7000d6c3dbbaf466d433c947a685e1ffad0c359367248df76659b1724ae",
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
