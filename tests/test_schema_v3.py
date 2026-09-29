"""Kiểm thử tính đúng đắn của Bank Schema v3 và di trú tự động từ v2/v1."""
import gzip
import json
import pytest

from chuviettay.model.bank import Bank, merge_bank_dicts
from chuviettay.model.bank_schema import (
    CURRENT_VERSION,
    BankValidationError,
    load_and_validate,
    migrate_bank_dict,
    validate_bank_dict,
)


def _sample_v2_dict():
    """Tạo dictionary chuẩn Schema v2."""
    return {
        "schema_version": 2,
        "words": {
            "xin": [{"s": [[0.0, 0.0, 5.0, 2.0]], "w": 20.0, "T": "", "vi": -1, "ti": -1}],
        },
        "digits": {"1": [{"s": [[0.0, 0.0, 1.0, 5.0]], "w": 8.0}]},
        "punct": {",": [{"s": [[0.0, 0.0, 1.0, 1.0]], "w": 4.0}]},
        "xh": 10.0,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.2"},
        "line": 24.0,
        "width": 500.0,
        "x0": 78.0,
        "wgaps": [11.0],
        "dgaps": [3.5],
        "ratio": 6.6,
        "v": 1,
    }


def test_validate_v3_valid():
    d = _sample_v2_dict()
    d["schema_version"] = 3
    d["symbols"] = {
        "≤": [{"s": [[0.0, 0.0, 5.0, 0.0], [0.0, 2.0, 5.0, 5.0]], "w": 15.0}],
    }
    version = validate_bank_dict(d, allow_legacy=False)
    assert version == 3


def test_validate_v3_missing_symbols_rejected_when_not_legacy():
    d = _sample_v2_dict()
    d["schema_version"] = 3
    # thiếu "symbols"
    with pytest.raises(BankValidationError, match="Kho mẫu thiếu trường bắt buộc: 'symbols'"):
        validate_bank_dict(d, allow_legacy=False)


def test_validate_v2_allowed_when_legacy_flag_set():
    d = _sample_v2_dict()
    version = validate_bank_dict(d, allow_legacy=True)
    assert version == 2


def test_migration_v2_to_v3():
    d = _sample_v2_dict()
    upgraded = migrate_bank_dict(d, from_version=2)
    assert upgraded["schema_version"] == 3
    assert "symbols" in upgraded
    assert upgraded["symbols"] == {}
    # Xác nhận qua validate_bank_dict v3 nghiêm ngặt
    assert validate_bank_dict(upgraded, allow_legacy=False) == 3


def test_migration_v1_to_v3():
    # v1 không có schema_version và thiếu các trường v2/v3
    d = {
        "words": {},
        "digits": {},
        "punct": {},
        "xh": 8.0,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.0"},
    }
    version = validate_bank_dict(d, allow_legacy=True)
    assert version == 1
    upgraded = migrate_bank_dict(d, from_version=1)
    assert upgraded["schema_version"] == 3
    assert upgraded["symbols"] == {}
    assert upgraded["line"] == 24.0
    assert validate_bank_dict(upgraded, allow_legacy=False) == 3


def test_merge_bank_dicts_handles_symbols():
    base = {
        "schema_version": 3,
        "words": {},
        "digits": {},
        "punct": {},
        "symbols": {
            "≤": [{"s": [[0.0, 0.0, 5.0, 0.0]], "w": 12.0}],
        },
    }
    disk = {
        "schema_version": 3,
        "words": {},
        "digits": {},
        "punct": {},
        "symbols": {
            "≤": [{"s": [[0.0, 0.0, 5.0, 0.0]], "w": 12.0}],  # trùng lặp
            "∑": [{"s": [[0.0, 0.0, 10.0, 10.0]], "w": 18.0}], # mới
        },
    }

    merged = merge_bank_dicts(base, disk)
    assert len(merged["symbols"]["≤"]) == 1
    assert "∑" in merged["symbols"]
    assert len(merged["symbols"]["∑"]) == 1


def test_bank_add_and_drop_symbol(tmp_path):
    bank_path = str(tmp_path / "test_v3_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    assert bank.d["schema_version"] == 3
    assert bank.symbols == {}

    # Thêm ký hiệu
    inst = bank.add_symbol_sample("π", [[0.0, 5.0, 5.0, 5.0]], 14.0)
    assert inst["w"] == 14.0
    assert "π" in bank.symbols
    assert len(bank.symbols["π"]) == 1

    bank.save()

    # Nạp lại từ đĩa
    reloaded = Bank(bank_path)
    assert reloaded.d["schema_version"] == 3
    assert "π" in reloaded.symbols
    assert len(reloaded.symbols["π"]) == 1

    # Xoá ký hiệu
    removed_count = reloaded.drop_symbol("π")
    assert removed_count == 1
    assert "π" not in reloaded.symbols
