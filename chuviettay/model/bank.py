"""
Bank -- kho mẫu chữ viết tay đã học (file chu_cua_ban.json.gz).

Đây là "Model" trung tâm của ứng dụng: toàn bộ nét chữ đã dạy, cộng với vài chỉ mục
tính sẵn (rebuild()) để Writer (writer.py) tra cứu nhanh khi ghép văn bản thành chữ
viết tay.

So với bản gốc, có 2 thay đổi đáng chú ý (hành vi bên ngoài KHÔNG đổi, chỉ đổi CÁCH
báo lỗi/tái sử dụng code):
1. Không tìm thấy file kho mẫu -> ném BankNotFoundError thay vì gọi sys.exit() thẳng
   trong Model. Model không nên tự ý thoát chương trình hay in ra màn hình -- đó là
   việc của CLI/GUI (xem cli.py bắt lỗi này để in ra & thoát, còn GUI bắt lỗi này để
   hiện hộp thoại). Nhờ vậy Bank có thể dùng lại được trong bất kỳ ngữ cảnh nào (kể cả
   test) mà không sợ bị thoát chương trình đột ngột.
2. Thêm add_sample()/drop() để gộp lại đúng 4 dòng logic "thêm một mẫu mới vào kho"
   / "xoá một từ khỏi kho" mà bản gốc viết LẶP LẠI ở cả cmd_learn (hw_note.py) lẫn
   TeachTab/BankTab (hw_gui.py). Sửa một lần ở đây là đủ cho cả dòng lệnh lẫn giao diện.
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import sys
import tempfile
from typing import Any

from chuviettay.config import NANG, TONES
from chuviettay.model.bank_schema import (
    CURRENT_VERSION,
    BankCorruptedError,
    BankError,
    BankMigrationError,
    BankNotFoundError,
    BankSchemaError,
    BankValidationError,
    UnsupportedSchemaVersionError,
    load_and_validate,
)
from chuviettay.model.file_lock import FileLock
from chuviettay.model.text_utils import (
    Stroke,
    find_tone,
    near_extreme,
    shift,
    strip_tone,
    tone_info,
    vowel_x,
)

_log = logging.getLogger(__name__)

__all__ = [
    "CURRENT_VERSION",
    "Bank",
    "BankCorruptedError",
    "BankError",
    "BankMigrationError",
    "BankNotFoundError",
    "BankSchemaError",
    "BankValidationError",
    "UnsupportedSchemaVersionError",
    "merge_bank_dicts",
]


def _stroke_signature(inst: dict) -> tuple:
    """Tạo chữ ký toạ độ nét vẽ (làm tròn 2 chữ số) để so sánh trùng lặp mẫu."""
    strokes = inst.get("s", [])
    return tuple(tuple(round(float(c), 2) for c in s) for s in strokes)


def merge_bank_dicts(base: dict[str, Any], disk: dict[str, Any], deleted_words: set[str] | None = None) -> dict[str, Any]:
    """Hợp nhất dữ liệu kho mẫu trên đĩa (disk) vào kho mẫu trong bộ nhớ (base).
    Tránh lost-update khi nhiều tiến trình cùng ghi."""
    if deleted_words:
        for w in deleted_words:
            base.get("words", {}).pop(w, None)

    for c_name in ("words", "digits", "punct"):
        disk_c = disk.get(c_name, {})
        base_c = base.setdefault(c_name, {})
        for label, disk_samples in disk_c.items():
            if c_name == "words" and deleted_words and label in deleted_words:
                continue
            if label not in base_c:
                base_c[label] = list(disk_samples)
            else:
                existing_sigs = {_stroke_signature(s) for s in base_c[label]}
                for s in disk_samples:
                    sig = _stroke_signature(s)
                    if sig not in existing_sigs:
                        base_c[label].append(s)
                        existing_sigs.add(sig)

    return base


class Bank:
    """Kho mẫu chữ viết tay: self.words = {nhãn: [mẫu, ...]}, mỗi mẫu là 1 dict
    {"w": độ rộng, "s": danh sách nét tương đối, "T": dấu thanh, "vi": vị trí nguyên âm
    mang dấu, "ti": chỉ số nét là dấu thanh (hoặc -1)}.
    """

    def __init__(self, path: str):
        self.path = path
        self.d = load_and_validate(path)
        self.words: dict[str, list[dict]] = self.d["words"]
        self.digits: dict[str, list[dict]] = self.d["digits"]
        self.punct: dict[str, list[dict]] = self.d["punct"]
        self.xh: float = float(self.d["xh"])
        self.pen: dict = self.d["pen"]
        self.tl: dict[str, list[tuple[str, dict]]] = {}
        self.marks: dict[str, list[dict]] = {}
        self._deleted_words: set[str] = set()
        self.rebuild()
        _log.debug("Đã mở kho mẫu %s (%d từ)", path, len(self.words))

    # -------------------------------------------------------------- tạo kho mới
    @staticmethod
    def empty_dict() -> dict:
        """Cấu trúc kho mẫu trống, đúng những gì Bank/Writer cần để hoạt động được
        (giữ nguyên từ hw_gui.py bản gốc: new_empty_bank_dict())."""
        return {
            "schema_version": CURRENT_VERSION,
            "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0,
            "words": {}, "digits": {}, "punct": {}, "v": 1,
            "pen": {"tool": "pen", "color": "#000000ff", "width": "1.2", "capStyle": "round"},
            "x0": 78.0, "width": 500.0, "ratio": 6.6,
        }

    @classmethod
    def create_empty(cls, path: str) -> Bank:
        """Tạo một file kho mẫu TRỐNG tại `path` an toàn qua pipeline save() rồi mở lên."""
        bank = cls.__new__(cls)
        bank.path = os.path.abspath(path)
        bank.d = cls.empty_dict()
        bank.words = bank.d["words"]
        bank.digits = bank.d["digits"]
        bank.punct = bank.d["punct"]
        bank.xh = float(bank.d["xh"])
        bank.pen = bank.d["pen"]
        bank.tl = {}
        bank.marks = {}
        bank._deleted_words = set()
        bank.rebuild()
        bank.save()
        _log.info("Đã tạo kho mẫu trống mới: %s", path)
        return bank

    @classmethod
    def load_or_create(cls, path: str) -> Bank:
        """Mở kho mẫu tại `path`; nếu chưa tồn tại thì tự tạo kho trống mới trước khi
        mở. Dùng cho GUI (người dùng có thể trỏ tới một đường dẫn hoàn toàn mới để bắt
        đầu dạy chữ từ đầu) -- CLI vẫn dùng thẳng Bank(path) và báo lỗi nếu thiếu, như
        bản gốc, để tránh việc gõ sai đường dẫn --bank lại âm thầm tạo kho rỗng mới."""
        if not os.path.exists(path):
            return cls.create_empty(path)
        return cls(path)

    # -------------------------------------------------------------- chỉ mục tra cứu
    def rebuild(self) -> None:
        """Tính lại 2 chỉ mục tra cứu nhanh dùng khi ghép chữ (Writer):
        - self.tl: {chữ_đã_bỏ_dấu_thanh: [(nhãn_gốc, mẫu), ...]} -- để thay thế khi
          không có đúng từ nhưng có từ khác cùng "phần thân", ghép thêm dấu thanh riêng.
        - self.marks: {dấu_thanh: [mẫu_dấu_thanh_đã_tách_rời, ...]} -- các nét dấu
          thanh đã "gặt" (harvest) được từ những từ đã học, dùng để GHÉP vào thân chữ
          khi thay thế ở trên.
        Gọi lại sau khi thêm/xoá mẫu."""
        self.tl = {}
        for k, insts in self.words.items():
            tk = strip_tone(k)
            for inst in insts:
                if inst.get("T", "") == "" or inst.get("ti", -1) >= 0:
                    self.tl.setdefault(tk, []).append((k, inst))
        self.marks = {t: [] for t in TONES}
        for k, insts in self.words.items():
            for inst in insts:
                self._harvest(k, inst)
        for t, lst in self.marks.items():          # bỏ các dấu nằm quá xa (nhận nhầm hoặc viết lệch hẳn)
            if len(lst) >= 10:
                lo_dy, hi_dy = sorted(m["dy"] for m in lst)[len(lst) // 10], sorted(m["dy"] for m in lst)[-len(lst) // 10 - 1]
                lo_dx, hi_dx = sorted(m["dx"] for m in lst)[len(lst) // 10], sorted(m["dx"] for m in lst)[-len(lst) // 10 - 1]
                self.marks[t] = [m for m in lst if lo_dy <= m["dy"] <= hi_dy and lo_dx <= m["dx"] <= hi_dx]

    def _harvest(self, key: str, inst: dict) -> None:
        """Tách riêng nét dấu thanh ra khỏi một mẫu đã học (nếu mẫu đó có xác định
        được đâu là nét dấu thanh -- inst["ti"] >= 0), quy về gốc toạ độ (0,0), lưu vào
        self.marks để dùng ghép cho từ khác cùng dấu thanh về sau."""
        T, vi, ti = inst.get("T", ""), inst.get("vi", -1), inst.get("ti", -1)
        if not T or ti < 0 or vi < 0:
            return
        s = inst["s"][ti]
        xs, ys = s[0::2], s[1::2]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        body = [st for k, st in enumerate(inst["s"]) if k != ti]
        if not body:
            return
        xv = vowel_x(tone_info(key)[3], vi, inst["w"])
        dy = cy - (max(0.0, near_extreme(body, cx, max)) if T == NANG else near_extreme(body, cx, min))
        self.marks[T].append({"s": [shift(s, -cx, -cy)], "dx": cx - xv, "dy": dy})

    # -------------------------------------------------------------- đọc/ghi
    def save(self) -> None:
        """Ghi kho mẫu xuống đĩa AN TOÀN:
        1. Khóa file liên tiến trình qua {path}.lock (tránh xung đột khi chạy đồng thời GUI/CLI).
        2. Đọc và hợp nhất thay đổi trên đĩa (nếu có) để tránh lost-update.
        3. Ghi ra file tạm ngẫu nhiên duy nhất qua tempfile.mkstemp trong cùng thư mục.
        4. flush + fsync dữ liệu xuống đĩa vật lý, đóng sạch handle trước khi replace.
        5. os.replace nguyên tử đè lên file thật.
        6. fsync thư mục cha trên POSIX."""
        lock_path = self.path + ".lock"
        with FileLock(lock_path, timeout=10.0):
            # Nếu file đã tồn tại trên đĩa, đọc và hợp nhất các thay đổi từ đĩa
            if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
                try:
                    disk_d = load_and_validate(self.path)
                    merge_bank_dicts(self.d, disk_d, self._deleted_words)
                    self.rebuild()
                except (BankError, OSError, ValueError, KeyError) as e:
                    _log.warning("Không thể đọc/hợp nhất file trên đĩa (%s): %s", self.path, e)

            self.d["schema_version"] = CURRENT_VERSION
            parent_dir = os.path.dirname(self.path) or "."
            fd, tmp = tempfile.mkstemp(dir=parent_dir, prefix=".bank_", suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as raw_f:
                    with gzip.open(raw_f, "wt", encoding="utf-8", compresslevel=9) as gz_f:
                        json.dump(self.d, gz_f, ensure_ascii=False, separators=(",", ":"))
                    raw_f.flush()
                    os.fsync(raw_f.fileno())

                os.replace(tmp, self.path)

                if sys.platform != "win32":
                    try:
                        dirfd = os.open(parent_dir, os.O_RDONLY)
                        try:
                            os.fsync(dirfd)
                        finally:
                            os.close(dirfd)
                    except OSError:
                        pass
                self._deleted_words.clear()
            except BaseException:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
        _log.debug("Đã lưu kho mẫu %s (%d từ)", self.path, len(self.words))

    # -------------------------------------------------------------- truy vấn
    def can(self, w: str) -> bool:
        """Có đủ mẫu để viết được từ/token `w` không (khớp thẳng, hoặc ghép được từ
        phần thân + dấu thanh rời)?"""
        if w in self.words:
            return True
        T = tone_info(w)[0]
        return strip_tone(w) in self.tl and (not T or bool(self.marks.get(T)))

    # -------------------------------------------------------------- thêm / xoá mẫu
    def add_sample(self, label: str, rel_strokes: list[Stroke], width: float) -> dict:
        """Thêm MỘT mẫu mới cho `label`. `rel_strokes` phải đã ở toạ độ TƯƠNG ĐỐI theo
        đơn vị kho mẫu (gốc = chân chữ ở x trái nhất) -- xem model/learning.py (học từ
        file .xopp) và view/word_canvas.py (vẽ trực tiếp trong app) để biết cách quy
        đổi. KHÔNG tự gọi rebuild()/save(): gọi rebuild() rồi save() một lần sau khi
        thêm xong một hoặc nhiều mẫu, để tránh phải rebuild lại nhiều lần liên tiếp khi
        học nhiều từ cùng lúc."""
        T, vi, _, _ = tone_info(label)
        # chỉ tìm nét dấu thanh khi từ CÓ dấu thanh và không phải một CỤM nhiều từ
        # (cụm nhiều từ viết liền, ví dụ "cà phê" dạy như một nhãn -- xem README) --
        # cùng điều kiện với bản gốc ở cả cmd_learn lẫn TeachTab.
        ti = find_tone(rel_strokes, label, self.xh) if (T and " " not in label) else -1
        inst = {"w": round(width, 2), "s": rel_strokes, "T": T, "vi": vi, "ti": ti}
        self.words.setdefault(label, []).append(inst)
        self._deleted_words.discard(label)
        return inst

    def add_sample_incremental(self, label: str, rel_strokes: list[Stroke], width: float) -> dict:
        """Thêm MỘT mẫu mới và cập nhật chỉ mục tra cứu (tl, marks) theo cách tăng dần (incremental)
        với độ phức tạp O(1), không duyệt lại toàn bộ kho mẫu."""
        inst = self.add_sample(label, rel_strokes, width)

        tk = strip_tone(label)
        if inst.get("T", "") == "" or inst.get("ti", -1) >= 0:
            self.tl.setdefault(tk, []).append((label, inst))

        T = inst.get("T", "")
        if T and T in self.marks:
            self._harvest(label, inst)
            lst = self.marks[T]
            if len(lst) >= 10:
                lo_dy, hi_dy = sorted(m["dy"] for m in lst)[len(lst) // 10], sorted(m["dy"] for m in lst)[-len(lst) // 10 - 1]
                lo_dx, hi_dx = sorted(m["dx"] for m in lst)[len(lst) // 10], sorted(m["dx"] for m in lst)[-len(lst) // 10 - 1]
                self.marks[T] = [m for m in lst if lo_dy <= m["dy"] <= hi_dy and lo_dx <= m["dx"] <= hi_dx]

        return inst

    def drop(self, word: str) -> int:
        """Xoá hết mẫu của `word` khỏi kho, trả về số mẫu đã xoá (0 nếu chưa có từ đó).
        KHÔNG tự rebuild()/save()."""
        self._deleted_words.add(word)
        return len(self.words.pop(word, []))
