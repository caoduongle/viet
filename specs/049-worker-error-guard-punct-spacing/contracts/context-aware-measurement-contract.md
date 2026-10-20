# Contract: Context-Aware Width Measurement

## Context
Hàm đo độ rộng văn bản `Writer.measure_text_width` và bộ bố cục `DocumentLayoutEngine._layout_inlines`.

## Signature
```python
def measure_text_width(
    self,
    text: str,
    scale: float = 1.0,
    context: SeedContext | None = None,
) -> float: ...
```

## Invariant 1: State Mutation Freedom
Lời gọi `measure_text_width` là hàm thuần túy (pure function) đối với trạng thái bên ngoài:
1. `_token_counts` của `Writer` trước và sau lời gọi phải giống hệt nhau.
2. `self.last` và `self._token_last` trước và sau lời gọi phải được phục hồi nguyên vẹn.
3. Trạng thái ngữ cảnh hiện hành (`_current_ctx_type`, `_current_tok`, `_current_k`, `_char_idx`, `_current_context`) phải được phục hồi trong khối `finally`.

## Invariant 2: Context Parity with Rendering
Khi `context` được cung cấp (với `content_type`, `element_id`, `occurrence`):
1. Đối với chuỗi số (`NUMRE.match(text)`), `measure_text_width` chuyển tiếp `context` vào `self.number(nfc_text, k=k_idx, context=context)`.
2. Biến thể chữ số được chọn trong bước đo khớp chính xác với biến thể chữ số được chọn trong bước kết xuất thực tế `Writer.token(text, context=context)`.
3. Sai lệch độ rộng ước lượng và độ rộng kết xuất thực tế:
   $$|\text{est\_w} - \text{actual\_w}| \le 0.05 \cdot xh$$

## Invariant 3: Backward Compatibility
Khi gọi `measure_text_width(text)` hoặc `measure_text_width(text, scale)` không truyền `context`:
- Hàm tự động xử lý với ngữ cảnh mặc định (`context=None`), hoàn toàn tương thích với mọi lời gọi hiện có trong codebase.
