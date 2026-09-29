"""WordCanvas: phần quy đổi pixel -> đơn vị kho mẫu là hàm thuần (không cần Tk);
phần vẽ cần cửa sổ Tk (Linux không màn hình: chạy `xvfb-run -a pytest`)."""
import pytest

from tests import conftest

if not conftest.is_tk_usable():
    pytest.skip(f"Môi trường Tk/Tcl không khả dụng ({conftest._tk_unusable_reason}). Trên Linux hãy chạy: xvfb-run -a pytest", allow_module_level=True)

pytestmark = [pytest.mark.gui]

from chuviettay.view import word_canvas as wc
from chuviettay.view.word_canvas import BASE_PX, ZOOM, strokes_to_bank_units


# ------------------------------------------------------------ hàm thuần
def test_quy_doi_goc_toa_do_va_don_vi():
    rel, w = strokes_to_bank_units([[(100, BASE_PX), (100 + 10 * ZOOM, BASE_PX - 5 * ZOOM)]], 1.0)
    assert rel == [[0.0, 0.0, 10.0, -5.0]] and w == 10.0


def test_quy_doi_nhan_he_so_co_tay():
    rel, w = strokes_to_bank_units([[(0, BASE_PX), (10 * ZOOM, BASE_PX - 5 * ZOOM)]], 2.0)
    assert rel == [[0.0, 0.0, 20.0, -10.0]] and w == 20.0


def test_quy_doi_goc_x_la_diem_trai_nhat_cua_moi_net():
    rel, w = strokes_to_bank_units([[(50, BASE_PX), (60, BASE_PX)], [(30, BASE_PX), (40, BASE_PX)]], 1.0)
    assert rel[0][0] == 2.0 and rel[1][0] == 0.0 and w == 3.0


def test_quy_doi_khong_co_net_thi_bao_loi():
    with pytest.raises(ValueError):
        strokes_to_bank_units([], 1.0)


# ------------------------------------------------------------ cần Tk
@pytest.fixture
def canvas(tk_root):
    from tests import conftest
    if not conftest.is_tk_usable():
        pytest.skip(f"Môi trường Tk/Tcl không khả dụng ({conftest._tk_unusable_reason})")
    c = wc.WordCanvas(tk_root, get_xh=lambda: 7.0)
    c.pack()
    return c


def draw(c, pts):
    c.start(*pts[0])
    for p in pts[1:]:
        c.move(*p)
    c.end()


def test_ve_hoan_tac_xoa(canvas):
    assert not canvas.has_ink()
    draw(canvas, [(10, 100), (40, 100), (70, 90)])
    draw(canvas, [(80, 100), (120, 100)])
    assert canvas.has_ink() and len(canvas.strokes) == 2
    canvas.undo()
    assert len(canvas.strokes) == 1
    canvas.clear()
    assert not canvas.has_ink()
    canvas.undo()                                    # hoàn tác khi rỗng không được lỗi


def test_cham_don_le_khong_thanh_net(canvas):
    canvas.start(5, 5); canvas.end()
    assert not canvas.has_ink()


def test_loc_bot_diem_qua_gan_nhau(canvas):
    canvas.start(10, 100)
    for x in (10.5, 11, 11.5, 12):                   # đều gần hơn MIN_POINT_DIST so với điểm trước
        canvas.move(x, 100)
    canvas.move(30, 100)
    canvas.end()
    assert len(canvas.strokes[0]) == 2


def test_to_bank_strokes_dung_he_so(canvas):
    draw(canvas, [(20, BASE_PX), (20 + 10 * ZOOM, BASE_PX - 5 * ZOOM)])
    assert canvas.to_bank_strokes(1.0) == ([[0.0, 0.0, 10.0, -5.0]], 10.0)
    assert canvas.to_bank_strokes(0.5) == ([[0.0, 0.0, 5.0, -2.5]], 5.0)


def test_vach_ke_mo_theo_chieu_cao_chu_thuong(canvas):
    assert len(canvas.canvas.find_withtag("guide")) == 2
    canvas.draw_guides()
    assert len(canvas.canvas.find_withtag("guide")) == 2     # vẽ lại không bị nhân đôi
