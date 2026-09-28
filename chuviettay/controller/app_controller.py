"""
AppController -- lớp điều phối DUY NHẤT giữa Model và giao diện (CLI/GUI).

VÌ SAO CÓ LỚP NÀY (so với bản gốc):
Bản gốc có 2 "đường" riêng biệt cùng làm những việc gần giống nhau:
  - hw_note.py: các hàm cmd_write/cmd_learn/cmd_check/cmd_drop/cmd_stats/cmd_seed nhận
    argparse.Namespace, tự thao tác Bank, tự print() kết quả.
  - hw_gui.py: các tab tự thao tác thẳng vào bank.words / bank.rebuild() / bank.save(),
    và riêng tab Viết chữ còn giả lập một argparse.Namespace rồi gọi cmd_write() +
    redirect_stdout để "bắt" chuỗi in ra -- rất dễ vỡ nếu ai đó đổi câu chữ in ra.
Hệ quả: cùng một việc (thống kê, xuất file kiểm tra, hiệu chỉnh cỡ tay, tìm từ thiếu...)
được viết 2 lần, hai bản dần lệch nhau (ví dụ: danh sách "từ còn thiếu" của GUI bỏ qua
tuỳ chọn strict-case của chính lần viết đó).

Giờ cả cli.py lẫn view/ đều chỉ gọi các phương thức ở đây. Quy ước:
  - Nhận/trả dữ liệu thuần (str, số, list, dataclass) -- KHÔNG argparse.Namespace, KHÔNG
    tkinter, KHÔNG print().
  - Không tự nuốt lỗi: lỗi cứ ném lên, nơi gọi (CLI/GUI) quyết định trình bày cho người
    dùng thế nào. Controller chỉ ghi log các thao tác thành công/quan trọng.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

from chuviettay import paths
from chuviettay.config import TONES
from chuviettay.controller.results import (
    BankStats, CheckResult, DropResult, LearnResult, SeedResult, TeachOutcome,
    WriteOptions, WriteResult,
)
from chuviettay.model import composer, learning, xopp
from chuviettay.model.bank import (  # noqa: F401  (re-export cho cli.py/view)
    Bank, BankCorruptedError, BankError, BankNotFoundError, BankValidationError, UnsupportedSchemaVersionError,
)
from chuviettay.model.calibration import compute_scale
from chuviettay.model.seed_words import SEED
from chuviettay.model.text_utils import Stroke

_log = logging.getLogger(__name__)

# Nhãn hiển thị các dấu thanh, đúng thứ tự trong config.TONES
TONE_NAMES = ("huyền", "sắc", "ngã", "hỏi", "nặng")


class AppController:
    """Giữ trạng thái ứng dụng (kho mẫu đang mở + hệ số cỡ tay của phiên dạy hiện tại)
    và cung cấp các thao tác nghiệp vụ. Một Controller cho mỗi tiến trình: CLI tạo mới
    mỗi lần chạy lệnh, GUI tạo một lần khi mở cửa sổ và giữ suốt phiên làm việc."""

    def __init__(self, bank_path: str | None = None):
        self.bank_path: str = bank_path or paths.default_bank_path()
        self.bank: Bank | None = None
        # Hệ số cỡ tay của PHIÊN dạy hiện tại (1.0 = chưa hiệu chỉnh). Là trạng thái
        # nghiệp vụ chứ không phải trạng thái giao diện nên để ở Controller.
        self.session_scale: float = 1.0
        _log.debug("Khởi tạo AppController (bank_path=%s)", self.bank_path)

    # ------------------------------------------------------------------ kho mẫu
    def load_bank(self, path: str | None = None, create_if_missing: bool = False) -> Bank:
        """Mở kho mẫu (mặc định: đường dẫn hiện tại của Controller).

        create_if_missing=False (CLI): thiếu file -> BankNotFoundError, đúng hành vi
            bản gốc, tránh việc gõ sai --bank lại âm thầm tạo kho rỗng mới.
        create_if_missing=True (GUI): thiếu file -> tự tạo kho trống đúng cấu trúc để
            người dùng bắt đầu dạy chữ từ đầu.
        Đổi kho mẫu thì hệ số cỡ tay của phiên cũ không còn ý nghĩa -> đặt lại 1.0.
        """
        target = path or self.bank_path
        bank = Bank.load_or_create(target) if create_if_missing else Bank(target)
        self.bank = bank
        self.bank_path = target
        self.session_scale = 1.0
        _log.info("Đã mở kho mẫu: %s (%d từ)", target, len(bank.words))
        return bank

    def reload_bank(self) -> Bank:
        """Nạp lại đúng kho mẫu đang mở từ đĩa (đường dẫn không đổi), để chắc chắn dữ
        liệu trong bộ nhớ khớp với file -- dùng khi nghi ngờ file bị chương trình khác
        ghi đè."""
        scale = self.session_scale                     # cùng một kho mẫu -> giữ hệ số cỡ tay của phiên
        bank = self.load_bank(self.bank_path, create_if_missing=False)
        self.session_scale = scale
        return bank

    @property
    def has_bank(self) -> bool:
        """Đã có kho mẫu hợp lệ được nạp hay chưa."""
        return self.bank is not None

    @property
    def x_height(self) -> float:
        """Chiều cao chữ thường của kho mẫu -- giao diện dùng để vẽ đường kẻ mốc."""
        return self._require_bank().xh

    def _require_bank(self) -> Bank:
        if self.bank is None:
            raise RuntimeError("Chưa mở kho mẫu nào (hãy gọi load_bank() trước).")
        return self.bank

    # ------------------------------------------------------------------ viết chữ
    def write_text(self, text: str, opts: WriteOptions, out_path: str) -> WriteResult:
        """Đổi văn bản thành file .xopp nét viết tay. Kết quả có sẵn `missing` (các
        token chưa có mẫu, tính từ CHÍNH lần viết này theo đúng tuỳ chọn người dùng đã
        đặt) nên nơi gọi không cần tính lại lần nữa."""
        opts.validate()
        bank = self._require_bank()
        result = composer.write_document(bank, text, opts, out_path)
        _log.info("Viết %s: %d dòng, %d nét, thiếu mẫu %d/%d token",
                  out_path, result.n_lines, result.n_strokes,
                  result.n_missing_tokens, result.n_tokens)
        return result

    # ------------------------------------------------------------------ học / dạy
    def learn_from_files(self, files: list[str]) -> LearnResult:
        """Học từ các file .xopp đã viết tay vào lưới ô (lệnh `learn`)."""
        bank = self._require_bank()
        result = learning.learn_from_files(bank, files)
        _log.info("Học thêm %d mẫu từ %d file", result.n_added, len(files))
        return result

    def pick_calibration_word(self) -> str | None:
        """Từ đã có nhiều mẫu, độ rộng ổn định -- dùng làm từ mốc để hiệu chỉnh cỡ tay."""
        return xopp.pick_calib_word(self._require_bank())

    def teach_word(
        self,
        label: str,
        rel_strokes: list[Stroke],
        width: float,
        calibrating: bool = False,
        recompute: Callable[[float], tuple[list[Stroke], float]] | None = None,
    ) -> TeachOutcome:
        """Lưu MỘT từ vừa vẽ trực tiếp trong app (không qua file .xopp trung gian).

        rel_strokes/width: nét + độ rộng đã quy về đơn vị kho mẫu bằng session_scale
            HIỆN TẠI (việc quy đổi từ pixel màn hình là của view/word_canvas.py).
        calibrating: đây là từ mốc do pick_calibration_word() chọn -- so độ rộng vừa
            vẽ với độ rộng trung vị đã học trước đây của đúng từ đó để suy ra hệ số
            cỡ tay MỚI (calibration.compute_scale), cập nhật self.session_scale rồi
            tính lại nét/độ rộng theo hệ số mới trước khi lưu.
        recompute: hàm nhận hệ số mới, trả (nét, độ rộng) tính lại TỪ DỮ LIỆU PIXEL GỐC
            (view truyền canvas.to_bank_strokes vào đây). Chính xác nhất vì không bị
            làm tròn 2 lần. Nếu không truyền, tự co giãn nét đã có theo tỉ lệ mới/cũ
            (kết quả tương đương, lệch tối đa ~0.01 đơn vị do làm tròn).
        """
        bank = self._require_bank()
        recalibrated = False
        if calibrating:
            ref_list = bank.words.get(label)
            if ref_list and width > 0.5:
                raw_width = width / self.session_scale     # quy ngược về "thô" (chưa nhân hệ số cũ)
                new_scale = compute_scale(ref_list, raw_width)
                if recompute is not None:
                    rel_strokes, width = recompute(new_scale)
                else:
                    factor = new_scale / self.session_scale
                    rel_strokes = [[round(v * factor, 2) for v in s] for s in rel_strokes]
                    width = round(width * factor, 2)
                self.session_scale = new_scale
                recalibrated = True

        instance = bank.add_sample(label, rel_strokes, width)
        bank.rebuild()
        bank.save()
        _log.info("Dạy từ %r (%s), hệ số cỡ tay phiên hiện tại: %.2fx",
                  label, "hiệu chỉnh cỡ tay" if recalibrated else "bình thường", self.session_scale)
        return TeachOutcome(label=label, instance=instance,
                            session_scale=self.session_scale, recalibrated=recalibrated)

    def missing_seed_words(self, n: int, exclude: Iterable[str] = ()) -> list[str]:
        """Tối đa n từ tiếng Việt thông dụng (SEED) mà kho mẫu CHƯA đủ để viết, bỏ qua
        các từ trong `exclude` (ví dụ đã nằm sẵn trong hàng đợi dạy)."""
        bank = self._require_bank()
        excl = set(exclude)
        return [w for w in SEED if not bank.can(w) and w not in excl][:n]

    def export_seed_grid(self, n: int, out_path: str) -> SeedResult:
        """Lệnh `seed`: tạo file lưới ô các từ thông dụng còn thiếu để viết mẫu."""
        bank = self._require_bank()
        todo = self.missing_seed_words(n)
        xopp.make_grid(
            out_path, todo, bank,
            "Từ tiếng Việt thông dụng còn thiếu: viết mỗi từ vào ô rồi Ctrl+S và chạy: "
            "python hw_note.py learn %s" % out_path)
        _log.info("Xuất %s với %d từ thông dụng còn thiếu", out_path, len(todo))
        return SeedResult(out_path=out_path, words=todo)

    # ------------------------------------------------------------------ quản lý kho
    def get_stats(self) -> BankStats:
        bank = self._require_bank()
        return BankStats(
            n_words=len(bank.words),
            n_samples=sum(len(v) for v in bank.words.values()),
            digit_counts={k: len(v) for k, v in sorted(bank.digits.items())},
            punct_counts={k: len(v) for k, v in bank.punct.items()},
            tone_mark_counts={t: len(bank.marks[t]) for t in TONES},
        )

    def list_words(self) -> list[tuple[str, int]]:
        """[(từ, số mẫu), ...] sắp theo thứ tự chữ cái -- để hiển thị/tìm kiếm."""
        bank = self._require_bank()
        return sorted((w, len(insts)) for w, insts in bank.words.items())

    def drop_words(self, words: list[str]) -> DropResult:
        """Xoá hết mẫu của các từ đã cho, rồi rebuild + lưu MỘT lần."""
        bank = self._require_bank()
        removed: dict[str, int] = {}
        for w in words:
            removed[w] = removed.get(w, 0) + bank.drop(w)   # trùng từ -> cộng dồn, không ghi đè
        bank.rebuild()
        bank.save()
        _log.info("Xoá từ khỏi kho: %s", removed)
        return DropResult(removed=removed)

    def export_check(self, out_path: str) -> CheckResult:
        """Lệnh `check`: xuất file lưới ô xem lại toàn bộ chữ đã học (kèm chữ gõ)."""
        bank = self._require_bank()
        keys = sorted(bank.words)
        samples = {k: bank.words[k][0]["s"] for k in keys}
        xopp.make_grid(
            out_path, keys, bank,
            "Kiểm tra kho mẫu: chữ gõ ở góc ô phải khớp chữ viết tay. "
            "Sai thì: python hw_note.py drop <từ>",
            samples, calib=False)
        _log.info("Xuất file kiểm tra %s (%d từ)", out_path, len(keys))
        return CheckResult(out_path=out_path, n_words=len(keys))
