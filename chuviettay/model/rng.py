"""Bộ sinh số ngẫu nhiên cục bộ tất định (Scoped RNG).

Phục vụ chế độ stable_variants=True:
- Dẫn xuất hạt giống con (sub-seed) từ (master_seed, *context_keys) bằng hàm băm chính tắc blake2b
  phân tách bằng ký tự null (\\x00).
- Lớp ScopedRNG bọc random.Random(sub_seed) của thư viện chuẩn nhưng CHỈ phụ thuộc vào
  phương thức random.Random.random().
- Tự cài đặt uniform, randrange, choice, randint và gauss (Box-Muller biến đổi trực tiếp, phi trạng thái).
- Bảo đảm tính tất định 100% bit-exact giữa các phiên bản Python (3.10+, 3.12, 3.14) và Pyodide WASM.
"""
from __future__ import annotations

import hashlib
import math
import random
from typing import Any, Sequence, TypeVar

T = TypeVar("T")


def derive_seed(master_seed: int, *keys: Any) -> int:
    """Dẫn xuất một số nguyên 64-bit từ master_seed và chuỗi các khóa ngữ cảnh
    bằng hàm băm chính tắc blake2b với phân tách byte null (\\x00)."""
    hasher = hashlib.blake2b(digest_size=8)
    hasher.update(str(master_seed).encode("utf-8"))
    hasher.update(b"\x00")
    for k in keys:
        hasher.update(str(k).encode("utf-8"))
        hasher.update(b"\x00")
    return int.from_bytes(hasher.digest(), "big")


class ScopedRNG:
    """Bộ sinh số ngẫu nhiên cục bộ cho một phần tử ngữ cảnh nhất định."""

    __slots__ = ("_seed", "_rnd")

    def __init__(self, master_seed: int, *keys: Any) -> None:
        self._seed = derive_seed(master_seed, *keys)
        self._rnd = random.Random(self._seed)

    @property
    def seed(self) -> int:
        """Hạt giống con đã dẫn xuất."""
        return self._seed

    def random(self) -> float:
        """Sinh số thực ngẫu nhiên trong khoảng [0.0, 1.0)."""
        return self._rnd.random()

    def uniform(self, a: float, b: float) -> float:
        """Sinh số thực ngẫu nhiên phân bố đều trong khoảng [a, b]."""
        return a + (b - a) * self.random()

    def randrange(self, start: int, stop: int | None = None) -> int:
        """Sinh số nguyên ngẫu nhiên trong dải range(start, stop)."""
        if stop is None:
            stop = start
            start = 0
        n = stop - start
        if n <= 0:
            raise ValueError("empty range")
        return start + int(self.random() * n)

    def randint(self, a: int, b: int) -> int:
        """Sinh số nguyên ngẫu nhiên trong khoảng [a, b]."""
        return self.randrange(a, b + 1)

    def choice(self, seq: Sequence[T]) -> T:
        """Chọn ngẫu nhiên một phần tử từ chuỗi seq."""
        if not seq:
            raise IndexError("cannot choose from an empty sequence")
        return seq[int(self.random() * len(seq))]

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Sinh số thực phân bố chuẩn N(mu, sigma^2) sử dụng thuật toán Box-Muller trực tiếp.
        Thuật toán hoàn toàn phi trạng thái (stateless), tiêu thụ đúng 2 giá trị random() mỗi lần gọi,
        loại bỏ sự khác biệt thuật toán polar có cache trạng thái giữa các bản CPython.
        """
        u1 = self.random()
        while u1 <= 1e-15:
            u1 = self.random()
        u2 = self.random()
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mu + z0 * sigma
