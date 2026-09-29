"""Kiểm thử tương tranh đa tiến trình (multi-process) thực sự giữa các process OS độc lập.
Kiểm tra FileLock, merge_bank_dicts, và chống tranh chấp giữa add và drop trên Windows và POSIX.
"""
import multiprocessing as mp
import time

from chuviettay.model.bank import Bank


# Module-level worker functions (bắt buộc cho cơ chế 'spawn' trên Windows)
def _worker_concurrent_save(path: str, worker_id: int, num_words: int, barrier, queue):
    try:
        barrier.wait(timeout=15.0)
        bank = Bank(path)
        for i in range(num_words):
            word = f"w_{worker_id}_{i}"
            bank.add_sample(word, [[0.0, 0.0, float(i + 1), 0.0]], float(i + 1))
        bank.save()
        queue.put(("OK", worker_id, None))
    except Exception as e:  # noqa: BLE001
        queue.put(("ERR", worker_id, str(e)))


def _worker_delete(path: str, word: str, barrier, queue):
    try:
        bank = Bank(path)
        barrier.wait(timeout=15.0)
        bank.drop(word)
        bank.save()
        queue.put(("OK", "delete", None))
    except Exception as e:  # noqa: BLE001
        queue.put(("ERR", "delete", str(e)))


def _worker_add_stale(path: str, word: str, barrier, queue):
    try:
        bank = Bank(path)
        barrier.wait(timeout=15.0)
        # Nghỉ nhẹ 0.15s để bảo đảm worker_delete đã hoàn tất save trước
        time.sleep(0.15)
        bank.add_sample(word, [[0.0, 0.0, 99.0, 0.0]], 99.0)
        bank.save()
        queue.put(("OK", "add_stale", None))
    except Exception as e:  # noqa: BLE001
        queue.put(("ERR", "add_stale", str(e)))


def test_multiprocess_concurrent_writes_integrity(tmp_path):
    """Nhiều tiến trình OS độc lập cùng ghi vào 1 file kho mẫu qua FileLock;
    không bị hỏng file và không làm mất cập nhật của tiến trình khác."""
    p = str(tmp_path / "shared_mp.json.gz")
    init_b = Bank.create_empty(p)
    init_b.add_sample("goc", [[0.0, 0.0, 5.0, 0.0]], 5.0)
    init_b.save()

    num_workers = 3
    words_per_worker = 5
    barrier = mp.Barrier(num_workers)
    queue = mp.Queue()

    processes = []
    for wid in range(num_workers):
        proc = mp.Process(
            target=_worker_concurrent_save,
            args=(p, wid, words_per_worker, barrier, queue),
        )
        processes.append(proc)
        proc.start()

    results = []
    for _ in range(num_workers):
        results.append(queue.get(timeout=30.0))

    for proc in processes:
        proc.join(timeout=5.0)
        if proc.is_alive():
            proc.terminate()

    # Tất cả workers đều phải thành công
    for status, wid, err in results:
        assert status == "OK", f"Worker {wid} thất bại: {err}"

    # Nạp lại và kiểm tra toàn vẹn
    final_bank = Bank(p)
    assert "goc" in final_bank.words
    for wid in range(num_workers):
        for i in range(words_per_worker):
            expected_word = f"w_{wid}_{i}"
            assert expected_word in final_bank.words, f"Mất từ {expected_word} sau khi chạy đa tiến trình!"


def test_multiprocess_delete_vs_stale_add_race(tmp_path):
    """Tiến trình 1 xoá từ 'target' và lưu.
    Tiến trình 2 đã nạp snapshot có 'target' trước đó, thêm mẫu cho 'target' rồi lưu.
    Tombstone của Tiến trình 1 phải chiến thắng: 'target' vẫn bị xoá trên đĩa."""
    p = str(tmp_path / "race_mp.json.gz")
    init_b = Bank.create_empty(p)
    init_b.add_sample("target", [[0.0, 0.0, 5.0, 0.0]], 5.0)
    init_b.add_sample("safe", [[0.0, 0.0, 6.0, 0.0]], 6.0)
    init_b.save()

    barrier = mp.Barrier(2)
    queue = mp.Queue()

    p_del = mp.Process(target=_worker_delete, args=(p, "target", barrier, queue))
    p_add = mp.Process(target=_worker_add_stale, args=(p, "target", barrier, queue))

    p_del.start()
    p_add.start()

    res1 = queue.get(timeout=30.0)
    res2 = queue.get(timeout=30.0)

    p_del.join(timeout=5.0)
    p_add.join(timeout=5.0)
    if p_del.is_alive():
        p_del.terminate()
    if p_add.is_alive():
        p_add.terminate()

    assert res1[0] == "OK", f"Lỗi {res1[1]}: {res1[2]}"
    assert res2[0] == "OK", f"Lỗi {res2[1]}: {res2[2]}"

    final_bank = Bank(p)
    assert "safe" in final_bank.words
    assert "target" not in final_bank.words, "'target' bị hồi sinh bởi snapshot cũ trong multiprocess race!"
    assert "target" in final_bank.d.get("tombstones", {}), "Tombstone của 'target' bị mất sau multiprocess race!"
