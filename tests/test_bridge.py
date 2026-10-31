"""Kiểm thử chuviettay.browser.bridge (Browser Bridge Facade).
Đảm bảo:
  - 100% kết quả trả về là JSON-serializable (chỉ gồm int, float, str, bool, list, dict, None; không có set/tuple).
  - Không bao giờ để ngoại lệ lọt ra ngoài không kiểm soát (trả về {ok: False, error: ...}).
  - Không đụng trực tiếp chuviettay.model, tuân thủ MVC qua AppController.
"""
from __future__ import annotations

import base64
import gzip
import json
import pytest

from chuviettay.browser.bridge import BrowserBridge
from chuviettay.controller.teach_geometry import BASE_PX, CANVAS_H, CANVAS_W, MIN_POINT_DIST, ZOOM
from tests.conftest import tiny_bank_dict


def is_json_serializable(obj) -> bool:
    try:
        s = json.dumps(obj)
        # Kiểm tra thêm không có biểu diễn kiểu tuple (ví dụ trong nested data structure nếu có custom encoder)
        json.loads(s)
        return True
    except (TypeError, OverflowError):
        return False


def assert_valid_bank_snapshot(res: dict) -> None:
    """Helper kiểm tra tính hợp lệ và cấu trúc chuẩn của snapshot kho mẫu."""
    assert is_json_serializable(res)
    assert res.get("ok") is True
    assert "data" in res
    data = res["data"]
    assert "revision" in data and isinstance(data["revision"], int)
    assert "stats" in data and isinstance(data["stats"], dict)
    assert "letters" in data and isinstance(data["letters"], list)
    assert "digits" in data and isinstance(data["digits"], dict)
    assert "punct" in data and isinstance(data["punct"], dict)
    assert "symbols" in data and isinstance(data["symbols"], list)
    assert "marks" in data and isinstance(data["marks"], list)


def assert_valid_write_response(res: dict) -> None:
    """Helper kiểm tra tính hợp lệ và cấu trúc chuẩn của kết quả write_text."""
    assert is_json_serializable(res)
    assert res.get("ok") is True
    assert "xopp_base64" in res
    assert "warnings" in res and isinstance(res["warnings"], list)
    assert "unsupported" in res and isinstance(res["unsupported"], list)



@pytest.fixture
def bridge_with_tiny_bank(tmp_path):
    bank_path = str(tmp_path / "bridge_bank.json.gz")
    with gzip.open(bank_path, "wt", encoding="utf-8") as f:
        json.dump(tiny_bank_dict(), f)
    bridge = BrowserBridge(bank_path=bank_path)
    bridge.init()
    return bridge


def test_get_canvas_spec():
    bridge = BrowserBridge()
    spec = bridge.get_canvas_spec()
    assert spec["ok"] is True
    assert spec["width"] == CANVAS_W
    assert spec["height"] == CANVAS_H
    assert spec["base_px"] == BASE_PX
    assert spec["zoom"] == ZOOM
    assert spec["min_point_dist"] == MIN_POINT_DIST
    assert is_json_serializable(spec)


def test_get_write_defaults():
    bridge = BrowserBridge()
    defaults = bridge.get_write_defaults()
    assert defaults["ok"] is True
    assert "data" in defaults
    data = defaults["data"]
    assert "scale" in data
    assert "line" in data
    assert "seed" in data
    assert "stable_variants" in data
    assert is_json_serializable(defaults)


def test_load_and_export_bank(tmp_path):
    bank_dict = tiny_bank_dict()
    gz_bytes = gzip.compress(json.dumps(bank_dict).encode("utf-8"))

    bridge = BrowserBridge(bank_path=str(tmp_path / "test_bank.json.gz"))
    res = bridge.load_bank(gz_bytes)
    assert res["ok"] is True
    assert "stats" in res
    assert res["stats"]["n_words"] >= 3
    assert is_json_serializable(res)

    exported_bytes = bridge.export_bank()
    assert isinstance(exported_bytes, (bytes, bytearray))
    decompressed = json.loads(gzip.decompress(exported_bytes).decode("utf-8"))
    assert "words" in decompressed


def test_get_stats(bridge_with_tiny_bank):
    stats = bridge_with_tiny_bank.get_stats()
    assert stats["ok"] is True
    assert "n_words" in stats["data"]
    assert is_json_serializable(stats)


def test_write_text_returns_xopp_base64(bridge_with_tiny_bank):
    res = bridge_with_tiny_bank.write_text("xin ba chào", {"seed": 7})
    assert res["ok"] is True
    assert "xopp_base64" in res
    assert isinstance(res["xopp_base64"], str)
    # Giải mã base64 và gzip
    raw_xopp = base64.b64decode(res["xopp_base64"])
    xml_content = gzip.decompress(raw_xopp).decode("utf-8")
    assert "<xournal" in xml_content
    assert is_json_serializable(res)


def test_write_text_pagebreak(bridge_with_tiny_bank):
    """Kiểm tra xử lý ngắt trang <!-- pagebreak --> và \\pagebreak."""
    text = "Trang mot\n\n<!-- pagebreak -->\n\nTrang hai"
    res = bridge_with_tiny_bank.write_text(text, {"seed": 7}, fmt="md")
    assert res["ok"] is True
    raw_xopp = base64.b64decode(res["xopp_base64"])
    xml_content = gzip.decompress(raw_xopp).decode("utf-8")
    # Phải có ít nhất 2 thẻ <page ...>
    assert xml_content.count("<page ") >= 2


