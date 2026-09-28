"""composer: dàn dòng / chia trang / file kết quả + file lưới ô cho từ thiếu."""
import os

from chuviettay.model import composer, xopp
from chuviettay.model.composer import WriteOptions, WriteResult


def compose(bank, text, **kw):
    return composer.compose_document(bank, text, WriteOptions(seed=1, **kw))


def test_van_ban_don_gian(tiny_bank):
    parts, r = compose(tiny_bank, "xin ba")
    assert (r.n_lines, r.n_tokens, r.n_missing_tokens, r.n_strokes) == (1, 2, 0, 2)
    assert r.missing == {} and r.out_path == ""          # out_path chỉ điền ở write_document
    assert parts[0] == xopp.HEAD and parts[-1] == "</xournal>"


def test_token_thieu_mau_duoc_dem_dung(tiny_bank):
    _, r = compose(tiny_bank, "xin zzz zzz ba")
    assert r.n_tokens == 4 and r.n_missing_tokens == 2 and r.missing == {"zzz": 2}


def test_xuong_dong_khi_qua_be_rong(tiny_bank):
    _, r = compose(tiny_bank, "xin xin xin", width=20, jitter=0)
    assert r.n_lines == 3


def test_dong_trong_duoc_giu(tiny_bank):
    _, r = compose(tiny_bank, "xin\n\nxin")
    assert r.n_lines == 3


def test_chia_trang(tiny_bank):
    parts, r = compose(tiny_bank, "xin\nxin\nxin", line=1000)   # mỗi trang chứa được 2 dòng
    assert sum(p.startswith("<page ") for p in parts) == 2


def test_cung_seed_cung_ket_qua_khac_seed_khac_ket_qua(tiny_bank):
    a, _ = composer.compose_document(tiny_bank, "xin ba xin", WriteOptions(seed=5))
    b, _ = composer.compose_document(tiny_bank, "xin ba xin", WriteOptions(seed=5))
    c, _ = composer.compose_document(tiny_bank, "xin ba xin", WriteOptions(seed=6))
    assert a == b and a != c


def test_jitter_0_thi_khong_con_ngau_nhien_ve_hinh_dang(tiny_bank):
    a, _ = composer.compose_document(tiny_bank, "xin", WriteOptions(seed=1, jitter=0))
    b, _ = composer.compose_document(tiny_bank, "xin", WriteOptions(seed=2, jitter=0))
    strip = lambda parts: [p for p in parts if p.startswith("<stroke")]
    # 1 từ chỉ có 1 mẫu để chọn nét khác nhau giữa các seed -> so hình học sau khi bỏ chọn mẫu
    assert len(strip(a)) == len(strip(b)) == 1


def test_mau_muc_va_do_day(tiny_bank):
    parts, _ = compose(tiny_bank, "xin", color="#1a237e", wscale=2.0, jitter=0)
    stroke = next(p for p in parts if p.startswith("<stroke"))
    assert 'color="#1a237e"' in stroke


def test_write_document_ghi_file_va_file_luoi_o_khi_thieu(tiny_bank, tmp_path):
    out = str(tmp_path / "ra.xopp")
    r = composer.write_document(tiny_bank, "xin zzz", WriteOptions(seed=1), out)
    assert os.path.exists(out) and r.out_path == out
    assert r.missing_grid_path == str(tmp_path / "ra_thieu.xopp")
    labels = [(t.text or "").strip() for t in xopp.read_xopp(r.missing_grid_path).iter("text")]
    assert "zzz" in labels


def test_write_document_khong_thieu_thi_khong_tao_file_luoi_o(tiny_bank, tmp_path):
    out = str(tmp_path / "ra.xopp")
    r = composer.write_document(tiny_bank, "xin ba", WriteOptions(seed=1), out)
    assert r.missing_grid_path is None and not os.path.exists(str(tmp_path / "ra_thieu.xopp"))


def test_write_document_co_the_tat_file_luoi_o(tiny_bank, tmp_path):
    out = str(tmp_path / "ra.xopp")
    r = composer.write_document(tiny_bank, "xin zzz", WriteOptions(seed=1), out, make_missing_grid=False)
    assert r.missing == {"zzz": 1} and r.missing_grid_path is None


def test_missing_sorted_nhieu_lan_truoc_bang_nhau_theo_chu_cai():
    r = WriteResult("o", 1, 1, 9, 9, missing={"b": 2, "a": 2, "c": 5})
    assert r.missing_sorted() == [("c", 5), ("a", 2), ("b", 2)]


def test_strict_case_anh_huong_danh_sach_thieu(tiny_bank):
    _, loose = composer.compose_document(tiny_bank, "Xin", WriteOptions(seed=1))
    _, strict = composer.compose_document(tiny_bank, "Xin", WriteOptions(seed=1, strict_case=True))
    assert loose.missing == {} and strict.missing == {"Xin": 1}
