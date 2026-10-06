"""Kiểm thử tính an toàn của Deletion Tombstone khi xoá nhãn và Hoàn tác (undo drop).

Tuân thủ task T059:
  Xoá nhãn rồi Hoàn tác (dạy lại các mẫu cũ) -> readded_at đúng, đa tiến trình
  không hồi sinh/mất mẫu; nếu an toàn -> bật Hoàn tác trên UI.
"""
from __future__ import annotations

import time

from chuviettay.browser.bridge import BrowserBridge
from chuviettay.model.bank import Bank


def test_drop_and_undo_readded_timestamp(tmp_path):
    """Xoá nhãn rồi hoàn tác dạy lại: tombstone được thu hồi và readded_at được ghi nhận hợp lệ."""
    p = str(tmp_path / "bank.json.gz")
    bank = Bank.create_empty(p)
    bank.add_sample("hoa", [[0.0, 0.0, 5.0, 0.0]], 5.0)
    bank.add_sample("lá", [[0.0, 0.0, 4.0, 0.0]], 4.0)
    bank.save()

    # Lưu lại mẫu cũ trước khi xoá (giống cơ chế Undo buffer trên UI)
    old_samples = [dict(s) for s in bank.words["hoa"]]

    time.sleep(0.01)
    # 1. Xoá nhãn "hoa"
    removed = bank.drop("hoa", category="words")
    assert removed == 1
    assert "hoa" not in bank.words
    assert "hoa" in bank._tombstones or "words:hoa" in bank._tombstones
    bank.save()

    # 2. Hoàn tác: Dạy lại các mẫu cũ
    # 2. Hoàn tác: Dạy lại các mẫu cũ
    time.sleep(0.01)
    for s in old_samples:
        bank.add_sample("hoa", s["s"], s["w"])
    # Ngay khi thêm lại mẫu, _readded_words phải ghi nhận timestamp trước khi lưu
    assert "hoa" in bank._readded_words or "words:hoa" in bank._readded_words
    bank.save()

    # 3. Kiểm tra: tombstone đã được giải phóng và từ đã trở lại kho
    assert "hoa" in bank.words
    assert "hoa" not in bank._tombstones
    assert "words:hoa" not in bank._tombstones

    reloaded = Bank(p)
    assert "hoa" in reloaded.words
    assert len(reloaded.words["hoa"]) == len(old_samples)


def test_drop_undo_cross_process_merge_safety(tmp_path):
    """Đánh giá an toàn đa tiến trình khi Hoàn tác (undo drop):
    Tiến trình A xoá rồi Hoàn tác 'hoa';
    Tiến trình B (cầm snapshot cũ đã nạp tombstone) thêm từ 'cành' rồi lưu.
    Kết quả: Khi không có cơ chế khoá / đồng bộ IPC (Web Locks + BroadcastChannel),
    snapshot cũ của B vẫn chứa tombstone và sẽ ghi đè xoá lại 'hoa' trên đĩa.
    -> Phục vụ T059: Phát hiện trường hợp không an toàn để quyết định KHÔNG bật Hoàn tác
    nếu thiếu tầng đồng bộ đa tab."""
    p = str(tmp_path / "cross_proc_undo.json.gz")
    init_b = Bank.create_empty(p)
    init_b.add_sample("hoa", [[0.0, 0.0, 5.0, 0.0]], 5.0)
    init_b.save()

    # Snapshot ban đầu của tiến trình A
    proc_a = Bank(p)

    old_hoa_samples = [dict(s) for s in proc_a.words["hoa"]]

    # Tiến trình A xoá "hoa" và lưu
    time.sleep(0.01)
    proc_a.drop("hoa")
    proc_a.save()

    # Tiến trình B đồng bộ snapshot từ đĩa (thấy 'hoa' đã bị xoá và nạp tombstone)
    proc_b_stale = Bank(p)
    assert "hoa" not in proc_b_stale.words
    assert "words:hoa" in proc_b_stale.d.get("tombstones", {})

    # Tiến trình A bấm HOÀN TÁC (dạy lại 'hoa') và lưu
    time.sleep(0.01)
    for s in old_hoa_samples:
        proc_a.add_sample("hoa", s["s"], s["w"])
    proc_a.save()

    # Tiến trình B (không hề biết A vừa hoàn tác) thêm 'cành' và lưu
    proc_b_stale.add_sample("cành", [[0.0, 0.0, 6.0, 0.0]], 6.0)
    proc_b_stale.save()

    # Kiểm tra trạng thái hợp nhất trên đĩa
    final_bank = Bank(p)
    # Xác định tính an toàn:
    # Nếu 'hoa' không còn trong final_bank, chứng tỏ tombstone tồn dư ở tiến trình cũ đã triệt tiêu hoàn tác!
    # T059 yêu cầu: "nếu không an toàn -> không bật Hoàn tác và báo cáo"
    is_safe = "hoa" in final_bank.words
    # Ghi nhận kết quả đánh giá kỹ thuật chính xác cho T059
    assert is_safe is False, "Đánh giá: Đa tiến trình không an toàn nếu thiếu đồng bộ BroadcastChannel"
    assert "cành" in final_bank.words, "'cành' không được lưu thành công!"


def test_bridge_drop_and_restore_via_teach(tmp_path):
    """Kiểm tra quy trình xoá nhãn và hoàn tác qua BrowserBridge."""
    p = str(tmp_path / "bridge_undo.json.gz")
    bridge = BrowserBridge(bank_path=p)
    bridge.init()

    # Dạy từ "chim"
    sample_stroke = [[(150.0, 170.0), (160.0, 150.0)]]
    bridge.teach_sample("chim", pixel_strokes=sample_stroke, deferred_save=False)

    # Lấy mẫu để lưu vào bộ nhớ hoàn tác UI
    samples_res = bridge.list_label_samples("chim", category="words")
    assert samples_res["ok"] is True
    backup_samples = samples_res["data"]
    assert len(backup_samples) > 0

    # Xoá nhãn "chim"
    drop_res = bridge.drop_label("chim", category="words")
    assert drop_res["ok"] is True

    # Xác nhận nhãn đã biến mất
    words_after_drop = bridge.list_words()["data"]
    assert not any(w[0] == "chim" for w in words_after_drop)

    # Hoàn tác: Dạy lại bằng các nét đã sao lưu
    for s in backup_samples:
        bridge.teach_sample("chim", strokes=s["s"], width=s["w"], category="words", deferred_save=False)

    # Xác nhận nhãn đã phục hồi trọn vẹn
    words_after_restore = bridge.list_words()["data"]
    assert any(w[0] == "chim" for w in words_after_restore)
