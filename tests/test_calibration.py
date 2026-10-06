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


def test_pick_calibration_char():
    from chuviettay.model.xopp import pick_calibration_char

    class MockBank:
        def __init__(self, letters=None):
            self.letters = letters or {}

    # 1. Kho rỗng -> None
    assert pick_calibration_char(MockBank()) is None

    # 2. Ưu tiên chữ x-height (o, a, e, n, u, c, m) có >= 3 mẫu
    bank_pref = MockBank({
        "k": [{"w": 4.0}] * 5,  # không thuộc preferred
        "a": [{"w": 3.0}, {"w": 3.0}, {"w": 3.0}],  # preferred
    })
    assert pick_calibration_char(bank_pref) == "a"

    # 3. Giữa các chữ preferred, chọn chữ có điểm biến thiên tốt hơn (CV thấp, nhiều mẫu)
    bank_cv = MockBank({
        "o": [{"w": 2.0}, {"w": 4.0}, {"w": 6.0}],  # CV cao
        "n": [{"w": 3.0}, {"w": 3.0}, {"w": 3.0}, {"w": 3.0}],  # ổn định hơn
    })
    assert pick_calibration_char(bank_cv) == "n"

    # 4. Khi không có chữ preferred nào đủ >= 3 mẫu -> chọn chữ cái thường khác có >= 3 mẫu
    bank_other = MockBank({
        "o": [{"w": 3.0}, {"w": 3.0}],  # chỉ có 2 mẫu
        "b": [{"w": 4.0}, {"w": 4.0}, {"w": 4.0}],  # 3 mẫu
    })
    assert pick_calibration_char(bank_other) == "b"

    # 5. Khi không có chữ nào đủ 3 mẫu -> chọn chữ có nhiều mẫu nhất
    bank_few = MockBank({
        "x": [{"w": 2.5}],
        "y": [{"w": 2.5}, {"w": 2.5}],
    })
    assert pick_calibration_char(bank_few) == "y"
