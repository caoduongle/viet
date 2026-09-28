"""Định dạng file .xopp + file lưới ô: vòng tròn ghi ra -> đọc lại phải ra đúng dữ liệu."""
import gzip

import pytest

from chuviettay.config import BASE, CH, COLS, CW, MXT, MYT, ROWS, TAG_CALIB, TAG_PLAIN
from chuviettay.model import xopp


def texts(path):
    return [(t.text or "").strip() for t in xopp.read_xopp(path).iter("text")]


def test_cell_xy_theo_hang_roi_cot_roi_trang():
    assert xopp.cell_xy(0) == (0, MXT, MYT)
    assert xopp.cell_xy(1) == (0, MXT + CW, MYT)
    assert xopp.cell_xy(COLS) == (0, MXT, MYT + CH)                   # hết hàng -> xuống hàng
    assert xopp.cell_xy(COLS * ROWS) == (1, MXT, MYT)                  # hết trang -> sang trang


def test_save_va_read_xopp_deu_nen_gzip(tmp_path):
    p = str(tmp_path / "a.xopp")
    xopp.save_xopp(p, [xopp.HEAD, "</xournal>"])
    assert open(p, "rb").read()[:2] == b"\x1f\x8b"
    assert xopp.read_xopp(p).tag == "xournal"


def test_read_xopp_doc_duoc_ca_file_khong_nen(tmp_path):
    p = tmp_path / "plain.xopp"
    p.write_text(xopp.HEAD + "\n</xournal>", encoding="utf-8")
    assert xopp.read_xopp(str(p)).tag == "xournal"


def test_text_xml_thoat_ky_tu_dac_biet():
    assert "&lt;a&gt; &amp;" in xopp.text_xml(0, 0, "<a> &")


def test_stroke_xml_mau_va_do_day():
    pen = {"tool": "pen", "color": "#000000ff", "width": "2", "capStyle": "round"}
    s = xopp.stroke_xml([(0, 0), (1, 2)], pen, color="#1a237e", wscale=1.5)
    assert 'color="#1a237e"' in s and 'width="3"' in s and ">0 0 1 2<" in s


def test_pick_calib_word_chon_tu_nhieu_mau_on_dinh(tiny_bank):
    assert xopp.pick_calib_word(tiny_bank) == "xin"          # chỉ "xin" có >= 5 mẫu


def test_pick_calib_word_du_phong_khi_khong_tu_nao_du_5_mau(tiny_bank):
    tiny_bank.words.pop("xin")
    assert xopp.pick_calib_word(tiny_bank) == "ba"           # rơi về từ đầu tiên trong kho


def test_make_grid_co_o_do_co_tay_o_dau_tien(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba", "chào"], tiny_bank, "tiêu đề thử")
    ts = texts(p)
    assert TAG_CALIB in ts and TAG_PLAIN not in ts
    assert ts.count("xin") == 1 and "ba" in ts and "chào" in ts and "tiêu đề thử" in ts


def test_make_grid_khong_calib(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba"], tiny_bank, "h", calib=False)
    ts = texts(p)
    assert TAG_PLAIN in ts and TAG_CALIB not in ts and "xin" not in ts


def test_make_grid_nhieu_trang(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    labels = ["w%d" % i for i in range(COLS * ROWS + 5)]      # tràn sang trang 2
    xopp.make_grid(p, labels, tiny_bank, "h", calib=False)
    assert len(xopp.read_xopp(p).findall("page")) == 2


def test_vong_tron_make_grid_roi_parse_learn_file(tiny_bank, tmp_path):
    """Ghi các mẫu đã có vào lưới ô (như lệnh check), đọc lại: phải ra đúng nhãn + đúng hình nét."""
    p = str(tmp_path / "g.xopp")
    keys = ["ba", "chào", "xin"]
    samples = {k: tiny_bank.words[k][0]["s"] for k in keys}
    xopp.make_grid(p, keys, tiny_bank, "h", samples, calib=False)

    raw, has_calib = xopp.parse_learn_file(p)
    assert has_calib is False
    assert sorted(c.label for c in raw.values()) == keys
    for (page, col, row), cell in raw.items():
        assert page == 0 and 0 <= col < COLS and 0 <= row < ROWS
        assert cell.base == pytest.approx(MYT + row * CH + BASE, abs=1e-6)
        orig = samples[cell.label]
        assert len(cell.strokes) == len(orig)
        # quy về toạ độ tương đối như learning.py rồi so với nét gốc (mẫu gốc đều bắt đầu từ x=0)
        for got, want in zip(cell.strokes, orig):
            rel = [v - (cell.left if i % 2 == 0 else cell.base) for i, v in enumerate(got)]
            assert rel == pytest.approx(want, abs=0.011)


def test_parse_learn_file_nhan_biet_o_do_co_tay(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba"], tiny_bank, "h", {"xin": tiny_bank.words["xin"][0]["s"]}, calib=True)
    raw, has_calib = xopp.parse_learn_file(p)
    assert has_calib is True
    assert raw[(0, 0, 0)].label == "xin"                       # ô (trang 0, cột 0, hàng 0) = ô đo cỡ tay


def test_parse_learn_file_bo_qua_net_ke_mo_va_net_ngoai_o(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba"], tiny_bank, "h", calib=False)     # chỉ có nét kẻ mờ, chưa viết gì
    raw, _ = xopp.parse_learn_file(p)
    assert raw == {}


def test_parse_learn_file_chi_lay_net_pen(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba"], tiny_bank, "h", {"ba": [[0, 0, 4, -5]]}, calib=False)
    raw, _ = xopp.parse_learn_file(p)
    (cell,) = raw.values()
    # thêm một nét highlighter vào đúng ô đó -> không được tính
    x0, y0 = MXT, MYT
    hl = '<stroke tool="highlighter" color="#ffff00ff" width="9">%f %f %f %f</stroke>' % (x0 + 9, y0 + 20, x0 + 30, y0 + 20)
    content = gzip.decompress(open(p, "rb").read()).decode("utf-8").replace("</layer>", hl + "\n</layer>")
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(content)
    raw2, _ = xopp.parse_learn_file(p)
    assert len(next(iter(raw2.values())).strokes) == len(cell.strokes)
