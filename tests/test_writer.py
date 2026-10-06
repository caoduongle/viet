"""Writer: ghép token thành nét -- nhánh khớp thẳng / ghép dấu thanh / số / dấu câu / thiếu mẫu."""
import random

import pytest

from chuviettay.model.writer import Writer


def W(bank, seed=1, **kw):
    return Writer(bank, random.Random(seed), **kw)


def test_ghep_tu_ky_tu_don(tiny_bank):
    st, w, miss = W(tiny_bank).token("xin")
    assert miss == [] and len(st) == 3 and w > 0


def test_ghep_dau_thanh_tu_than_chu_va_net_dau_roi(tiny_bank):
    st, w, miss = W(tiny_bank).token("bà")
    assert miss == []
    assert len(st) == 3                    # nét b + nét a + nét dấu huyền
    assert w > 0
    tone_stroke = st[2]
    assert min(tone_stroke[1::2]) < -5     # dấu nằm phía trên thân chữ (y âm = lên trên)


def test_thieu_dau_thanh_thi_bao_thieu_ky_tu(tiny_bank):
    st, w, miss = W(tiny_bank).token("bá")
    assert st == [] and miss == ["\u0301"] and w > 0


def test_chu_hoa_dau_tu_loose_va_strict(tiny_bank):
    assert W(tiny_bank).token("Xin")[2] == []
    assert W(tiny_bank, loose_case=False).token("Xin")[2] == ["X"]


def test_so_ghep_tung_chu_so_voi_khoang_cach(tiny_bank):
    st, w, miss = W(tiny_bank).token("12")
    assert miss == [] and len(st) == 2
    assert w == pytest.approx(3.0 + 3.5 + 4.0)      # '1' rộng 3, khoảng cách dgaps 3.5, '2' rộng 4


def test_so_thieu_chu_so_thi_bao_dung_chu_so_thieu(tiny_bank):
    st, w, miss = W(tiny_bank).token("1,5")
    assert miss == ["5"] and len(st) == 2            # '1' và dấu phẩy có, chữ số 5 chưa có mẫu


def test_dau_cau_bao_quanh(tiny_bank):
    st, w, miss = W(tiny_bank).token("xin.")
    assert miss == [] and len(st) == 4               # 3 nét chữ 'x', 'i', 'n' + 1 dấu chấm
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


def test_standalone_punctuation_without_w_in_bank(tiny_bank):
    # Punctuation sample in legacy bank does not have 'w' attribute
    tiny_bank.punct[","] = [{"s": [[0.0, 0.0, 1.0, 2.0]]}]
    wr = W(tiny_bank)
    strokes, w, miss = wr.token(",")
    assert len(strokes) == 1
    assert w > 0
    assert miss == []


def test_writer_does_not_use_bank_words(tiny_bank):
    # Đặt một mẫu giả dị biệt vào bank.words["xin"]
    tiny_bank.words["xin"] = [{"w": 999.0, "s": [[0, 0, 999, 999]], "T": "", "vi": -1, "ti": -1}]
    wr = W(tiny_bank)
    st, w, miss = wr.token("xin")
    assert miss == []
    # Khẳng định Writer hoàn toàn không lấy mẫu 999.0 từ bank.words
    assert w != 999.0
    assert not any(stk == [0, 0, 999, 999] for stk in st)
    assert len(st) == 3

