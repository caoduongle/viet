"""Kiểm thử tính năng Deletion Tombstones và an toàn đa tiến trình chống hồi sinh từ đã xoá."""
from chuviettay.model.bank import Bank


def test_tombstone_recorded_and_persisted_on_drop(tmp_path):
    """Khi drop(word), từ phải được đưa vào tombstones và lưu bền vững xuống file."""
    p = str(tmp_path / "bank.json.gz")
    b = Bank.create_empty(p)
    b.add_sample("xin", [[0, 0, 5, 0]], 5.0)
    b.add_sample("chao", [[0, 0, 6, 0]], 6.0)
    b.save()

    # Xoá từ "xin"
    removed = b.drop("xin")
    assert removed == 1
    assert "xin" not in b.words
    assert "xin" in b._tombstones
    b.save()

    # Nạp lại từ đĩa ở một tiến trình mới
    reloaded = Bank(p)
    assert "xin" not in reloaded.words
    assert "xin" in reloaded.d.get("tombstones", {})
    assert "chao" in reloaded.words


def test_cross_process_deletion_prevents_resurrection(tmp_path):
    """Tiến trình A xoá 'xin' và lưu; tiến trình B giữ snapshot cũ và thêm 'ba';
    khi B lưu, 'xin' KHÔNG được bị hồi sinh bởi snapshot cũ của B."""
    p = str(tmp_path / "shared.json.gz")
    init_b = Bank.create_empty(p)
    init_b.add_sample("xin", [[0, 0, 5, 0]], 5.0)
    init_b.add_sample("chao", [[0, 0, 6, 0]], 6.0)
    init_b.save()

    # Tiến trình A và B cùng mở kho
    proc_a = Bank(p)
    proc_b = Bank(p)

    # A xoá 'xin' và lưu
    proc_a.drop("xin")
    proc_a.save()

    # B thêm mẫu cho 'chao' (vẫn có 'xin' cũ trong bộ nhớ) rồi lưu
    proc_b.add_sample("chao", [[0, 0, 6.5, 0]], 6.5)
    proc_b.save()

    # Kiểm tra file cuối cùng trên đĩa
    final_b = Bank(p)
    assert "xin" not in final_b.words, "'xin' bị hồi sinh bởi snapshot cũ của tiến trình B!"
    assert len(final_b.words["chao"]) == 2, "Mẫu mới của 'chao' phải được bảo toàn!"


def test_explicit_reteaching_revokes_tombstone(tmp_path):
    """Khi người dùng chủ động dạy lại một từ đã xoá, tombstone phải bị huỷ và từ được phục hồi."""
    p = str(tmp_path / "retech.json.gz")
    b = Bank.create_empty(p)
    b.add_sample("xin", [[0, 0, 5, 0]], 5.0)
    b.save()

    b.drop("xin")
    b.save()
    assert "xin" not in Bank(p).words

    # Dạy lại từ 'xin'
    b.add_sample_incremental("xin", [[0, 0, 5.2, 0]], 5.2)
    assert "xin" not in b._tombstones
    b.save()

    reloaded = Bank(p)
    assert "xin" in reloaded.words
    assert len(reloaded.words["xin"]) == 1
    assert "xin" not in reloaded.d.get("tombstones", {})
