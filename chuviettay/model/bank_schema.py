"""Kiểm tra cấu trúc (schema validation) và di trú phiên bản (migration) cho kho mẫu chữ viết tay.

Đặc tả định dạng kho mẫu (gzip-compressed JSON):
- Phiên bản hiện tại: schema_version = 4 (hỗ trợ chữ cái ghép words/letters, dấu thanh rời marks, ký hiệu toán học symbols và tombstones đồng bộ)
- Bản cũ (v1, v2, v3): tự động phát hiện và nâng cấp di trú an toàn trong bộ nhớ lên phiên bản hiện tại (CURRENT_VERSION = 4).
"""
from __future__ import annotations

import gzip
import json
import math
import os
import re
import zlib
from collections.abc import Callable
from typing import Any

from chuviettay.config import TONES

CURRENT_VERSION = 4

# Các trường bắt buộc ở cấp cao nhất và kiểu dữ liệu tương ứng (Schema v3)
REQUIRED_METADATA_KEYS: dict[str, type | tuple[type, ...]] = {
    "words": dict,
    "digits": dict,
    "punct": dict,
    "symbols": dict,
    "xh": (int, float),
    "pen": dict,
    "line": (int, float),
    "width": (int, float),
    "x0": (int, float),
    "wgaps": list,
    "dgaps": list,
    "ratio": (int, float),
    "v": (int, float),
}

DEFAULT_METRICS: dict[str, Any] = {
    "line": 24.0,
    "width": 500.0,
    "x0": 78.0,
    "wgaps": [11.0],
    "dgaps": [3.5],
    "ratio": 6.6,
    "v": 1,
}

_REQUIRED_FIELDS = REQUIRED_METADATA_KEYS

_V2_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
    "words": dict,
    "digits": dict,
    "punct": dict,
    "xh": (int, float),
    "pen": dict,
    "line": (int, float),
    "width": (int, float),
    "x0": (int, float),
    "wgaps": list,
    "dgaps": list,
    "ratio": (int, float),
    "v": (int, float),
}

