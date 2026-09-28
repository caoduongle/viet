"""Kiểm thử giao diện thật (MainWindow + 3 tab) -- điều khiển bằng lời gọi hàm/sự kiện như
người dùng thao tác, các hộp thoại (messagebox/filedialog) được thay bằng bản giả để test
không bị treo chờ bấm. Cần màn hình: Linux không màn hình -> `xvfb-run -a pytest`."""
import os

import pytest

pytest.importorskip("tkinter")
from tkinter import filedialog, messagebox, simpledialog  # noqa: E402

from chuviettay.controller.app_controller import AppController  # noqa: E402
from chuviettay.model.bank import Bank  # noqa: E402
from chuviettay.view import dialogs  # noqa: E402
from chuviettay.view.app_window import MainWindow  # noqa: E402
from chuviettay.view.word_canvas import BASE_PX, ZOOM  # noqa: E402


class Dialogs:
    """Ghi lại mọi hộp thoại đã hiện; askyesno luôn trả lời Có (đổi được bằng .yes)."""
    def __init__(self, monkeypatch):
        self.calls, self.yes = [], True
        for kind in ("showinfo", "showwarning", "showerror"):
            monkeypatch.setattr(messagebox, kind, lambda title, msg, _k=kind, **kw: self.calls.append((_k, title, msg)))
        monkeypatch.setattr(messagebox, "askyesno", lambda title, msg, **kw: self.yes)

    def kinds(self):
        return [c[0] for c in self.calls]


@pytest.fixture
def dlg(monkeypatch):
    return Dialogs(monkeypatch)


@pytest.fixture
def app(tk_root, tiny_bank_path, dlg):
    tk_root.destroy()          # MainWindow tự là cửa sổ Tk gốc; bỏ cửa sổ ẩn của fixture
    w = MainWindow(AppController(tiny_bank_path))
    w.withdraw()
    w.update()
    yield w
    try:
        w.destroy()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _recreate_root_for_fixture_teardown(monkeypatch):
    # fixture tk_root sẽ destroy() một cửa sổ đã bị destroy -> bỏ qua lỗi đó
    import tkinter as tk
    orig = tk.Tk.destroy
    def safe(self):
        try:
            orig(self)
        except tk.TclError:
            pass
    monkeypatch.setattr(tk.Tk, "destroy", safe)


def draw(canvas, x0, y0, x1, y1):
    canvas.start(x0, y0)
    canvas.move((x0 + x1) / 2, (y0 + y1) / 2)
    canvas.move(x1, y1)
    canvas.end()


# ------------------------------------------------------------ cửa sổ chính
def test_cua_so_mo_dung_tab_va_thong_ke(app):
    assert [app.notebook.tab(t, "text") for t in app.notebook.tabs()] == ["Viết chữ", "Dạy từ mới", "Kho mẫu"]
    assert "3 từ, 9 mẫu" in app.bank_tab.stats_lbl.cget("text")
    assert app.path_lbl.cget("text").startswith("Kho mẫu: ")
    assert app.bank_tab.word_list.size() == 3


def test_mo_kho_that_cua_nguoi_dung(tk_root, real_bank_path, dlg):
    tk_root.destroy()
    w = MainWindow(AppController(real_bank_path))
    w.update()
    assert "362 từ, 859 mẫu" in w.bank_tab.stats_lbl.cget("text")
    assert w.bank_tab.word_list.size() == 362
    w.destroy()


def test_khoi_dong_that_bai_van_co_cua_so_va_sau_do_chon_kho_thi_dung_tab(tk_root, tiny_bank_path, dlg, tmp_path):
    tk_root.destroy()
    w = MainWindow(AppController(str(tmp_path / "khong" / "ton" / "tai" / "b.json.gz")))
    w.update()
    assert dlg.kinds() == ["showerror"] and not w._tabs_built           # báo lỗi, hiện màn hình hướng dẫn
    assert w.placeholder.winfo_manager() == "pack"
    assert w._switch_bank(tiny_bank_path)
    w.update()
    assert w._tabs_built and w.placeholder.winfo_manager() == ""
    assert "3 từ, 9 mẫu" in w.bank_tab.stats_lbl.cget("text")           # bản gốc: cửa sổ trống trơn mãi
    w.destroy()