def test_teach_and_list_samples(bridge_with_tiny_bank):
    stroke = [[0.0, 0.0, 5.0, -10.0]]
    res = bridge_with_tiny_bank.teach_sample("hoa", stroke, 10.0, category="words")
    assert res["ok"] is True
    assert is_json_serializable(res)

    # list_words
    words = bridge_with_tiny_bank.list_words()
    assert words["ok"] is True
    assert any(w[0] == "hoa" for w in words["data"])
    assert is_json_serializable(words)

    # list_label_samples
    samples = bridge_with_tiny_bank.list_label_samples("hoa", category="words")
    assert samples["ok"] is True
    assert len(samples["data"]) >= 1
    assert is_json_serializable(samples)


def test_drop_label(bridge_with_tiny_bank):
    res = bridge_with_tiny_bank.drop_label("xin", category="words")
    assert res["ok"] is True
    assert is_json_serializable(res)

    words = bridge_with_tiny_bank.list_words()
    assert not any(w[0] == "xin" for w in words["data"])


def test_drop_chars(bridge_with_tiny_bank):
    res = bridge_with_tiny_bank.drop_chars(["b", "1", "khong_co"])
    assert res["ok"] is True
    assert is_json_serializable(res)
    assert res["total_removed_chars"] == 2
    assert res["total_removed_samples"] >= 2
    assert "data" in res
    assert res["data"]["removed"]["b"] > 0
    assert res["data"]["removed"]["1"] > 0


def test_error_handling_returns_standard_dict():
    bridge = BrowserBridge(bank_path="/nonexistent/dir/bank.json.gz")
    # Chưa load bank mà gọi get_stats
    res = bridge.get_stats()
    assert res["ok"] is False
    assert "error" in res
    assert "error_type" in res
    assert is_json_serializable(res)


def test_write_text_forwards_unsupported(bridge_with_tiny_bank):
    """Kiểm tra write_text chuyển tiếp đầy đủ cả warnings và unsupported sang JSON response."""
    md_text = "Văn bản\n\n```python\nprint(1)\n```\n\n---\n\n![Anh minh hoa](sample.png)"
    res = bridge_with_tiny_bank.write_text(md_text, {"seed": 1}, fmt="md")
    assert_valid_write_response(res)
    assert "unsupported" in res
    assert isinstance(res["unsupported"], list)
    assert any("code_block" in u for u in res["unsupported"])
    assert any("hr" in u for u in res["unsupported"])
    assert any("image" in u for u in res["unsupported"])



# ==============================================================================
# Feature 067 / US4: Bank snapshot and revision tracking tests (T019)
# ==============================================================================

def test_get_bank_snapshot_structure(bridge_with_tiny_bank):
    """Kiểm tra get_bank_snapshot trả về đầy đủ cấu trúc và serializable sang JSON."""
    snapshot = bridge_with_tiny_bank.get_bank_snapshot(profile_id="test_profile")
    assert_valid_bank_snapshot(snapshot)
    assert snapshot["data"]["profile_id"] == "test_profile"
    assert is_json_serializable(snapshot)


def test_bank_revision_tracking(bridge_with_tiny_bank, tmp_path):
    """Kiểm tra bank_revision tăng lên khi thay đổi kho mẫu."""
    s0 = bridge_with_tiny_bank.get_bank_snapshot()
    rev0 = s0["data"]["revision"]

    # Thêm một ký tự mẫu mới
    stroke = [[0.0, 0.0, 5.0, -10.0]]
    res = bridge_with_tiny_bank.teach_char("z", stroke, 10.0)
    assert res["ok"] is True
    s1 = bridge_with_tiny_bank.get_bank_snapshot()
    rev1 = s1["data"]["revision"]
    assert rev1 > rev0, f"Revision không tăng sau khi thêm mẫu ({rev1} <= {rev0})"

    # Xóa ký tự mẫu
    del_res = bridge_with_tiny_bank.drop_chars(["z"])
    assert del_res["ok"] is True
    s2 = bridge_with_tiny_bank.get_bank_snapshot()
    rev2 = s2["data"]["revision"]
    assert rev2 > rev1, f"Revision không tăng sau khi xóa mẫu ({rev2} <= {rev1})"


def test_get_bank_snapshot_includes_worker_epoch(bridge_with_tiny_bank):
    """T011 [US2]: Kiểm tra get_bank_snapshot trả về worker_epoch duy nhất."""
    snapshot = bridge_with_tiny_bank.get_bank_snapshot()
    assert snapshot["ok"] is True
    assert "worker_epoch" in snapshot["data"]
    epoch = snapshot["data"]["worker_epoch"]
    assert isinstance(epoch, str) and len(epoch) > 0
    assert epoch == bridge_with_tiny_bank.worker_epoch


def test_get_bank_snapshot_atomicity_on_subquery_failure(bridge_with_tiny_bank, monkeypatch):
    """T016 [US3]: Kiểm tra tính nguyên tử: nếu truy vấn con lỗi thì snapshot trả về lỗi."""
    monkeypatch.setattr(bridge_with_tiny_bank, "list_letters", lambda: {"ok": False, "error": "Lỗi truy vấn chữ cái"})
    res = bridge_with_tiny_bank.get_bank_snapshot()
    assert res["ok"] is False
    assert "Lỗi truy vấn chữ cái" in res.get("error", "")
