"""Kiểm thử công cụ di trú kho ký tự (migrate_letter_bank)."""
import copy
import gzip
import json
import pytest

from chuviettay.model.bank import Bank
from chuviettay.model.bank_schema import validate_bank_dict
from scripts.migrate_letter_bank import extract_tone_from_sample, migrate_bank_dict_letters


def _sample_v3_with_letters():
    return {
        "schema_version": 3,
        "words": {
            "a": [{"s": [[0.0, -3.85, 2.0, -3.85, 4.0, 0.0, 0.0, 0.0]], "w": 4.0}],
            "b": [{"s": [[0.0, -7.0, 0.0, 0.0, 3.5, 0.0, 3.5, -3.85]], "w": 3.5}],
            "á": [{
                "s": [
                    [0.0, -3.85, 2.0, -3.85, 4.0, 0.0, 0.0, 0.0],
                    [3.5, -6.0, 2.5, -4.5],
                ],
                "w": 4.0,
            }],
            "ạ": [{
                "s": [
                    [0.0, -3.85, 2.0, -3.85, 4.0, 0.0, 0.0, 0.0],
                    [2.0, 0.5, 2.5, 1.0],
                ],
                "w": 4.0,
            }],
            "xin": [{"s": [[0.0, -4.0, 10.0, -4.0]], "w": 10.0}],
        },
        "digits": {"1": [{"s": [[0.0, 0.0, 1.0, 5.0]], "w": 8.0}]},
        "punct": {",": [{"s": [[0.0, 0.0, 1.0, 1.0]], "w": 4.0}]},
        "symbols": {"+": [{"s": [[0.0, 0.0, 2.0, 0.0]], "w": 6.0}]},
        "letters": {},
        "marks": {},
        "xh": 3.85,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41"},
        "line": 24.0,
        "width": 500.0,
        "x0": 78.0,
        "wgaps": [11.0],
        "dgaps": [3.5],
        "ratio": 6.6,
        "v": 1,
    }


def test_extract_tone_from_sample():
    # Kiểm tra tách dấu sắc cho chữ 'á'
    strokes_sac = [
        [0.0, -3.85, 2.0, -3.85, 4.0, 0.0, 0.0, 0.0],
        [3.5, -6.0, 2.5, -4.5],
    ]
    res_sac = extract_tone_from_sample("á", strokes_sac, raw_w=4.0)
    assert res_sac is not None
    ti_sac, mark_sac, body_sac = res_sac
    assert ti_sac == 1
    assert mark_sac["T"] == "\u0301"
    assert len(body_sac) == 1

    # Kiểm tra tách dấu nặng cho chữ 'ạ'
    strokes_nang = [
        [0.0, -3.85, 2.0, -3.85, 4.0, 0.0, 0.0, 0.0],
        [2.0, 0.5, 2.5, 1.0],
    ]
    res_nang = extract_tone_from_sample("ạ", strokes_nang, raw_w=4.0)
    assert res_nang is not None
    ti_nang, mark_nang, body_nang = res_nang
    assert ti_nang == 1
    assert mark_nang["T"] == "\u0323"
    assert len(body_nang) == 1


def test_migrate_bank_dict_preserves_and_normalizes(tmp_path):
    orig = _sample_v3_with_letters()
    orig_copy = copy.deepcopy(orig)

    migrated = migrate_bank_dict_letters(orig, target_xh=7.94)

    # 1. Không làm thay đổi từ điển gốc
    assert orig == orig_copy

    # 2. Chữ cái đơn chuyển từ words sang letters
    assert "a" in migrated["letters"]
    assert "b" in migrated["letters"]
    assert "á" in migrated["letters"]
    assert "ạ" in migrated["letters"]

    # Từ nhiều hơn 1 ký tự ("xin") vẫn giữ ở words
    assert "xin" in migrated["words"]
    # Các ký tự đơn đã chuyển khỏi words
    assert "a" not in migrated["words"]

    # 3. Ký tự số, dấu câu, ký hiệu được giữ nguyên
    assert "1" in migrated["digits"]
    assert "," in migrated["punct"]
    assert "+" in migrated["symbols"]

    # 4. Có mẫu dấu thanh tách rời trong marks
    sac_tone = "\u0301"
    nang_tone = "\u0323"
    assert sac_tone in migrated["marks"]
    assert nang_tone in migrated["marks"]
    assert len(migrated["marks"][sac_tone]) >= 1
    assert len(migrated["marks"][nang_tone]) >= 1

    # 5. Các mẫu trong letters có đầy đủ trường hình học và được scale
    sample_a = migrated["letters"]["a"][0]
    assert "lsb" in sample_a
    assert "rsb" in sample_a
    assert "adv" in sample_a
    assert "cat" in sample_a
    assert sample_a["cat"] == "x_height"

    # Kiểm tra x-height mới của kho được cập nhật
    assert pytest.approx(migrated["xh"], abs=0.05) == 7.94

    # 6. Kiểm định schema hợp lệ
    val_ver = validate_bank_dict(migrated, allow_legacy=True)
    assert val_ver in (3, 4)

    # 7. Mở lại được bằng Bank
    bank_path = tmp_path / "migrated.json.gz"
    with gzip.open(bank_path, "wt", encoding="utf-8") as gf:
        json.dump(migrated, gf)

    b = Bank(str(bank_path))
    assert "a" in b.letters
    assert "b" in b.letters
    assert b.marks[sac_tone]
    assert b.marks[nang_tone]
