# Contract: Luồng Ngẫu nhiên Cục bộ cho Stable Variants (CTR-036-LOCALIZED-RNG)

**Mã hợp đồng**: `CTR-036-LOCALIZED-RNG`  
**Gói công việc**: WP2 - Ngẫu nhiên cục bộ để stable_variants đúng nghĩa  
**Ngày ban hành**: 2026-10-13  
**Trạng thái**: Ratified (Đã tinh chỉnh sau Engineering Review)

---

## 1. Module `chuviettay/model/rng.py`

### 1.1 Hàm Dẫn xuất Hạt giống Con (`derive_seed`)
```python
def derive_seed(master_seed: int, *keys: Any) -> int:
    """Dẫn xuất một số nguyên 64-bit từ master_seed và chuỗi các khóa ngữ cảnh
    bằng hàm băm chính tắc blake2b với phân tách byte null (\x00)."""
    hasher = hashlib.blake2b(digest_size=8)
    hasher.update(str(master_seed).encode("utf-8"))
    hasher.update(b"\x00")
    for k in keys:
        hasher.update(str(k).encode("utf-8"))
        hasher.update(b"\x00")
    return int.from_bytes(hasher.digest(), "big")
```

### 1.2 Lớp `ScopedRNG`
```python
class ScopedRNG:
    def __init__(self, master_seed: int, *keys: Any):
        self._seed = derive_seed(master_seed, *keys)
        self._rnd = random.Random(self._seed)

    def random(self) -> float:
        return self._rnd.random()

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def randrange(self, start: int, stop: int | None = None) -> int:
        if stop is None:
            stop = start
            start = 0
        n = stop - start
        if n <= 0:
            raise ValueError("empty range")
        return start + int(self.random() * n)

    def choice(self, seq: Sequence[T]) -> T:
        if not seq:
            raise IndexError("cannot choose from an empty sequence")
        return seq[int(self.random() * len(seq))]

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        # Box-Muller biến đổi trực tiếp, hoàn toàn phi trạng thái (stateless)
        u1 = self.random()
        while u1 <= 1e-15:
            u1 = self.random()
        u2 = self.random()
        z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mu + z0 * sigma
```

### 1.3 Tính chất Ràng buộc (Invariants)
1. **Chỉ phụ thuộc `random()`**: Tuyệt đối không gọi các phương thức cấp cao có lưu cache trạng thái của `random.Random` như `self._rnd.gauss()` hay `self._rnd.choice()`.
2. **Tính tất định đa nền tảng**: Đảm bảo 100% bit-exact parity giữa Python 3.10, Python 3.12, Python 3.14 và Pyodide WebAssembly.
3. **Bảo toàn Golden Master khi `stable_variants=False`**:
   - Khi `stable_variants=False`, hệ thống tiếp tục sử dụng luồng tuần tự `self.rnd` hiện tại.
   - Toàn bộ SHA-256 trong `tests/test_golden_master_real_path.py` và `scripts/test_golden_pyodide.mjs` giữ nguyên từng byte.

---

## 2. Giao diện `Writer.token` và Tự Động Đếm Số Lần Xuất Hiện

### 2.1 Đặc tả Phương thức
```python
def token(self, tok: str, k: int | None = None) -> tuple[list[Stroke], float, list[str]]:
```
- Nếu `k is None`:
  Tự động tra cứu và tăng bộ đếm trong `self._token_counts`:
  ```python
  k_idx = self._token_counts.get(tok, 0)
  self._token_counts[tok] = k_idx + 1
  ```
- Nếu `k is not None`:
  Sử dụng trực tiếp `k_idx = k`.
- Điều này cho phép các bài kiểm thử hoặc tầng layout truyền `k` tường minh nếu cần, đồng thời bảo đảm các lệnh gọi `writer.token(t)` đơn lẻ vẫn hoạt động độc lập và hoàn toàn tất định.

---

## 3. Quy ước Khóa Neo Ngữ cảnh (Context Key Convention)

Khi `stable_variants=True`:
1. **Biến thể chữ cái & dấu thanh**:
   `ScopedRNG(master_seed, "tok", text, k_idx, "variant", char_idx)`
2. **Jitter khoảng cách chữ cái (`jitter`)**:
   `ScopedRNG(master_seed, "tok", text, k_idx, "jitter", char_idx)`
3. **Khoảng cách chữ số (`dgap`)**:
   `ScopedRNG(master_seed, "tok", text, k_idx, "dgap", digit_idx)`
4. **Biến thiên hình học nét (scale, rot, dy, wscale)**:
   `ScopedRNG(master_seed, "tok", text, k_idx, "geom", stroke_idx)`
5. **Khoảng cách giữa các từ (`wgap`)**:
   `ScopedRNG(master_seed, "wgap", prev_tok, curr_tok, k_idx)`
6. **Đường lượn sóng và độ nghiêng dòng**:
   `ScopedRNG(master_seed, "line", first_tok_text, line_idx)`
7. **Viền bảng biểu**:
   `ScopedRNG(master_seed, "tbl_border", table_idx, slice_start_row, r, c)`
8. **Công thức toán inline**:
   `ScopedRNG(master_seed, "math", latex_str, k_idx)`

---

## 4. Chống Lặp Biến thể Cục bộ (Token-Local De-duplication)

- Khi `stable_variants=True`:
  Bộ nhớ chống lặp mẫu (`self.last`) chỉ hoạt động trong phạm vi xử lý nội bộ của một token.
  Trước khi xử lý token mới, xóa hoặc cô lập bộ nhớ `self.last`, bảo đảm lựa chọn của token `A` không làm thay đổi biến thể của token `B` đứng sau.
  Đối với từ lặp lại nhiều lần trong tài liệu: vì mỗi lần xuất hiện có $k$ khác nhau, `ScopedRNG` với hạt giống khác nhau sẽ tự nhiên chọn các biến thể phong phú trong kho mà không làm hai lần liên tiếp bị trùng lặp.
