"""AppController: mọi thao tác nghiệp vụ mà CLI và GUI dùng chung."""
import os

import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.model import xopp
from chuviettay.model.bank import Bank, BankNotFoundError

BODY, TONE = [0, 0, 5, -5, 10, 0], [4, -12, 6, -10]


@pytest.fixture
def ctl(tiny_bank_path):
    c = AppController(tiny_bank_path)
    c.load_bank()
    return c


def test_chua_mo_kho_thi_bao_loi_ro_rang(tiny_bank_path):
    with pytest.raises(RuntimeError, match="load_bank"):
        AppController(tiny_bank_path).get_stats()


def test_load_bank_thieu_file(tmp_path):
    c = AppController(str(tmp_path / "x.json.gz"))
    with pytest.raises(BankNotFoundError):
        c.load_bank()
    assert c.bank is None
    c.load_bank(create_if_missing=True)                       # kiểu GUI: tự tạo kho trống
    assert c.bank is not None and c.bank.words == {}


def test_doi_kho_thi_dat_lai_he_so_co_tay_con_reload_thi_giu(ctl, tiny_bank_path):
    ctl.session_scale = 0.5
    ctl.reload_bank()
    assert ctl.session_scale == 0.5
    ctl.load_bank(tiny_bank_path)
    assert ctl.session_scale == 1.0


def test_write_text(ctl, tmp_path):
    out = str(tmp_path / "ra.xopp")
    r = ctl.write_text("xin ba zzz", WriteOptions(seed=1), out)
    assert os.path.exists(out) and r.n_tokens == 3 and r.missing == {"z": 3}


def test_get_stats_va_list_words(ctl):
    s = ctl.get_stats()
    assert s.n_letters == 8 and s.n_samples == 14
    assert s.digit_counts == {"1": 1, "2": 1} and s.punct_counts == {",": 1, ".": 1}
    assert list(s.tone_mark_counts.values()) == [2, 0, 0, 0, 0]       # huyền, sắc, ngã, hỏi, nặng
    assert ctl.list_words() == [("ba", 2), ("chào", 2), ("xin", 5)]
    assert ctl.bank_size == 13
    assert ctl.x_height == 7.0


def test_drop_words_cong_don_khi_trung_va_luu_xuong_dia(ctl, tiny_bank_path):
    r = ctl.drop_words(["ba", "khong_co", "ba"])
    assert r.removed == {"ba": 2, "khong_co": 0}
    assert "ba" not in Bank(tiny_bank_path).words


def test_missing_seed_words(ctl):
    todo = ctl.missing_seed_words(10 ** 6)
    assert "tôi" in todo and "ba" not in todo and "chào" not in todo and "xin" not in todo
    assert ctl.missing_seed_words(2)[:2] == ["tôi", "không"]
    assert ctl.missing_seed_words(2, exclude=["tôi"])[:2] == ["không", "là"]
    assert len(ctl.missing_seed_words(5)) == 5


def test_export_seed_grid(ctl, tmp_path):
    out = str(tmp_path / "s.xopp")
    r = ctl.export_seed_grid(7, out)
    assert len(r.words) == 7 and os.path.exists(out)
    labels = [(t.text or "").strip() for t in xopp.read_xopp(out).iter("text")]
    assert all(w in labels for w in r.words)


def test_export_check_ghi_du_mau_de_doc_lai(ctl, tmp_path):
    out = str(tmp_path / "k.xopp")
    r = ctl.export_check(out)
    assert r.n_words > 0 and os.path.exists(out)
    raw, has_calib = xopp.parse_learn_file(out)
    labels = sorted(c.label for c in raw.values())
    assert has_calib is False and "a" in labels and "1" in labels and "," in labels


def test_learn_from_files(ctl, tmp_path):
    p = str(tmp_path / "g.xopp")
    xopp.make_grid(p, ["ba"], ctl.bank, "h", {"ba": [[0, 0, 4, -5.2, 8.2, 0]]}, calib=False)
    assert ctl.learn_from_files([p]).n_added == 1



