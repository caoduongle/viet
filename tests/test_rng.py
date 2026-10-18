"""Kiểm thử unit cho module chuviettay/model/rng.py (ScopedRNG)."""
from __future__ import annotations

import math
import pytest

from chuviettay.model.rng import ScopedRNG, SeedContext, derive_seed


def test_seed_context_invariants():
    """Kiểm tra SeedContext bất biến, token_id và to_keys."""
    ctx = SeedContext(content_type="text", element_id="hôm_nay", occurrence=2, purpose="geom", sub_index=0)
    assert ctx.token_id == "text:hôm_nay#2"
    assert ctx.to_keys() == ("text", "hôm_nay", 2, "geom", 0)

    # Thử sửa trường trên dataclass frozen -> phải ném lỗi
    with pytest.raises(Exception):
        ctx.occurrence = 3

    # with_purpose tạo bản sao mới với mục đích khác
    ctx2 = ctx.with_purpose("jitter", sub_index=1)
    assert ctx2.purpose == "jitter"
    assert ctx2.sub_index == 1
    assert ctx2.token_id == ctx.token_id
    assert ctx.purpose == "geom"


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


def test_canonical_key_encoding_vectors():
    """T031: Bộ test vectors cố định cho derive_seed v2:
    - Phân biệt số nguyên 1 vs chuỗi '1'
    - Phân biệt boolean True vs số 1, False vs số 0
    - Phân biệt chuỗi chứa byte null '\x00' vs nhiều khóa tách rời
    - Xử lý an toàn số âm (-1) và số nguyên 64-bit unsigned (>= 2**63) không gây tràn số
    - Chuỗi Unicode dạng dựng sẵn (NFC) và tổ hợp (NFD) sinh cùng một hạt giống chuẩn tắc
    - Hỗ trợ version='v1' tương thích ngược
    """
    import unicodedata
    from chuviettay.model.rng import encode_canonical_key

    # 1. 1 vs "1"
    s_int = derive_seed(42, 1)
    s_str = derive_seed(42, "1")
    assert s_int != s_str
    assert encode_canonical_key(1) != encode_canonical_key("1")

    # 2. True vs 1, False vs 0
    s_bool_true = derive_seed(42, True)
    assert s_bool_true != s_int
    assert encode_canonical_key(True) != encode_canonical_key(1)
    assert derive_seed(42, False) != derive_seed(42, 0)
    assert encode_canonical_key(False) != encode_canonical_key(0)

    # 3. None vs empty string
    assert derive_seed(42, None) != derive_seed(42, "")

    # 4. Chuỗi chứa null byte vs nhiều khóa
    s_embedded_null = derive_seed(42, "a\x00b")
    s_separate_keys = derive_seed(42, "a", "b")
    assert s_embedded_null != s_separate_keys

    # 5. Số âm và số >= 2**63
    s_neg = derive_seed(-1, -999999)
    assert isinstance(s_neg, int) and s_neg > 0
    s_big = derive_seed(2**63 + 12345, 2**64 - 1)
    assert isinstance(s_big, int) and s_big > 0

    # 6. Unicode NFC vs NFD
    s_nfc = unicodedata.normalize("NFC", "tiếng Việt mẫu chữ đẹp")
    s_nfd = unicodedata.normalize("NFD", "tiếng Việt mẫu chữ đẹp")
    assert s_nfc != s_nfd
    assert derive_seed(42, s_nfc) == derive_seed(42, s_nfd)

    # 7. Version 'v1' vs 'v2'
    s_v1 = derive_seed(42, "token", 0, version="v1")
    s_v2 = derive_seed(42, "token", 0, version="v2")
    assert s_v1 != s_v2

    # 8. Type tags theo data-model.md & seed-pipeline-contract.md ('n', '?', 'i', 'f', 's', 'b', 'c', 't')
    from chuviettay.model.rng import SeedContext
    ctx = SeedContext("text", "hôm", 0, "p0", 1)
    assert encode_canonical_key(None).startswith(b"n")
    assert encode_canonical_key(True).startswith(b"?")
    assert encode_canonical_key(1).startswith(b"i")
    assert encode_canonical_key(1.5).startswith(b"f")
    assert encode_canonical_key("abc").startswith(b"s")
    assert encode_canonical_key(b"xyz").startswith(b"b")
    assert encode_canonical_key(ctx).startswith(b"c")
    assert encode_canonical_key((1, 2)).startswith(b"t")
    # Nested tuple vs flat tuple phải khác nhau nhờ mã hóa số phần tử
    assert encode_canonical_key(((1, 2),)) != encode_canonical_key((1, 2))
    assert derive_seed(42, ((1, 2),)) != derive_seed(42, (1, 2))

