"""Kiểm thử đối chiếu: cùng một công thức đi qua LaTeX (parser nội bộ) và qua OMML THẬT do pandoc sinh ra
(pandoc/texmath ghi OMML giống Word) phải cho cùng một cây AST. Tự bỏ qua nếu máy không có pandoc."""
import os
import shutil
import subprocess

import pytest

from chuviettay.importer.docx_importer import DocxImporter
from chuviettay.document.ir import MathBlock
from chuviettay.math import parse_latex_math, to_latex
from tests.mathtest_helpers import canon_for_compare

pytestmark = pytest.mark.skipif(shutil.which("pandoc") is None, reason="cần pandoc để sinh OMML thật")

CORPUS = os.path.join(os.path.dirname(__file__), "data", "math_corpus.txt")
# Pandoc không dịch được \dbinom / \over; x^23 và \tfrac được pandoc hiểu khác chuẩn TeX -> không so sánh
SKIP = (r"\dbinom", r"\over", "x^23", r"\tfrac")
# Khác biệt có chủ đích giữa hai đường (không phải lỗi): pandoc ghi \operatorname{Var} thành chữ thường m:nor
# và \setminus: pandoc ghi U+005C '\\', parser LaTeX ghi U+2216 '∖' (hai cách viết cùng một nét chéo, layout vẽ như nhau)
KNOWN_DIFFERENT = (r"\operatorname{Var}", r"\setminus")


def _lines():
    with open(CORPUS, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    return [ln for ln in lines if not any(s in ln for s in SKIP)]


@pytest.fixture(scope="module")
def omml_blocks(tmp_path_factory):
    d = tmp_path_factory.mktemp("pandoc")
    lines = _lines()
    md = d / "c.md"
    md.write_text("\n\n".join(f"$${ln}$$" for ln in lines) + "\n", encoding="utf-8")
    out = d / "c.docx"
    subprocess.run(["pandoc", str(md), "-f", "markdown+tex_math_dollars", "-t", "docx", "-o", str(out)],
                   check=True, capture_output=True)
    res = DocxImporter().import_file(str(out))
    blocks = [b for b in res.document.blocks if isinstance(b, MathBlock)]
    return lines, blocks, res


def test_every_formula_became_one_math_block(omml_blocks):
    lines, blocks, res = omml_blocks
    assert len(blocks) == len(lines)
    assert res.unsupported == [] and res.warnings == []


def test_latex_and_omml_paths_agree(omml_blocks):
    lines, blocks, _ = omml_blocks
    diffs = []
    for src, blk in zip(lines, blocks):
        if any(k in src for k in KNOWN_DIFFERENT):
            continue
        a, b = canon_for_compare(parse_latex_math(src)), canon_for_compare(blk.ast)
        if a != b:
            diffs.append((src, to_latex(a), to_latex(b)))
    assert not diffs, "\n".join(f"{s}\n  LaTeX: {a}\n  OMML : {b}" for s, a, b in diffs[:5])


def test_omml_formulas_have_non_empty_latex_text(omml_blocks):
    _, blocks, _ = omml_blocks
    assert all(b.latex.strip() for b in blocks)
