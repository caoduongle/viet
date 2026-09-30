"""Kiểm thử tính năng học và viết chữ số, số thập phân và dấu câu (User Story 1 - L1)."""
import random
import pytest
from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer


def test_learn_digits_and_punct_routes_properly(tmp_path):
    """Mẫu chữ số được định tuyến vào bank.digits và dấu câu vào bank.punct."""
    bank_path = str(tmp_path / "digits_bank.json.gz")
    bank = Bank.create_empty(bank_path)

    stroke = [10.0, 10.0, 20.0, 20.0]
    for d in "0123456789":
        bank.add_sample(d, [stroke], 15.0)

    for p in (",", ".", "(", ")", "-"):
        bank.add_sample(p, [stroke], 10.0)

    for d in "0123456789":
        assert d in bank.digits, f"Chữ số {d} phải có trong bank.digits"
        assert d not in bank.words, f"Chữ số {d} không được nằm trong bank.words"

    for p in (",", ".", "(", ")", "-"):
        assert p in bank.punct, f"Dấu câu {p} phải có trong bank.punct"
        assert p not in bank.words, f"Dấu câu {p} không được nằm trong bank.words"


def test_writer_number_with_digits_and_decimal(tmp_path):
    """Writer.number ghép đúng chữ số từ bank.digits và dấu câu từ bank.punct."""
    bank_path = str(tmp_path / "digits_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    stroke = [10.0, 10.0, 20.0, 20.0]
    for d in "02345":
        bank.add_sample(d, [stroke], 15.0)
    bank.add_sample(",", [stroke], 10.0)

    rnd = random.Random(42)
    writer = Writer(bank, rnd)

    # 1. Số nguyên nhiều chữ số: 2024
    st, w, miss = writer.number("2024")
    assert not miss, f"Viết 2024 không được thiếu mẫu, nhưng báo: {miss}"
    assert st, "Phải sinh nét vẽ cho 2024"
    assert w > 0

    # 2. Số thập phân: 3,5
    st_dec, w_dec, miss_dec = writer.number("3,5")
    assert not miss_dec, f"Viết 3,5 không được thiếu mẫu, nhưng báo: {miss_dec}"
    assert st_dec, "Phải sinh nét vẽ cho 3,5"


def test_writer_number_backward_compatibility_fallback_to_words(tmp_path):
    """Tương thích ngược: Nếu kho cũ lưu số trong bank.words, Writer.number vẫn tự lùi về bank.words."""
    bank_path = str(tmp_path / "legacy_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    stroke = [10.0, 10.0, 20.0, 20.0]

    # Giả lập kho cũ lưu vào words
    bank.words["9"] = [{"w": 15.0, "s": [stroke], "T": "", "vi": -1, "ti": -1}]

    rnd = random.Random(42)
    writer = Writer(bank, rnd)

    st, w, miss = writer.number("9")
    assert not miss, "Writer phải tự động fallback sang bank.words khi bank.digits chưa có chữ số"
    assert st


def test_minimal_essentials_queue(tmp_path):
    """Kiểm tra danh sách bộ tối thiểu (0-9, dấu câu, top 60 từ) và Controller.missing_minimal_essentials."""
    from chuviettay.controller.app_controller import AppController
    from chuviettay.model.seed_words import get_minimal_essentials

    essentials = get_minimal_essentials(60)
    assert len(essentials) >= 80  # 10 digits + 11 punct + 60 words
    assert "0" in essentials and "9" in essentials
    assert "," in essentials and "." in essentials
    assert "tôi" in essentials

    bank_path = str(tmp_path / "empty.json.gz")
    ctl = AppController()
    ctl.load_bank(bank_path, create_if_missing=True)

    missing = ctl.missing_minimal_essentials()
    assert len(missing) == len(essentials)

    # Thêm số 0 và dấu phẩy, kiểm tra chúng không còn trong missing_minimal_essentials
    ctl.bank.add_sample("0", [[0.0, 0.0, 10.0, 10.0]], 10.0)
    ctl.bank.add_sample(",", [[0.0, 0.0, 5.0, 5.0]], 5.0)
    missing_after = ctl.missing_minimal_essentials()
    assert "0" not in missing_after
    assert "," not in missing_after
    assert len(missing_after) == len(essentials) - 2


def test_writer_standalone_punctuation_from_punct(tmp_path):
    """Writer.token ghép đúng dấu câu đứng độc lập từ bank.punct."""
    bank_path = str(tmp_path / "standalone_punct.json.gz")
    bank = Bank.create_empty(bank_path)
    stroke = [10.0, 10.0, 20.0, 20.0]
    bank.add_sample(",", [stroke], 8.0)
    bank.add_sample(".", [stroke], 8.0)

    rnd = random.Random(42)
    writer = Writer(bank, rnd)

    st_comma, w_comma, miss_comma = writer.token(",")
    assert not miss_comma, f"Dấu phẩy độc lập không được báo thiếu: {miss_comma}"
    assert st_comma, "Dấu phẩy phải sinh nét"
    assert w_comma > 0

    st_dot, w_dot, miss_dot = writer.token(".")
    assert not miss_dot, f"Dấu chấm độc lập không được báo thiếu: {miss_dot}"
    assert st_dot, "Dấu chấm phải sinh nét"