def test_chon_kho_khac_cap_nhat_giao_dien(app, real_bank_path, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: real_bank_path)
    app.choose_bank()
    assert app.ctl.bank_path == real_bank_path
    assert real_bank_path in app.path_lbl.cget("text")
    assert "362 từ" in app.bank_tab.stats_lbl.cget("text")


def test_tao_kho_moi(app, tmp_path, monkeypatch, dlg):
    p = str(tmp_path / "moi.json.gz")
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: p)
    app.new_bank()
    assert os.path.exists(p) and "0 từ, 0 mẫu" in app.bank_tab.stats_lbl.cget("text")
    assert dlg.calls == []                                               # kho mới thì không cần báo gì


def test_tao_kho_moi_tren_file_da_co_thi_mo_ra_chu_khong_ghi_de(app, real_bank_path, monkeypatch, dlg):
    before = open(real_bank_path, "rb").read()
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: real_bank_path)
    app.new_bank()
    assert open(real_bank_path, "rb").read() == before                   # dữ liệu còn nguyên từng byte
    assert "362 từ" in app.bank_tab.stats_lbl.cget("text") and dlg.kinds() == ["showinfo"]


def test_loi_bat_ngo_trong_su_kien_duoc_ghi_log_va_hien_hop_thoai(app, dlg, caplog):
    try:
        raise KeyError("lỗi thử")
    except KeyError as e:
        app.report_callback_exception(type(e), e, e.__traceback__)
    assert dlg.kinds() == ["showerror"] and "chuviettay.log" in dlg.calls[0][2]
    assert any("lỗi thử" in r.getMessage() and r.exc_info for r in caplog.records)   # có traceback trong log


# ------------------------------------------------------------ tab Viết chữ
def test_viet_chu_thanh_cong_va_hien_ket_qua(app, tmp_path, monkeypatch):
    out = str(tmp_path / "ra.xopp")
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: out)
    t = app.write_tab
    t.text.insert("1.0", "xin ba zzz")
    t.v_seed.set("1")
    t.do_write()
    shown = t.status.get("1.0", "end")
    assert "Xong: %s" % out in shown and "zzz" in shown
    assert os.path.exists(out) and os.path.exists(str(tmp_path / "ra_thieu.xopp"))
    assert t.miss_list.get(0) == "zzz  (x1)"


def test_viet_chu_van_ban_trong_thi_canh_bao(app, dlg):
    app.write_tab.do_write()
    assert dlg.kinds() == ["showwarning"]


def test_o_nhap_sai_thi_bao_dung_ten_o(app, dlg, monkeypatch):
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: pytest.fail("không được đi tới bước chọn file"))
    t = app.write_tab
    t.text.insert("1.0", "xin")
    t.v_scale.set("abc")
    t.do_write()
    assert dlg.kinds() == ["showerror"] and "Cỡ chữ" in dlg.calls[0][2] and "'abc'" in dlg.calls[0][2]
    dlg.calls.clear()
    t.v_scale.set("1"); t.v_seed.set("1.5")
    t.do_write()
    assert "Seed" in dlg.calls[0][2]


def test_tuy_chon_duoc_doc_dung(app):
    t = app.write_tab
    t.v_scale.set("1.2"); t.v_line.set("30"); t.v_color.set("#ff0000"); t.v_seed.set("7"); t.v_strict.set(True)
    o = t.read_options()
    assert (o.scale, o.line, o.width, o.color, o.seed, o.strict_case) == (1.2, 30.0, None, "#ff0000", 7, True)


def test_strict_case_danh_sach_thieu_khop_voi_thuc_te_tren_trang(app, tmp_path, monkeypatch):
    """Lỗi âm thầm của bản gốc: bật strict-case mà danh sách 'từ còn thiếu' vẫn tính như tắt."""
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: str(tmp_path / "o.xopp"))
    t = app.write_tab
    t.text.insert("1.0", "Xin")
    t.v_strict.set(True)
    t.do_write()
    assert t.miss_list.get(0) == "Xin  (x1)"


