"""Unit tests for Vietnamese letter decomposition, greedy set-cover ranking, and word assembly."""
import pytest
import unicodedata

from chuviettay.config import TONES
from chuviettay.model.text_utils import missing_letters_ranked, split_letters


def test_split_letters_unaccented_simple():
    letters, tone, vi = split_letters("ba")
    assert letters == ["b", "a"]
    assert tone == ""
    assert vi == -1


def test_split_letters_with_tone_huyen():
    letters, tone, vi = split_letters("bà")
    assert letters == ["b", "a"]
    assert tone == "\u0300"
    assert vi == 1


def test_split_letters_vietnamese_diacritics_horns_and_hats():
    # đường -> letters: đ, ư, ơ, n, g (NFC characters, NOT stripped of horns)
    letters, tone, vi = split_letters("đường")
    assert letters == ["đ", "ư", "ơ", "n", "g"]
    assert tone == "\u0300"
    assert vi == 2  # 'ơ' carries the tone


def test_split_letters_chao_and_hoc():
    letters, tone, vi = split_letters("chào")
    assert letters == ["c", "h", "a", "o"]
    assert tone == "\u0300"
    assert vi == 2

    letters, tone, vi = split_letters("học")
    assert letters == ["h", "o", "c"]
    assert tone == "\u0323"  # nặng
    assert vi == 1


def test_split_letters_preserves_case():
    letters, tone, vi = split_letters("Bà")
    assert letters == ["B", "a"]
    assert tone == "\u0300"
    assert vi == 1


def test_missing_letters_ranked_greedy_coverage():
    # If missing words are "ba", "bà", "bá", "ca", "cá"
    # letters needed:
    # "ba": b, a
    # "bà": b, a, tone \u0300
    # "bá": b, a, tone \u0301
    # "ca": c, a
    # "cá": c, a, tone \u0301
    # Letter 'a' is in all 5 words!
    # Letter 'b' is in 3 words.
    # Letter 'c' is in 2 words.
    bank_letters = {}
    bank_marks = {}
    missing_words = ["ba", "bà", "bá", "ca", "cá"]
    ranked = missing_letters_ranked(missing_words, bank_letters, bank_marks)

    # First ranked should be 'a' with unlock count 5
    assert len(ranked) >= 3
    assert ranked[0][0] == "a"
    assert ranked[0][1] == 5
    assert set(ranked[0][2]) == set(missing_words)


def test_missing_letters_ranked_when_some_already_learned():
    # Bank already has 'a' and 'b' and tone \u0300
    bank_letters = {"a": [{"s": [], "w": 10.0}], "b": [{"s": [], "w": 10.0}]}
    bank_marks = {"\u0300": [{"s": [], "dx": 0, "dy": 0}]}
    missing_words = ["ba", "bà", "bá", "ca"]
    # "ba": has b, a -> no missing letters!
    # "bà": has b, a, \u0300 -> no missing letters!
    # "bá": needs tone \u0301
    # "ca": needs letter 'c'
    ranked = missing_letters_ranked(missing_words, bank_letters, bank_marks)
    missing_chars = [item[0] for item in ranked]
    assert "a" not in missing_chars
    assert "b" not in missing_chars
    assert "\u0300" not in missing_chars
    assert "c" in missing_chars
    assert "\u0301" in missing_chars


def test_controller_missing_letters_for_words(tiny_bank_path):
    from chuviettay.controller.app_controller import AppController

    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    # tiny_bank has 'xin', 'ba', 'bà', 'chào'
    # Request missing letters for ["phở", "gà"]
    ranked = ctl.missing_letters_for_words(["phở", "gà"])
    missing_chars = [item[0] for item in ranked]
    assert "p" in missing_chars
    assert "h" in missing_chars
    assert "ở" in missing_chars or "ơ" in missing_chars
    assert "g" in missing_chars


def test_writer_assemble_word_unaccented(tmp_path):
    import random
    from chuviettay.model.bank import Bank
    from chuviettay.model.writer import Writer

    bank = Bank.create_empty(str(tmp_path / "synth_bank.json.gz"))
    # Teach letters 'c', 'a'
    bank.add_letter_sample("c", [[0.0, 0.0, 5.0, 0.0]], width=6.0)
    bank.add_letter_sample("a", [[0.0, 0.0, 4.0, 4.0]], width=5.0)

    wr = Writer(bank, random.Random(42), assemble_letters=True)
    res = wr.word("ca")
    assert res is not None
    strokes, w = res
    assert len(strokes) == 2
    assert w > 0
    assert "ca" in wr.assembled


