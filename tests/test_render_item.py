"""Kiểm thử đơn vị cho lớp RenderItem: giải nén tuple, truy cập chỉ số, cắt lát (slice) và chỉ số âm."""
from __future__ import annotations

import pytest
from chuviettay.layout.engine import RenderItem


def test_render_item_basic_properties():
    item = RenderItem(
        start=10.5,
        strokes=[[(0.0, 0.0), (1.0, 1.0)]],
        width=25.0,
        missing=["x"],
        token="xin",
        token_id="text:xin#0",
        occurrence=0,
    )
    assert item.start == 10.5
    assert len(item.strokes) == 1
    assert item.width == 25.0
    assert item.missing == ["x"]
    assert item.token == "xin"
    assert item.token_id == "text:xin#0"
    assert item.occurrence == 0
    assert len(item) == 7


def test_render_item_integer_indexing():
    item = RenderItem(
        start=5.0,
        strokes=[[(1.0, 2.0)]],
        width=15.0,
        missing=[],
        token="chao",
        token_id="text:chao#1",
        occurrence=1,
    )
    assert item[0] == 5.0
    assert item[1] == [[(1.0, 2.0)]]
    assert item[2] == 15.0
    assert item[3] == []
    assert item[4] == "chao"
    assert item[5] == "text:chao#1"
    assert item[6] == 1


def test_render_item_negative_indexing():
    item = RenderItem(
        start=5.0,
        strokes=[],
        width=15.0,
        missing=[],
        token="chao",
        token_id="text:chao#1",
        occurrence=1,
    )
    assert item[-1] == 1
    assert item[-2] == "text:chao#1"
    assert item[-3] == "chao"
    assert item[-7] == 5.0


def test_render_item_slice_unpacking():
    st = [[(0.0, 0.0)]]
    item = RenderItem(
        start=12.0,
        strokes=st,
        width=30.0,
        missing=["a"],
        token="test",
        token_id="text:test#2",
        occurrence=2,
    )

    # Cắt lát 3 phần tử đầu tiên (tương thích docstring: start, st, w = item[:3])
    start, strokes, width = item[:3]
    assert start == 12.0
    assert strokes == st
    assert width == 30.0

    # Cắt lát các dải tùy ý
    assert item[1:4] == (st, 30.0, ["a"])
    assert item[4:] == ("test", "text:test#2", 2)
    assert item[:] == (12.0, st, 30.0, ["a"], "test", "text:test#2", 2)
    assert item[::2] == (12.0, 30.0, "test", 2)


def test_render_item_iteration_and_unpacking():
    item = RenderItem(
        start=1.0,
        strokes=[],
        width=2.0,
        missing=[],
        token="t",
        token_id="text:t#0",
        occurrence=0,
    )
    a, b, c, d, e, f, g = item
    assert (a, b, c, d, e, f, g) == (1.0, [], 2.0, [], "t", "text:t#0", 0)
    assert list(item) == [1.0, [], 2.0, [], "t", "text:t#0", 0]


def test_render_item_out_of_bounds_index_error():
    item = RenderItem(start=0.0, strokes=[], width=0.0)
    with pytest.raises(IndexError):
        _ = item[7]
    with pytest.raises(IndexError):
        _ = item[-8]
