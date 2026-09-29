"""Kiểm thử kiểm định cấu trúc sâu (deep schema invariants):
- Dấu thanh (ti, vi, T)
- Cấu hình bút vẽ (pen.tool, pen.color, pen.width)
- Độ rộng mẫu câu/dấu chấm (punct w optional)
- Deletion tombstones
- Tương thích ngược với kho mẫu thực tế (chu_cua_ban.json.gz)
"""
import copy
import os

import pytest

from chuviettay.model.bank_schema import (
    BankValidationError,
    load_and_validate,
    validate_bank_dict,
    validate_sample,
)


@pytest.fixture
def minimal_valid_bank_dict():
    return {
        "schema_version": 2,
        "xh": 7.0,
        "line": 24.0,
        "width": 500.0,
        "x0": 78.0,
        "wgaps": [11.0],
        "dgaps": [3.5],
        "ratio": 6.6,
        "v": 1.0,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.2", "capStyle": "round"},
        "words": {
            "chào": [
                {
                    "w": 10.0,
                    "s": [[0.0, 0.0, 5.0, 0.0], [4.0, -10.0, 6.0, -8.0]],
                    "T": "\u0300",
                    "vi": 1,
                    "ti": 1,
                }
            ],
            "ba": [
                {
                    "w": 8.0,
                    "s": [[0.0, 0.0, 4.0, 0.0]],
                    "T": "",
                    "vi": -1,
                    "ti": -1,
                }
            ],
        },
        "digits": {
            "1": [{"w": 5.0, "s": [[0.0, 0.0, 0.0, 10.0]]}]
        },
        "punct": {
            ".": [{"s": [[0.0, 0.0, 1.0, 0.0]]}],  # punct không bắt buộc có 'w'
            ",": [{"w": 3.0, "s": [[0.0, 0.0, 1.0, -2.0]]}],  # punct có 'w' vẫn hợp lệ
        },
        "tombstones": {
            "cũ": 1727500000.0,
        },
    }


def test_minimal_valid_bank_passes(minimal_valid_bank_dict):
    version = validate_bank_dict(minimal_valid_bank_dict)
    assert version == 2


# ------------------------------------------------------------------ punct w optional
def test_punct_sample_without_w_is_valid():
    sample = {"s": [[1.0, 2.0, 3.0, 4.0]]}
    validate_sample(sample, is_punct=True)


def test_punct_sample_with_positive_w_is_valid():
    sample = {"w": 4.5, "s": [[1.0, 2.0, 3.0, 4.0]]}
    validate_sample(sample, is_punct=True)


def test_punct_sample_with_invalid_w_fails():
    sample = {"w": -2.0, "s": [[1.0, 2.0, 3.0, 4.0]]}
    with pytest.raises(BankValidationError, match="độ rộng 'w'"):
        validate_sample(sample, is_punct=True)


def test_word_sample_without_w_fails():
    sample = {"s": [[1.0, 2.0, 3.0, 4.0]]}
    with pytest.raises(BankValidationError, match="thiếu độ rộng 'w'"):
        validate_sample(sample, is_punct=False)


# ------------------------------------------------------------------ tone invariants
def test_tone_ti_out_of_bounds_fails():
    # ti >= len(s)
    sample = {
        "w": 10.0,
        "s": [[0.0, 0.0, 5.0, 0.0]],
        "T": "\u0300",
        "vi": 1,
        "ti": 1,
    }
    with pytest.raises(BankValidationError, match="ti=1 ngoài phạm vi"):
        validate_sample(sample)

    # ti < -1
    sample["ti"] = -2
    with pytest.raises(BankValidationError, match="ti=-2 ngoài phạm vi"):
        validate_sample(sample)


def test_tone_ti_valid_but_missing_or_invalid_T_fails():
    sample = {
        "w": 10.0,
        "s": [[0.0, 0.0, 5.0, 0.0], [1.0, 1.0, 2.0, 2.0]],
        "T": "",
        "vi": 1,
        "ti": 1,
    }
    with pytest.raises(BankValidationError, match="không phải dấu thanh hợp lệ"):
        validate_sample(sample)

    sample["T"] = "invalid_tone"
    with pytest.raises(BankValidationError, match="dấu thanh không hợp lệ"):
        validate_sample(sample)


