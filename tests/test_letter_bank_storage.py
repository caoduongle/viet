"""Unit tests for Bank storage schema, migrations, and concurrency safety for letters."""
import copy
import os
import pytest
import time

from chuviettay.config import TONES
from chuviettay.model.bank import Bank, merge_bank_dicts


def test_bank_add_and_drop_letter(tmp_path):
    bank_path = str(tmp_path / "test_letter_bank.json.gz")
    bank = Bank.create_empty(bank_path)

    assert "letters" in bank.d
    assert hasattr(bank, "letters")
    assert len(bank.letters) == 0

    # Add sample for letter 'a'
    strokes = [[0.0, 0.0, 5.0, 5.0], [5.0, 5.0, 10.0, 0.0]]
    inst = bank.add_letter_sample("a", strokes, width=10.0)
    assert inst["w"] == 10.0
    assert inst["s"] == strokes
    assert "a" in bank.letters
    assert len(bank.letters["a"]) == 1
    assert bank.is_dirty

    # Adding duplicate with dedup=True returns existing sample
    inst2 = bank.add_letter_sample("a", strokes, width=10.0, dedup=True)
    assert len(bank.letters["a"]) == 1
    assert inst2 == inst

    # Save and reload
    bank.save()
    reloaded = Bank(bank_path)
    assert "a" in reloaded.letters
    assert len(reloaded.letters["a"]) == 1

    # Drop letter 'a'
    gen_before = reloaded._generation
    removed = reloaded.drop_letter("a")
    assert removed == 1
    assert "a" not in reloaded.letters
    assert reloaded._generation == gen_before + 1
    assert "a" in reloaded._tombstones
    reloaded.save()

    reloaded2 = Bank(bank_path)
    assert "a" not in reloaded2.letters


def test_merge_bank_dicts_letters_concurrency():
    base = Bank.empty_dict()
    disk = Bank.empty_dict()

    # Disk has letter 'b'
    sample_b = {"w": 8.0, "s": [[0.0, 0.0, 0.0, 12.0]]}
    disk["letters"]["b"] = [sample_b]

    # Base has letter 'a'
    sample_a = {"w": 7.0, "s": [[0.0, 0.0, 5.0, 5.0]]}
    base["letters"]["a"] = [sample_a]

    merged = merge_bank_dicts(base, disk)
    assert "a" in merged["letters"]
    assert "b" in merged["letters"]
    assert len(merged["letters"]["a"]) == 1
    assert len(merged["letters"]["b"]) == 1


def test_merge_bank_dicts_letter_tombstone():
    base = Bank.empty_dict()
    disk = Bank.empty_dict()

    # Disk has letter 'c'
    disk["letters"]["c"] = [{"w": 6.0, "s": [[0.0, 0.0, 4.0, 4.0]]}]

    # Base has tombstone for 'c'
    base["tombstones"]["c"] = {"deleted_at": time.time() + 10, "generation": 1}

    merged = merge_bank_dicts(base, disk)
    assert "c" not in merged["letters"]


def test_standalone_tone_mark_persistence(tmp_path):
    bank_path = str(tmp_path / "test_standalone_tone.json.gz")
    bank = Bank.create_empty(bank_path)

    # Add standalone tone mark '\u0300' (huyền)
    stroke = [0.0, 0.0, 3.0, -2.0]
    bank.add_tone_sample("\u0300", stroke, dx=0.0, dy=-5.0)

    assert len(bank.marks["\u0300"]) >= 1
    bank.save()

    # Reload bank and rebuild
    reloaded = Bank(bank_path)
    assert len(reloaded.marks["\u0300"]) >= 1


def test_controller_teach_and_drop_letter(tmp_path):
    from chuviettay.controller.app_controller import AppController

    bank_path = str(tmp_path / "test_ctl_letter.json.gz")
    Bank.create_empty(bank_path)

    ctl = AppController(bank_path)
    ctl.load_bank()

    outcome = ctl.teach_letter("m", [[0.0, 0.0, 5.0, 0.0]], width=8.0)
    assert outcome.label == "m"
    assert "m" in ctl.bank.letters

    res = ctl.drop_letter("m")
    assert res.removed.get("m") == 1
    assert "m" not in ctl.bank.letters
