"""Kiểm tra cấu trúc (schema validation) và di trú phiên bản (migration) cho kho mẫu chữ viết tay.

Đặc tả định dạng kho mẫu (gzip-compressed JSON):
- Phiên bản hiện tại: schema_version = 2
- Bản cũ (v1): không có trường schema_version (được coi là v1 và tự nâng cấp trong bộ nhớ).
"""
from __future__ import annotations

import gzip
import json
import os
import zlib
from collections.abc import Callable
from typing import Any

CURRENT_VERSION = 2

# Các trường bắt buộc ở cấp cao nhất và kiểu dữ liệu tương ứng
_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "words": dict,
    "digits": dict,
    "punct": dict,
    "xh": (int, float),
    "pen": dict,
}


# ------------------------------------------------------------------ Phân cấp ngoại lệ
class BankError(Exception):
    """Lớp cha cho mọi lỗi liên quan đến kho mẫu chữ viết tay."""


class BankNotFoundError(BankError, FileNotFoundError):
    """Không tìm thấy file kho mẫu tại đường dẫn đã cho."""


class BankCorruptedError(BankError):
    """File kho mẫu bị hỏng vật lý (0 bytes, hỏng gzip, hoặc JSON không hợp lệ)."""


class BankValidationError(BankError, ValueError):
    """Cấu trúc dữ liệu trong kho mẫu không đúng quy chuẩn (thiếu trường, sai kiểu dữ liệu)."""


class BankSchemaError(BankError):
    """Lỗi liên quan đến phiên bản schema hoặc luồng di trú."""


class UnsupportedSchemaVersionError(BankSchemaError):
    """Phiên bản schema của file mới hơn phiên bản ứng dụng hỗ trợ."""


class BankMigrationError(BankSchemaError):
    """Xảy ra lỗi trong quá trình di trú dữ liệu giữa các phiên bản."""


# ------------------------------------------------------------------ Kiểm tra cấu trúc
def validate_bank_dict(d: Any, context: str = "") -> int:
    """Kiểm tra tính hợp lệ về cấu trúc của dictionary kho mẫu.

    Trả về schema_version (1 nếu là bản cũ chưa có trường này).
    Ném BankValidationError nếu sai cấu trúc.
    Ném UnsupportedSchemaVersionError nếu schema_version > CURRENT_VERSION.
    """
    ctx = f" ({context})" if context else ""

    if not isinstance(d, dict):
        raise BankValidationError(f"Dữ liệu kho mẫu phải là một JSON object (dict), nhận được: {type(d).__name__}{ctx}")

    # 1. Kiểm tra các trường bắt buộc
    for key, expected_types in _REQUIRED_FIELDS.items():
        if key not in d:
            raise BankValidationError(f"Kho mẫu thiếu trường bắt buộc: '{key}'{ctx}")
        if not isinstance(d[key], expected_types):
            type_names = (
                "/".join(t.__name__ for t in expected_types)
                if isinstance(expected_types, tuple)
                else expected_types.__name__
            )
            raise BankValidationError(
                f"Trường '{key}' phải có kiểu {type_names}, nhận được: {type(d[key]).__name__}{ctx}"
            )

    # 2. Kiểm tra giá trị xh
    if d["xh"] <= 0:
        raise BankValidationError(f"Chiều cao chữ 'xh' phải là số dương, nhận được: {d['xh']}{ctx}")

    # 3. Kiểm tra thông số bút vẽ
    pen = d["pen"]
    for pk in ("tool", "color", "width"):
        if pk not in pen:
            raise BankValidationError(f"Thông số bút 'pen' thiếu thuộc tính bắt buộc: '{pk}'{ctx}")

    # 4. Kiểm tra cấu trúc danh sách mẫu trong words/digits/punct
    for c_name in ("words", "digits", "punct"):
        container = d[c_name]
        for label, samples in container.items():
            if not isinstance(samples, list):
                raise BankValidationError(
                    f"Mục '{c_name}[{label!r}]' phải là danh sách mẫu (list), nhận được: {type(samples).__name__}{ctx}"
                )
            for idx, item in enumerate(samples):
                if not isinstance(item, dict):
                    raise BankValidationError(
                        f"Mẫu thứ {idx} của '{c_name}[{label!r}]' phải là dict{ctx}"
                    )
                if "s" not in item:
                    raise BankValidationError(
                        f"Mẫu thứ {idx} của '{c_name}[{label!r}]' thiếu nét vẽ 's'{ctx}"
                    )
                if "w" not in item or not isinstance(item["w"], (int, float)):
                    raise BankValidationError(
                        f"Mẫu thứ {idx} của '{c_name}[{label!r}]' thiếu hoặc sai kiểu độ rộng 'w'{ctx}"
                    )

    # 5. Kiểm tra schema_version
    version = d.get("schema_version", 1)
    if not isinstance(version, int) or version < 1:
        raise BankValidationError(f"Trường 'schema_version' phải là số nguyên dương, nhận được: {version!r}{ctx}")

    if version > CURRENT_VERSION:
        raise UnsupportedSchemaVersionError(
            f"Kho mẫu có schema_version={version}, nhưng phiên bản hiện tại chỉ hỗ trợ đến v{CURRENT_VERSION}. "
            f"Vui lòng nâng cấp phần mềm.{ctx}"
        )

    return version


