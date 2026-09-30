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
import time
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
    classify_token,
    find_tone,
    near_extreme,
    sample_signature,
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


def _sample_signature(inst: dict) -> tuple:
    """Tạo chữ ký định danh mẫu gồm toạ độ nét vẽ (làm tròn 2 chữ số) và siêu dữ liệu (w, T, vi, ti)
    để so sánh và khử trùng lặp chính xác."""
    strokes = tuple(tuple(round(float(c), 2) for c in s) for s in inst.get("s", []))
    w = round(float(inst.get("w", 0.0)), 2)
    T = str(inst.get("T", ""))
    vi = int(inst.get("vi", -1))
    ti = int(inst.get("ti", -1))
    return (strokes, w, T, vi, ti)


# Giữ alias tương thích ngược nếu có module khác gọi _stroke_signature
_stroke_signature = _sample_signature


def _tombstone_ts(val: Any) -> float:
    if isinstance(val, dict):
        return float(val.get("deleted_at", 0.0))
    if isinstance(val, (int, float)):
        return float(val)
    return 0.0


def merge_bank_dicts(
    base: dict[str, Any],
    disk: dict[str, Any],
    deleted_words: set[str] | None = None,
    readded_words: dict[str, float] | set[str] | None = None,
) -> dict[str, Any]:
    """Hợp nhất dữ liệu kho mẫu trên đĩa (disk) vào kho mẫu trong bộ nhớ (base).
    Tránh lost-update khi nhiều tiến trình cùng ghi, đồng thời bảo vệ deletion tombstones."""
    # 1. Hợp nhất deletion tombstones
    disk_tombstones = dict(disk.get("tombstones", {}))
    base_tombstones = dict(base.setdefault("tombstones", {}))

    # Chuẩn hoá readded_words sang dict[str, float]
    readd_map: dict[str, float] = {}
    if readded_words:
        if isinstance(readded_words, dict):
            readd_map = dict(readded_words)
        else:
            now = time.time()
            readd_map = {w: now for w in readded_words}

    # Nếu có deleted_words vừa xoá trong phiên hiện tại -> cập nhật tombstone
    now_ts = time.time()
    base_gen = int(base.get("generation", 0))
    if deleted_words:
        for w in deleted_words:
            if w not in base_tombstones:
                base_tombstones[w] = {"deleted_at": now_ts, "generation": base_gen}

    # Hợp nhất disk_tombstones và base_tombstones: timestamp xoá mới hơn thì thắng
    merged_tombstones: dict[str, Any] = {}
    all_tomb_keys = set(disk_tombstones.keys()) | set(base_tombstones.keys())
    for w in all_tomb_keys:
        t_disk = disk_tombstones.get(w)
        t_base = base_tombstones.get(w)
        if t_disk is not None and t_base is not None:
            chosen = t_base if _tombstone_ts(t_base) >= _tombstone_ts(t_disk) else t_disk
        elif t_disk is not None:
            chosen = t_disk
        else:
            chosen = t_base
        if isinstance(chosen, (int, float)) and not isinstance(chosen, bool):
            chosen = {"deleted_at": float(chosen), "generation": 0}
        merged_tombstones[w] = chosen

    # Nếu base có từ chủ động dạy lại trong phiên hiện tại với readded_at > deleted_at -> xoá tombstone
    if readd_map:
        for w, r_ts in readd_map.items():
            t_val = merged_tombstones.get(w)
            if t_val is not None:
                if r_ts > _tombstone_ts(t_val):
                    merged_tombstones.pop(w, None)
            else:
                merged_tombstones.pop(w, None)

    # Cập nhật in-place vào base["tombstones"] để bảo toàn identity với self._tombstones
    base_tomb_dict = base.setdefault("tombstones", {})
    base_tomb_dict.clear()
    base_tomb_dict.update(merged_tombstones)

    # Áp dụng tombstone để loại bỏ từ / ký hiệu / chữ số / dấu câu / chữ cái đã bị xoá
    for w in merged_tombstones:
        for c_name in ("words", "digits", "punct", "symbols", "letters"):
            base.get(c_name, {}).pop(w, None)

    # Đồng bộ generation cao hơn giữa base và disk
    disk_gen = int(disk.get("generation", 0))
    if disk_gen > base_gen:
        base["generation"] = disk_gen

    # 2. Hợp nhất words, digits, punct, symbols, letters
    for c_name in ("words", "digits", "punct", "symbols", "letters"):
        disk_c = disk.get(c_name, {})
        base_c = base.setdefault(c_name, {})
        for label, disk_samples in disk_c.items():
            if label in merged_tombstones:
                continue
            if label not in base_c:
                base_c[label] = list(disk_samples)
            else:
                existing_sigs = {_sample_signature(s) for s in base_c[label]}
                for s in disk_samples:
                    sig = _sample_signature(s)
                    if sig not in existing_sigs:
                        base_c[label].append(s)
                        existing_sigs.add(sig)

    # 3. Hợp nhất marks tự dạy nếu có
    disk_marks = disk.get("marks", {})
    if disk_marks:
        base_marks = base.setdefault("marks", {t: [] for t in TONES})
        for t in TONES:
            existing_sigs = {_sample_signature(s) for s in base_marks.get(t, [])}
            for m in disk_marks.get(t, []):
                sig = _sample_signature(m)
                if sig not in existing_sigs:
                    base_marks.setdefault(t, []).append(m)
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
        self.symbols: dict[str, list[dict]] = self.d.setdefault("symbols", {})
        self.letters: dict[str, list[dict]] = self.d.setdefault("letters", {})
        self.xh: float = float(self.d["xh"])
        self.pen: dict = self.d["pen"]
        self.tl: dict[str, list[tuple[str, dict]]] = {}
        self._raw_marks: dict[str, list[dict]] = {t: [] for t in TONES}
        self.marks: dict[str, list[dict]] = {t: [] for t in TONES}
        self._tombstones: dict[str, Any] = self.d.setdefault("tombstones", {})
        for k, v in list(self._tombstones.items()):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                self._tombstones[k] = {"deleted_at": float(v), "generation": 0}
        self._deleted_words: set[str] = set()
        self._readded_words: dict[str, float] = {}
        self._generation: int = int(self.d.get("generation", 0))
        self._last_synced_mtime_ns: int | None = None
        self._last_synced_size: int | None = None
        try:
            st = os.stat(path)
            self._last_synced_mtime_ns = st.st_mtime_ns
            self._last_synced_size = st.st_size
        except OSError:
            pass
        self._dirty: bool = False
        self.rebuild()
        _log.debug("Đã mở kho mẫu %s (%d từ, %d ký hiệu, %d chữ cái)", path, len(self.words), len(self.symbols), len(self.letters))

    # -------------------------------------------------------------- tạo kho mới
    @staticmethod
    def empty_dict() -> dict:
        """Cấu trúc kho mẫu trống, đúng những gì Bank/Writer cần để hoạt động được
        (giữ nguyên từ hw_gui.py bản gốc: new_empty_bank_dict())."""
        return {
            "schema_version": CURRENT_VERSION,
            "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0,
            "words": {}, "digits": {}, "punct": {}, "symbols": {}, "letters": {}, "v": 1,
            "pen": {"tool": "pen", "color": "#000000ff", "width": "1.2", "capStyle": "round"},
            "x0": 78.0, "width": 500.0, "ratio": 6.6,
            "tombstones": {},
            "generation": 0,
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
        bank.symbols = bank.d["symbols"]
        bank.letters = bank.d["letters"]
        bank.xh = float(bank.d["xh"])
        bank.pen = bank.d["pen"]
        bank.tl = {}
        bank._raw_marks = {t: [] for t in TONES}
        bank.marks = {t: [] for t in TONES}
        bank._tombstones = bank.d.setdefault("tombstones", {})
        bank._deleted_words = set()
        bank._readded_words = {}
        bank._generation = 0
        bank._last_synced_mtime_ns = None
        bank._last_synced_size = None
        bank._dirty = False
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
        self._raw_marks = {t: [] for t in TONES}
        standalone_marks = self.d.get("marks", {})
        for t in TONES:
            for m in standalone_marks.get(t, []):
                self._raw_marks[t].append(dict(m))
        for k, insts in self.words.items():
            for inst in insts:
                self._harvest(k, inst)
        self.marks = {t: [] for t in TONES}
        for t in TONES:
            self._refresh_tone_marks(t)

    def _harvest(self, key: str, inst: dict) -> dict | None:
        """Tách riêng nét dấu thanh ra khỏi một mẫu đã học (nếu mẫu đó có xác định
        được đâu là nét dấu thanh -- inst["ti"] >= 0), quy về gốc toạ độ (0,0), lưu vào
        self._raw_marks để dùng ghép cho từ khác cùng dấu thanh về sau."""
        T, vi, ti = inst.get("T", ""), inst.get("vi", -1), inst.get("ti", -1)
        if not T or ti < 0 or vi < 0 or T not in self._raw_marks:
            return None
        if ti >= len(inst["s"]):
            return None
        s = inst["s"][ti]
        xs, ys = s[0::2], s[1::2]
        if not xs or not ys:
            return None
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        body = [st for k, st in enumerate(inst["s"]) if k != ti]
        if not body:
            return None
        xv = vowel_x(tone_info(key)[3], vi, inst["w"])
        dy = cy - (max(0.0, near_extreme(body, cx, max)) if T == NANG else near_extreme(body, cx, min))
        mark = {"s": [shift(s, -cx, -cy)], "dx": cx - xv, "dy": dy, "_src": key}
        self._raw_marks[T].append(mark)
        return mark

    def _refresh_tone_marks(self, T: str) -> None:
        """Cập nhật self.marks[T] từ self._raw_marks[T] bằng cách lọc phân vị 10-90% khi có >= 10 mẫu.
        Bảo toàn toàn bộ dấu trong self._raw_marks để không bị mất khi phân vị dịch chuyển."""
        lst = self._raw_marks.get(T, [])
        n = len(lst)
        if n >= 10:
            cut = n // 10
            lo_idx = cut
            hi_idx = n - 1 - cut
            dy_vals = sorted(m["dy"] for m in lst)
            dx_vals = sorted(m["dx"] for m in lst)
            lo_dy, hi_dy = dy_vals[lo_idx], dy_vals[hi_idx]
            lo_dx, hi_dx = dx_vals[lo_idx], dx_vals[hi_idx]
            self.marks[T] = [m for m in lst if lo_dy <= m["dy"] <= hi_dy and lo_dx <= m["dx"] <= hi_dx]
        else:
            self.marks[T] = list(lst)

    # -------------------------------------------------------------- cờ lưu hoãn (US7)
    @property
    def is_dirty(self) -> bool:
        """Kiểm tra kho mẫu có thay đổi chưa được ghi xuống đĩa hay không."""
        return self._dirty

    def mark_dirty(self) -> None:
        """Đánh dấu kho mẫu đã có thay đổi mới trong bộ nhớ."""
        self._dirty = True

    def flush(self, force_overwrite: bool = False) -> None:
        """Ép ghi các thay đổi dơ (dirty) xuống đĩa nếu có."""
        if self._dirty:
            self.save(force_overwrite=force_overwrite)

    # -------------------------------------------------------------- đọc/ghi
    def save(self, force_overwrite: bool = False) -> None:
        """Ghi kho mẫu xuống đĩa AN TOÀN:
        1. Khóa file liên tiến trình qua {path}.lock (tránh xung đột khi chạy đồng thời GUI/CLI).
        2. Đọc và hợp nhất thay đổi trên đĩa (nếu có thay đổi ngoài) để tránh lost-update.
           Nếu đọc/hợp nhất thất bại, huỷ bỏ ngay lập tức và raise BankError, không ghi đè,
           trừ khi force_overwrite=True.
        3. Ghi ra file tạm ngẫu nhiên duy nhất qua tempfile.mkstemp trong cùng thư mục.
        4. flush + fsync dữ liệu xuống đĩa vật lý, đóng sạch handle trước khi replace.
        5. os.replace nguyên tử đè lên file thật.
        6. fsync thư mục cha trên POSIX."""
        lock_path = self.path + ".lock"
        with FileLock(lock_path, timeout=10.0):
            # Nếu file đã tồn tại trên đĩa và không force_overwrite, kiểm tra xem có bị tiến trình khác sửa đổi không
            needs_merge = not force_overwrite
            if force_overwrite:
                _log.warning("force_overwrite=True: Ghi đè trực tiếp kho mẫu xuống đĩa bỏ qua kiểm tra hợp nhất (%s)", self.path)
            elif os.path.exists(self.path) and os.path.getsize(self.path) > 0:
                try:
                    st = os.stat(self.path)
                    if (
                        self._last_synced_mtime_ns is not None
                        and self._last_synced_size is not None
                        and st.st_mtime_ns == self._last_synced_mtime_ns
                        and st.st_size == self._last_synced_size
                    ):
                        needs_merge = False
                except OSError:
                    needs_merge = True

                if needs_merge:
                    try:
                        disk_d = load_and_validate(self.path)
                        merge_bank_dicts(self.d, disk_d, self._deleted_words, self._readded_words)
                        self._tombstones = self.d.setdefault("tombstones", {})
                        self._generation = int(self.d.get("generation", 0))
                        self.rebuild()
                    except BankError:
                        _log.error("Không thể đọc/hợp nhất file trên đĩa (%s); dừng ghi để bảo vệ file gốc.", self.path)
                        raise
                    except (OSError, ValueError, KeyError) as e:
                        _log.error("Lỗi khi đọc file trên đĩa (%s): %s; dừng ghi để bảo vệ file gốc.", self.path, e)
                        raise BankCorruptedError(f"Không thể đọc/hợp nhất file trên đĩa ({self.path}): {e}") from e

            self.d["schema_version"] = CURRENT_VERSION
            parent_dir = os.path.dirname(self.path) or "."
            fd, tmp = tempfile.mkstemp(dir=parent_dir, prefix=".bank_", suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as raw_f:
                    with gzip.open(raw_f, "wt", encoding="utf-8", compresslevel=1) as gz_f:
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

                try:
                    st = os.stat(self.path)
                    self._last_synced_mtime_ns = st.st_mtime_ns
                    self._last_synced_size = st.st_size
                except OSError:
                    self._last_synced_mtime_ns = None
                    self._last_synced_size = None
                self._deleted_words.clear()
                self._readded_words.clear()
                self._dirty = False
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
        if w in self.words or w in self.digits or w in self.punct or w in self.symbols:
            return True
        T = tone_info(w)[0]
        return strip_tone(w) in self.tl and (not T or bool(self.marks.get(T)))

    # -------------------------------------------------------------- thêm / xoá mẫu
    def add_sample(self, label: str, rel_strokes: list[Stroke], width: float, dedup: bool = True) -> dict:
        """Thêm MỘT mẫu mới cho `label`. `rel_strokes` phải đã ở toạ độ TƯƠNG ĐỐI theo
        đơn vị kho mẫu (gốc = chân chữ ở x trái nhất). Tự động phân loại vào words, digits, punct hoặc symbols."""
        category = classify_token(label, set(self.symbols.keys()))
        target_dict = self.words
        if category == "digits":
            target_dict = self.digits
        elif category == "punct":
            target_dict = self.punct
        elif category == "symbols":
            target_dict = self.symbols

        # Khử trùng mẫu nét trùng lặp (T020)
        sig = sample_signature(rel_strokes)
        existing = target_dict.setdefault(label, [])
        if dedup:
            for ex in existing:
                ex_sig = ex.get("_sig")
                if ex_sig is None:
                    ex_sig = sample_signature(ex.get("s", []))
                    ex["_sig"] = ex_sig
                if ex_sig == sig:
                    return ex

        T, vi, _, _ = tone_info(label) if category == "words" else ("", -1, "", "")
        ti = find_tone(rel_strokes, label, self.xh) if (T and " " not in label) else -1
        inst = {"w": round(width, 2), "s": rel_strokes, "T": T, "vi": vi, "ti": ti, "_sig": sig}
        existing.append(inst)
        self._dirty = True

        # Chỉ đánh dấu vào _readded_words nếu từ này đang ở trạng thái bị xoá (có tombstone)
        if label in self._tombstones or label in self._deleted_words:
            self._readded_words[label] = time.time()
        self._deleted_words.discard(label)
        self._tombstones.pop(label, None)
        return inst

    def add_sample_incremental(self, label: str, rel_strokes: list[Stroke], width: float) -> dict:
        """Thêm MỘT mẫu mới và cập nhật chỉ mục tra cứu (tl, marks) theo cách tăng dần (incremental),
        bảo toàn toàn bộ dấu thanh thô và đảm bảo marks luôn khớp chính xác với rebuild()."""
        category = classify_token(label, set(self.symbols.keys()))
        target_dict = self.words
        if category == "digits":
            target_dict = self.digits
        elif category == "punct":
            target_dict = self.punct
        elif category == "symbols":
            target_dict = self.symbols
        existing = target_dict.get(label, [])
        count_before = len(existing)

        inst = self.add_sample(label, rel_strokes, width)
        if len(target_dict.get(label, [])) == count_before:
            return inst

        if category == "words":
            tk = strip_tone(label)
            if inst.get("T", "") == "" or inst.get("ti", -1) >= 0:
                self.tl.setdefault(tk, []).append((label, inst))

            T = inst.get("T", "")
            if T and T in self._raw_marks:
                mark = self._harvest(label, inst)
                if mark is not None:
                    self._refresh_tone_marks(T)

        return inst

    def drop(self, word: str) -> int:
        """Xoá hết mẫu của `word` (từ, chữ số, dấu câu hoặc ký hiệu) khỏi kho, trả về số mẫu đã xoá (0 nếu chưa có).
        Tự động dọn dẹp các chỉ mục tra cứu trong bộ nhớ (tl, _raw_marks, marks) và ghi nhận tombstone. KHÔNG tự save()."""
        target_dict = self.words
        if word in self.symbols:
            target_dict = self.symbols
        elif word in self.digits:
            target_dict = self.digits
        elif word in self.punct:
            target_dict = self.punct
        elif word in getattr(self, "letters", {}):
            target_dict = self.letters
        elif word not in self.words:
            return 0

        self._generation += 1
        self.d["generation"] = self._generation
        self._deleted_words.add(word)
        self._tombstones[word] = {"deleted_at": time.time(), "generation": self._generation}
        self._readded_words.pop(word, None)

        removed_samples = target_dict.pop(word, [])
        count = len(removed_samples)
        if count > 0:
            self._dirty = True

        # 1. Dọn dẹp chỉ mục thay thế thân chữ self.tl
        tk = strip_tone(word)
        if tk in self.tl:
            self.tl[tk] = [entry for entry in self.tl[tk] if entry[0] != word]
            if not self.tl[tk]:
                del self.tl[tk]

        # 2. Dọn dẹp các nét dấu thanh gặt được từ word trong self._raw_marks
        T = tone_info(word)[0]
        if T and T in self._raw_marks:
            self._raw_marks[T] = [m for m in self._raw_marks[T] if m.get("_src") != word]
            self._refresh_tone_marks(T)

        return count

    def add_symbol_sample(self, symbol: str, rel_strokes: list[Stroke], width: float) -> dict:
        """Thêm MỘT mẫu ký hiệu toán học mới vào kho symbols."""
        inst = {"w": round(width, 2), "s": rel_strokes}
        self.symbols.setdefault(symbol, []).append(inst)
        self._dirty = True
        return inst

    def drop_symbol(self, symbol: str) -> int:
        """Xoá toàn bộ mẫu của `symbol` khỏi kho symbols và ghi nhận tombstone."""
        if symbol not in self.symbols:
            return 0
        self._generation += 1
        self.d["generation"] = self._generation
        self._deleted_words.add(symbol)
        self._tombstones[symbol] = {"deleted_at": time.time(), "generation": self._generation}
        self._readded_words.pop(symbol, None)
        removed = self.symbols.pop(symbol, [])
        if removed:
            self._dirty = True
        return len(removed)

    def add_letter_sample(self, letter: str, rel_strokes: list[Stroke], width: float, dedup: bool = True) -> dict:
        """Thêm MỘT mẫu chữ cái mới vào self.letters."""
        sig = sample_signature(rel_strokes)
        existing = self.letters.setdefault(letter, [])
        if dedup:
            for ex in existing:
                ex_sig = ex.get("_sig")
                if ex_sig is None:
                    ex_sig = sample_signature(ex.get("s", []))
                    ex["_sig"] = ex_sig
                if ex_sig == sig:
                    return ex
        inst = {"w": round(width, 2), "s": rel_strokes, "_sig": sig}
        existing.append(inst)
        self._dirty = True

        if letter in self._tombstones or letter in self._deleted_words:
            self._readded_words[letter] = time.time()
        self._deleted_words.discard(letter)
        self._tombstones.pop(letter, None)
        return inst

    def drop_letter(self, letter: str) -> int:
        """Xoá toàn bộ mẫu của một chữ cái khỏi kho letters và ghi nhận tombstone."""
        if letter not in self.letters:
            return 0
        self._generation += 1
        self.d["generation"] = self._generation
        self._deleted_words.add(letter)
        self._tombstones[letter] = {"deleted_at": time.time(), "generation": self._generation}
        self._readded_words.pop(letter, None)
        removed = self.letters.pop(letter, [])
        if removed:
            self._dirty = True
        return len(removed)

    def add_tone_sample(self, tone: str, stroke: Stroke, dx: float = 0.0, dy: float = 0.0) -> dict:
        """Thêm MỘT mẫu dấu thanh rời trực tiếp vào kho marks."""
        if tone not in TONES:
            raise ValueError(f"Dấu thanh không hợp lệ: {tone!r}. Chỉ chấp nhận các dấu trong TONES.")
        xs, ys = stroke[0::2], stroke[1::2]
        cx = sum(xs) / len(xs) if xs else 0.0
        cy = sum(ys) / len(ys) if ys else 0.0
        mark = {"s": [shift(stroke, -cx, -cy)], "dx": dx, "dy": dy, "_src": "standalone"}
        marks_dict = self.d.setdefault("marks", {t: [] for t in TONES})
        marks_dict.setdefault(tone, []).append(mark)
        self._raw_marks.setdefault(tone, []).append(mark)
        self._refresh_tone_marks(tone)
        self._dirty = True
        return mark
