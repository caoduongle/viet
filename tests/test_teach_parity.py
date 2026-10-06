"""Kiểm thử tính tương đương 100% giữa đường dạy mẫu trực tiếp (AppController / Tkinter)
và đường Web (BrowserBridge.teach_sample).

Tuân thủ task T052:
  Chuỗi điểm cố định ->
  (a) strokes_to_bank_units + teach_word / teach_letter trực tiếp,
  (b) bridge teach_sample
  -> JSON kho giống hệt, phủ từ/cụm từ, chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh,
  và hiệu chỉnh cỡ tay (calibrating=True).
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from chuviettay.browser.bridge import BrowserBridge
from chuviettay.controller.app_controller import AppController
from chuviettay.controller.teach_geometry import strokes_to_bank_units
from tests.conftest import tiny_bank_dict

# Chuỗi điểm vẽ pixel cố định giả lập nét chữ vẽ trên màn hình
SAMPLE_PX_STROKES: list[list[tuple[float, float]]] = [
    [(150.0, 170.0), (155.0, 140.0), (160.0, 110.0), (165.0, 140.0), (170.0, 170.0)],
    [(155.0, 150.0), (165.0, 150.0)],
]


def _read_bank_json(path: str) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _init_pair_banks(tmp_path: Path) -> tuple[AppController, str, BrowserBridge, str]:
    """Tạo 2 kho giống hệt nhau ban đầu cho Controller (A) và Bridge (B)."""
    base_dict = tiny_bank_dict()
    path_a = str(tmp_path / "bank_a.json.gz")
    path_b = str(tmp_path / "bank_b.json.gz")

    with gzip.open(path_a, "wt", encoding="utf-8") as f:
        json.dump(base_dict, f)
    with gzip.open(path_b, "wt", encoding="utf-8") as f:
        json.dump(base_dict, f)

    ctl_a = AppController(bank_path=path_a, timer_factory=lambda *a, **k: None)
    ctl_a.load_bank(path_a)

    bridge_b = BrowserBridge(bank_path=path_b)
    bridge_b.init()

    return ctl_a, path_a, bridge_b, path_b


def test_teach_word_and_phrase_parity(tmp_path):
    """Kiểm thử tính tương đương khi dạy từ đơn và cụm từ có dấu cách."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    for label in ["mùa", "cà phê"]:
        # (a) Trực tiếp qua Controller
        rel_a, w_a = strokes_to_bank_units(SAMPLE_PX_STROKES, ctl_a.session_scale)
        ctl_a.teach_word(label, rel_a, w_a, deferred_save=False)

        # (b) Qua Bridge
        res_b = bridge_b.teach_sample(label, pixel_strokes=SAMPLE_PX_STROKES, deferred_save=False)
        assert res_b["ok"] is True

        # So khớp JSON lưu trên đĩa
        assert _read_bank_json(path_a) == _read_bank_json(path_b)


def test_teach_letter_parity(tmp_path):
    """Kiểm thử tính tương đương khi dạy chữ cái đơn lẻ."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    for letter in ["b", "A", "đ"]:
        # (a) Trực tiếp
        rel_a, w_a = strokes_to_bank_units(SAMPLE_PX_STROKES, ctl_a.session_scale)
        ctl_a.teach_letter(letter, rel_a, w_a, deferred_save=False)

        # (b) Bridge
        res_b = bridge_b.teach_sample(letter, pixel_strokes=SAMPLE_PX_STROKES, deferred_save=False)
        assert res_b["ok"] is True

        assert _read_bank_json(path_a) == _read_bank_json(path_b)


def test_teach_digit_parity(tmp_path):
    """Kiểm thử tính tương đương khi dạy chữ số."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    for digit in ["5", "8"]:
        # (a) Trực tiếp
        rel_a, w_a = strokes_to_bank_units(SAMPLE_PX_STROKES, ctl_a.session_scale)
        ctl_a.teach_word(digit, rel_a, w_a, deferred_save=False)

        # (b) Bridge
        res_b = bridge_b.teach_sample(digit, pixel_strokes=SAMPLE_PX_STROKES, deferred_save=False)
        assert res_b["ok"] is True

        assert _read_bank_json(path_a) == _read_bank_json(path_b)


