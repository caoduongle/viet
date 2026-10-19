"""Bộ sinh số ngẫu nhiên cục bộ tất định (Scoped RNG).

Phục vụ chế độ stable_variants=True:
- Dẫn xuất hạt giống con (sub-seed) từ (master_seed, *context_keys) bằng hàm băm chính tắc blake2b
  phân tách bằng ký tự null (\\x00).
- Lớp ScopedRNG bọc random.Random(sub_seed) của thư viện chuẩn nhưng CHỈ phụ thuộc vào
  phương thức random.Random.random().
- Tự cài đặt uniform, randrange, choice, randint và gauss (Box-Muller biến đổi trực tiếp, phi trạng thái).
- Phạm vi cam kết tính tái lập:
  * Cam kết 100% bit-exact trong cùng runtime CPython: hai lần chạy với cùng seed và khóa ngữ cảnh
    cho dãy số và kết quả hình học nét chữ hoàn toàn trùng khớp từng byte.
  * Cam kết tương đương phân phối thống kê giữa các nền tảng/runtime khác biệt (ví dụ CPython và Pyodide WASM),
    do hàm gauss() sử dụng Box-Muller (math.log, math.sqrt, math.cos) có thể có sai số dấu phẩy động cực nhỏ
    ở cấp độ FPU/libc giữa các hệ điều hành và kiến trúc phần cứng.
"""
from __future__ import annotations

import hashlib
import math
import random
import secrets
import struct
import unicodedata
from dataclasses import dataclass
from typing import Any, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class SeedContext:
    """Ngữ cảnh hạt giống thống nhất cho một phần tử kết xuất."""
    content_type: str        # "text", "cell", "sym", "math_inline", "math_block", "wgap", "tbl_border"
    element_id: str          # Token string, symbol, latex formula, hoặc table ID
    occurrence: int = 0      # Số lần xuất hiện của (content_type, element_id)
    purpose: str = "variant" # "variant", "geom", "jitter", "dgap"
    sub_index: int = 0       # Chỉ số phụ (ký tự, chữ số, nét)

    @property
    def token_id(self) -> str:
        """Định danh chuỗi chuẩn hóa tương thích với RenderItem và kiểm thử."""
        return f"{self.content_type}:{self.element_id}#{self.occurrence}"

    def with_purpose(self, purpose: str, sub_index: int = 0) -> SeedContext:
        """Tạo bản sao ngữ cảnh với mục đích hoặc chỉ số phụ mới."""
        return SeedContext(
            content_type=self.content_type,
            element_id=self.element_id,
            occurrence=self.occurrence,
            purpose=purpose,
            sub_index=sub_index,
        )

    def to_keys(self) -> tuple[Any, ...]:
        """Chuyển đổi thành tuple khóa dùng cho ScopedRNG hoặc derive_seed."""
        return (self.content_type, self.element_id, self.occurrence, self.purpose, self.sub_index)


def resolve_effective_seed(seed: int | None, stable_variants: bool) -> int:
    """Xác định hạt giống hiệu dụng một lần duy nhất tại đầu mỗi phiên viết
    theo hợp đồng CTR-036-SEED-LIFECYCLE."""
    if seed is not None:
        return seed
    if stable_variants:
        return 0
    return secrets.randbits(32)


def encode_canonical_key(val: Any) -> bytes:
    """Mã hóa một khóa ngữ cảnh thành dạng chuẩn tắc (canonical byte sequence) theo CTR-043-SEED-PIPELINE:
    - 1-byte type tag: 'n' (None), '?' (bool), 'i' (int), 'f' (float), 's' (str), 'b' (bytes), 'c' (SeedContext), 't' (tuple/list)
    - 4-byte big-endian unsigned int length prefix (item count cho tuple/list/SeedContext, byte length cho các kiểu còn lại)
    - Chuỗi byte payload đã chuẩn hóa (NFC cho str, ASCII thập phân cho int chống tràn 64-bit)
    """
    if val is None:
        return b"n\x00\x00\x00\x00"
    if isinstance(val, bool):
        payload = b"\x01" if val else b"\x00"
        return b"?" + struct.pack(">I", 1) + payload
    if isinstance(val, int):
        payload = str(int(val)).encode("ascii")
        return b"i" + struct.pack(">I", len(payload)) + payload
    if isinstance(val, float):
        payload = struct.pack(">d", val)
        return b"f" + struct.pack(">I", len(payload)) + payload
    if isinstance(val, str):
        payload = unicodedata.normalize("NFC", val).encode("utf-8")
        return b"s" + struct.pack(">I", len(payload)) + payload
    if isinstance(val, (bytes, bytearray)):
        payload = bytes(val)
        return b"b" + struct.pack(">I", len(payload)) + payload
    if isinstance(val, SeedContext):
        fields = val.to_keys()
        items_bytes = bytearray()
        for f in fields:
            items_bytes.extend(encode_canonical_key(f))
        return b"c" + struct.pack(">I", len(fields)) + bytes(items_bytes)
    if isinstance(val, (list, tuple)):
        items_bytes = bytearray()
        for item in val:
            items_bytes.extend(encode_canonical_key(item))
        return b"t" + struct.pack(">I", len(val)) + bytes(items_bytes)
    raise TypeError(f"Unsupported key type for canonical encoding: {type(val).__name__}")


def derive_seed(master_seed: int, *keys: Any, version: str = "v2") -> int:
    """Dẫn xuất một số nguyên 64-bit từ master_seed và chuỗi các khóa ngữ cảnh
    bằng hàm băm blake2b.
    - version="v2" (mặc định): Tiền tố domain 'rng-v2\\x00' và mã hóa khóa chuẩn tắc
      encode_canonical_key loại bỏ va chạm khóa và lỗi tràn số nguyên 64-bit.
    - version="v1": Tương thích ngược thuật toán v1 (nối chuỗi phân tách byte null).
    """
    if version == "v1":
        payload = ("%d\x00" % master_seed + "\x00".join(map(str, keys)) + "\x00").encode("utf-8")
        return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")

    buf = bytearray(b"rng-v2\x00")
    buf.extend(encode_canonical_key(master_seed))
    for k in keys:
        buf.extend(encode_canonical_key(k))
    return int.from_bytes(hashlib.blake2b(bytes(buf), digest_size=8).digest(), "big")



class ScopedRNG:
    """Bộ sinh số ngẫu nhiên cục bộ cho một phần tử ngữ cảnh nhất định."""

    __slots__ = ("_seed", "_rnd")

    def __init__(self, master_seed: int, *keys: Any, version: str = "v2") -> None:
        self._seed = derive_seed(master_seed, *keys, version=version)
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
