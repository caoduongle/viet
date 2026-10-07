from chuviettay.formatting import MAX_MISSING_SHOWN, write_report_lines
from chuviettay.model.composer import WriteResult


def test_bao_cao_khong_thieu_gi():
    r = WriteResult("ra.xopp", 3, 40, 10, 0)
    assert write_report_lines(r) == [
        "Xong: ra.xopp  (3 dòng, 40 nét; đủ mẫu cho 10/10 từ)",
        "Mở file này -> Ctrl+A -> Ctrl+C -> dán vào sổ của bạn (Ctrl+V) rồi kéo về đúng chỗ.",
    ]


def test_bao_cao_co_tu_thieu():
    r = WriteResult("ra.xopp", 1, 5, 4, 2, missing={"b": 1, "a": 3}, missing_grid_path="ra_thieu.xopp")
    lines = write_report_lines(r)
    assert lines[0].endswith("đủ mẫu cho 2/4 từ)")
    assert lines[2] == "Chưa có mẫu cho 2 mục (chỗ đó đang để trống): a b"
    assert lines[3] == ("Đã tạo ra_thieu.xopp: viết các từ đó một lần, lưu, rồi chạy: "
                        "python hw_note.py learn ra_thieu.xopp")


def test_bao_cao_cat_bot_khi_qua_nhieu_tu_thieu():
    missing = {"w%02d" % i: 1 for i in range(MAX_MISSING_SHOWN + 5)}
    r = WriteResult("o", 1, 1, 99, 30, missing=missing)
    line = write_report_lines(r)[2]
    assert line.endswith(" ...") and line.count("w") == MAX_MISSING_SHOWN


def test_khong_co_dong_da_tao_khi_khong_ghi_file_luoi_o():
    r = WriteResult("o", 1, 1, 2, 1, missing={"x": 1})
    assert len(write_report_lines(r)) == 3


def test_bao_cao_co_ky_hieu_thieu():
    r = WriteResult(
        "ra.xopp",
        1,
        10,
        5,
        2,
        missing={"abc": 1},
        missing_symbols={"∑": 3, "≤": 1},
    )
    lines = write_report_lines(r)
    assert any("Ký hiệu thiếu mẫu" in line for line in lines)
    sym_line = next(line for line in lines if "Ký hiệu thiếu mẫu" in line)
    assert "∑ (x3)" in sym_line
    assert "≤ (x1)" in sym_line


def test_format_stats_gui_char_first():
    """T021: format_stats_gui hiển thị trọng tâm theo ký tự và mẫu nét, phụ chú từ cũ nếu có."""
    from chuviettay.controller.results import BankStats
    from chuviettay.formatting import format_stats_gui

    # Kho chỉ có ký tự (không có legacy words)
    stats = BankStats(
        n_words=0,
        n_samples=25,
        digit_counts={"1": 2, "2": 3},
        punct_counts={",": 1},
        tone_mark_counts={"\u0300": 1, "\u0301": 2, "\u0303": 0, "\u0309": 1, "\u0323": 1},
        n_letters=5,
        letter_counts={"a": 3, "b": 2, "c": 1, "d": 2, "e": 2},
    )
    # total_chars = 5 (letters) + 2 (digits) + 1 (punct) + 4 (tones with > 0) = 12
    text = format_stats_gui(stats)
    lines = text.splitlines()
    assert "12 ký tự, 25 mẫu nét" in lines[0]
    assert "từ cũ" not in lines[0]
    assert "Chữ cái đơn lẻ (5 chữ):" in lines[1]
    assert "Chữ số có mẫu: 1:2 2:3" in lines[2]
    assert "Dấu câu có mẫu: ,:1" in lines[3]

    # Kho có từ cũ (legacy words)
    legacy_stats = BankStats(
        n_words=3,
        n_samples=15,
        digit_counts={"1": 1},
        punct_counts={},
        tone_mark_counts={},
        n_letters=2,
        letter_counts={"a": 1, "b": 1},
    )
    # total_chars = 2 (letters) + 1 (digits) = 3
    leg_text = format_stats_gui(legacy_stats)
    leg_lines = leg_text.splitlines()
    assert "3 ký tự, 15 mẫu nét (kèm 3 từ cũ)" in leg_lines[0]