def test_teach_punct_parity(tmp_path):
    """Kiểm thử tính tương đương khi dạy dấu câu."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    for punct in ["?", "!"]:
        # (a) Trực tiếp
        rel_a, w_a = strokes_to_bank_units(SAMPLE_PX_STROKES, ctl_a.session_scale)
        ctl_a.teach_word(punct, rel_a, w_a, deferred_save=False)

        # (b) Bridge
        res_b = bridge_b.teach_sample(punct, pixel_strokes=SAMPLE_PX_STROKES, deferred_save=False)
        assert res_b["ok"] is True

        assert _read_bank_json(path_a) == _read_bank_json(path_b)


def test_teach_symbol_parity(tmp_path):
    """Kiểm thử tính tương đương khi dạy ký hiệu."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    for sym in ["+", "="]:
        # (a) Trực tiếp
        rel_a, w_a = strokes_to_bank_units(SAMPLE_PX_STROKES, ctl_a.session_scale)
        ctl_a.teach_word(sym, rel_a, w_a, deferred_save=False)

        # (b) Bridge
        res_b = bridge_b.teach_sample(sym, pixel_strokes=SAMPLE_PX_STROKES, deferred_save=False)
        assert res_b["ok"] is True

        assert _read_bank_json(path_a) == _read_bank_json(path_b)


def test_teach_tone_mark_parity(tmp_path):
    """Kiểm thử tính tương đương khi dạy dấu thanh rời."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    tone = "\u0301"  # Dấu sắc
    tone_strokes = [[(155.0, 130.0), (165.0, 120.0)]]

    # (a) Trực tiếp
    rel_a, w_a = strokes_to_bank_units(tone_strokes, ctl_a.session_scale)
    ctl_a.teach_letter(tone, rel_a, w_a, deferred_save=False)

    # (b) Bridge
    res_b = bridge_b.teach_sample(tone, pixel_strokes=tone_strokes, deferred_save=False)
    assert res_b["ok"] is True

    assert _read_bank_json(path_a) == _read_bank_json(path_b)


def test_teach_calibration_parity(tmp_path):
    """Kiểm thử tính tương đương khi hiệu chỉnh cỡ tay (calibrating=True)."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    # Từ mốc có sẵn trong tiny_bank là "ba"
    calib_word = "ba"

    # Nét vẽ với độ rộng khác để kích hoạt tính lại session_scale
    wide_px_strokes: list[list[tuple[float, float]]] = [
        [(100.0, 170.0), (110.0, 120.0), (120.0, 170.0)],
        [(130.0, 170.0), (140.0, 130.0), (150.0, 170.0)],
    ]

    # (a) Trực tiếp với recompute
    rel_a, w_a = strokes_to_bank_units(wide_px_strokes, ctl_a.session_scale)
    outcome_a = ctl_a.teach_word(
        calib_word,
        rel_a,
        w_a,
        calibrating=True,
        recompute=lambda s: strokes_to_bank_units(wide_px_strokes, s),
        deferred_save=False,
    )
    assert outcome_a.recalibrated is True

    # (b) Bridge với pixel_strokes và calibrating=True
    res_b = bridge_b.teach_sample(
        calib_word,
        pixel_strokes=wide_px_strokes,
        calibrating=True,
        deferred_save=False,
    )
    assert res_b["ok"] is True
    assert res_b["recalibrated"] is True
    assert round(ctl_a.session_scale, 4) == round(bridge_b.session_scale, 4)

    assert _read_bank_json(path_a) == _read_bank_json(path_b)


def test_teach_sequential_full_parity(tmp_path):
    """Kiểm thử chuỗi dạy liên hoàn đa thể loại và kiểm tra deferred_save + flush_save."""
    ctl_a, path_a, bridge_b, path_b = _init_pair_banks(tmp_path)

    tokens = [
        ("hoa", False),
        ("5", False),
        ("ba", True),      # Hiệu chỉnh cỡ tay
        ("c", False),      # Chữ cái sau khi đã đổi session_scale
        ("?", False),
        ("\u0301", False),  # Dấu sắc
    ]

    for token, calib in tokens:
        # Đường A
        rel_a, w_a = strokes_to_bank_units(SAMPLE_PX_STROKES, ctl_a.session_scale)
        if not calib and ctl_a.is_letter_token(token):
            ctl_a.teach_letter(token, rel_a, w_a, deferred_save=True)
        else:
            ctl_a.teach_word(
                token,
                rel_a,
                w_a,
                calibrating=calib,
                recompute=lambda s, t=SAMPLE_PX_STROKES: strokes_to_bank_units(t, s),
                deferred_save=True,
            )

        # Đường B
        bridge_b.teach_sample(
            token,
            pixel_strokes=SAMPLE_PX_STROKES,
            calibrating=calib,
            deferred_save=True,
        )

    # Đều ép lưu bằng flush_save
    ctl_a.flush_save()
    bridge_b.flush_save()

    assert round(ctl_a.session_scale, 4) == round(bridge_b.session_scale, 4)
    assert _read_bank_json(path_a) == _read_bank_json(path_b)
