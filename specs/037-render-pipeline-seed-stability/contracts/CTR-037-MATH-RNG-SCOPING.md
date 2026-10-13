# Contract CTR-037-MATH-RNG-SCOPING: Cô lập Ngữ cảnh Hạt giống Toán học và Chữ số

## Mục đích
Quy định nguyên tắc thiết lập ngữ cảnh hạt giống độc lập cho chữ số và các biểu thức toán học, đồng bộ hóa giữa bước đo thử `_scratch()` và bước kết xuất thực tế.

---

## 1. Hợp đồng Xử lý Chữ số trong `Writer.number()`

Khi gọi `Writer.number(s: str, k: int | None = None)`:

```python
def number(self, s: str, k: int | None = None) -> tuple[list[Stroke], float, list[str]]:
    if self.stable_variants:
        if k is None:
            k_idx = self._token_counts.get(s, 0)
            self._token_counts[s] = k_idx + 1
        else:
            k_idx = k
        self._current_tok = s
        self._current_k = k_idx
        self._char_idx = 0
        self.last = {}
    ...
```

- **Tính toán khoảng cách số `_resolve_dgap`**:
  ```python
  if self.stable_variants:
      from chuviettay.model.rng import ScopedRNG
      master_seed = self.seed if self.seed is not None else 0
      rnd = ScopedRNG(master_seed, "tok", self._current_tok, self._current_k, "dgap", digit_idx)
  ```
  Nhờ việc thiết lập `self._current_tok = s` và `self._current_k = k_idx`, `_resolve_dgap()` luôn neo vào chính chuỗi số đang vẽ và thứ tự số trong phiên, không bao giờ kế thừa từ đoạn văn trước.

---

## 2. Hợp đồng Ngữ cảnh Công thức Toán trong `MathLayoutEngine`

1. **Khởi tạo bộ đo thử `_scratch()`**:
   - `_scratch()` phải kế thừa đầy đủ cấu hình từ engine chính, bao gồm hạt giống dẫn xuất của công thức:
   ```python
   def _scratch(self) -> MathLayoutEngine:
       from chuviettay.model.writer import Writer
       w = self.writer
       sw = Writer(
           self.bank,
           self.rnd,
           w.J,
           w.loose,
           w.space,
           stable_variants=w.stable_variants,
           seed=w.seed,
           assemble_letters=w.assemble_letters,
           letter_gap=w.letter_gap,
           pen_clearance_factor=w.pen_clearance_factor,
       )
       # Trong stable_variants=True: sao chép trạng thái _token_counts ban đầu của công thức
       if w.stable_variants:
           sw._token_counts = dict(w._token_counts)
       return MathLayoutEngine(self.bank, S=self.S, writer=sw, rnd=self.rnd, display=self.display)
   ```

2. **Cách ly ngữ cảnh khi render trong `engine.py`**:
   - Khi `render_math_block` hoặc `render_math_inline`:
     - Mỗi công thức sử dụng một instance `MathLayoutEngine` với Writer cục bộ có seed được dẫn xuất riêng:
       `math_seed = ScopedRNG(self.effective_seed, "math", block.latex).seed`
     - Việc xử lý công thức không làm thay đổi biến đếm token của Writer văn bản thường xung quanh.
