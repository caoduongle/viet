"""Kiểm thử bộ đệm trang (PageBuffer) streaming tài liệu nhiều trang."""
import gzip
import xml.etree.ElementTree as ET
import pytest

from chuviettay.layout.stream import PageBuffer


def test_page_buffer_multi_page_streaming(tmp_path):
    out_file = str(tmp_path / "stream_out.xopp")

    with PageBuffer(out_file, page_w=500.0, default_page_h=800.0) as pb:
        # Ghi 5 trang
        for p in range(5):
            strokes = [
                '<stroke tool="pen" color="#000000ff" width="1.41">10 10 20 20</stroke>',
                '<stroke tool="pen" color="#000000ff" width="1.41">30 30 40 40</stroke>',
            ]
            pb.append_page(strokes)

    assert pb.n_pages == 5

    # Đọc lại và kiểm tra tính hợp lệ của file XML đã nén
    raw = gzip.decompress(open(out_file, "rb").read())
    root = ET.fromstring(raw)
    assert root.tag == "xournal"
    pages = root.findall("page")
    assert len(pages) == 5
    for pg in pages:
        assert pg.attrib["width"] == "500"
        assert pg.attrib["height"] == "800"
        strokes = pg.findall("layer/stroke")
        assert len(strokes) == 2
