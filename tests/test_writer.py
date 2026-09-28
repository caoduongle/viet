"""Writer: ghép token thành nét -- nhánh khớp thẳng / ghép dấu thanh / số / dấu câu / thiếu mẫu."""
import random

import pytest

from chuviettay.model.writer import Writer


def W(bank, seed=1, **kw):
    return Writer(bank, random.Random(seed), **kw)


def test_khop_thang(tiny_bank):
    st, w, miss = W(tiny_bank).token("xin")
    assert miss == [] and len(st) == 1 and w in (8.8, 8.9, 9.0, 9.1, 9.2)


def test_ghep_dau_thanh_tu_than_chu_va_net_dau_roi(tiny_bank):
    st, w, miss = W(tiny_bank).token("bà")
    assert miss == []
    assert len(st) == 2                    # 1 nét thân "ba" + 1 nét dấu huyền ghép vào
    assert w in (8.0, 8.4)                 # độ rộng lấy theo thân chữ
    tone_stroke = st[1]
    assert min(tone_stroke[1::2]) < -5     # dấu nằm phía trên thân chữ (y âm = lên trên)


def test_thieu_dau_thanh_thi_bao_thieu_ca_tu(tiny_bank):
    st, w, miss = W(tiny_bank).token("bá")
    assert st == [] and miss == ["bá"] and w > 0


def test_chu_hoa_dau_tu_loose_va_strict(tiny_bank):
    assert W(tiny_bank).token("Xin")[2] == []
    assert W(tiny_bank, loose_case=False).token("Xin")[2] == ["Xin"]


def test_so_ghep_tung_chu_so_voi_khoang_cach(tiny_bank):
    st, w, miss = W(tiny_bank).token("12")
    assert miss == [] and len(st) == 2
    assert w == pytest.approx(3.0 + 3.5 + 4.0)      # '1' rộng 3, khoảng cách dgaps 3.5, '2' rộng 4


def test_so_thieu_chu_so_thi_bao_dung_chu_so_thieu(tiny_bank):
    st, w, miss = W(tiny_bank).token("1,5")
    assert miss == ["5"] and len(st) == 2            # '1' và dấu phẩy có, chữ số 5 chưa có mẫu


def test_dau_cau_bao_quanh(tiny_bank):
    st, w, miss = W(tiny_bank).token("xin.")
    assert miss == [] and len(st) == 2               # 1 nét chữ + 1 dấu chấm
    st2, _, miss2 = W(tiny_bank).token("(xin)")
    assert miss2 == ["(", ")"]                       # chưa có mẫu ngoặc -> báo thiếu, phần chữ vẫn viết


def test_token_toan_dau_cau_chua_co_mau(tiny_bank):
    assert W(tiny_bank).token("?!")[2] == ["?!"]


def test_pick_khong_chon_trung_lien_tiep(tiny_bank):
    wr = W(tiny_bank, seed=42)
    lst = list(range(5))
    seq = [wr.pick(lst, "t") for _ in range(200)]
    assert all(a != b for a, b in zip(seq, seq[1:]))
    assert wr.pick([7], "u") == 7                    # chỉ 1 lựa chọn -> vẫn chọn được


def test_cung_seed_cung_ket_qua(tiny_bank):
    a = [W(tiny_bank, seed=9).token(t) for t in ("xin", "bà", "12", "xin.")]
    b = [W(tiny_bank, seed=9).token(t) for t in ("xin", "bà", "12", "xin.")]
    assert a == b


def test_khong_thay_doi_du_lieu_kho_khi_ghep(tiny_bank):
    before = repr(tiny_bank.words)
    for t in ("xin", "bà", "12", "xin.", "(xin)"):
        W(tiny_bank).token(t)
    assert repr(tiny_bank.words) == before           # shift() luôn tạo nét mới, không sửa mẫu gốc
