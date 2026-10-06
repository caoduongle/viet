"""Kiểm thử chu trình xuất / nhập kho mẫu và tương thích CLI hw-note stats.

Tuân thủ task T058:
  - Xuất kho qua BrowserBridge.export_bank() -> chạy được `hw-note stats --bank <file>` thành công.
  - Nhập kho schema cũ (v2, v3) -> tự động nâng cấp lên schema v4 và sử dụng được bình thường.
"""
from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

from chuviettay import cli
from chuviettay.browser.bridge import BrowserBridge
from chuviettay.model.bank import Bank
from tests.conftest import tiny_bank_dict


def test_bank_export_roundtrip_cli_stats(tmp_path, capsys):
    """Xuất kho mẫu qua BrowserBridge.export_bank() rồi kiểm tra bằng lệnh CLI `hw-note stats`."""
    base_dict = tiny_bank_dict()
    init_path = str(tmp_path / "init_bank.json.gz")
    with gzip.open(init_path, "wt", encoding="utf-8") as f:
        json.dump(base_dict, f)

    bridge = BrowserBridge(bank_path=init_path)
    bridge.init()

    # Thêm một mẫu mới qua bridge
    sample_stroke = [[(150.0, 170.0), (160.0, 150.0), (170.0, 170.0)]]
    res_teach = bridge.teach_sample("hoa", pixel_strokes=sample_stroke, deferred_save=False)
    assert res_teach["ok"] is True

    # Xuất kho thành binary (.json.gz)
    exported_bytes = bridge.export_bank()
    assert isinstance(exported_bytes, (bytes, bytearray))
    assert len(exported_bytes) > 0

    exported_path = str(tmp_path / "exported_bank.json.gz")
    with open(exported_path, "wb") as f:
        f.write(exported_bytes)

    # Chạy lệnh CLI hw-note stats --bank <exported_path>
    rc = cli.main(["--bank", exported_path, "stats"])
    assert rc == 0

    captured = capsys.readouterr()
    assert "chữ cái" in captured.out or "từ" in captured.out
    assert "mẫu" in captured.out


def test_old_schema_v2_v3_imported_and_upgraded(tmp_path):
    """Nhập kho có schema cũ (v2 hoặc v3 thiếu letters, marks) -> nâng cấp lên schema v4 và hoạt động bình thường."""
    # Tạo cấu trúc kho cũ v2 (không có letters, symbols, marks, tombstones)
    old_v2_dict = {
        "words": {
            "xin": [{"s": [[0.0, 0.0, 10.0, 0.0]], "w": 10.0, "T": "", "vi": -1, "ti": -1}],
            "chao": [{"s": [[0.0, 0.0, 12.0, 0.0]], "w": 12.0, "T": "", "vi": -1, "ti": -1}],
        },
        "digits": {"1": [{"s": [[0.0, 0.0, 2.0, 5.0]], "w": 6.0}]},
        "punct": {".": [{"s": [[0.0, 0.0, 1.0, 1.0]], "w": 3.0}]},
        "xh": 7.94,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41"},
        "line": 24.0,
        "width": 500.0,
        "x0": 78.0,
        "wgaps": [11.0],
        "dgaps": [3.5],
        "ratio": 6.6,
        "v": 1,
    }
    old_gz_bytes = gzip.compress(json.dumps(old_v2_dict).encode("utf-8"))

    # Nạp kho cũ vào bridge
    target_path = str(tmp_path / "migrated_bank.json.gz")
    bridge = BrowserBridge(bank_path=target_path)
    res_load = bridge.load_bank(old_gz_bytes)
    assert res_load["ok"] is True
    assert res_load["stats"]["n_words"] == 2

    # Thử viết chữ bằng kho vừa nạp
    write_res = bridge.write_text("xin chao", {"seed": 1})
    assert write_res["ok"] is True
    assert "xopp_base64" in write_res

    # Dạy thêm một chữ cái mới
    letter_stroke = [[(150.0, 170.0), (160.0, 150.0)]]
    res_letter = bridge.teach_sample("b", pixel_strokes=letter_stroke, deferred_save=False)
    assert res_letter["ok"] is True

    # Xuất kho và kiểm tra schema_version
    exported_bytes = bridge.export_bank()
    decompressed = json.loads(gzip.decompress(exported_bytes).decode("utf-8"))

    assert decompressed["schema_version"] == 4
    assert "letters" in decompressed
    assert "symbols" in decompressed
    assert "b" in decompressed["letters"]
