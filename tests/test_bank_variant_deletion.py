"""Bộ kiểm thử đơn vị tự động toàn diện cho tính năng xóa biến thể mẫu nét (051)."""
import os
import pytest
from chuviettay.model.bank import Bank
from chuviettay.controller.app_controller import AppController
from chuviettay.browser.bridge import BrowserBridge


def test_drop_single_variant_letter(tmp_path):
    """Xóa 1 biến thể đơn lẻ của chữ cái: bảo toàn các mẫu còn lại, không tạo tombstone."""
    p = str(tmp_path / "test_letter.json.gz")
    b = Bank.create_empty(p)

    # Thêm 3 mẫu nét cho chữ "Ơ"
    b.add_letter_sample("Ơ", [[0.0, 0.0, 10.0, 10.0]], 5.0)
    b.add_letter_sample("Ơ", [[0.0, 0.0, 20.0, 20.0]], 6.0)
    b.add_letter_sample("Ơ", [[0.0, 0.0, 30.0, 30.0]], 7.0)
    assert len(b.letters["Ơ"]) == 3

    # Xóa mẫu nét ở chỉ số 1 (Mẫu #2)
    res = b.drop_samples("Ơ", [1], category="letters")
    assert res["removed_count"] == 1
    assert res["remaining_count"] == 2
    assert res["label_deleted"] is False

    # Kiểm tra các mẫu còn lại giữ nguyên nét và độ rộng của s1 và s3
    samples = b.letters["Ơ"]
    assert len(samples) == 2
    assert samples[0]["w"] == 5.0
    assert samples[1]["w"] == 7.0
    assert "letters:Ơ" not in b._tombstones


def test_drop_multiple_variants_descending(tmp_path):
    """Xóa nhiều biến thể cùng lúc theo chỉ số giảm dần, ngăn ngừa trượt chỉ số."""
    p = str(tmp_path / "test_multi.json.gz")
    b = Bank.create_empty(p)

    # Thêm 4 mẫu nét
    for w in [4.0, 5.0, 6.0, 7.0]:
        b.add_letter_sample("A", [[0.0, 0.0, w, w]], w)
    assert len(b.letters["A"]) == 4

    # Xóa chỉ số 0 và 2 (truyền lộn xộn [2, 0, 2] để kiểm tra dedup và sort)
    res = b.drop_samples("A", [2, 0, 2], category="letters")
    assert res["removed_count"] == 2
    assert res["remaining_count"] == 2
    assert res["label_deleted"] is False

    samples = b.letters["A"]
    # Trước: [4.0, 5.0, 6.0, 7.0] -> Bỏ 0 (4.0) và 2 (6.0) -> Còn lại [5.0, 7.0]
    assert samples[0]["w"] == 5.0
    assert samples[1]["w"] == 7.0


def test_drop_all_variants_cleans_label_and_creates_tombstone(tmp_path):
    """Xóa sạch tất cả biến thể của nhãn: tự động dọn nhãn, tạo tombstone và label_deleted = True."""
    p = str(tmp_path / "test_all.json.gz")
    b = Bank.create_empty(p)

    b.add_letter_sample("B", [[0.0, 0.0, 1.0, 1.0]], 5.0)
    b.add_letter_sample("B", [[0.0, 0.0, 2.0, 2.0]], 6.0)
    assert len(b.letters["B"]) == 2

    res = b.drop_samples("B", [0, 1], category="letters")
    assert res["removed_count"] == 2
    assert res["remaining_count"] == 0
    assert res["label_deleted"] is True
    assert "B" not in b.letters
    assert "letters:B" in b._tombstones
    assert "letters:B" in b._deleted_words


def test_drop_samples_invalid_indices_safe(tmp_path):
    """Chỉ số không hợp lệ (âm, vượt quá số mẫu, rỗng, không phải số) phải được bỏ qua an toàn."""
    p = str(tmp_path / "test_invalid.json.gz")
    b = Bank.create_empty(p)

    b.add_sample("1", [[0.0, 0.0, 1.0, 1.0]], 4.0)
    assert len(b.digits["1"]) == 1

    # Truyền chỉ số âm, vượt biên, chuỗi, rỗng
    res1 = b.drop_samples("1", [-1, 5, "invalid", None], category="digits")
    assert res1["removed_count"] == 0
    assert res1["remaining_count"] == 1
    assert res1["label_deleted"] is False

    res2 = b.drop_samples("1", [], category="digits")
    assert res2["removed_count"] == 0
    assert res2["remaining_count"] == 1

    # Nhãn không tồn tại
    res3 = b.drop_samples("non_existent", [0], category="digits")
    assert res3["removed_count"] == 0
    assert res3["remaining_count"] == 0
    assert res3["label_deleted"] is False


def test_drop_samples_word_rebuilds_tl(tmp_path):
    """Xóa biến thể của từ trong words phải cập nhật và tái lập chỉ mục self.tl."""
    p = str(tmp_path / "test_word.json.gz")
    b = Bank.create_empty(p)

    b.add_sample("chao", [[0.0, 0.0, 1.0, 1.0]], 10.0)
    b.add_sample("chao", [[0.0, 0.0, 2.0, 2.0]], 12.0)
    b.rebuild()
    assert len(b.words["chao"]) == 2
    assert "chao" in b.tl
    assert len(b.tl["chao"]) == 2

    # Xóa 1 biến thể của "chao"
    res = b.drop_samples("chao", [0], category="words")
    assert res["removed_count"] == 1
    assert res["remaining_count"] == 1
    assert len(b.tl["chao"]) == 1
    assert b.tl["chao"][0][1]["w"] == 12.0


def test_drop_samples_marks_category(tmp_path):
    """Xóa biến thể của dấu thanh trong category marks."""
    p = str(tmp_path / "test_marks.json.gz")
    b = Bank.create_empty(p)

    # Thêm 2 mẫu dấu huyền (\u0300)
    b.add_tone_sample("\u0300", [[0.0, 0.0, 1.0, 1.0]])
    b.add_tone_sample("\u0300", [[0.0, 0.0, 2.0, 2.0]])
    assert len(b.marks["\u0300"]) == 2

    res = b.drop_samples("\u0300", [0], category="marks")
    assert res["removed_count"] == 1
    assert res["remaining_count"] == 1
    assert len(b.marks["\u0300"]) == 1


def test_controller_and_bridge_integration(tmp_path):
    """Kiểm tra tích hợp lưu đĩa qua AppController và phong bì trả về của BrowserBridge."""
    p = str(tmp_path / "test_ctl.json.gz")
    b = Bank.create_empty(p)
    b.add_letter_sample("X", [[0.0, 0.0, 1.0, 1.0]], 5.0)
    b.add_letter_sample("X", [[0.0, 0.0, 2.0, 2.0]], 6.0)
    b.save()

    # Kiểm tra trực tiếp qua AppController
    ctl = AppController(bank_path=p)
    ctl.load_bank()
    res_ctl = ctl.drop_label_samples("X", [0], category="letters")
    assert res_ctl["removed_count"] == 1
    assert res_ctl["remaining_count"] == 1

    # Kiểm tra qua BrowserBridge
    bridge = BrowserBridge(bank_path=p)
    init_res = bridge.init()
    assert init_res["ok"] is True
    res_bridge = bridge.drop_label_samples("X", [0], category="letters")
    assert res_bridge["ok"] is True
    data = res_bridge["data"]
    assert data["removed_count"] == 1
    assert data["remaining_count"] == 0
    assert data["label_deleted"] is True

    # Nạp lại từ đĩa để xác minh đã save
    reloaded = Bank(p)
    assert "X" not in reloaded.letters
