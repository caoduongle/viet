"""Markdown: các kiểu dấu phân cách toán, môi trường amsmath, toán trong danh sách và lọc HTML an toàn."""
from chuviettay.document.ir import ListBlock, MathBlock, MathInline, Text
from chuviettay.importer.markdown_importer import MarkdownImporter


def imp(md):
    return MarkdownImporter().import_text(md)


def inline_maths(par):
    return [i.latex for i in par.inlines if isinstance(i, MathInline)]


def test_latex_paren_delimiters_are_math():
    res = imp(r"Cho \(x^2+1=0\) thì")
    par = res.document.blocks[0]
    assert inline_maths(par) == ["x^2+1=0"]
    assert [i.text for i in par.inlines if isinstance(i, Text)] == ["Cho ", " thì"]


def test_latex_bracket_display_delimiters_are_math_block():
    res = imp("Ta có\n\n\\[\n\\frac{a}{b}\n\\]\n\nxong")
    kinds = [type(b).__name__ for b in res.document.blocks]
    assert kinds == ["Paragraph", "MathBlock", "Paragraph"]
    assert res.document.blocks[1].latex == r"\frac{a}{b}"


def test_bare_amsmath_environment_is_math_block():
    res = imp("\\begin{align}\na &= b \\\\\nc &= d\n\\end{align}")
    assert len(res.document.blocks) == 1 and isinstance(res.document.blocks[0], MathBlock)
    assert "\\begin{align}" in res.document.blocks[0].latex


def test_double_dollar_inline_in_paragraph_is_math():
    par = imp("Ta có $$x^2$$ nữa và $y$.").document.blocks[0]
    assert inline_maths(par) == ["x^2", "y"]


def test_display_math_inside_list_item_is_kept():
    """Lỗi cũ: $$...$$ trong mục danh sách bị bỏ im lặng."""
    res = imp("1. Giải:\n\n   $$x^2=4$$\n\n2. Kết luận")
    lst = res.document.blocks[0]
    assert isinstance(lst, ListBlock)
    assert any(isinstance(b, MathBlock) and b.latex == "x^2=4" for b in lst.items[0])
    assert len(lst.items) == 2


def test_nested_list_structure_is_preserved():
    res = imp("- cha\n  - con 1\n  - con $x$\n- cha 2")
    lst = res.document.blocks[0]
    nested = [b for b in lst.items[0] if isinstance(b, ListBlock)]
    assert len(nested) == 1 and len(nested[0].items) == 2


def test_currency_dollar_is_not_math():
    par = imp("Giá 5$ rồi 10$ nữa").document.blocks[0]
    assert inline_maths(par) == []
    assert "5$ rồi 10$" in "".join(i.text for i in par.inlines if isinstance(i, Text))


def test_math_starting_with_digit_still_works():
    par = imp("Có $4500 > 4000$ và $2x+1$ ok").document.blocks[0]
    assert inline_maths(par) == ["4500 > 4000", "2x+1"]


def test_comparison_operators_in_prose_are_preserved():
    """Lỗi cũ: bước lọc HTML xoá đoạn nằm giữa < và >: 'a<b và c>d' thành 'ad'."""
    par = imp("Nếu a<b và c>d thì đúng, còn x < y và z > w").document.blocks[0]
    assert "a<b và c>d" in par.inlines[0].text and "x < y và z > w" in par.inlines[0].text


def test_real_html_is_still_removed():
    par = imp('Chữ <b>đậm</b> <span class="x">này</span><br/>hết <script>alert(1)</script>ok').document.blocks[0]
    text = "".join(i.text for i in par.inlines if isinstance(i, Text))
    assert "<" not in text and "alert" not in text and "đậm" in text and "này" in text


def test_code_fence_and_inline_code_are_not_touched():
    res = imp("Dòng `\\(x\\)` giữ nguyên.\n\n```\n\\(y\\) <b>z</b>\n```\n")
    par = res.document.blocks[0]
    assert inline_maths(par) == []
    assert res.unsupported == ["code_block"]           # hợp đồng IR: code block được báo là chưa hỗ trợ


def test_table_cells_keep_math():
    res = imp("| a | b |\n| - | - |\n| $\\frac{1}{2}$ | $x^2$ |\n")
    table = res.document.blocks[0]
    cells = table.rows[1].cells
    assert inline_maths(cells[0].blocks[0]) == [r"\frac{1}{2}"] and inline_maths(cells[1].blocks[0]) == ["x^2"]


def test_unsupported_contract_for_hr_and_code_is_unchanged():
    res = imp("a\n\n---\n\n```python\nx=1\n```\n")
    assert res.unsupported == ["hr: horizontal rule", "code_block: python"]


def test_empty_math_block_is_ignored():
    res = imp("$$\n$$\n\ntext")
    assert not any(isinstance(b, MathBlock) for b in res.document.blocks)


def test_delimiter_conversion_edge_cases():
    conv = MarkdownImporter._normalize_math_delimiters
    assert conv(r"Cho \( x^2 \) thì") == "Cho $x^2$ thì"
    assert conv("a\n\\[\nx\n\\]\nb") == "a\n$$\nx\n$$\nb"
    assert conv(r"\(a\) và \(b\) và \[c\]") == "$a$ và $b$ và $$c$$"
    assert conv(r"một \\(không phải\\) toán") == r"một \\(không phải\\) toán"      # \\( là gạch ngược thoát
    assert conv(r"mở \( rồi hết") == r"mở \( rồi hết"                             # không đóng: giữ nguyên
    assert conv(r"\(\) và \(  \)") == r"\(\) và \(  \)"                           # rỗng: giữ nguyên
    assert conv("`\\(x\\)` và ```\n\\[y\\]\n``` ok \\(z\\)") == "`\\(x\\)` và ```\n\\[y\\]\n``` ok $z$"


def test_pathological_delimiters_are_linear_time():
    import time

    for txt in ("\\(" * 20000 + " x", "\\[" * 20000 + " x", "\\(" * 10000 + "\\)", "$" * 20000):
        t = time.perf_counter()
        imp(txt)
        assert time.perf_counter() - t < 2.0
