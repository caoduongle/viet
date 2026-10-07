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

from typing import TYPE_CHECKING

from chuviettay.model.composer import WriteResult

if TYPE_CHECKING:
    from chuviettay.controller.results import BankStats

MAX_MISSING_SHOWN = 25   # hiện tối đa bao nhiêu từ thiếu trong bản tóm tắt


def write_report_lines(result: WriteResult) -> list[str]:
    ok = result.n_tokens - result.n_missing_tokens
    lines = [
        "Xong: %s  (%d dòng, %d nét; đủ mẫu cho %d/%d từ)"
        % (result.out_path, result.n_lines, result.n_strokes, ok, result.n_tokens),
        "Mở file này -> Ctrl+A -> Ctrl+C -> dán vào sổ của bạn (Ctrl+V) rồi kéo về đúng chỗ.",
    ]
    if getattr(result, "assembled_words", None):
        shown = result.assembled_words[:MAX_MISSING_SHOWN]
        lines.append("Đã ghép từ chữ cái cho %d từ: %s%s" % (
            len(result.assembled_words),
            " ".join(shown),
            " ..." if len(result.assembled_words) > MAX_MISSING_SHOWN else ""))
    if result.missing:
        items = result.missing_sorted()
        lines.append("Chưa có mẫu cho %d mục (chỗ đó đang để trống): %s%s" % (
            len(items),
            " ".join(k for k, _ in items[:MAX_MISSING_SHOWN]),
            " ..." if len(items) > MAX_MISSING_SHOWN else ""))
        if getattr(result, "missing_letters", None):
            let_items = [f"{item[0]}(x{item[1]})" for item in result.missing_letters[:MAX_MISSING_SHOWN]]
            lines.append("Chữ cái/dấu còn thiếu để ghép (%d): %s%s" % (
                len(result.missing_letters),
                " ".join(let_items),
                " ..." if len(result.missing_letters) > MAX_MISSING_SHOWN else ""))
        if result.missing_grid_path:
            lines.append("Đã tạo %s: viết các từ đó một lần, lưu, rồi chạy: python hw_note.py learn %s"
                         % (result.missing_grid_path, result.missing_grid_path))
    if getattr(result, "missing_symbols", None):
        sym_items = result.missing_symbols_sorted()
        lines.append("Ký hiệu thiếu mẫu (%d): %s" % (
            len(sym_items),
            ", ".join("%s (x%d)" % (s, c) for s, c in sym_items[:MAX_MISSING_SHOWN])))
    return lines


TONE_NAMES = ("huyền", "sắc", "ngã", "hỏi", "nặng")


def format_stats_gui(stats: BankStats) -> str:
    """Nhãn thống kê nhiều dòng cho tab Kho mẫu (thuần: không cần Tk, test được)."""
    digits = " ".join("%s:%d" % kv for kv in stats.digit_counts.items()) or "(chưa có)"
    puncts = " ".join("%s:%d" % kv for kv in stats.punct_counts.items()) or "(chưa có)"
    marks = " ".join(str(n) for n in stats.tone_mark_counts.values())
    letters = " ".join("%s:%d" % kv for kv in stats.letter_counts.items()) or "(chưa có)"

    total_chars = (
        stats.n_letters
        + len(stats.digit_counts)
        + len(stats.punct_counts)
        + sum(1 for c in stats.tone_mark_counts.values() if c > 0)
    )
    legacy_note = f" (kèm {stats.n_words} từ cũ)" if stats.n_words > 0 else ""
    headline = f"{total_chars} ký tự, {stats.n_samples} mẫu nét{legacy_note}"

    lines = [
        headline,
        "Chữ cái đơn lẻ (%d chữ): %s" % (stats.n_letters, letters),
        "Chữ số có mẫu: " + digits,
        "Dấu câu có mẫu: " + puncts,
        "Dấu thanh để ghép (%s): %s" % (",".join(TONE_NAMES), marks),
    ]
    return "\n".join(lines)
