import logging
import os
import sys

import pytest

from chuviettay import logging_setup, paths


def test_duong_dan_mac_dinh_khi_chay_tu_ma_nguon(monkeypatch, tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert paths.app_base_dir() == root

    # Nhánh 1: Nếu file cục bộ tồn tại ở app_base_dir -> ưu tiên dùng file cục bộ
    fake_app_dir = tmp_path / "app_source"
    fake_app_dir.mkdir()
    local_bank = fake_app_dir / "chu_cua_ban.json.gz"
    local_bank.write_text("fake_bank_data", encoding="utf-8")
    monkeypatch.setattr(paths, "app_base_dir", lambda: str(fake_app_dir))
    assert paths.default_bank_path() == str(local_bank)

    # Nhánh 2: Nếu không có file cục bộ -> dùng thư mục dữ liệu người dùng (user_data_dir)
    local_bank.unlink()
    expected_user_path = os.path.join(paths.user_data_dir(), "chu_cua_ban.json.gz")
    assert paths.default_bank_path() == expected_user_path


def test_duong_dan_mac_dinh_khi_da_dong_goi_dung_thu_muc_cua_file_exe(monkeypatch, tmp_path):
    exe = tmp_path / "app" / "hw_gui.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert paths.app_base_dir() == str(exe.parent)
    assert paths.default_bank_path() == str(exe.parent / "chu_cua_ban.json.gz")


@pytest.fixture
def clean_logging(monkeypatch, tmp_path):
    root = logging.getLogger()
    saved, level = root.handlers[:], root.level
    monkeypatch.setattr(logging_setup, "_configured", False)
    monkeypatch.setattr(logging_setup, "app_base_dir", lambda: str(tmp_path))
    yield tmp_path
    for h in root.handlers[:]:
        if h not in saved:
            h.close()
            root.removeHandler(h)
    root.setLevel(level)


def test_ghi_log_ra_file_canh_ung_dung(clean_logging):
    path = logging_setup.configure_logging()
    assert path == str(clean_logging / "chuviettay.log")
    try:
        raise ValueError("lỗi thử nghiệm")
    except ValueError:
        logging.getLogger("thu").exception("có lỗi")
    for h in logging.getLogger().handlers:
        h.flush()
    content = open(path, encoding="utf-8").read()
    assert "có lỗi" in content and "Traceback" in content and "lỗi thử nghiệm" in content


def test_configure_logging_chi_thiet_lap_mot_lan(clean_logging):
    logging_setup.configure_logging()
    n = len(logging.getLogger().handlers)
    logging_setup.configure_logging()
    assert len(logging.getLogger().handlers) == n


def test_verbose_bat_debug_va_console(clean_logging):
    logging_setup.configure_logging(verbose=True)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert any(type(h) is logging.StreamHandler for h in root.handlers)


def test_thu_muc_chi_doc_thi_van_chay_duoc(monkeypatch, tmp_path):
    monkeypatch.setattr(logging_setup, "_configured", False)
    monkeypatch.setattr(logging_setup, "app_base_dir", lambda: str(tmp_path / "khong" / "ton" / "tai"))
    root = logging.getLogger()
    saved = root.handlers[:]
    try:
        logging_setup.configure_logging()            # không được ném lỗi
    finally:
        for h in root.handlers[:]:
            if h not in saved:
                root.removeHandler(h)


def test_user_data_dir_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")
    assert paths.user_data_dir() == os.path.join(r"C:\Users\Test\AppData\Roaming", "chuviettay")


def test_user_data_dir_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", "/Users/testuser")
    expected = os.path.expanduser("~/Library/Application Support/chuviettay")
    assert paths.user_data_dir() == expected


def test_user_data_dir_linux_xdg(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "/custom/share")
    assert paths.user_data_dir() == os.path.join("/custom/share", "chuviettay")


def test_user_data_dir_linux_default(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", "/home/testuser")
    assert paths.user_data_dir() == os.path.join(os.path.expanduser("~/.local/share"), "chuviettay")


def test_default_bank_path_fallback_to_user_data_dir(monkeypatch, tmp_path):
    empty_dir = tmp_path / "site_packages"
    empty_dir.mkdir()
    monkeypatch.setattr(paths, "app_base_dir", lambda: str(empty_dir))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    expected = str(tmp_path / "share" / "chuviettay" / "chu_cua_ban.json.gz")
    assert paths.default_bank_path() == expected

