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
        "xopp": "0e9198eeda15627e535937943ce6cdee156dd35a77d139cb296ebe4c0d5e0f06",
        "thieu": "acb71b94f99fcf51b639b91a2abcc906267a7a5e1be4a5c3b4c333115cc6338c",
    },
    "tuy_chon": {
        "xopp": "cc710e3994f9a611dae9a747f9494921c8dd8b0fd41aa934ebb02296dd612b3c",
    },
    "nhieu_trang": {
        "xopp": "5552508f031d160fe23819e28693bf71ac2835e814639b9e0598faf7549a4542",
    },
    "strict_case": {
        "xopp": "04beeac960da1920fc69912d9fc4872a62b56a84d3d3b37d02e68431beea7e7e",
        "thieu": "d68b8bb1b8dfef125d7495598715c0204c681f3d842f8ac17586064a46cae029",
    },
    "assemble_letters": {
        "xopp": "70e9ecaa3a8aa81dd0781ce719826c98aead718c60635ef9e14bd103e9b8aeed",
    },
    "math": {
        "xopp": "98096eb19692921ed459ad0ef43421d907040ba88441741efd4499b3c0d83c69",
    },
    "table": {
        "xopp": "1508e182493a0b315c1eb6a3038f1f27e151a28ff08851e50d2b79e38871d03b",
    },
    "markdown_list": {
        "xopp": "39a1fd33e2d9d2e3b989631e2ce3663316fdb8b4069d07a31db9098f7e325a66",
        "thieu": "239e7b0d55a5abf5fa13898179fb273b900ec3935b11a2576e32103d18b9ca0a",
    },
}

CASES = {
    "co_ban": ("xin ba bà chào Xin 12 1,2 xin. (xin) zzz bá", WriteOptions(seed=7, missing_grid=True)),
    "tuy_chon": (
        "xin ba bà chào\n\nxin xin xin ba ba 12 1,2 xin",
        WriteOptions(width=60, scale=1.3, space=1.2, jitter=0.5, seed=21, color="#1a237e", wscale=1.4),
    ),
    "nhieu_trang": ("\n".join(["xin ba bà"] * 7), WriteOptions(line=1000, seed=3)),
    "strict_case": ("Xin Ba xin", WriteOptions(strict_case=True, seed=1, missing_grid=True)),
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
    result = ctl.write_document(doc, WriteOptions(seed=19, missing_grid=True), out)

    actual_xopp_sha = sha(out)
    assert actual_xopp_sha == GOLDEN_REAL["markdown_list"]["xopp"], (
        f"markdown_list: file .xopp khác bản gốc đường thật. Mã băm mới: {actual_xopp_sha}"
    )
    assert result.missing_grid_path, "markdown_list: kỳ vọng có file _thieu.xopp nhưng không có"
    actual_thieu_sha = sha(result.missing_grid_path)
    assert actual_thieu_sha == GOLDEN_REAL["markdown_list"]["thieu"], (
        f"markdown_list: file _thieu.xopp khác bản gốc đường thật. Mã băm mới: {actual_thieu_sha}"
    )


def test_real_path_stable_variants(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    out = str(tmp_path / "stable.xopp")
    result = ctl.write_text("xin ba bà chào Xin 12 1,2 xin. (xin) zzz bá", WriteOptions(seed=7, stable_variants=True, missing_grid=True), out)

    actual_xopp_sha = sha(out)
    expected_xopp_sha = "923b969736c9724339216b46803e85ddba829de25ca813527e2142ea3774b386"
    assert actual_xopp_sha == expected_xopp_sha, (
        f"stable_variants: file .xopp khác bản gốc cố định. Mã băm mới: {actual_xopp_sha}"
    )
    assert result.missing_grid_path, "stable_variants: kỳ vọng có file _thieu.xopp nhưng không có"
    actual_thieu_sha = sha(result.missing_grid_path)
    expected_thieu_sha = "acb71b94f99fcf51b639b91a2abcc906267a7a5e1be4a5c3b4c333115cc6338c"
    assert actual_thieu_sha == expected_thieu_sha, (
        f"stable_variants: file _thieu.xopp khác bản gốc cố định. Mã băm mới: {actual_thieu_sha}"
    )

