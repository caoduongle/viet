"""Kiểm thử tính năng kế hoạch dạy chữ và giải phóng hàng đợi SEED (WP3 / User Story 4).

Đảm bảo:
1. 38 mục ký tự cốt lõi (33 chữ cái thường + 5 dấu thanh rời) mở khoá 100% (700/700) từ trong SEED.
2. Với chỉ 33 chữ thường không có dấu thanh, chỉ viết được đúng 185/700 từ SEED.
3. Khi người dùng dạy một từ nguyên khối (ví dụ 'tôi') qua teach_char(), từ đó được lưu vào bank.words
   và Bank.can('tôi') công nhận, giải phóng 'tôi' khỏi hàng đợi missing_minimal_essentials().
4. Dạy dấu thanh rời (ví dụ 'dấu sắc') qua teach_char() được Bank.can('dấu sắc') công nhận.
"""
from __future__ import annotations

import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.model.bank import Bank
from chuviettay.model.char_catalog import VIETNAMESE_LOWERCASE, TONE_MARKS
from chuviettay.model.seed_words import (
    CORE_ESSENTIALS_38,
    SEED,
    get_core_essentials_38,
    get_minimal_essentials,
)
from chuviettay.model.text_utils import HW3_TONE_NAMES


def test_core_essentials_38_constants():
    """Kiểm tra cấu trúc và tính đầy đủ của 38 mục ký tự cốt lõi."""
    essentials = get_core_essentials_38()
    assert len(essentials) == 38
    assert len(CORE_ESSENTIALS_38) == 38

    # Chứa đúng 33 chữ cái thường
    for ch in VIETNAMESE_LOWERCASE:
        assert ch in essentials

    # Chứa đúng 5 dấu thanh rời
    for tm in TONE_MARKS:
        assert tm in essentials


def test_core_essentials_38_covers_all_700_seed_words(tmp_path):
    """Kiểm chứng 38 mục cốt lõi mở khóa 100% (700/700) từ trong tập SEED."""
    bank_path = str(tmp_path / "core_bank.json.gz")
    bank = Bank.create_empty(bank_path)

    dummy_stroke = [[0.0, 0.0, 5.0, 5.0]]

    # Thêm 33 chữ cái thường
    for ch in VIETNAMESE_LOWERCASE:
        bank.add_letter_sample(ch, dummy_stroke, 6.0)

    # 1. Khi chưa có dấu thanh: chỉ viết được đúng 185 / 700 từ SEED
    count_without_marks = sum(1 for w in SEED if bank.can(w))
    assert count_without_marks == 185, f"Kỳ vọng 185 từ khi chưa có dấu thanh, nhưng được {count_without_marks}"

    # 2. Thêm 5 dấu thanh rời
    for tm in TONE_MARKS:
        t_code = HW3_TONE_NAMES[tm]
        bank.add_tone_sample(t_code, dummy_stroke)

    # Khi có đủ 38 mục: viết được 100% (700/700) từ SEED
    count_with_marks = sum(1 for w in SEED if bank.can(w))
    assert count_with_marks == len(SEED) == 700, f"Kỳ vọng 700/700 từ sau khi có 38 mục, nhưng được {count_with_marks}"


def test_teach_word_unblocks_minimal_essentials_queue(tmp_path):
    """Kiểm chứng gỡ tắc nghẽn hàng đợi dạy chữ:
    Khi dạy từ 'tôi' qua teach_char(), từ đó được ghi vào bank.words và
    Bank.can('tôi') công nhận, không còn bị kẹt trong missing_minimal_essentials().
    """
    bank_path = str(tmp_path / "queue_bank.json.gz")
    ctl = AppController()
    ctl.load_bank(bank_path, create_if_missing=True)

    missing_initial = ctl.missing_minimal_essentials()
    assert "tôi" in missing_initial, "'tôi' phải nằm trong hàng đợi ban đầu"

    # Dạy từ 'tôi' trực tiếp dưới dạng từ nguyên khối
    dummy_stroke = [[0.0, 0.0, 10.0, 10.0]]
    outcome = ctl.teach_char("tôi", dummy_stroke, 12.0)
    assert outcome.label == "tôi"
    assert "tôi" in ctl.bank.words, "'tôi' phải được lưu vào bank.words"

    # Bank.can('tôi') phải trả về True
    assert ctl.bank.can("tôi") is True

    # 'tôi' phải biến mất khỏi hàng đợi cần học
    missing_after = ctl.missing_minimal_essentials()
    assert "tôi" not in missing_after, "'tôi' đã được học nên không được còn trong hàng đợi"
    assert len(missing_after) == len(missing_initial) - 1


def test_teach_tone_mark_recognized_by_can(tmp_path):
    """Kiểm chứng Bank.can() nhận biết tên dấu thanh tiếng Việt (ví dụ 'dấu sắc')."""
    bank_path = str(tmp_path / "tone_bank.json.gz")
    ctl = AppController()
    ctl.load_bank(bank_path, create_if_missing=True)

    dummy_stroke = [[0.0, 0.0, 2.0, 2.0]]
    assert ctl.bank.can("dấu sắc") is False

    ctl.teach_char("dấu sắc", dummy_stroke, 3.0)
    assert ctl.bank.can("dấu sắc") is True
