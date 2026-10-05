"""CLI chạy trong tiến trình (gọi cli.main) -- kiểm tra đầu ra + mã thoát + xử lý lỗi."""
import io
import os

import pytest

from chuviettay import cli
from chuviettay.controller.app_controller import AppController
from chuviettay.model import xopp
from chuviettay.model.bank import Bank


def run(capsys, tiny_bank_path, *args):
    rc = cli.main(["--bank", tiny_bank_path, *args])
    return rc, capsys.readouterr()


def test_stats(capsys, tiny_bank_path):
    rc, cap = run(capsys, tiny_bank_path, "stats")
    assert rc == 0
    assert cap.out.splitlines() == [
        "3 từ, 9 mẫu; chữ số: 1:1 2:1; dấu câu: ,:1 .:1",
        "Dấu thanh có mẫu để ghép: 2 0 0 0 0 (huyền, sắc, ngã, hỏi, nặng)",
    ]


def test_write_in_bao_cao_va_tao_file(capsys, tiny_bank_path, tmp_path):
    out = str(tmp_path / "ra.xopp")
    rc, cap = run(capsys, tiny_bank_path, "write", "-t", "xin ba zzz", "-o", out, "--seed", "1")
    assert rc == 0 and os.path.exists(out) and os.path.exists(str(tmp_path / "ra_thieu.xopp"))
    lines = cap.out.splitlines()
    assert lines[0] == "Xong: %s  (1 dòng, 2 nét; đủ mẫu cho 2/3 từ)" % out
    assert lines[2] == "Chưa có mẫu cho 1 mục (chỗ đó đang để trống): zzz"


def test_write_doc_tu_file_co_bom(capsys, tiny_bank_path, tmp_path):
    src = tmp_path / "vb.txt"
    src.write_text("xin ba", encoding="utf-8-sig")
    rc, cap = run(capsys, tiny_bank_path, "write", "-f", str(src), "-o", str(tmp_path / "o.xopp"))
    assert rc == 0 and "đủ mẫu cho 2/2 từ" in cap.out


def test_write_doc_tu_stdin(capsys, monkeypatch, tiny_bank_path, tmp_path):
    monkeypatch.setattr("sys.stdin", io.StringIO("xin ba"))
    rc, cap = run(capsys, tiny_bank_path, "write", "-o", str(tmp_path / "o.xopp"))
    assert rc == 0 and "đủ mẫu cho 2/2 từ" in cap.out


def test_write_khong_co_nguon_van_ban_va_stdin_la_terminal(monkeypatch, tiny_bank_path):
    class Tty(io.StringIO):
        def isatty(self):
            return True
    monkeypatch.setattr("sys.stdin", Tty())
    with pytest.raises(SystemExit) as ei:
        cli.main(["--bank", tiny_bank_path, "write"])
    assert "Cần -f" in str(ei.value)


def test_write_doc_tu_positional_file_khi_stdin_la_terminal(capsys, monkeypatch, tiny_bank_path, tmp_path):
    class Tty(io.StringIO):
        def isatty(self):
            return True
    monkeypatch.setattr("sys.stdin", Tty())
    src = tmp_path / "vb_pos.txt"
    src.write_text("xin ba", encoding="utf-8")
    out = tmp_path / "o_pos.xopp"
    rc, cap = run(capsys, tiny_bank_path, "write", str(src), "-o", str(out))
    assert rc == 0 and "đủ mẫu cho 2/2 từ" in cap.out


def test_drop(capsys, tiny_bank_path):
    rc, cap = run(capsys, tiny_bank_path, "drop", "ba", "khong_co")
    assert cap.out.splitlines() == ["Đã xóa 2 mẫu của 'ba'", "Không có 'khong_co' trong kho"]
    assert "ba" not in Bank(tiny_bank_path).words


def test_check_va_seed(capsys, tiny_bank_path, tmp_path):
    rc, cap = run(capsys, tiny_bank_path, "check", "-o", str(tmp_path / "k.xopp"))
    assert cap.out.strip() == "Đã tạo %s (3 từ)." % (tmp_path / "k.xopp")
    rc, cap = run(capsys, tiny_bank_path, "seed", "12", "-o", str(tmp_path / "s.xopp"))
    assert "với 12 từ" in cap.out


def test_learn_vong_tron_voi_check(capsys, tiny_bank_path, tmp_path):
    k = str(tmp_path / "k.xopp")
    run(capsys, tiny_bank_path, "check", "-o", k)
    rc, cap = run(capsys, tiny_bank_path, "learn", k)
    assert cap.out.strip() == "Đã học thêm 3 mẫu. Chạy lại lệnh write để có đủ chữ."
    assert len(Bank(tiny_bank_path).words["ba"]) == 3


def test_thieu_kho_mau_thoat_voi_thong_bao_tieng_viet(tmp_path):
    with pytest.raises(SystemExit) as ei:
        cli.main(["--bank", str(tmp_path / "khong_co.json.gz"), "stats"])
    assert "Không thấy kho mẫu" in str(ei.value)


def test_loi_bat_ngo_thi_ghi_log_va_bao_gon_gang(monkeypatch, tiny_bank_path):
    def boom(self, *a, **k):
        raise ZeroDivisionError("chia cho 0")
    monkeypatch.setattr(AppController, "get_stats", boom)
    with pytest.raises(SystemExit) as ei:
        cli.main(["--bank", tiny_bank_path, "stats"])
    msg = str(ei.value)
    assert "Lỗi: chia cho 0" in msg and "chuviettay.log" in msg and "-v" in msg


def test_verbose_thi_nem_lai_loi_de_thay_traceback(monkeypatch, tiny_bank_path):
    monkeypatch.setattr(AppController, "get_stats", lambda self: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        cli.main(["--bank", tiny_bank_path, "-v", "stats"])


def test_d4_cli_no_missing_grid_flag(capsys, tiny_bank_path, tmp_path):
    """[D4] Kiểm tra cờ --no-missing-grid trong CLI không sinh file _thieu.xopp."""
    out = str(tmp_path / "cli_no_grid.xopp")
    rc = cli.main(["--bank", tiny_bank_path, "write", "-t", "zebra quokka", "-o", out, "--no-missing-grid"])
    assert rc == 0
    assert os.path.exists(out)
    assert not os.path.exists(str(tmp_path / "cli_no_grid_thieu.xopp"))