# ------------------------------------------------------------------ Di trú phiên bản
def _migrate_v1_to_v2(d: dict[str, Any]) -> dict[str, Any]:
    """Nâng cấp từ v1 (legacy) lên v2: thêm schema_version và chuẩn hóa các trường mặc định."""
    d["schema_version"] = 2
    d.setdefault("wgaps", [11.0])
    d.setdefault("dgaps", [3.5])
    return d


_MIGRATORS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _migrate_v1_to_v2,
}


def migrate_bank_dict(d: dict[str, Any], from_version: int, context: str = "") -> dict[str, Any]:
    """Áp dụng chuỗi nâng cấp tuần tự từ from_version lên CURRENT_VERSION."""
    v = from_version
    ctx = f" ({context})" if context else ""
    while v < CURRENT_VERSION:
        migrator = _MIGRATORS.get(v)
        if migrator is None:
            raise BankMigrationError(f"Không có bước nâng cấp từ schema v{v} lên v{v + 1}{ctx}")
        d = migrator(d)
        new_v = d.get("schema_version")
        if new_v != v + 1:
            raise BankMigrationError(f"Di trú v{v}->v{v + 1} không đặt đúng schema_version{ctx}")
        v = new_v
    return d


# ------------------------------------------------------------------ Nạp và kiểm định an toàn
def load_and_validate(path: str) -> dict[str, Any]:
    """Nạp file .json.gz từ đĩa, kiểm định tính toàn vẹn và di trú trong bộ nhớ nếu là bản cũ."""
    if not os.path.exists(path):
        raise BankNotFoundError(f"Không thấy kho mẫu: {path} (để cùng thư mục với hw_note.py hoặc dùng --bank)")

    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise BankNotFoundError(f"Không thể truy cập file kho mẫu: {path} ({e})") from e

    if size == 0:
        raise BankCorruptedError(f"File kho mẫu bị rỗng (0 bytes): {path}")

    try:
        with open(path, "rb") as rf:
            raw_bytes = rf.read()
    except OSError as e:
        raise BankNotFoundError(f"Không đọc được file kho mẫu: {path} ({e})") from e

    try:
        decompressed = gzip.decompress(raw_bytes)
        text = decompressed.decode("utf-8")
    except (gzip.BadGzipFile, zlib.error, EOFError) as e:
        raise BankCorruptedError(f"File không phải định dạng nén gzip hợp lệ hoặc bị cắt cụt: {path}") from e
    except UnicodeDecodeError as e:
        raise BankCorruptedError(f"Nội dung kho mẫu giải nén không phải UTF-8 hợp lệ: {path}") from e

    try:
        d = json.loads(text)
    except json.JSONDecodeError as e:
        raise BankCorruptedError(f"Nội dung JSON bị lỗi cú pháp tại dòng {e.lineno}, cột {e.colno}: {path}") from e

    version = validate_bank_dict(d, context=path)
    if version < CURRENT_VERSION:
        d = migrate_bank_dict(d, version, context=path)
        validate_bank_dict(d, context=path)

    return d
