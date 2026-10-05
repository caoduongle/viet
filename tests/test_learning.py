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
    # Truyền dedup=False vì test dùng lại chính mẫu nét từ tiny_bank để kiểm tra học không calib
    r = learn_from_files(tiny_bank, [p], dedup=False)
    assert r.n_added == 2 and r.file_notes == []
    assert len(tiny_bank.words["ba"]) == 3 and len(tiny_bank.words["chào"]) == 3
    new = tiny_bank.words["chào"][-1]
    assert new["T"] == "\u0300" and new["ti"] == 1 and new["w"] == pytest.approx(14.0, abs=0.02)


def test_hoc_tu_chinh_co_tay_khi_viet_to_gap_doi(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    ref = tiny_bank.words["xin"][0]["s"]
    xopp.make_grid(p, ["ba"], tiny_bank, "h",
                   {"xin": scaled(ref, 2), "ba": scaled([[0, 0, 4, -5, 8, 0]], 2)}, calib=True)
    # Truyền dedup=False vì mẫu ref sau khi chỉnh cỡ sẽ khớp lại mẫu gốc trong tiny_bank
    r = learn_from_files(tiny_bank, [p], dedup=False)
    assert r.n_added == 2
    assert len(r.file_notes) == 1 and "to hơn" in r.file_notes[0] and "2.0" in r.file_notes[0] and "g.xopp" in r.file_notes[0]
    assert tiny_bank.words["ba"][-1]["w"] == pytest.approx(8.0, abs=0.05)     # 16 * 0.5
    assert tiny_bank.words["xin"][-1]["w"] == pytest.approx(9.0, abs=0.05)    # về đúng cỡ đã học


def test_viet_nho_hon_thi_phong_to(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    ref = tiny_bank.words["xin"][0]["s"]
    xopp.make_grid(p, [], tiny_bank, "h", {"xin": scaled(ref, 0.5)}, calib=True)
    # Truyền dedup=False vì mẫu ref sau khi chỉnh cỡ sẽ khớp lại mẫu gốc trong tiny_bank
    r = learn_from_files(tiny_bank, [p], dedup=False)
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
    # Truyền dedup=False để giữ nguyên ý định kiểm tra gộp nhiều file cộng dồn mẫu khi tắt khử trùng
    r = learn_from_files(tiny_bank, files, dedup=False)
    assert r.n_added == 2
    assert len(Bank(tiny_bank.path).words["ba"]) == 4       # 2 mẫu cũ + 2 mới, đã ghi xuống đĩa


def test_file_chua_viet_gi_thi_khong_them_mau(tiny_bank, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba"], tiny_bank, "h", calib=False)
    assert learn_from_files(tiny_bank, [p]).n_added == 0


def test_hoc_ky_hieu_toan_hoc(tiny_bank, tmp_path):
    p = str(tmp_path / "sym_grid.xopp")
    xopp.make_grid(
        p,
        ["∑", "\\alpha"],
        tiny_bank,
        "h",
        {"∑": [[0, 0, 4, -5, 8, 0]], "\\alpha": [[0, -5, 4, 0, 8, -5]]},
        calib=False,
    )
    r = learn_from_files(tiny_bank, [p])
    assert r.n_added == 2
    # Phải được lưu vào symbols chứ không phải words
    assert "∑" in tiny_bank.symbols
    assert len(tiny_bank.symbols["∑"]) == 1
    assert "\\alpha" in tiny_bank.symbols
    assert len(tiny_bank.symbols["\\alpha"]) == 1
    assert "∑" not in tiny_bank.words


def test_d3_learn_idempotent_with_gzip_header_change_and_duplicate_samples(tiny_bank, tmp_path):
    """D3: learn_from_files phải idempotent khi cùng nội dung XML dù header gzip đổi mtime hoặc file khác."""
    import gzip
    samples = {"khoai": [[0.0, -5.0, 3.0, 0.0, 6.0, -5.0]]}
    f1 = str(tmp_path / "g1.xopp")
    f2 = str(tmp_path / "g2.xopp")
    xopp.make_grid(f1, ["khoai"], tiny_bank, "t", samples=samples, calib=False, grid_version="hw3")

    raw = gzip.decompress(open(f1, "rb").read())
    with open(f2, "wb") as raw_f, gzip.GzipFile(fileobj=raw_f, mode="wb", mtime=1234567890) as g:
        g.write(raw)

    r1 = learn_from_files(tiny_bank, [f1])
    assert r1.n_added == 1
    n1 = len(tiny_bank.words.get("khoai", []))

    r2 = learn_from_files(tiny_bank, [f2])
    assert r2.n_added == 0, f"Học lại file cùng nội dung phải idempotent, nhưng r2.n_added = {r2.n_added}"
    n2 = len(tiny_bank.words.get("khoai", []))
    assert n2 == n1, f"Số mẫu 'khoai' bị tăng sau khi học lại file cùng nội dung: {n1} -> {n2}"


def test_d3_learn_symbols_and_cells_dedup(tiny_bank, tmp_path):
    """D3: add_symbol_sample hỗ trợ dedup và learn_from_files khử trùng từng ô."""
    f1 = str(tmp_path / "sym1.xopp")
    f2 = str(tmp_path / "sym2.xopp")
    xopp.make_grid(f1, ["π"], tiny_bank, "t", samples={"π": [[0.0, 0.0, 5.0, 5.0]]}, calib=False)
    xopp.make_grid(f2, ["π", "chào"], tiny_bank, "t", samples={"π": [[0.0, 0.0, 5.0, 5.0]], "chào": [[0.0, 0.0, 10.0, 10.0]]}, calib=False)

    r1 = learn_from_files(tiny_bank, [f1])
    assert r1.n_added == 1
    assert len(tiny_bank.symbols.get("π", [])) == 1

    r2 = learn_from_files(tiny_bank, [f2])
    # π đã có mẫu nét trùng nên dedup, chỉ thêm 'chào'
    assert r2.n_added == 1
    assert len(tiny_bank.symbols.get("π", [])) == 1
    assert len(tiny_bank.words.get("chào", [])) == 3