def test_pick_calibration_word(ctl):
    char = ctl.pick_calibration_char()
    assert char is not None and char in ctl.bank.letters
    assert ctl.pick_calibration_word() == char


def test_boc_tach_ky_tu_don_vao_hang_doi():
    import unicodedata
    input_text = "cà phê"
    chars = [ch for ch in unicodedata.normalize("NFC", input_text) if not ch.isspace()]
    assert "c" in chars and "à" in chars and "p" in chars and "h" in chars and "ê" in chars


def test_teach_char_luu_dung_danh_muc(ctl):
    out = ctl.teach_char("k", [[0, 0, 5, -5]], 5.0)
    assert out.label == "k"
    assert "k" in ctl.bank.letters
    out_digit = ctl.teach_char("9", [[0, 0, 4, -6]], 4.0)
    assert out_digit.label == "9"
    assert "9" in ctl.bank.digits


def test_bank_size_va_get_stats_ky_tu_moi(ctl):
    stats = ctl.get_stats()
    assert stats.n_letters == len(ctl.bank.letters)
    assert ctl.bank_size == len(ctl.bank.letters) + len(ctl.bank.digits) + len(ctl.bank.punct) + len(getattr(ctl.bank, "symbols", {})) + len([t for t, v in ctl.bank.marks.items() if v])


# ------------------------------------------------------------ dạy trực tiếp + hiệu chỉnh cỡ tay
def test_teach_word_thuong(ctl, tiny_bank_path):
    out = ctl.teach_word("bà", [BODY, TONE], 10.0)
    assert not out.recalibrated and out.session_scale == 1.0
    assert out.instance["ti"] == 1
    assert "bà" in Bank(tiny_bank_path).words                 # đã lưu xuống đĩa ngay


def test_teach_word_hieu_chinh_dung_callback_tinh_lai_tu_pixel_goc(ctl):
    xin_strokes = [[0, 0, 6, -10, 12, 0, 18, -10]]            # viết to gấp đôi mẫu cũ: rộng 18 vs trung vị 9
    seen = []

    def recompute(scale):
        seen.append(scale)
        return [[v * scale for v in xin_strokes[0]]], round(18 * scale, 2)

    out = ctl.teach_word("xin", xin_strokes, 18.0, calibrating=True, recompute=recompute)
    assert seen == [0.5] and out.recalibrated and ctl.session_scale == 0.5
    assert out.instance["w"] == 9.0 and out.instance["s"] == [[0.0, 0.0, 3.0, -5.0, 6.0, 0.0, 9.0, -5.0]]


def test_teach_word_hieu_chinh_khong_callback_thi_co_gian_net_da_co(ctl):
    out = ctl.teach_word("xin", [[0, 0, 6, -10, 12, 0, 18, -10]], 18.0, calibrating=True)
    assert ctl.session_scale == 0.5
    assert out.instance["w"] == 9.0 and out.instance["s"] == [[0.0, 0.0, 3.0, -5.0, 6.0, 0.0, 9.0, -5.0]]


def test_hieu_chinh_lan_hai_khong_cong_don(ctl):
    """Người dùng hiệu chỉnh 2 lần trong một phiên bằng đúng cùng một nét chữ -> phải ra cùng
    một hệ số (đo lại từ độ rộng THÔ), không bị nhân dồn."""
    raw = [[0, 0, 6, -10, 12, 0, 18, -10]]
    ctl.teach_word("xin", raw, 18.0, calibrating=True)
    assert ctl.session_scale == 0.5
    at_half = [[v * 0.5 for v in raw[0]]]                      # cùng nét đó nhưng đang quy đổi ở hệ số 0.5
    ctl.teach_word("xin", at_half, 9.0, calibrating=True)
    assert ctl.session_scale == pytest.approx(0.5)


