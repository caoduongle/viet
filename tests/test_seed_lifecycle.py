"""Kiểm thử vòng đời Hạt giống ngẫu nhiên (CTR-036-SEED-LIFECYCLE).

Bao gồm:
1. Kiểm chuẩn WriteOptions.validate() đối với seed (hợp lệ và bất hợp lệ).
2. Kiểm chứng lý do kỹ thuật chặn seed âm: Random(-5) trùng Random(5) trong CPython.
3. Tái tạo bit-exact qua WriteResult.seed_used (cả semantic và fidelity mode).
4. Hành vi seed=None khi stable_variants=True -> effective seed = 0.
"""
from __future__ import annotations

import gzip
import hashlib
import random
import pytest

from chuviettay.controller.results import WriteOptions, WriteResult
from chuviettay.document.ir import Document, Paragraph, Text
from chuviettay.layout.engine import DocumentLayoutEngine
from tests.test_letter_assembly_quality import _create_quality_test_bank


def test_random_negative_seed_collision_proof():
    """Kiểm chứng thực nghiệm lý do kỹ thuật chặn seed âm:
    Trong CPython Mersenne Twister, Random(-5) sinh ra cùng dãy số chính xác như Random(5).
    """
    r_neg = random.Random(-5)
    r_pos = random.Random(5)
    seq_neg = [r_neg.random() for _ in range(20)]
    seq_pos = [r_pos.random() for _ in range(20)]
    assert seq_neg == seq_pos, "Random(-5) phải trùng Random(5) trong CPython"


@pytest.mark.parametrize("valid_seed", [None, 0, 1, 42, 2**32 - 1])
def test_write_options_seed_valid(valid_seed):
    """Kiểm tra các giá trị seed hợp lệ."""
    opts = WriteOptions(seed=valid_seed)
    opts.validate()
    assert opts.seed == valid_seed


@pytest.mark.parametrize(
    "invalid_seed",
    [
        True,
        False,
        -1,
        -5,
        2**32,
        2**32 + 10,
        3.14,
        "42",
        [],
        {},
    ],
)
def test_write_options_seed_invalid(invalid_seed):
    """Kiểm tra các giá trị seed bất hợp lệ bị ném ValueError tiếng Việt."""
    opts = WriteOptions(seed=invalid_seed)
    with pytest.raises(ValueError, match="Hạt giống \\(seed\\) phải là số nguyên không âm trong khoảng \\[0, 4294967295\\] hoặc None"):
        opts.validate()


def test_effective_seed_and_bit_exact_reproducibility(tmp_path):
    """Kiểm chứng tái tạo bit-exact qua WriteResult.seed_used."""
    bank = _create_quality_test_bank(tmp_path)
    doc = Document(blocks=[Paragraph(inlines=[Text(text="Xin chào Việt Nam tươi đẹp")])])

    # Lượt 1: seed=None, tự sinh
    opts1 = WriteOptions(seed=None, jitter=1.0)
    out1 = str(tmp_path / "out1.xopp")
    engine1 = DocumentLayoutEngine(bank, opts1)
    res1 = engine1.render(doc, out1)

    assert isinstance(res1, WriteResult)
    assert res1.seed_used is not None
    assert isinstance(res1.seed_used, int)
    assert 0 <= res1.seed_used < 2**32

    # Lượt 2: Chạy lại đúng với res1.seed_used
    opts2 = WriteOptions(seed=res1.seed_used, jitter=1.0)
    out2 = str(tmp_path / "out2.xopp")
    engine2 = DocumentLayoutEngine(bank, opts2)
    res2 = engine2.render(doc, out2)

    assert res2.seed_used == res1.seed_used

    # Đọc và so sánh nội dung XML giải nén của cả hai tệp
    with gzip.open(out1, "rb") as gz1, gzip.open(out2, "rb") as gz2:
        content1 = gz1.read()
        content2 = gz2.read()

    hash1 = hashlib.sha256(content1).hexdigest()
    hash2 = hashlib.sha256(content2).hexdigest()
    assert hash1 == hash2, "Tái tạo lại với res1.seed_used phải cho kết quả XML bit-exact trùng khớp 100%"


def test_seed_none_with_stable_variants_resolves_to_zero(tmp_path):
    """Khi stable_variants=True và seed=None, effective seed phải là 0."""
    bank = _create_quality_test_bank(tmp_path)
    doc = Document(blocks=[Paragraph(inlines=[Text(text="Kiểm tra seed ổn định")])])

    opts = WriteOptions(seed=None, stable_variants=True)
    out = str(tmp_path / "stable_zero.xopp")
    engine = DocumentLayoutEngine(bank, opts)
    res = engine.render(doc, out)

    assert res.seed_used == 0, f"Kỳ vọng seed_used=0 khi stable_variants=True và seed=None, nhận được: {res.seed_used}"


def test_fidelity_engine_seed_used_bit_exact_reproducibility(tmp_path):
    """Kiểm chứng tính tái tạo bit-exact qua WriteResult.seed_used trên FidelityLayoutEngine."""
    from chuviettay.fidelity.engine import FidelityLayoutEngine
    from chuviettay.fidelity.fixed_model import FixedDocument, FixedPage, TextBox

    bank = _create_quality_test_bank(tmp_path)
    fixed_doc = FixedDocument(
        source_path="test.docx",
        background_pdf_path="test_bg.pdf",
        pages=[
            FixedPage(
                page_index=0,
                width=595.0,
                height=842.0,
                boxes=[
                    TextBox(x=50.0, y=100.0, width=300.0, height=20.0, text="Xin chào Việt Nam tươi đẹp", font_size=12.0),
                    TextBox(x=50.0, y=150.0, width=300.0, height=20.0, text="Chữ viết tay độ trung thực cao", font_size=12.0),
                ],
            )
        ]
    )

    # Lượt 1: seed=None, jitter=1.0
    opts1 = WriteOptions(seed=None, jitter=1.0)
    out1 = str(tmp_path / "fid_out1.xopp")
    engine1 = FidelityLayoutEngine(bank, opts1)
    res1 = engine1.render(fixed_doc, out1)

    assert isinstance(res1, WriteResult)
    assert res1.seed_used is not None
    assert isinstance(res1.seed_used, int)
    assert 0 <= res1.seed_used < 2**32

    # Lượt 2: Chạy lại với đúng res1.seed_used
    opts2 = WriteOptions(seed=res1.seed_used, jitter=1.0)
    out2 = str(tmp_path / "fid_out2.xopp")
    engine2 = FidelityLayoutEngine(bank, opts2)
    res2 = engine2.render(fixed_doc, out2)

    assert res2.seed_used == res1.seed_used

    with gzip.open(out1, "rb") as gz1, gzip.open(out2, "rb") as gz2:
        content1 = gz1.read()
        content2 = gz2.read()

    hash1 = hashlib.sha256(content1).hexdigest()
    hash2 = hashlib.sha256(content2).hexdigest()
    assert hash1 == hash2, "FidelityLayoutEngine: Tái tạo lại với res1.seed_used phải bit-exact 100%"

    # Lượt 3: Kiểm tra seed=None khi stable_variants=True
    opts3 = WriteOptions(seed=None, stable_variants=True)
    out3 = str(tmp_path / "fid_out3.xopp")
    engine3 = FidelityLayoutEngine(bank, opts3)
    res3 = engine3.render(fixed_doc, out3)
    assert res3.seed_used == 0