_V1_REQUIRED_FIELDS: dict[str, type | tuple[type, ...]] = {
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


def validate_stroke(stroke: Any, path: str = "stroke") -> None:
    """Kiểm tra tính hợp lệ của một nét vẽ (danh sách toạ độ)."""
    if not isinstance(stroke, list):
        raise BankValidationError(f"{path}: nét vẽ phải là danh sách toạ độ (list), nhận được: {type(stroke).__name__}")
    if len(stroke) < 2:
        raise BankValidationError(f"{path}: nét vẽ phải có ít nhất 1 điểm (2 toạ độ x, y), nhận được: {len(stroke)}")
    if len(stroke) % 2 != 0:
        raise BankValidationError(f"{path}: số lượng toạ độ phải là số chẵn, nhận được: {len(stroke)}")
    for i, c in enumerate(stroke):
        if not isinstance(c, (int, float)) or not math.isfinite(c):
            raise BankValidationError(f"{path}[{i}]: toạ độ phải là số hữu hạn, nhận được: {c!r}")


def validate_sample(
    item: Any,
    path: str = "sample",
    is_punct: bool = False,
    label: str = "",
) -> None:
    """Kiểm tra tính hợp lệ của một mẫu chữ (gồm nét vẽ 's', độ rộng 'w' và siêu dữ liệu dấu thanh)."""
    if not isinstance(item, dict):
        raise BankValidationError(f"{path}: mẫu phải là dict, nhận được: {type(item).__name__}")
    if "s" not in item:
        raise BankValidationError(f"{path}: mẫu thiếu nét vẽ 's'")
    if not isinstance(item["s"], list) or len(item["s"]) == 0:
        raise BankValidationError(f"{path}: 's' phải là danh sách nét vẽ không rỗng")
    for s_idx, stroke in enumerate(item["s"]):
        validate_stroke(stroke, path=f"{path}['s'][{s_idx}]")

    # Độ rộng 'w' là bắt buộc với words và digits, nhưng là tuỳ chọn với punct
    if not is_punct and "w" not in item:
        raise BankValidationError(f"{path}: thiếu độ rộng 'w'")
    if "w" in item:
        w_val = item["w"]
        if (
            not isinstance(w_val, (int, float))
            or isinstance(w_val, bool)
            or not math.isfinite(w_val)
            or w_val <= 0
        ):
            raise BankValidationError(f"{path}: độ rộng 'w' phải là số dương hữu hạn, nhận được: {w_val!r}")

    # Kiểm tra bất biến siêu dữ liệu dấu thanh (T, ti, vi)
    T = item.get("T")
    ti = item.get("ti")
    vi = item.get("vi")

    if T is not None:
        if not isinstance(T, str):
            raise BankValidationError(f"{path}['T']: dấu thanh phải là chuỗi (str), nhận được: {type(T).__name__}")
        if T != "" and T not in TONES:
            raise BankValidationError(f"{path}['T']: dấu thanh không hợp lệ: {T!r}")

    if ti is not None:
        if not isinstance(ti, int) or isinstance(ti, bool):
            raise BankValidationError(f"{path}['ti']: chỉ số nét dấu thanh phải là số nguyên (int), nhận được: {type(ti).__name__}")
        if ti < -1 or ti >= len(item["s"]):
            raise BankValidationError(f"{path}['ti']: chỉ số nét dấu thanh ti={ti} ngoài phạm vi [-1, {len(item['s']) - 1}]")

    if vi is not None:
        if not isinstance(vi, int) or isinstance(vi, bool):
            raise BankValidationError(f"{path}['vi']: chỉ số nguyên âm mang dấu phải là số nguyên (int), nhận được: {type(vi).__name__}")
        if vi < -1:
            raise BankValidationError(f"{path}['vi']: chỉ số nguyên âm vi={vi} không được nhỏ hơn -1")
        if label and vi >= len(label):
            raise BankValidationError(f"{path}['vi']: chỉ số nguyên âm vi={vi} vượt quá độ dài nhãn '{label}' ({len(label)})")

    # Tính nhất quán khi có nét dấu thanh
    if ti is not None and ti >= 0:
        if not T or T not in TONES:
            raise BankValidationError(f"{path}: mẫu có ti={ti} >= 0 nhưng T={T!r} không phải dấu thanh hợp lệ")
        if vi is None or vi < 0:
            raise BankValidationError(f"{path}: mẫu có ti={ti} >= 0 nhưng vi={vi!r} < 0")


# ------------------------------------------------------------------ Kiểm tra cấu trúc
def validate_bank_dict(d: Any, context: str = "", allow_legacy: bool = False) -> int:
    """Kiểm tra tính hợp lệ về cấu trúc của dictionary kho mẫu.

    Trả về schema_version (1 nếu là bản cũ chưa có trường này).
    Ném BankValidationError nếu sai cấu trúc.
    Ném UnsupportedSchemaVersionError nếu schema_version > CURRENT_VERSION.
    """
    ctx = f" ({context})" if context else ""

    if not isinstance(d, dict):
        raise BankValidationError(f"Dữ liệu kho mẫu phải là một JSON object (dict), nhận được: {type(d).__name__}{ctx}")

    # 1. Kiểm tra schema_version
    version = d.get("schema_version", 1)
    if not isinstance(version, int) or version < 1:
        raise BankValidationError(f"Trường 'schema_version' phải là số nguyên dương, nhận được: {version!r}{ctx}")

    if version > CURRENT_VERSION:
        raise UnsupportedSchemaVersionError(
            f"Kho mẫu có schema_version={version}, nhưng phiên bản hiện tại chỉ hỗ trợ đến v{CURRENT_VERSION}. "
            f"Vui lòng nâng cấp phần mềm.{ctx}"
        )

    # 2. Kiểm tra các trường bắt buộc
    is_legacy_v1 = allow_legacy and version == 1
    is_legacy_v2 = allow_legacy and version == 2
    if is_legacy_v1:
        fields_to_check = _V1_REQUIRED_FIELDS
    elif is_legacy_v2:
        fields_to_check = _V2_REQUIRED_FIELDS
    else:
        fields_to_check = _REQUIRED_FIELDS
    for key, expected_types in fields_to_check.items():
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

    # 3. Kiểm tra giá trị các trường số học và metadata
    if not math.isfinite(d["xh"]) or d["xh"] <= 0:
        raise BankValidationError(f"Chiều cao chữ 'xh' phải là số dương hữu hạn, nhận được: {d['xh']}{ctx}")

    if not is_legacy_v1:
        for num_key in ("line", "width", "ratio"):
            val = d[num_key]
            if not math.isfinite(val) or val <= 0:
                raise BankValidationError(f"Trường '{num_key}' phải là số dương hữu hạn, nhận được: {val}{ctx}")
        if not math.isfinite(d["x0"]) or d["x0"] < 0:
            raise BankValidationError(f"Trường 'x0' phải là số không âm hữu hạn, nhận được: {d['x0']}{ctx}")
        if not math.isfinite(d["v"]):
            raise BankValidationError(f"Trường 'v' phải là số hữu hạn, nhận được: {d['v']}{ctx}")

        for list_key in ("wgaps", "dgaps"):
            val = d[list_key]
            if len(val) == 0:
                raise BankValidationError(f"Trường '{list_key}' không được là danh sách rỗng{ctx}")
            for idx, g in enumerate(val):
                if not isinstance(g, (int, float)) or not math.isfinite(g) or g <= 0:
                    raise BankValidationError(f"Khoảng cách '{list_key}[{idx}]' phải là số dương hữu hạn, nhận được: {g!r}{ctx}")

    # 4. Kiểm tra thông số bút vẽ
    pen = d["pen"]
    for pk in ("tool", "color", "width"):
        if pk not in pen:
            raise BankValidationError(f"Thông số bút 'pen' thiếu thuộc tính bắt buộc: '{pk}'{ctx}")

    tool_val = pen["tool"]
    if not isinstance(tool_val, str) or not tool_val.strip():
        raise BankValidationError(f"Thông số bút 'pen.tool' phải là chuỗi không rỗng, nhận được: {tool_val!r}{ctx}")

    color_val = pen["color"]
    if not isinstance(color_val, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", color_val):
        raise BankValidationError(f"Màu bút 'pen.color' phải là mã hex dạng #RRGGBB hoặc #RRGGBBAA, nhận được: {color_val!r}{ctx}")

    pen_w = pen["width"]
    pen_w_num = None
    if isinstance(pen_w, (int, float)) and not isinstance(pen_w, bool):
        pen_w_num = float(pen_w)
    elif isinstance(pen_w, str):
        try:
            pen_w_num = float(pen_w)
        except ValueError:
            pass
    if pen_w_num is None or not math.isfinite(pen_w_num) or pen_w_num <= 0:
        raise BankValidationError(f"Độ rộng nét bút 'pen.width' phải là số dương hữu hạn, nhận được: {pen_w!r}{ctx}")

    # Kiểm tra tombstones nếu có
    if "tombstones" in d:
        tombstones = d["tombstones"]
        if not isinstance(tombstones, dict):
            raise BankValidationError(f"Trường 'tombstones' phải là dict, nhận được: {type(tombstones).__name__}{ctx}")
        for t_k, t_v in tombstones.items():
            if not isinstance(t_k, str):
                raise BankValidationError(f"Khoá của 'tombstones' phải là chuỗi, nhận được: {t_k!r}{ctx}")
            if isinstance(t_v, dict):
                del_at = t_v.get("deleted_at")
                if not isinstance(del_at, (int, float)) or isinstance(del_at, bool) or not math.isfinite(del_at):
                    raise BankValidationError(
                        f"Giá trị tombstone['{t_k}']['deleted_at'] phải là timestamp số hữu hạn, nhận được: {del_at!r}{ctx}"
                    )
                if "generation" in t_v:
                    gen = t_v["generation"]
                    if not isinstance(gen, int) or isinstance(gen, bool) or gen < 0:
                        raise BankValidationError(
                            f"Giá trị tombstone['{t_k}']['generation'] phải là số nguyên không âm, nhận được: {gen!r}{ctx}"
                        )
            elif isinstance(t_v, (int, float)) and not isinstance(t_v, bool) and math.isfinite(t_v):
                pass
            else:
                raise BankValidationError(
                    f"Giá trị tombstone['{t_k}'] phải là timestamp số hữu hạn hoặc dict cấu trúc, nhận được: {t_v!r}{ctx}"
                )

    # Kiểm tra generation nếu có
    if "generation" in d:
        gen = d["generation"]
        if not isinstance(gen, int) or isinstance(gen, bool) or gen < 0:
            raise BankValidationError(f"Trường 'generation' phải là số nguyên không âm, nhận được: {gen!r}{ctx}")

    # 5. Kiểm tra sâu cấu trúc danh sách mẫu trong words/digits/punct/symbols/letters
    if "letters" in d:
        categories = ("words", "digits", "punct", "symbols", "letters")
    elif "symbols" in d:
        categories = ("words", "digits", "punct", "symbols")
    else:
        categories = ("words", "digits", "punct")
    for c_name in categories:
        container = d[c_name]
        is_punct = (c_name == "punct")
        for label, samples in container.items():
            if not isinstance(samples, list):
                raise BankValidationError(
                    f"Mục '{c_name}[{label!r}]' phải là danh sách mẫu (list), nhận được: {type(samples).__name__}{ctx}"
                )
            for idx, item in enumerate(samples):
                validate_sample(item, path=f"{c_name}[{label!r}][{idx}]{ctx}", is_punct=is_punct, label=label)

    return version


# ------------------------------------------------------------------ Di trú phiên bản
def _migrate_v1_to_v2(d: dict[str, Any]) -> dict[str, Any]:
    """Nâng cấp từ v1 (legacy) lên v2: thêm schema_version và chuẩn hóa các trường mặc định."""
    d["schema_version"] = 2
    for k, default_val in DEFAULT_METRICS.items():
        if k not in d:
            d[k] = list(default_val) if isinstance(default_val, list) else default_val
    return d


def _migrate_v2_to_v3(d: dict[str, Any]) -> dict[str, Any]:
    """Nâng cấp từ v2 lên v3: thêm schema_version = 3, chuẩn bị kho symbols và letters."""
    d["schema_version"] = 3
    if "symbols" not in d:
        d["symbols"] = {}
    if "letters" not in d:
        d["letters"] = {}
    return d


def _migrate_v3_to_v4(d: dict[str, Any]) -> dict[str, Any]:
    """Nâng cấp từ v3 lên v4: thêm schema_version = 4, chuẩn hoá tombstones hỗ trợ phân tách không gian tên."""
    d["schema_version"] = 4
    if "tombstones" not in d:
        d["tombstones"] = {}
    return d


_MIGRATORS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
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
        raise BankNotFoundError(f"Không thấy kho mẫu: {path} (dùng --bank <đường_dẫn> hoặc chạy lệnh 'seed' để tạo)")

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

    version = validate_bank_dict(d, context=path, allow_legacy=True)
    if version < CURRENT_VERSION:
        d = migrate_bank_dict(d, version, context=path)
        validate_bank_dict(d, context=path, allow_legacy=False)

    return d