def test_hieu_chinh_tu_chua_co_mau_thi_bo_qua_nhung_van_luu(ctl):
    out = ctl.teach_word("moi", [[0, 0, 4, -5]], 4.0, calibrating=True)
    assert not out.recalibrated and ctl.session_scale == 1.0 and "moi" in ctl.bank.words


def test_drop_batch_va_drop_chars_single_lock(ctl, tiny_bank_path):
    # tiny_bank có letters ("b", "a", "x", "i", "n", "c", "h", "o"), digits ("1", "2"), punct (",", ".")
    res = ctl.drop_chars(["b", "1", ",", "khong_co"])
    assert res.removed["b"] > 0
    assert res.removed["1"] > 0
    assert res.removed[","] > 0
    assert res.removed["khong_co"] == 0
    assert res.total_removed_chars == 3
    assert res.total_removed_samples >= 3

    # Kiểm tra đã lưu xuống đĩa
    reloaded = Bank(tiny_bank_path)
    assert "b" not in reloaded.letters
    assert "1" not in reloaded.digits
    assert "," not in reloaded.punct


def test_teach_char_multi_stroke_tone_marks(ctl, tiny_bank_path):
    """T011: Kiểm tra dạy dấu thanh đa nét (N >= 2 nét bút) giữ nguyên số nét khi lưu và nạp lại."""
    stroke1 = [0.0, 0.0, 2.0, -3.0]
    stroke2 = [3.0, -3.0, 5.0, 0.0]
    ctl.teach_char("dấu hỏi", [stroke1, stroke2], 5.0)

    tone_code = "\u0309"
    assert tone_code in ctl.bank.marks
    assert len(ctl.bank.marks[tone_code]) > 0
    saved_inst = ctl.bank.marks[tone_code][-1]
    assert len(saved_inst["s"]) == 2, f"Mẫu dấu hỏi trong bộ nhớ phải có đủ 2 nét, thực tế có {len(saved_inst['s'])}"

    # Nạp lại từ đĩa để xác nhận persistence
    reloaded = Bank(tiny_bank_path)
    assert tone_code in reloaded.marks
    assert len(reloaded.marks[tone_code]) > 0
    disk_inst = reloaded.marks[tone_code][-1]
    assert len(disk_inst["s"]) == 2, f"Mẫu dấu hỏi lưu trên đĩa phải có đủ 2 nét, thực tế có {len(disk_inst['s'])}"


def test_export_check_covers_all_tone_marks_with_offsets(ctl, tmp_path):
    """T012: Kiểm tra export_check() bao phủ đầy đủ 5 dấu thanh kèm nhãn tiếng Việt và offset dy chuẩn."""
    ctl.teach_char("dấu huyền", [[0.0, 0.0, 3.0, 3.0]], 3.0)
    ctl.teach_char("dấu sắc", [[0.0, 0.0, 3.0, -3.0]], 3.0)
    ctl.teach_char("dấu hỏi", [[0.0, 0.0, 2.0, -2.0], [3.0, -2.0, 5.0, 0.0]], 5.0)
    ctl.teach_char("dấu ngã", [[0.0, 0.0, 2.0, -1.0, 4.0, 1.0]], 4.0)
    ctl.teach_char("dấu nặng", [[0.0, 0.0, 1.0, 1.0]], 1.0)

    out = str(tmp_path / "check_full.xopp")
    res = ctl.export_check(out)
    assert res.n_words >= 5
    assert os.path.exists(out)

    root = xopp.read_xopp(out)
    text_labels = [(t.text or "").strip() for t in root.iter("text")]

    expected_tone_labels = ["dấu huyền", "dấu sắc", "dấu hỏi", "dấu ngã", "dấu nặng"]
    for tl in expected_tone_labels:
        assert tl in text_labels, f"File kiểm tra .xopp phải chứa nhãn tiếng Việt '{tl}'"