def test_tone_ti_valid_but_negative_vi_fails():
    sample = {
        "w": 10.0,
        "s": [[0.0, 0.0, 5.0, 0.0], [1.0, 1.0, 2.0, 2.0]],
        "T": "\u0300",
        "vi": -1,
        "ti": 1,
    }
    with pytest.raises(BankValidationError, match="vi=-1 < 0"):
        validate_sample(sample)


def test_vi_exceeds_label_length_fails():
    sample = {
        "w": 10.0,
        "s": [[0.0, 0.0, 5.0, 0.0], [1.0, 1.0, 2.0, 2.0]],
        "T": "\u0300",
        "vi": 5,
        "ti": 1,
    }
    with pytest.raises(BankValidationError, match="vượt quá độ dài nhãn 'ba'"):
        validate_sample(sample, label="ba")


# ------------------------------------------------------------------ pen configuration
def test_pen_tool_must_be_non_empty(minimal_valid_bank_dict):
    d = copy.deepcopy(minimal_valid_bank_dict)
    d["pen"]["tool"] = "   "
    with pytest.raises(BankValidationError, match="pen.tool"):
        validate_bank_dict(d)


@pytest.mark.parametrize("invalid_color", ["red", "#123", "#12345", "#GGGGGG", "#000000fff", "123456"])
def test_pen_color_invalid_format_fails(minimal_valid_bank_dict, invalid_color):
    d = copy.deepcopy(minimal_valid_bank_dict)
    d["pen"]["color"] = invalid_color
    with pytest.raises(BankValidationError, match="pen.color"):
        validate_bank_dict(d)


@pytest.mark.parametrize("valid_color", ["#000000", "#ffffff", "#000000ff", "#12ABcdEF", "#AABBCC"])
def test_pen_color_valid_formats(minimal_valid_bank_dict, valid_color):
    d = copy.deepcopy(minimal_valid_bank_dict)
    d["pen"]["color"] = valid_color
    assert validate_bank_dict(d) == 2


@pytest.mark.parametrize("invalid_width", [0, -1.5, "0", "-2", "abc", None, True])
def test_pen_width_invalid_fails(minimal_valid_bank_dict, invalid_width):
    d = copy.deepcopy(minimal_valid_bank_dict)
    d["pen"]["width"] = invalid_width
    with pytest.raises(BankValidationError, match="pen.width"):
        validate_bank_dict(d)


@pytest.mark.parametrize("valid_width", [1.2, 2, "1.41", "2.0"])
def test_pen_width_valid(minimal_valid_bank_dict, valid_width):
    d = copy.deepcopy(minimal_valid_bank_dict)
    d["pen"]["width"] = valid_width
    assert validate_bank_dict(d) == 2


# ------------------------------------------------------------------ tombstones validation
def test_tombstones_invalid_type_fails(minimal_valid_bank_dict):
    d = copy.deepcopy(minimal_valid_bank_dict)
    d["tombstones"] = ["xin", "chao"]
    with pytest.raises(BankValidationError, match="tombstones.*phải là dict"):
        validate_bank_dict(d)


def test_tombstones_invalid_values_fails(minimal_valid_bank_dict):
    d = copy.deepcopy(minimal_valid_bank_dict)
    d["tombstones"] = {"xin": "not-a-number"}
    with pytest.raises(BankValidationError, match="timestamp"):
        validate_bank_dict(d)


# ------------------------------------------------------------------ real-world legacy bank compatibility
def test_real_world_chu_cua_ban_loads_cleanly():
    if os.path.exists("chu_cua_ban.json.gz"):
        d = load_and_validate("chu_cua_ban.json.gz")
        assert len(d["words"]) > 0
        assert len(d["punct"]) > 0
