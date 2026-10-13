"""Kiểm thử unit cho module chuviettay/model/rng.py (ScopedRNG)."""
from __future__ import annotations

import math
import pytest

from chuviettay.model.rng import ScopedRNG, derive_seed


def test_derive_seed_determinism():
    """Hàm derive_seed phải tất định và phân biệt các khóa khác nhau."""
    s1 = derive_seed(42, "tok", "nay", 0, "variant", 1)
    s2 = derive_seed(42, "tok", "nay", 0, "variant", 1)
    assert s1 == s2
    assert isinstance(s1, int)
    assert s1 > 0

    # Khác khóa -> khác hạt giống
    s3 = derive_seed(42, "tok", "nay", 1, "variant", 1)
    assert s1 != s3

    # Khác master_seed -> khác hạt giống
    s4 = derive_seed(43, "tok", "nay", 0, "variant", 1)
    assert s1 != s4


def test_scoped_rng_methods_determinism():
    """ScopedRNG tạo cùng kết quả cho cùng hạt giống và khóa."""
    rng1 = ScopedRNG(100, "token_key")
    rng2 = ScopedRNG(100, "token_key")

    assert [rng1.random() for _ in range(5)] == [rng2.random() for _ in range(5)]
    assert rng1.uniform(1.0, 10.0) == rng2.uniform(1.0, 10.0)
    assert rng1.randrange(5, 50) == rng2.randrange(5, 50)
    assert rng1.randint(1, 100) == rng2.randint(1, 100)

    seq = ["a", "b", "c", "d"]
    assert rng1.choice(seq) == rng2.choice(seq)
    assert rng1.gauss(0, 1) == rng2.gauss(0, 1)


def test_scoped_rng_errors():
    """ScopedRNG ném đúng ngoại lệ khi dữ liệu đầu vào không hợp lệ."""
    rng = ScopedRNG(42, "err_test")
    with pytest.raises(IndexError):
        rng.choice([])
    with pytest.raises(ValueError):
        rng.randrange(10, 5)


def test_scoped_rng_gauss_distribution():
    """Kiểm tra Box-Muller gauss xấp xỉ phân bố chuẩn N(0, 1)."""
    rng = ScopedRNG(999, "gauss_stats")
    n = 2000
    samples = [rng.gauss(0.0, 1.0) for _ in range(n)]
    mean = sum(samples) / n
    variance = sum((x - mean) ** 2 for x in samples) / (n - 1)

    assert abs(mean) < 0.1  # Kỳ vọng mean ~ 0.0
    assert abs(variance - 1.0) < 0.15  # Kỳ vọng variance ~ 1.0
