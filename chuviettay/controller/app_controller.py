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
import os
import threading
from collections.abc import Callable, Iterable

from chuviettay import paths
from chuviettay.config import TONES
from chuviettay.controller.results import (
    BankStats, CheckResult, DropResult, LearnResult, SeedResult, TeachOutcome,
    WriteOptions, WriteResult,
)
from chuviettay.document.ir import Document
from chuviettay.importer.base import ImportResult
from chuviettay.layout.engine import DocumentLayoutEngine
from chuviettay.model import learning, xopp
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
        self.debounce_delay: float = 2.0
        self._save_timer: threading.Timer | None = None
        self._save_lock = threading.Lock()
        _log.debug("Khởi tạo AppController (bank_path=%s)", self.bank_path)

    # ------------------------------------------------------------------ debounce save (US7)
    def schedule_save(self) -> None:
        """Lên lịch lưu kho mẫu sau khoảng thời gian debounce (mặc định 2.0s)."""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(self.debounce_delay, self._on_debounce_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _on_debounce_save(self) -> None:
        self.flush_save()

    def flush_save(self) -> None:
        """Ép ghi các thay đổi dơ (dirty) ngay lập tức xuống đĩa và huỷ timer."""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
            if self.bank and self.bank.is_dirty:
                self.bank.save()

    # ------------------------------------------------------------------ kho mẫu
    def load_bank(self, path: str | None = None, create_if_missing: bool = False) -> Bank:
        """Mở kho mẫu (mặc định: đường dẫn hiện tại của Controller).

        create_if_missing=False (CLI): thiếu file -> BankNotFoundError, đúng hành vi
            bản gốc, tránh việc gõ sai --bank lại âm thầm tạo kho rỗng mới.
        create_if_missing=True (GUI): thiếu file -> tự tạo kho trống đúng cấu trúc để
            người dùng bắt đầu dạy chữ từ đầu.
        Đổi kho mẫu thì hệ số cỡ tay của phiên cũ không còn ý nghĩa -> đặt lại 1.0.
        """
        self.flush_save()
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
    def bank_size(self) -> int:
        """Số lượng từ trong kho mẫu hiện tại."""
        return len(self.bank.words) if self.bank else 0

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
        """Đổi văn bản thuần thành file .xopp nét viết tay qua Document IR và DocumentLayoutEngine."""
        from chuviettay.importer.txt_importer import TxtImporter

        doc = TxtImporter().import_text(text).document
        return self.write_document(doc, opts, out_path)

    def write_document(self, document: Document, opts: WriteOptions, out_path: str) -> WriteResult:
        """Đổi Document IR thành file .xopp nét viết tay qua DocumentLayoutEngine."""
        opts.validate()
        bank = self._require_bank()
        engine = DocumentLayoutEngine(bank, opts)
        result = engine.render(document, out_path)
        _log.info("Viết document %s: %d dòng, %d nét, thiếu mẫu %d/%d token",
                  out_path, result.n_lines, result.n_strokes,
                  result.n_missing_tokens, result.n_tokens)
        return result

    def write_docx_fidelity(self, docx_path: str, opts: WriteOptions, out_path: str) -> WriteResult:
        """Đổi tệp DOCX thành .xopp theo chế độ Fidelity (giữ nguyên số trang, ảnh, bảng và vị trí)."""
        from chuviettay.fidelity.background import WhiteoutBackgroundGenerator
        from chuviettay.fidelity.converter import FidelityConverter
        from chuviettay.fidelity.engine import FidelityLayoutEngine
        from chuviettay.fidelity.extractor import SpatialTextExtractor

        opts.validate()
        bank = self._require_bank()

        out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
        os.makedirs(out_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(out_path))[0]
        bg_pdf_path = os.path.join(out_dir, f"{base_name}_background.pdf")

        # 1. Tạo tệp DOCX whiteout và chuyển sang PDF nền
        whiteout_docx = WhiteoutBackgroundGenerator.create_whiteout_docx(docx_path)
        try:
            FidelityConverter.convert_to_pdf(whiteout_docx, bg_pdf_path)
        finally:
            if os.path.exists(whiteout_docx):
                try:
                    os.remove(whiteout_docx)
                except OSError:
                    pass

        # 2. Trích xuất cấu trúc không gian các TextBox
        extractor = SpatialTextExtractor()
        doc = extractor.extract(docx_path, background_pdf=bg_pdf_path)

        # 3. Kết xuất nét viết tay vào từng Bounding Box
        engine = FidelityLayoutEngine(bank, opts)
        result = engine.render(doc, out_path)

        _log.info(
            "Fidelity render %s: %d trang, %d ảnh, %d bảng, %d dòng, %d nét, thiếu mẫu %d/%d token",
            out_path,
            result.n_pages,
            result.n_images,
            result.n_tables,
            result.n_lines,
            result.n_strokes,
            result.n_missing_tokens,
            result.n_tokens,
        )
        return result

    def import_document(self, file_path: str, fmt: str = "auto") -> ImportResult:
        """Nạp tài liệu từ file_path (hỗ trợ .txt, .md, .docx) thành Document IR."""
        from chuviettay.importer.base import get_importer_for_path

        importer = get_importer_for_path(file_path, fmt)
        res = importer.import_file(file_path)
        _log.info(
            "Nạp tài liệu %s: %d khối, %d cảnh báo, %d phần tử chưa hỗ trợ",
            file_path,
            len(res.document.blocks),
            len(res.warnings),
            len(res.unsupported),
        )
        return res

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
        deferred_save: bool = False,
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
        deferred_save: nếu True, đánh dấu dirty và lên lịch ghi hoãn (debounced 2.0s)
            thay vì ghi đè đồng bộ ngay lập tức, giúp UI phản hồi < 50ms.
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

        instance = bank.add_sample_incremental(label, rel_strokes, width)
        bank.mark_dirty()
        if deferred_save:
            self.schedule_save()
        else:
            bank.save()
        _log.info("Dạy từ %r (%s), hệ số cỡ tay phiên hiện tại: %.2fx",
                  label, "hiệu chỉnh cỡ tay" if recalibrated else "bình thường", self.session_scale)
        return TeachOutcome(label=label, instance=instance,
                            session_scale=self.session_scale, recalibrated=recalibrated)

    def teach_letter(
        self,
        letter: str,
        rel_strokes: list[Stroke],
        width: float,
        deferred_save: bool = False,
    ) -> TeachOutcome:
        """Lưu một mẫu chữ cái đơn lẻ vào kho letters (hoặc marks nếu là dấu thanh)."""
        bank = self._require_bank()
        if letter in TONES and rel_strokes:
            instance = bank.add_tone_sample(letter, rel_strokes[0])
        else:
            instance = bank.add_letter_sample(letter, rel_strokes, width)
        bank.mark_dirty()
        if deferred_save:
            self.schedule_save()
        else:
            bank.save()
        _log.info("Dạy chữ cái %r, hệ số cỡ tay phiên hiện tại: %.2fx", letter, self.session_scale)
        return TeachOutcome(
            label=letter,
            instance=instance,
            session_scale=self.session_scale,
            recalibrated=False,
        )

    def is_letter_token(self, token: str) -> bool:
        """Kiểm tra token có phải là chữ cái hoặc dấu thanh đơn lẻ hay không."""
        from chuviettay.model.text_utils import PUNCT_CHARS
        t = token.strip()
        if len(t) == 1 and not t.isdigit() and t not in PUNCT_CHARS:
            return True
        return t in TONES

    def drop_letter(self, letter: str) -> DropResult:
        """Xoá toàn bộ mẫu của chữ cái đã cho khỏi kho letters và lưu."""
        bank = self._require_bank()
        removed_count = bank.drop_letter(letter)
        bank.save()
        _log.info("Xoá chữ cái khỏi kho: %s (%d mẫu)", letter, removed_count)
        return DropResult(removed={letter: removed_count})

    def missing_seed_words(self, n: int, exclude: Iterable[str] = ()) -> list[str]:
        """Tối đa n từ tiếng Việt thông dụng (SEED) mà kho mẫu CHƯA đủ để viết, bỏ qua
        các từ trong `exclude` (ví dụ đã nằm sẵn trong hàng đợi dạy)."""
        bank = self._require_bank()
        excl = set(exclude)
        return [w for w in SEED if not bank.can(w) and w not in excl][:n]

    def missing_minimal_essentials(self, exclude: Iterable[str] = ()) -> list[str]:
        """Danh sách các ký tự/từ trong bộ tối thiểu (chữ số, dấu câu, top 60 từ) còn thiếu."""
        from chuviettay.model.seed_words import get_minimal_essentials

        bank = self._require_bank()
        excl = set(exclude)
        items = get_minimal_essentials(60)
        return [item for item in items if not bank.can(item) and item not in excl]

    def missing_letters_for_words(
        self,
        words: list[str],
        strict_case: bool = False,
    ) -> list[tuple[str, int, list[str]]]:
        """Tính toán danh sách các chữ cái và dấu thanh còn thiếu để viết các từ đã cho,
        sắp xếp theo độ phủ tham lam (greedy coverage)."""
        from chuviettay.model.text_utils import missing_letters_ranked

        bank = self._require_bank()
        return missing_letters_ranked(
            words,
            getattr(bank, "letters", {}),
            getattr(bank, "marks", {}),
            strict_case=strict_case,
        )

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
        letters = getattr(bank, "letters", {})
        return BankStats(
            n_words=len(bank.words),
            n_samples=sum(len(v) for v in bank.words.values()),
            digit_counts={k: len(v) for k, v in sorted(bank.digits.items())},
            punct_counts={k: len(v) for k, v in bank.punct.items()},
            tone_mark_counts={t: len(bank.marks[t]) for t in TONES},
            n_letters=len(letters),
            letter_counts={k: len(v) for k, v in sorted(letters.items())},
        )

    def list_words(self) -> list[tuple[str, int]]:
        """[(từ, số mẫu), ...] sắp theo thứ tự chữ cái -- để hiển thị/tìm kiếm."""
        bank = self._require_bank()
        return sorted((w, len(insts)) for w, insts in bank.words.items())

    def list_letters(self) -> list[tuple[str, int]]:
        """[(chữ_cái, số mẫu), ...] sắp theo thứ tự chữ cái -- để hiển thị/tìm kiếm."""
        bank = self._require_bank()
        letters = getattr(bank, "letters", {})
        return sorted((ch, len(insts)) for ch, insts in letters.items())

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