def test_day_cac_tu_nay_chuyen_sang_tab_day_va_nap_hang_doi(app, tmp_path, monkeypatch):
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: str(tmp_path / "o.xopp"))
    t = app.write_tab
    t.text.insert("1.0", "xin zzz yyy")
    t.do_write()
    t.teach_missing()
    assert app.notebook.select() == str(app.teach_tab)
    assert sorted(app.teach_tab.queue) == ["yyy", "zzz"] and app.teach_tab.current in ("yyy", "zzz")


def test_nut_day_khi_chua_thieu_gi(app, dlg):
    app.write_tab.teach_missing()
    assert dlg.kinds() == ["showinfo"]


def test_mo_file_txt(app, tmp_path, monkeypatch):
    src = tmp_path / "vb.txt"
    src.write_text("Xin chào\nba", encoding="utf-8-sig")
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: str(src))
    app.write_tab.open_txt()
    assert app.write_tab.text.get("1.0", "end").strip() == "Xin chào\nba"


# ------------------------------------------------------------ tab Dạy từ mới
def test_them_tu_vao_hang_doi_khong_tach_cum_tu(app):
    t = app.teach_tab
    t.add_var.set("cà phê"); t.add_word()
    t.add_var.set("cà phê"); t.add_word()                                # trùng -> bỏ qua
    assert t.queue == ["cà phê"] and t.current == "cà phê"


def test_luu_tu_ghi_xuong_dia_va_chuyen_tu_tiep(app, tiny_bank_path):
    t = app.teach_tab
    t.add_var.set("ba"); t.add_word()
    t.add_var.set("mới"); t.add_word()
    draw(t.canvas, 20, BASE_PX, 20 + 8 * ZOOM, BASE_PX - 5 * ZOOM)
    t.save_word()
    assert t.current == "mới" and t.queue == ["mới"]
    saved = Bank(tiny_bank_path).words["ba"]
    assert len(saved) == 3 and saved[-1]["w"] == 8.0
    assert not t.canvas.has_ink()                                         # canvas sạch cho từ kế tiếp


def test_luu_khi_chua_ve_thi_canh_bao_va_khong_luu(app, dlg, tiny_bank_path):
    t = app.teach_tab
    t.add_var.set("ba"); t.add_word()
    t.save_word()
    assert dlg.kinds() == ["showwarning"] and len(Bank(tiny_bank_path).words["ba"]) == 2


def test_nap_tu_thong_dung(app, monkeypatch, dlg):
    monkeypatch.setattr(simpledialog, "askinteger", lambda *a, **kw: 5)
    t = app.teach_tab
    t.add_var.set("tôi"); t.add_word()
    t.add_seed()
    assert len(t.queue) == 6 and t.queue.count("tôi") == 1                # không thêm trùng từ đã có trong hàng đợi
    assert dlg.kinds() == ["showinfo"]


def test_hieu_chinh_co_tay_luong_day_du(app, tiny_bank_path, dlg):
    t = app.teach_tab
    assert "chưa hiệu chỉnh" in t.scale_lbl.cget("text")
    t.start_calibration()
    assert t.queue[0] == "xin" and "hiệu chỉnh cỡ tay" in t.word_lbl.cget("text")
    draw(t.canvas, 20, BASE_PX, 20 + 18 * ZOOM, BASE_PX - 5 * ZOOM)      # viết to gấp đôi mẫu cũ (rộng 18 vs 9)
    t.save_word()
    assert app.ctl.session_scale == pytest.approx(0.5)
    assert t.scale_lbl.cget("text") == "Hệ số cỡ tay hiện tại: 0.50x"
    assert Bank(tiny_bank_path).words["xin"][-1]["w"] == pytest.approx(9.0, abs=0.01)   # đã co về đúng cỡ
    assert not t._calib_pending


