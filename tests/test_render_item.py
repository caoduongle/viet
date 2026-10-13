"""Unit test cho lớp RenderItem (CTR-037-RENDER-ITEM-METADATA)."""
import pytest
from chuviettay.layout.engine import RenderItem


def test_render_item_attributes():
    item = RenderItem(
        start=10.5,
        strokes=[[1.0, 2.0, 3.0, 4.0]],
        width=25.0,
        missing=["x"],
        token="test",
        token_id="test#0",
        occurrence=0,
    )
    assert item.start == 10.5
    assert item.strokes == [[1.0, 2.0, 3.0, 4.0]]
    assert item.width == 25.0
    assert item.missing == ["x"]
    assert item.token == "test"
    assert item.token_id == "test#0"
    assert item.occurrence == 0


def test_render_item_tuple_indexing():
    item = RenderItem(
        start=5.0,
        strokes=[[0.0, 0.0]],
        width=12.0,
        missing=[],
        token="hôm",
        token_id="hôm#1",
        occurrence=1,
    )
    assert item[0] == 5.0
    assert item[1] == [[0.0, 0.0]]
    assert item[2] == 12.0
    assert item[3] == []
    assert item[4] == "hôm"
    assert item[5] == "hôm#1"
    assert item[6] == 1
    assert len(item) == 7

    with pytest.raises(IndexError):
        _ = item[7]


def test_render_item_unpacking():
    item = RenderItem(
        start=1.0,
        strokes=[],
        width=2.0,
        missing=["m"],
        token="nay",
        token_id="nay#0",
        occurrence=0,
    )
    # 1. Unpack đầy đủ 7 phần tử
    start, st, w, miss, tok, tok_id, occ = item
    assert start == 1.0
    assert tok == "nay"
    assert occ == 0

    # 2. Unpack 3 phần tử đầu kiểu lát cắt item[:3]
    s, st_list, width = tuple(item)[:3]
    assert s == 1.0
    assert width == 2.0
