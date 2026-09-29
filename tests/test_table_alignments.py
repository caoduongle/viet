"""Kiểm thử căn lề cột trong bảng (left, center, right)."""
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Paragraph, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.engine import DocumentLayoutEngine


def test_table_column_alignments(tiny_bank, tmp_path):
    tiny_bank.words["A"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["B"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["C"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]

    row = TableRow(cells=[
        TableCell.from_text("A"),
        TableCell.from_text("B"),
        TableCell.from_text("C"),
    ])
    table = Table(
        rows=[row],
        border_style=TableBorder.ALL,
        col_alignments=["left", "center", "right"],
    )
    doc = Document(blocks=[table])
    out = str(tmp_path / "table_align.xopp")

    opts = WriteOptions(scale=1.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out)

    assert res.n_tables == 1
    assert res.n_strokes > 0

    import gzip
    import xml.etree.ElementTree as ET

    with gzip.open(out, "rb") as f:
        root = ET.fromstring(f.read())

    char_strokes = [s.text.strip().split() for s in root.findall(".//stroke") if len(s.text.strip().split()) == 6]
    assert len(char_strokes) == 3
    x_A = float(char_strokes[0][0])
    x_B = float(char_strokes[1][0])
    x_C = float(char_strokes[2][0])

    assert x_A < x_B < x_C