def test_bo_qua_tu_moc_thi_huy_hieu_chinh(app, tiny_bank_path):
    """Bản gốc: cờ hiệu chỉnh bật mãi -> lần lưu kế tiếp bị coi nhầm là hiệu chỉnh."""
    t = app.teach_tab
    t.start_calibration()
    t.skip_word()
    assert not t._calib_pending
    t.add_var.set("xin"); t.add_word()
    draw(t.canvas, 20, BASE_PX, 20 + 30 * ZOOM, BASE_PX - 5 * ZOOM)
    t.save_word()
    assert app.ctl.session_scale == 1.0                                   # không bị hiệu chỉnh ngầm


def test_xoa_hang_doi_huy_hieu_chinh(app):
    t = app.teach_tab
    t.start_calibration()
    t.clear_queue()
    assert t.queue == [] and t.current is None and not t._calib_pending


def test_doi_kho_mau_dat_lai_he_so_co_tay(app, real_bank_path, monkeypatch):
    app.ctl.session_scale = 0.5
    app.teach_tab._calibrated = True
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: real_bank_path)
    app.choose_bank()
    assert app.ctl.session_scale == 1.0 and "chưa hiệu chỉnh" in app.teach_tab.scale_lbl.cget("text")


# ------------------------------------------------------------ tab Kho mẫu
def test_tim_kiem_loc_danh_sach(app):
    b = app.bank_tab
    b.search_var.set("ch"); b._filter()
    assert b.word_list.size() == 1 and b.word_list.get(0) == "chào  (2 mẫu)"
    b.search_var.set(""); b._filter()
    assert b.word_list.size() == 3


def test_xoa_tu_dung_tu_duoc_chon_ke_ca_khi_dang_loc(app, tiny_bank_path):
    b = app.bank_tab
    b.search_var.set("x"); b._filter()
    b.word_list.selection_set(0)
    assert b.selected_word() == "xin"
    b.drop_selected()
    assert "xin" not in Bank(tiny_bank_path).words
    assert "2 từ" in b.stats_lbl.cget("text")


def test_khong_xoa_khi_chua_chon_hoac_khi_bam_khong(app, dlg, tiny_bank_path):
    b = app.bank_tab
    b.drop_selected()                                                      # chưa chọn gì
    b.word_list.selection_set(0)
    dlg.yes = False
    b.drop_selected()
    assert len(Bank(tiny_bank_path).words) == 3


def test_xuat_file_kiem_tra(app, tmp_path, monkeypatch, dlg):
    out = str(tmp_path / "k.xopp")
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: out)
    app.bank_tab.export_check()
    assert os.path.exists(out) and dlg.kinds() == ["showinfo"] and "(3 từ)" in dlg.calls[0][2]


def test_loi_khi_xuat_file_duoc_bao_kem_traceback_trong_log(app, monkeypatch, dlg, caplog):
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: "/khong/co/thu/muc/nay/k.xopp")
    app.bank_tab.export_check()
    assert dlg.kinds() == ["showerror"]
    assert any(r.exc_info and r.levelname == "ERROR" for r in caplog.records)


def test_viet_chu_dung_kho_moi_nhat_tren_dia_ke_ca_khi_vua_hoc_bang_dong_lenh(app, tiny_bank_path, tmp_path, monkeypatch):
    """Bản gốc: mỗi lần bấm 'Tạo file viết tay' đều nạp lại kho từ đĩa. Ví dụ: đang mở cửa sổ thì bạn chạy
    `hw_note.py learn ...` ở dòng lệnh -> viết tiếp trong cửa sổ phải dùng được ngay các từ mới."""
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: str(tmp_path / "o.xopp"))
    t = app.write_tab
    t.text.insert("1.0", "zzz")
    t.do_write()
    assert t.miss_list.get(0) == "zzz  (x1)"                    # chưa có mẫu

    other_process = Bank(tiny_bank_path)                         # 'tiến trình khác' dạy thêm từ zzz và lưu
    other_process.add_sample("zzz", [[0, 0, 4, -5]], 4.0)
    other_process.rebuild(); other_process.save()

    t.do_write()
    assert t.miss_list.size() == 0 and "đủ mẫu cho 1/1 từ" in t.status.get("1.0", "end")
