"""Bank: nạp/lưu/tạo mới/thêm-xoá mẫu/chỉ mục tra cứu."""
import gzip
import os
import json

import pytest

from chuviettay.config import NANG, TONES
from chuviettay.model.bank import Bank, BankNotFoundError


def test_nap_kho_nho(tiny_bank):
    assert set(tiny_bank.words) == {"xin", "ba", "chào"}
    assert tiny_bank.xh == 7.0
    assert set(tiny_bank.digits) == {"1", "2"}


def test_thieu_file_nem_BankNotFoundError_chu_khong_thoat_chuong_trinh(tmp_path):
    p = str(tmp_path / "khong_co.json.gz")
    with pytest.raises(BankNotFoundError) as ei:
        Bank(p)
    assert p in str(ei.value)
    assert isinstance(ei.value, FileNotFoundError)


def test_create_empty_va_load_or_create(tmp_path):
    p = str(tmp_path / "moi.json.gz")
    b = Bank.load_or_create(p)                                   # chưa có -> tạo
    assert b.words == {} and b.xh == 7.0
    b.add_sample("xin", [[0, 0, 3, -5]], 3.0)
    b.rebuild(); b.save()
    again = Bank.load_or_create(p)                               # đã có -> KHÔNG ghi đè
    assert "xin" in again.words


def test_rebuild_tao_chi_muc_than_chu_va_dau_thanh(tiny_bank):
    assert {k for k in tiny_bank.tl} == {"ba", "chao", "xin"}
    assert len(tiny_bank.tl["chao"]) == 2
    assert len(tiny_bank.marks["\u0300"]) == 2                   # 2 mẫu "chào" cho ra 2 nét dấu huyền rời
    assert all(len(tiny_bank.marks[t]) == 0 for t in TONES if t != "\u0300")


def test_marks_da_quy_ve_goc_toa_do(tiny_bank):
    for m in tiny_bank.marks["\u0300"]:
        xs, ys = m["s"][0][0::2], m["s"][0][1::2]
        assert sum(xs) / len(xs) == pytest.approx(0, abs=1e-9)
        assert sum(ys) / len(ys) == pytest.approx(0, abs=1e-9)


def test_can(tiny_bank):
    assert tiny_bank.can("ba")            # có thẳng
    assert tiny_bank.can("bà")            # ghép thân "ba" + dấu huyền rời
    assert not tiny_bank.can("bá")        # có thân nhưng chưa có nét dấu sắc để ghép
    assert tiny_bank.can("chao")          # không dấu: dùng thân của "chào"
    assert not tiny_bank.can("zzz")


def test_add_sample_tu_tim_net_dau_thanh(tiny_bank):
    body, tone = [0, 0, 5, -5, 10, 0], [4, -12, 6, -10]
    inst = tiny_bank.add_sample("bà", [body, tone], 10.004)
    assert inst["T"] == "\u0300" and inst["vi"] == 1 and inst["ti"] == 1
    assert inst["w"] == 10.0                                      # làm tròn 2 số lẻ
    assert tiny_bank.words["bà"] == [inst]


def test_add_sample_cum_nhieu_tu_khong_tim_dau_thanh(tiny_bank):
    # Cùng bộ nét, chỉ khác nhãn: từ đơn thì nhận ra nét dấu, cụm có khoảng trắng thì KHÔNG dò
    # (cặp đối chứng -- nếu bỏ điều kiện `" " not in label` thì cụm cũng ra ti=1 và test này vỡ).
    body, tone = [0, 0, 5, -5, 10, 0], [4, -12, 6, -10]
    single = tiny_bank.add_sample("bà", [body, tone], 10)
    phrase = tiny_bank.add_sample("bà ba", [body, tone], 20)
    assert single["ti"] == 1
    assert phrase["ti"] == -1


def test_add_sample_khong_tu_rebuild(tiny_bank):
    tiny_bank.add_sample("bà", [[0, 0, 5, -5, 10, 0], [4, -12, 6, -10]], 10)
    assert "bà" not in [k for k, _ in sum(tiny_bank.tl.values(), [])]   # chỉ mục chưa cập nhật
    tiny_bank.rebuild()
    assert any(k == "bà" for k, _ in sum(tiny_bank.tl.values(), []))


def test_drop(tiny_bank):
    assert tiny_bank.drop("ba") == 2
    assert tiny_bank.drop("ba") == 0
    assert "ba" not in tiny_bank.words


def test_save_roi_nap_lai_giu_nguyen_tieng_viet(tiny_bank, tmp_path):
    tiny_bank.add_sample("bà", [[0, 0, 5, -5, 10, 0], [4, -12, 6, -10]], 10)
    tiny_bank.save()
    again = Bank(tiny_bank.path)
    assert "bà" in again.words and again.words["bà"][0]["ti"] == 1
    raw = gzip.decompress(open(tiny_bank.path, "rb").read()).decode("utf-8")
    assert "chào" in raw                                          # ensure_ascii=False: đọc được bằng mắt
    assert json.loads(raw)["xh"] == 7.0


def test_kho_that_nap_duoc_va_chi_muc_hop_ly(real_bank):
    assert len(real_bank.words) == 362
    assert sum(len(v) for v in real_bank.words.values()) == 859
    assert len(real_bank.marks[NANG]) > 0
    assert real_bank.can("số") and real_bank.can("sổ")            # "sổ" chưa dạy nhưng ghép được


# ------------------------------------------------------------ ghi an toàn
def test_save_bi_ngat_giua_chung_thi_kho_cu_con_nguyen_va_khong_de_lai_file_tam(tiny_bank, monkeypatch):
    """Mô phỏng mất điện/đầy đĩa GIỮA lúc ghi: file kho mẫu cũ phải còn đọc được như trước."""
    import json as _json
    before = open(tiny_bank.path, "rb").read()
    tiny_bank.add_sample("mới", [[0, 0, 4, -5]], 4.0)

    real_dump = _json.dump
    def dump_roi_ngat(obj, fp, **kw):
        fp.write("{\"xh\": 7.0, \"words\": {\"x\"")          # ghi dở dang rồi 'mất điện'
        raise OSError("đĩa đầy")
    monkeypatch.setattr("chuviettay.model.bank.json.dump", dump_roi_ngat)
    with pytest.raises(OSError, match="đĩa đầy"):
        tiny_bank.save()
    monkeypatch.setattr("chuviettay.model.bank.json.dump", real_dump)

    assert open(tiny_bank.path, "rb").read() == before                   # file thật không suy suyển một byte
    assert not os.path.exists(tiny_bank.path + ".tmp")                    # không để rác lại
    assert "mới" not in Bank(tiny_bank.path).words                        # vẫn nạp lại bình thường


def test_save_thanh_cong_khong_de_lai_file_tam(tiny_bank):
    tiny_bank.add_sample("mới", [[0, 0, 4, -5]], 4.0)
    tiny_bank.save()
    assert not os.path.exists(tiny_bank.path + ".tmp")
    assert "mới" in Bank(tiny_bank.path).words
