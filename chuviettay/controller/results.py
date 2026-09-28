"""
Các dataclass kết quả trả về từ AppController.

Bản gốc trộn lẫn kết quả với cách HIỂN THỊ kết quả (in thẳng ra màn hình bằng print()
ngay trong hàm xử lý). Ở đây Controller chỉ trả DỮ LIỆU; CLI (cli.py) và GUI (view/)
mỗi bên tự quyết định hiển thị dữ liệu đó kiểu gì (một dòng in ra terminal, hay một
nhãn nhiều dòng trong cửa sổ) -- xem docstring module chuviettay/__init__.py.

WriteOptions/WriteResult (lệnh "write") và LearnResult (lệnh "learn") đã định nghĩa sẵn
trong model/composer.py và model/learning.py (vì đó là kiểu trả về TRỰC TIẾP của một
hàm Model, hợp lý để khai báo cạnh hàm đó) -- import lại ở đây cho tiện, khỏi phải nhớ
2 nơi khác nhau khi dùng từ cli.py/view/.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from chuviettay.model.composer import WriteOptions, WriteResult  # re-export
from chuviettay.model.learning import LearnResult  # re-export

__all__ = [
    "WriteOptions", "WriteResult", "LearnResult",
    "CheckResult", "DropResult", "SeedResult", "BankStats", "TeachOutcome",
]


@dataclass
class CheckResult:
    """Kết quả lệnh 'check' -- xuất file lưới ô xem lại toàn bộ kho mẫu."""
    out_path: str
    n_words: int


@dataclass
class DropResult:
    """Kết quả xoá một hoặc nhiều từ khỏi kho. removed: {từ: số mẫu đã xoá} (0 nếu
    từ đó chưa từng có trong kho)."""
    removed: dict[str, int] = field(default_factory=dict)


@dataclass
class SeedResult:
    """Kết quả lệnh 'seed' -- xuất file lưới ô các từ thông dụng còn thiếu."""
    out_path: str
    words: list[str] = field(default_factory=list)


@dataclass
class BankStats:
    """Thống kê kho mẫu (lệnh 'stats' / tab Kho mẫu)."""
    n_words: int
    n_samples: int
    digit_counts: dict[str, int] = field(default_factory=dict)
    punct_counts: dict[str, int] = field(default_factory=dict)
    tone_mark_counts: dict[str, int] = field(default_factory=dict)   # theo thứ tự TONES


@dataclass
class TeachOutcome:
    """Kết quả lưu MỘT từ vừa dạy trực tiếp trong app (tab Dạy từ mới)."""
    label: str
    instance: dict
    session_scale: float     # hệ số cỡ tay hiện tại của phiên dạy (dùng cho từ tiếp theo)
    recalibrated: bool       # lần lưu này có tính lại hệ số cỡ tay không
