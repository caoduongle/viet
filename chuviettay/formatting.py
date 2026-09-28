"""
Định dạng thông báo hiển thị cho người dùng -- phần dùng CHUNG cho cả CLI lẫn GUI.

Bản gốc: GUI gọi cmd_write() rồi dùng contextlib.redirect_stdout để "bắt" những gì hàm
này print() ra, đem hiện vào ô "Kết quả". Cách đó vỡ ngay khi ai đó sửa câu chữ print()
hoặc thêm một dòng in debug. Giờ Controller trả WriteResult (dữ liệu thuần), còn câu chữ
báo cáo được dựng ở MỘT chỗ duy nhất này -- CLI in ra terminal, GUI hiện vào ô Kết quả,
hai bên luôn hiển thị y hệt nhau.

Câu chữ giữ NGUYÊN từ bản gốc.
"""
from __future__ import annotations

from chuviettay.model.composer import WriteResult

MAX_MISSING_SHOWN = 25   # hiện tối đa bao nhiêu từ thiếu trong bản tóm tắt


def write_report_lines(result: WriteResult) -> list[str]:
    ok = result.n_tokens - result.n_missing_tokens
    lines = [
        "Xong: %s  (%d dòng, %d nét; đủ mẫu cho %d/%d từ)"
        % (result.out_path, result.n_lines, result.n_strokes, ok, result.n_tokens),
        "Mở file này -> Ctrl+A -> Ctrl+C -> dán vào sổ của bạn (Ctrl+V) rồi kéo về đúng chỗ.",
    ]
    if result.missing:
        items = result.missing_sorted()
        lines.append("Chưa có mẫu cho %d mục (chỗ đó đang để trống): %s%s" % (
            len(items),
            " ".join(k for k, _ in items[:MAX_MISSING_SHOWN]),
            " ..." if len(items) > MAX_MISSING_SHOWN else ""))
        if result.missing_grid_path:
            lines.append("Đã tạo %s: viết các từ đó một lần, lưu, rồi chạy: python hw_note.py learn %s"
                         % (result.missing_grid_path, result.missing_grid_path))
    return lines
