"""Kiểm tra tính toàn vẹn và độ bao phủ của synthetic benchmark fixture.

Fixture tests/data/kho_mau_tong_hop.json.gz phải:
1. Có schema_version = 2 và cấu trúc chuẩn theo bank_schema.
2. Không chứa bất kỳ dữ liệu cá nhân nào từ kho mẫu cũ.
3. Đủ các dấu thanh tiếng Việt (huyền, sắc, hỏi, ngã, nặng) để harvest vào bank.marks.
4. Đủ các từ không dấu cơ bản để ghép từ mới (ví dụ "so" + dấu sắc -> "số", dấu hỏi -> "sổ").
5. Có từ mốc ổn định ("xin" với 5 mẫu) cho chức năng calibration.
"""
from __future__ import annotations

import os

from chuviettay.config import NANG, TONES
from chuviettay.model.bank import Bank
from chuviettay.model.bank_schema import CURRENT_VERSION, validate_bank_dict

HERE = os.path.dirname(os.path.abspath(__file__))
SYNTHETIC_PATH = os.path.join(HERE, "data", "kho_mau_tong_hop.json.gz")


def test_synthetic_bank_ton_tai_va_hop_le():
    assert os.path.exists(SYNTHETIC_PATH), f"Không tìm thấy fixture {SYNTHETIC_PATH}"
    b = Bank(SYNTHETIC_PATH)
    assert b.d.get("schema_version") == CURRENT_VERSION
    assert validate_bank_dict(b.d) == CURRENT_VERSION
    assert b.xh == 7.0
    assert len(b.words) >= 10
    assert len(b.digits) == 10
    assert len(b.punct) >= 5


def test_synthetic_bank_du_dau_thanh_va_ghep_duoc_tu_moi():
    b = Bank(SYNTHETIC_PATH)
    # Phải harvest được đầy đủ các dấu thanh
    for t in TONES:
        assert len(b.marks[t]) > 0, f"Thiếu nét dấu thanh {t} trong synthetic bank"

    assert len(b.marks[NANG]) > 0
    # "số" và "sổ" ghép được từ thân "so" + dấu thanh
    assert b.can("số")
    assert b.can("sổ")
    assert b.can("bà")
    assert b.can("bá")


def test_synthetic_bank_co_tu_moc_calibration():
    b = Bank(SYNTHETIC_PATH)
    assert "xin" in b.words
    assert len(b.words["xin"]) >= 5
