"""Dàn trang tích hợp: danh sách lồng nhau, toán trong danh sách, công thức dài, công thức cao trong dòng."""
import gzip
import xml.etree.ElementTree as ET

import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, ListBlock, MathBlock, MathInline, Paragraph, Text
from chuviettay.math import parse_latex_math
from tests.mathtest_helpers import make_block_bank

PAGE_W = 595.28


@pytest.fixture()
def ctl(tmp_path):
    c = AppController(make_block_bank(str(tmp_path / "bank.json.gz")))
    c.load_bank()
    return c


def write(ctl, tmp_path, doc, name="o.xopp"):
    out = str(tmp_path / name)
    res = ctl.write_document(doc, WriteOptions(seed=7), out)
    root = ET.fromstring(gzip.decompress(open(out, "rb").read()))
    strokes = []
    for page_no, page in enumerate(root.findall("page")):
        for st in page.iter("stroke"):
            nums = list(map(float, st.text.split()))
            strokes.append((page_no, list(zip(nums[0::2], nums[1::2]))))
    return res, strokes


def y_extent(strokes, page=0):
    ys = [y for p, pts in strokes if p == page for _, y in pts]
    return min(ys), max(ys)


def para(text):
    return Paragraph(inlines=[Text(text=text)])


def test_nested_list_items_are_rendered(ctl, tmp_path):
    """Lỗi cũ: danh sách con nằm trong mục danh sách bị bỏ hoàn toàn (mất 'Khối 1..4' ở bài giải)."""
    flat = Document(blocks=[ListBlock(ordered=False, items=[[para("a b")], [para("a b")]])])
    nested = Document(blocks=[ListBlock(ordered=False, items=[
        [para("a b"), ListBlock(ordered=False, items=[[para("a b a")], [para("b b")]])],
        [para("a b")]])])
    r_flat, _ = write(ctl, tmp_path, flat, "flat.xopp")
    r_nested, strokes = write(ctl, tmp_path, nested, "nested.xopp")
    assert r_nested.n_lines == r_flat.n_lines + 2
    assert r_nested.n_tokens > r_flat.n_tokens


def test_nested_list_is_indented(ctl, tmp_path):
    doc = Document(blocks=[ListBlock(ordered=False, items=[
        [para("a"), ListBlock(ordered=False, items=[[para("b")]])]])])
    _, strokes = write(ctl, tmp_path, doc)
    lines = {}
    for _, pts in strokes:
        y = round(pts[0][1] / 10)
        lines.setdefault(y, []).append(min(x for x, _ in pts))
    firsts = sorted(min(v) for v in lines.values())
    assert firsts[-1] - firsts[0] > 10          # dòng con thụt vào so với dòng cha


def test_display_math_inside_list_item_is_rendered(ctl, tmp_path):
    without = Document(blocks=[ListBlock(ordered=True, items=[[para("a")]])])
    with_math = Document(blocks=[ListBlock(ordered=True, items=[[para("a"), MathBlock(latex=r"\frac{a}{b}")]])])
    r0, _ = write(ctl, tmp_path, without, "a.xopp")
    r1, _ = write(ctl, tmp_path, with_math, "b.xopp")
    assert r1.n_math_blocks == r0.n_math_blocks + 1 and r1.n_strokes > r0.n_strokes


def test_long_display_formula_wraps_instead_of_overflowing_the_page(ctl, tmp_path):
    """Lỗi cũ: biểu thức dài 60 số hạng rộng ~1000pt tràn khỏi trang."""
    long_tex = " + ".join(["ab"] * 60) + " = c"
    res, strokes = write(ctl, tmp_path, Document(blocks=[MathBlock(latex=long_tex)]))
    assert max(x for _, pts in strokes for x, _ in pts) <= PAGE_W
    assert res.n_lines >= 2                       # đã tách thành nhiều dòng


