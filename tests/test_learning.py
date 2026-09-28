"""learning: học từ file .xopp đã viết tay, có/không có ô đo cỡ tay."""
import pytest

from chuviettay.model import xopp
from chuviettay.model.bank import Bank
from chuviettay.model.learning import learn_from_files


def scaled(strokes, k):
    return [[v * k for v in st] for st in strokes]


def test_hoc_khong_co_o_do_co_tay(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba", "chào"], tiny_bank, "h",
                   {"ba": [[0, 0, 4, -5, 8, 0]], "chào": [[0, 0, 5, -6, 10, 0, 14, -5], [7, -11, 9, -9]]}, calib=False)
    r = learn_from_files(tiny_bank, [p])
    assert r.n_added == 2 and r.file_notes == []
    assert len(tiny_bank.words["ba"]) == 3 and len(tiny_bank.words["chào"]) == 3
    new = tiny_bank.words["chào"][-1]
    assert new["T"] == "\u0300" and new["ti"] == 1 and new["w"] == pytest.approx(14.0, abs=0.02)


def test_hoc_tu_chinh_co_tay_khi_viet_to_gap_doi(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    ref = tiny_bank.words["xin"][0]["s"]
    xopp.make_grid(p, ["ba"], tiny_bank, "h",
                   {"xin": scaled(ref, 2), "ba": scaled([[0, 0, 4, -5, 8, 0]], 2)}, calib=True)
    r = learn_from_files(tiny_bank, [p])
    assert r.n_added == 2
    assert len(r.file_notes) == 1 and "to hơn" in r.file_notes[0] and "2.0" in r.file_notes[0] and "g.xopp" in r.file_notes[0]
    assert tiny_bank.words["ba"][-1]["w"] == pytest.approx(8.0, abs=0.05)     # 16 * 0.5
    assert tiny_bank.words["xin"][-1]["w"] == pytest.approx(9.0, abs=0.05)    # về đúng cỡ đã học


def test_viet_nho_hon_thi_phong_to(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    ref = tiny_bank.words["xin"][0]["s"]
    xopp.make_grid(p, [], tiny_bank, "h", {"xin": scaled(ref, 0.5)}, calib=True)
    r = learn_from_files(tiny_bank, [p])
    assert "nhỏ hơn" in r.file_notes[0]
    assert tiny_bank.words["xin"][-1]["w"] == pytest.approx(9.0, abs=0.05)


def test_lech_nho_duoi_5_phan_tram_thi_khong_thong_bao(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    ref = tiny_bank.words["xin"][0]["s"]
    xopp.make_grid(p, [], tiny_bank, "h", {"xin": scaled(ref, 1.03)}, calib=True)
    assert learn_from_files(tiny_bank, [p]).file_notes == []


def test_luu_kho_mot_lan_o_cuoi_va_nhieu_file_cong_don(tiny_bank, tmp_path):
    files = []
    for i in range(2):
        p = str(tmp_path / ("g%d.xopp" % i))
        xopp.make_grid(p, ["ba"], tiny_bank, "h", {"ba": [[0, 0, 4, -5, 8, 0]]}, calib=False)
        files.append(p)
    r = learn_from_files(tiny_bank, files)
    assert r.n_added == 2
    assert len(Bank(tiny_bank.path).words["ba"]) == 4       # 2 mẫu cũ + 2 mới, đã ghi xuống đĩa


def test_file_chua_viet_gi_thi_khong_them_mau(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba"], tiny_bank, "h", calib=False)
    assert learn_from_files(tiny_bank, [p]).n_added == 0
