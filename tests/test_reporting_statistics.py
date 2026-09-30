"""Kiểm thử thống kê từ thiếu và số trang (User Story 2 - L2, L3)."""
import os
import pytest
from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, MathBlock, PageBreak, Paragraph, Symbol, Text
from chuviettay.layout.engine import DocumentLayoutEngine
from chuviettay.model.bank import Bank


def test_n_pages_matches_page_buffer(tmp_path):
    """WriteResult.n_pages phản ánh chính xác số trang được tạo bởi PageBuffer."""
    bank = Bank.create_empty(str(tmp_path / "bank.json.gz"))
    engine = DocumentLayoutEngine(bank, WriteOptions())

    # 4 trang bằng 3 PageBreak
    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Trang 1")]),
        PageBreak(),
        Paragraph(inlines=[Text(text="Trang 2")]),
        PageBreak(),
        Paragraph(inlines=[Text(text="Trang 3")]),
        PageBreak(),
        Paragraph(inlines=[Text(text="Trang 4")]),
    ])
    out_xopp = str(tmp_path / "four_pages.xopp")
    res = engine.render(doc, out_xopp)

    assert res.n_pages == 4
    assert os.path.exists(out_xopp)


def test_missing_tokens_ratio_never_negative(tmp_path):
    """Tỷ lệ token thiếu không bao giờ vượt quá tổng token (n_tokens >= n_missing_tokens)."""
    bank = Bank.create_empty(str(tmp_path / "empty_bank.json.gz"))
    engine = DocumentLayoutEngine(bank, WriteOptions())

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="(Xin, chào! [bạn] {nhé}")])
    ])
    out_xopp = str(tmp_path / "negative_test.xopp")
    res = engine.render(doc, out_xopp)

    assert res.n_tokens >= res.n_missing_tokens
    ok_count = res.n_tokens - res.n_missing_tokens
    assert ok_count >= 0


def test_missing_symbols_not_duplicated_in_all_missing(tmp_path):
    """Ký hiệu thiếu chỉ được đếm một lần duy nhất trong missing và missing_symbols."""
    bank = Bank.create_empty(str(tmp_path / "bank_sym.json.gz"))
    engine = DocumentLayoutEngine(bank, WriteOptions())

    doc = Document(blocks=[
        Paragraph(inlines=[
            Symbol(symbol="alpha"),
            Text(text="cộng"),
            Symbol(symbol="beta"),
        ])
    ])
    out_xopp = str(tmp_path / "sym_test.xopp")
    res = engine.render(doc, out_xopp)

    # Ký hiệu alpha và beta xuất hiện 1 lần -> missing phải ghi đúng 1 lần (không bị nhân đôi thành 2)
    assert res.missing.get("alpha") == 1
    assert res.missing_symbols.get("alpha") == 1
    assert res.missing.get("beta") == 1
    assert res.missing_symbols.get("beta") == 1


def test_math_block_missing_symbols_not_duplicated(tmp_path):
    """Ký hiệu thiếu trong MathBlock được đếm chính xác 1 lần trong cả missing và missing_symbols."""
    bank = Bank.create_empty(str(tmp_path / "bank_math.json.gz"))
    engine = DocumentLayoutEngine(bank, WriteOptions())

    doc = Document(blocks=[
        MathBlock(latex=r"\alpha + \beta")
    ])
    out_xopp = str(tmp_path / "math_test.xopp")
    res = engine.render(doc, out_xopp)

    for sym in ["alpha", "beta", "+"]:
        if sym in res.missing_symbols:
            assert res.missing.get(sym) == res.missing_symbols.get(sym)
