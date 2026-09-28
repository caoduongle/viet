from chuviettay.model.calibration import compute_scale

REF = [{"w": 10.0}, {"w": 12.0}, {"w": 30.0}]      # trung vị = 12


def test_khong_co_mau_tham_chieu_thi_khong_hieu_chinh():
    assert compute_scale(None, 5.0) == 1.0
    assert compute_scale([], 5.0) == 1.0


def test_do_qua_nho_thi_khong_tin():
    assert compute_scale(REF, 0.5) == 1.0
    assert compute_scale(REF, 0.0) == 1.0


def test_ty_le_theo_trung_vi():
    assert compute_scale(REF, 6.0) == 2.0             # viết nhỏ bằng nửa -> phải phóng gấp 2
    assert compute_scale(REF, 24.0) == 0.5            # viết to gấp đôi -> thu lại còn nửa


def test_bi_chan_o_bien():
    assert compute_scale(REF, 1.0) == 3.0             # 12/1 = 12 -> chặn ở 3.0
    assert compute_scale(REF, 1000.0) == 0.3          # 0.012 -> chặn ở 0.3
    assert compute_scale(REF, 1.0, bounds=(0.1, 20.0)) == 12.0
