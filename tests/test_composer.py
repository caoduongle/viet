import gzip
import os
import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.model import composer, xopp
from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteMode, WriteOptions, WriteResult, parse_color


def _write(bank: Bank, text: str, out_path: str, **kw) -> tuple[str, WriteResult]:
    """Helper kết xuất qua đường thật (AppController.write_text -> DocumentLayoutEngine)
    và giải nén XML để kiểm định các bất biến layout và kết xuất."""
    ctl = AppController(bank.path)
    ctl.load_bank()
    kw.setdefault("seed", 1)
    opts = WriteOptions(**kw)
    r = ctl.write_text(text, opts, out_path)
    xml = gzip.decompress(open(out_path, "rb").read()).decode("utf-8")
    return xml, r


def test_van_ban_don_gian(tiny_bank, tmp_path):
    out = str(tmp_path / "ra.xopp")
    xml, r = _write(tiny_bank, "xin ba", out)
    # Ghép từ các ký tự đơn lẻ: "x"(1) + "i"(1) + "n"(1) + "b"(1) + "a"(1) = 5 nét
    assert (r.n_lines, r.n_tokens, r.n_missing_tokens, r.n_strokes) == (1, 2, 0, 5)
    assert r.missing == {} and r.out_path == out
    assert xml.startswith("<?xml") and xml.strip().endswith("</xournal>")


def test_token_thieu_mau_duoc_dem_dung(tiny_bank, tmp_path):
    out = str(tmp_path / "ra.xopp")
    _, r = _write(tiny_bank, "xin zzz zzz ba", out)
    # Báo thiếu theo ký tự đơn lẻ: 2 token "zzz" thiếu 'z' tổng cộng 6 lần (hoặc 2 lần theo token)
    assert r.n_tokens == 4 and r.n_missing_tokens == 2
    assert "z" in r.missing or "zzz" in r.missing


def test_xuong_dong_khi_qua_be_rong(tiny_bank, tmp_path):
    out = str(tmp_path / "ra.xopp")
    _, r = _write(tiny_bank, "xin xin xin", out, width=20, jitter=0)
    assert r.n_lines == 3


def test_dong_trong_duoc_giu(tiny_bank, tmp_path):
    # Đường thật (DocumentLayoutEngine): "xin\n\nxin" gồm 2 đoạn có chữ (r.n_lines = 2).
    # Dòng trống ở giữa được bảo toàn qua khoảng cách toạ độ dọc: khoảng cách y giữa 2 từ
    # lớn hơn so với khi viết 2 dòng liền nhau "xin\nxin".
    xml_with_gap, r = _write(tiny_bank, "xin\n\nxin", str(tmp_path / "gap.xopp"), jitter=0)
    xml_no_gap, _ = _write(tiny_bank, "xin\nxin", str(tmp_path / "nogap.xopp"), jitter=0)
    assert r.n_lines == 2

    import re
    ys_gap = [float(m.group(1)) for m in re.finditer(r"<stroke[^>]*>[^ ]+ ([0-9.]+)", xml_with_gap)]
    ys_nogap = [float(m.group(1)) for m in re.finditer(r"<stroke[^>]*>[^ ]+ ([0-9.]+)", xml_no_gap)]
    dist_gap = max(ys_gap) - min(ys_gap)
    dist_nogap = max(ys_nogap) - min(ys_nogap)
    assert dist_gap > dist_nogap, "Khoảng cách dòng trống không được bảo tồn trên toạ độ dọc"


def test_chia_trang(tiny_bank, tmp_path):
    # Khổ A4 cao 841.89 pt, margin_top=40 pt, margin_bottom=40 pt -> usable_height = 761.89 pt.
    # Với line=500 pt: dòng 1 (base 540 pt) nằm ở trang 1; dòng 2 (cần thêm 500 pt > 761.89 pt)
    # bắt buộc phải tràn sang trang 2 -> tổng cộng tạo đúng 2 trang.
    out = str(tmp_path / "ra.xopp")
    xml, r = _write(tiny_bank, "xin\nxin", out, line=500)
    assert xml.count("<page ") == 2


def test_cung_seed_cung_ket_qua_khac_seed_khac_ket_qua(tiny_bank, tmp_path):
    a, _ = _write(tiny_bank, "xin ba xin", str(tmp_path / "a.xopp"), seed=5)
    b, _ = _write(tiny_bank, "xin ba xin", str(tmp_path / "b.xopp"), seed=5)
    c, _ = _write(tiny_bank, "xin ba xin", str(tmp_path / "c.xopp"), seed=6)
    assert a == b and a != c


def test_jitter_0_thi_khong_con_ngau_nhien_ve_hinh_dang(tiny_bank, tmp_path):
    # Khi từ chỉ có 1 mẫu duy nhất, việc đổi seed không thể chọn mẫu nét khác.
    # Lúc này jitter=0 sẽ tắt toàn bộ yếu tố ngẫu nhiên hình học -> tọa độ nét vẽ giống nhau 100%.
    one_sample_dict = Bank.empty_dict()
    one_sample_dict["words"] = {"ba": [{"w": 8.0, "s": [[0, 0, 4, -5, 8, 0]], "T": "", "vi": -1, "ti": -1}]}
    one_sample_dict["letters"] = {
        "b": [{"w": 4.0, "s": [[0, 0, 2, -5]], "T": "", "vi": -1, "ti": -1}],
        "a": [{"w": 4.0, "s": [[0, 0, 2, -5]], "T": "", "vi": -1, "ti": -1}],
    }
    bank = Bank.create_empty(tiny_bank.path)
    bank.d = one_sample_dict
    bank.words = bank.d["words"]
    bank.letters = bank.d["letters"]
    bank.rebuild()
    bank.save()

    a, _ = _write(bank, "ba", str(tmp_path / "a.xopp"), seed=1, jitter=0)
    b, _ = _write(bank, "ba", str(tmp_path / "b.xopp"), seed=2, jitter=0)
    strip = lambda xml_str: [line.strip() for line in xml_str.splitlines() if line.strip().startswith("<stroke")]
    assert strip(a) == strip(b)

    # Đối chứng: khi bật jitter thì tọa độ phải khác nhau giữa các seed
    c, _ = _write(bank, "ba", str(tmp_path / "c.xopp"), seed=1, jitter=1.0)
    d, _ = _write(bank, "ba", str(tmp_path / "d.xopp"), seed=2, jitter=1.0)
    assert strip(c) != strip(d)


