"""Unit tests for UI assembly controls and CLI flags."""
import os
import pytest

from chuviettay import cli
from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions, WriteResult, BankStats
from chuviettay.formatting import format_stats_gui, write_report_lines
from chuviettay.model.bank import Bank


def test_cli_parser_assemble_flag():
    parser = cli.build_parser()
    args_default = parser.parse_args(["write", "-t", "chao"])
    assert getattr(args_default, "assemble", False) is False

    args_assemble = parser.parse_args(["write", "-t", "chao", "--assemble"])
    assert args_assemble.assemble is True


def test_bank_stats_contains_letters(tmp_path):
    bank_path = str(tmp_path / "bank.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.add_letter_sample("a", [[0.0, 0.0, 5.0, 5.0]], 5.0)
    bank.add_letter_sample("b", [[0.0, 0.0, 4.0, 8.0]], 4.0)
    bank.save()

    ctl = AppController(bank_path)
    ctl.load_bank()
    stats = ctl.get_stats()

    assert stats.n_letters == 2
    assert stats.letter_counts == {"a": 1, "b": 1}

    # Verify format_stats_gui
    gui_text = format_stats_gui(stats)
    assert "Chữ cái đơn lẻ (2 chữ)" in gui_text
    assert "a:1 b:1" in gui_text


def test_cli_stats_command_with_letters(capsys, tmp_path):
    bank_path = str(tmp_path / "bank.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.add_letter_sample("c", [[0.0, 0.0, 5.0, 5.0]], 5.0)
    bank.save()

    rc = cli.main(["--bank", bank_path, "stats"])
    assert rc == 0
    cap = capsys.readouterr()
    assert "Chữ cái đơn lẻ (1 chữ): c:1" in cap.out


def test_write_report_lines_with_assembled_and_missing():
    res = WriteResult(
        out_path="ra.xopp",
        n_lines=1,
        n_strokes=10,
        n_tokens=3,
        n_missing_tokens=1,
        missing={"hôm": 1},
        missing_letters=[("h", 1, ["hôm"]), ("m", 1, ["hôm"])],
        assembled_words=["chào", "bạn"],
    )

    lines = write_report_lines(res)
    full_report = "\n".join(lines)

    assert "Đã ghép từ chữ cái cho 2 từ: chào bạn" in full_report
    assert "Chưa có mẫu cho 1 mục (chỗ đó đang để trống): hôm" in full_report
    assert "Chữ cái/dấu còn thiếu để ghép (2):" in full_report


def test_cli_write_with_assemble_synthesizes_words(capsys, tmp_path):
    bank_path = str(tmp_path / "bank.json.gz")
    bank = Bank.create_empty(bank_path)
    # Dạy các chữ cái: c, a
    bank.add_letter_sample("c", [[0.0, 0.0, 4.0, 4.0]], 4.0)
    bank.add_letter_sample("a", [[0.0, 0.0, 5.0, 5.0]], 5.0)
    bank.save()

    out = str(tmp_path / "ra.xopp")
    rc = cli.main(["--bank", bank_path, "write", "-t", "ca", "--assemble", "-o", out])
    assert rc == 0
    assert os.path.exists(out)

    cap = capsys.readouterr()
    assert "Đã ghép từ chữ cái cho 1 từ: ca" in cap.out
    assert "đủ mẫu cho 1/1 từ" in cap.out
