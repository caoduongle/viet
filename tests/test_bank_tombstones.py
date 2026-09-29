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


def test_stale_snapshot_sample_addition_does_not_resurrect_deleted_word(tmp_path):
    """Kịch bản chạy đua:
    T0: Cả A và B cùng mở kho có 'foo' (mẫu S0).
    T1: A xoá 'foo' và lưu -> 'foo' biến mất, tombstone ghi nhận vào đĩa.
    T2: B (chưa hề biết 'foo' bị xoá trên đĩa) thêm mẫu S1 vào 'foo' rồi lưu.
    Kết quả: Khi B hợp nhất với đĩa, mẫu của B xuất phát từ snapshot cũ trước T1,
    nên 'foo' KHÔNG được hồi sinh trên đĩa và tombstone của 'foo' phải được giữ nguyên."""
    p = str(tmp_path / "stale_race.json.gz")
    init_b = Bank.create_empty(p)
    init_b.add_sample("foo", [[0, 0, 5, 0]], 5.0)
    init_b.save()

    # T0: Cả A và B nạp kho có 'foo'
    proc_a = Bank(p)
    proc_b = Bank(p)

    # T1: A xoá 'foo' và lưu
    proc_a.drop("foo")
    proc_a.save()

    # T2: B dùng snapshot cũ thêm mẫu mới cho 'foo' rồi lưu
    proc_b.add_sample("foo", [[0, 0, 5.5, 0]], 5.5)
    proc_b.save()

    # Kiểm tra trạng thái trên đĩa
    final_bank = Bank(p)
    assert "foo" not in final_bank.words, "'foo' đã bị hồi sinh bởi snapshot cũ của B!"
    assert "foo" in final_bank.d.get("tombstones", {}), "Tombstone của 'foo' bị xoá trái phép!"


def test_tombstones_dict_aliasing_preserved_after_merge(tmp_path):
    """Kiểm tra tính đồng nhất đối tượng (object identity) của _tombstones và d['tombstones']:
    Sau khi Bank.save() kích hoạt merge_bank_dicts, self._tombstones và self.d['tombstones']
    phải trỏ tới cùng một dictionary trong bộ nhớ."""
    p = str(tmp_path / "aliasing.json.gz")
    b1 = Bank.create_empty(p)
    b1.add_sample("xin", [[0, 0, 5, 0]], 5.0)
    b1.save()

    b2 = Bank(p)
    # Tiến trình 1 xoá 'xin' và lưu
    b1.drop("xin")
    b1.save()

    # Tiến trình 2 lưu một thay đổi khác -> kích hoạt merge_bank_dicts
    b2.add_sample("chao", [[0, 0, 6, 0]], 6.0)
    b2.save()

    # Sau khi save/merge, b2._tombstones PHẢI là b2.d["tombstones"]
    assert b2._tombstones is b2.d["tombstones"], "_tombstones và d['tombstones'] bị phân tách sau merge!"

    # Thử gọi drop() trên b2 và kiểm tra xem d['tombstones'] có nhận được ngay lập tức không
    b2.drop("chao")
    assert "chao" in b2.d["tombstones"], "Đột biến _tombstones sau merge không phản ánh vào d['tombstones']!"