def test_writer_assemble_word_with_tone_and_i_dot_suppression(tmp_path):
    import random
    from chuviettay.model.bank import Bank
    from chuviettay.model.writer import Writer

    bank_path = str(tmp_path / "tone_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.xh = 10.0

    # Letter 'g'
    bank.add_letter_sample("g", [[0.0, 0.0, 5.0, -5.0]], width=6.0)
    # Letter 'i' with body and dot
    # body stroke: [0, 0, 0, -10]
    # dot stroke: [0, -12, 1, -12] (bbox y max = -12 < -0.85 * xh)
    bank.add_letter_sample("i", [[0.0, 0.0, 0.0, -10.0], [0.0, -12.0, 1.0, -12.0]], width=4.0)

    # Tone '\u0300' (huyền)
    bank.add_tone_sample("\u0300", [0.0, 0.0, 3.0, -2.0], dx=0.0, dy=-3.0)

    # assemble_letters=False -> word("gì") returns None
    wr_off = Writer(bank, random.Random(42), assemble_letters=False)
    assert wr_off.word("gì") is None

    # assemble_letters=True -> word("gì") synthesizes and suppresses dot
    wr_on = Writer(bank, random.Random(42), assemble_letters=True)
    res = wr_on.word("gì")
    assert res is not None
    strokes, w = res
    # 'g' (1 stroke) + 'i' without dot (1 stroke) + tone (1 stroke) = 3 strokes
    assert len(strokes) == 3
    assert "gì" in wr_on.assembled


def test_kerning_pairs_different_contours(tmp_path):
    import random
    from chuviettay.model.bank import Bank
    from chuviettay.model.writer import Writer

    bank = Bank.create_empty(str(tmp_path / "contour_bank.json.gz"))
    bank.xh = 7.94
    bank.pen = {"name": "pen", "width": "1.41"}

    # Thêm 'o' (CURVED-CURVED), 'l' (STRAIGHT-STRAIGHT), 'v' (OPEN-OPEN)
    bank.add_letter_sample("o", [[0.0, -7.94, 4.0, -7.94, 4.0, 0.0, 0.0, 0.0]], width=4.0)
    bank.add_letter_sample("l", [[0.0, -15.0, 0.0, 0.0]], width=1.5)
    bank.add_letter_sample("v", [[0.0, -7.94, 2.0, 0.0, 4.0, -7.94]], width=4.0)

    wr = Writer(bank, random.Random(42), jitter=0.0, assemble_letters=True)

    res_oo = wr.assemble_word("oo")
    res_ll = wr.assemble_word("ll")
    res_vo = wr.assemble_word("vo")

    assert res_oo is not None and res_ll is not None and res_vo is not None
    # Đo khoảng cách advance giữa ký tự thứ 1 và ký tự thứ 2
    # Với 'oo', khoảng hở biên tiếp xúc cong-cong nhỏ hơn thẳng-thẳng 'll'
    # và đều lớn hơn 0
    assert res_oo[1] > 0
    assert res_ll[1] > 0
    assert res_vo[1] > 0


def test_dual_path_with_ascender_avoidance(tmp_path):
    import random
    from chuviettay.model.bank import Bank
    from chuviettay.model.writer import Writer

    bank = Bank.create_empty(str(tmp_path / "ascender_bank.json.gz"))
    bank.xh = 7.94
    bank.pen = {"name": "pen", "width": "1.41"}

    # 'h' (ascender vươn cao tới y = -16.0)
    bank.add_letter_sample("h", [[0.0, -16.0, 0.0, 0.0, 4.0, -7.94, 4.0, 0.0]], width=4.5)
    # 'e'
    bank.add_letter_sample("e", [[0.0, -4.0, 4.0, -4.0, 4.0, -7.94, 0.0, -7.94, 0.0, 0.0]], width=4.5)
    # Dấu sắc '\u0301'
    bank.add_tone_sample("\u0301", [0.0, 1.5, 2.0, 0.0], dx=-1.0, dy=-2.0)

    wr = Writer(bank, random.Random(42), jitter=0.0, assemble_letters=True)
    res = wr.assemble_word("hé")
    assert res is not None
    strokes, w = res
    assert len(strokes) >= 3


def test_assemble_word_path1_nang_baseline_alignment(tmp_path):
    import random
    from chuviettay.model.bank import Bank
    from chuviettay.model.writer import Writer

    bank = Bank.create_empty(str(tmp_path / "nang_bank.json.gz"))
    bank.xh = 7.94
    bank.pen = {"name": "pen", "width": "1.41"}

    # 't': baseline at 0.0
    bank.add_letter_sample("t", [[0.0, -8.0, 0.0, 0.0, 2.0, 0.0]], width=3.0)
    # 'p': baseline at 0.0
    bank.add_letter_sample("p", [[0.0, -8.0, 0.0, 4.0]], width=3.0)
    # 'ậ': precomposed sample where body is at y in [-14, -6] and dot at y in [-1, 0] (unaligned)
    body_st = [0.0, -14.0, 4.0, -6.0]
    nang_st = [2.0, -1.0, 2.0, 0.0]
    bank.add_letter_sample("ậ", [body_st, nang_st], width=4.0)

    wr = Writer(bank, random.Random(42), jitter=0.0, assemble_letters=True)
    res = wr.assemble_word("tập")
    assert res is not None
    strokes, total_w = res

    # The body of 'ậ' (stroke 1) must be pulled down to baseline near y = 0.0
    placed_body_ys = strokes[1][1::2]
    assert pytest.approx(max(placed_body_ys), abs=0.1) == 0.0
    # The dot of 'ậ' (stroke 2) must be below baseline (y > 0)
    placed_dot_ys = strokes[2][1::2]
    assert min(placed_dot_ys) > 0.0