def test_wide_inline_formula_is_shrunk_to_fit(ctl, tmp_path):
    ast = parse_latex_math(" + ".join(["ab"] * 25))
    doc = Document(blocks=[Paragraph(inlines=[Text(text="a "), MathInline(latex="x", ast=ast)])])
    res, strokes = write(ctl, tmp_path, doc)
    assert max(x for _, pts in strokes for x, _ in pts) <= PAGE_W
    assert res.n_lines == 2          # chữ "a" một dòng, công thức (đã thu nhỏ) không vừa dòng đó nên xuống dòng sau


def test_extremely_wide_inline_formula_is_broken_across_lines(ctl, tmp_path):
    """Công thức inline rộng gấp nhiều lần dòng: ngắt sau toán tử/quan hệ thay vì tràn lề hay thu quá nhỏ."""
    ast = parse_latex_math(" + ".join(["ab"] * 80) + " = c")
    doc = Document(blocks=[Paragraph(inlines=[Text(text="a "), MathInline(latex="x", ast=ast)])])
    res, strokes = write(ctl, tmp_path, doc)
    assert max(x for _, pts in strokes for x, _ in pts) <= PAGE_W
    assert res.n_lines >= 3


def test_tall_inline_formula_makes_room_for_following_line(ctl, tmp_path):
    tall = parse_latex_math(r"\frac{\frac{ab}{ba}}{\frac{ab}{\frac{ba}{ab}}}")
    short = parse_latex_math("ab")

    def doc(ast):
        return Document(blocks=[Paragraph(inlines=[Text(text="a"), MathInline(latex="x", ast=ast)]), para("b")])

    _, s_tall = write(ctl, tmp_path, doc(tall), "tall.xopp")
    _, s_short = write(ctl, tmp_path, doc(short), "short.xopp")
    assert y_extent(s_tall)[1] > y_extent(s_short)[1] + 5          # dòng sau bị đẩy xuống nhờ công thức cao


def test_short_inline_formula_does_not_change_line_pitch(ctl, tmp_path):
    base = Document(blocks=[para("a b"), para("b")])
    with_x = Document(blocks=[Paragraph(inlines=[Text(text="a "), MathInline(latex="x^2", ast=parse_latex_math("x^2"))]), para("b")])
    _, s0 = write(ctl, tmp_path, base, "b0.xopp")
    _, s1 = write(ctl, tmp_path, with_x, "b1.xopp")
    assert y_extent(s0)[1] == pytest.approx(y_extent(s1)[1], abs=1.0)


def test_math_in_table_cell_is_shrunk_to_cell_width(ctl, tmp_path):
    from chuviettay.document.ir import Table, TableCell, TableRow

    wide = parse_latex_math(" + ".join(["ab"] * 30))
    cell = TableCell(blocks=[Paragraph(inlines=[MathInline(latex="x", ast=wide)])])
    tbl = Table(rows=[TableRow(cells=[cell, TableCell(blocks=[para("a")]), TableCell(blocks=[para("b")])])])
    _, strokes = write(ctl, tmp_path, Document(blocks=[tbl]))
    assert max(x for _, pts in strokes for x, _ in pts) <= PAGE_W


def test_missing_vector_symbols_are_reported_in_result(ctl, tmp_path):
    res, _ = write(ctl, tmp_path, Document(blocks=[MathBlock(latex=r"a \le b \to c")]))
    assert res.missing_symbols.get("≤") == 1 and res.missing_symbols.get("→") == 1


def test_display_math_is_not_double_counted_when_wrapped(ctl, tmp_path):
    tex = " \\le ".join(["ab"] * 40)
    res, _ = write(ctl, tmp_path, Document(blocks=[MathBlock(latex=tex)]))
    assert res.missing_symbols.get("≤") == 39


def test_page_break_inside_long_math_does_not_lose_strokes(ctl, tmp_path):
    blocks = [MathBlock(latex=r"\begin{pmatrix} ab & ba \\ ba & ab \\ ab & ba \\ ba & ab \end{pmatrix}") for _ in range(12)]
    res, strokes = write(ctl, tmp_path, Document(blocks=blocks))
    assert len({p for p, _ in strokes}) >= 2 and res.n_math_blocks == 12