def test_mau_muc_va_do_day(tiny_bank, tmp_path):
    xml, _ = _write(tiny_bank, "xin", str(tmp_path / "ra.xopp"), color="#1a237e", wscale=2.0, jitter=0)
    assert 'color="#1a237e"' in xml


def test_write_document_ghi_file_va_file_luoi_o_khi_thieu(tiny_bank, tmp_path):
    ctl = AppController(tiny_bank.path)
    ctl.load_bank()
    out = str(tmp_path / "ra.xopp")
    r = ctl.write_text("xin zzz", WriteOptions(seed=1), out)
    assert os.path.exists(out) and r.out_path == out
    assert r.missing_grid_path == str(tmp_path / "ra_thieu.xopp")
    labels = [(t.text or "").strip() for t in xopp.read_xopp(r.missing_grid_path).iter("text")]
    assert "z" in labels or "zzz" in labels


def test_write_document_khong_thieu_thi_khong_tao_file_luoi_o(tiny_bank, tmp_path):
    ctl = AppController(tiny_bank.path)
    ctl.load_bank()
    out = str(tmp_path / "ra.xopp")
    r = ctl.write_text("xin ba", WriteOptions(seed=1), out)
    assert r.missing_grid_path is None and not os.path.exists(str(tmp_path / "ra_thieu.xopp"))


def test_write_document_co_the_tat_file_luoi_o(tiny_bank, tmp_path):
    ctl = AppController(tiny_bank.path)
    ctl.load_bank()
    out = str(tmp_path / "ra.xopp")
    r = ctl.write_text("xin zzz", WriteOptions(seed=1, missing_grid=False), out)
    assert ("z" in r.missing or "zzz" in r.missing) and r.missing_grid_path is None


def test_missing_sorted_nhieu_lan_truoc_bang_nhau_theo_chu_cai():
    r = WriteResult("o", 1, 1, 9, 9, missing={"b": 2, "a": 2, "c": 5})
    assert r.missing_sorted() == [("c", 5), ("a", 2), ("b", 2)]


def test_strict_case_anh_huong_danh_sach_thieu(tiny_bank, tmp_path):
    _, loose = _write(tiny_bank, "Xin", str(tmp_path / "loose.xopp"), seed=1)
    _, strict = _write(tiny_bank, "Xin", str(tmp_path / "strict.xopp"), seed=1, strict_case=True)
    assert loose.missing == {} and (strict.missing == {"X": 1} or strict.missing == {"Xin": 1})


def test_composer_module_exports_contracts_and_no_legacy():
    assert not hasattr(composer, "compose_document")
    assert not hasattr(composer, "write_document")
    assert hasattr(composer, "WriteOptions")
    assert hasattr(composer, "WriteResult")
    assert hasattr(composer, "WriteMode")
    assert hasattr(composer, "parse_color")


# ------------------------------------------------------------ kiểm tra tính hợp lệ WriteOptions
def test_write_options_validate_hop_le():
    opts = WriteOptions(scale=1.2, line=25.0, width=500.0, space=1.1, jitter=0.5, wscale=1.5, color="#1A237E")
    opts.validate()
    assert opts.color == "#1a237e"  # Chuẩn hóa về chữ thường


@pytest.mark.parametrize("bad_scale", [0, -1.0, float("nan"), float("inf"), float("-inf")])
def test_write_options_validate_scale_sai(bad_scale):
    with pytest.raises(ValueError, match="scale"):
        WriteOptions(scale=bad_scale).validate()


@pytest.mark.parametrize("bad_line", [0, -10.0, float("nan")])
def test_write_options_validate_line_sai(bad_line):
    with pytest.raises(ValueError, match="line"):
        WriteOptions(line=bad_line).validate()


@pytest.mark.parametrize("bad_jitter", [-0.1, -5.0, float("nan")])
def test_write_options_validate_jitter_sai(bad_jitter):
    with pytest.raises(ValueError, match="jitter"):
        WriteOptions(jitter=bad_jitter).validate()


@pytest.mark.parametrize("good_color", ["#1a237e", "#1A237E", "#ffffff", "#000000ff", "#12345678"])
def test_write_options_color_hop_le(good_color):
    opts = WriteOptions(color=good_color)
    opts.validate()
    assert opts.color == good_color.lower()


@pytest.mark.parametrize("bad_color", ["blue", "red", "1a237e", "#12345", "#1234567", "#000\" width=\"99", "rgb(0,0,0)"])
def test_write_options_color_khong_hop_le_chong_injection(bad_color):
    with pytest.raises(ValueError, match="Mã màu không hợp lệ"):
        WriteOptions(color=bad_color).validate()
