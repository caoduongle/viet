"""Kịch bản đo hiệu năng đọc/ghi kho mẫu (Bank I/O Benchmark)."""
import os
import tempfile
import time
from chuviettay.model.bank import Bank


def generate_mock_bank(n_words: int, samples_per_word: int = 5) -> Bank:
    fd, path = tempfile.mkstemp(prefix=f"bench_{n_words}_", suffix=".json.gz")
    os.close(fd)
    bank = Bank.create_empty(path)
    mock_stroke = [10.0, 10.0, 15.0, 15.0, 20.0, 10.0]
    for i in range(n_words):
        word = f"word_{i}"
        for s in range(samples_per_word):
            bank.add_sample(word, [mock_stroke], 25.0)
    bank.save()
    return bank


def benchmark_save(bank: Bank, iterations: int = 5) -> float:
    times = []
    mock_stroke = [10.0, 10.0, 15.0, 15.0, 20.0, 10.0]
    for i in range(iterations):
        bank.add_sample("benchmark_word", [mock_stroke], 25.0)
        t0 = time.perf_counter()
        bank.save()
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return sum(times) / len(times)


def main():
    print("=== CHỮ VIẾT TAY: BENCHMARK LƯU KHO MẪU (BANK I/O) ===")
    for n in (100, 300, 700):
        bank = generate_mock_bank(n, samples_per_word=4)
        avg_t = benchmark_save(bank, iterations=3)
        file_size_kb = os.path.getsize(bank.path) / 1024.0
        print(f"Kho {n:4d} từ ({file_size_kb:6.1f} KB): lưu trung bình {avg_t * 1000.0:6.1f} ms")
        if os.path.exists(bank.path):
            os.remove(bank.path)


if __name__ == "__main__":
    main()
