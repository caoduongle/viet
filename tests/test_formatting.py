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
