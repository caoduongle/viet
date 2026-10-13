# Data Model: Ổn định Dòng kết xuất và Tính tái lập Hạt giống

**Feature**: `037-render-pipeline-seed-stability`  
**Date**: 2026-10-13  
**Status**: Completed  

---

## Thực thể 1: RenderItem (Mục kết xuất trong dòng)

Đại diện cho một phần tử hiển thị (từ, số, ký hiệu, khoảng trống) trong một dòng văn bản hoặc trong một ô bảng biểu. Được truyền xuyên suốt qua các giai đoạn tính toán ngắt dòng, căn lề và sinh nét vẽ.

```python
@dataclass(slots=True)
class RenderItem:
    start: float                          # Tọa độ X tương đối tính từ đầu dòng (px)
    strokes: list[Stroke]                 # Danh sách các nét chữ nguyên thủy
    width: float                          # Chiều rộng chiếm dụng của phần tử (px)
    missing: list[str] = field(default_factory=list)  # Ký tự thiếu mẫu (nếu có)
    token: str = ""                       # Chuỗi văn bản của token gốc
    token_id: str = ""                    # Định danh duy nhất của token trong phiên
    occurrence: int = 0                   # Thứ tự xuất hiện của token này trong khối/tài liệu

    def __iter__(self) -> Iterator[Any]:
        """Hỗ trợ giải nén tuple (unpacking: a, b, c = item)."""
        yield self.start
        yield self.strokes
        yield self.width
        yield self.missing
        yield self.token
        yield self.token_id
        yield self.occurrence

    def __getitem__(self, idx: int) -> Any:
        """Hỗ trợ truy cập chỉ số kiểu tuple để tương thích ngược 100% với mã nguồn cũ."""
        if idx == 0: return self.start
        if idx == 1: return self.strokes
        if idx == 2: return self.width
        if idx == 3: return self.missing
        if idx == 4: return self.token
        if idx == 5: return self.token_id
        if idx == 6: return self.occurrence
        raise IndexError(f"Chỉ số RenderItem không hợp lệ: {idx}")

    def __len__(self) -> int:
        return 7
```

### Các quy tắc kiểm chuẩn
- `width >= 0.0`
- `start >= 0.0`
- `occurrence >= 0`
- Khi `token` có giá trị, `token_id` có dạng `f"{token}#{occurrence}"` hoặc chuỗi phân cấp tương đương.

---

## Thực thể 2: TokenIdentifier (Định danh Token Bền vững)

Cặp khóa định danh logic của một từ/token trong tài liệu, được cấp phát tăng đơn điệu theo thứ tự xuất hiện của từng chuỗi từ trong tài liệu hoặc khối:

```text
TokenIdentifier = tuple[str, int]  # (token_str, occurrence_index)
Ví dụ:
  ("Hôm", 0) -> Token "Hôm" xuất hiện lần đầu tiên
  ("nay", 0) -> Token "nay" xuất hiện lần đầu tiên
  ("trời", 0) -> Token "trời" xuất hiện lần đầu tiên
  ("Hôm", 1) -> Token "Hôm" xuất hiện lần thứ hai
```

### Ứng dụng trong ScopedRNG
- Khóa dẫn xuất hạt giống hình học nét: `ScopedRNG(master_seed, "tok", token_str, occurrence_index, "geom")`
- Khóa dẫn xuất hạt giống khoảng cách từ: `ScopedRNG(master_seed, "wgap", prev_token_str, curr_token_str)`

---

## Thực thể 3: MathRenderContext (Ngữ cảnh Kết xuất Toán học)

Ngữ cảnh cách ly hạt giống ngẫu nhiên dành riêng cho một khối biểu thức toán học hoặc công thức nội dòng (`MathBlock` hoặc `MathInline`).

```python
@dataclass
class MathRenderContext:
    formula_id: str                       # Khóa duy nhất đại diện cho công thức (ví dụ: băm chuỗi LaTeX)
    formula_seed: int                     # Hạt giống con dành riêng cho công thức: ScopedRNG(master_seed, "math", formula_id).seed
    token_counts: dict[str, int] = field(default_factory=dict)  # Bộ đếm cục bộ số lần xuất hiện trong công thức
```

### Vòng đời
1. Khởi tạo khi bắt đầu phân tích và bố cục một công thức toán học (`MathLayoutEngine`).
2. Chia sẻ đồng nhất giữa bước đo thử kích thước (`_scratch()`) và bước vẽ nét thực tế (`layout_lines()`).
3. Độc lập hoàn toàn với bộ đếm token của các đoạn văn bản xung quanh.

---

## Thực thể 4: WriteOptions & WriteResult (Cập nhật)

### WriteOptions
- Bổ sung trường cấu hình: `stable_variants: bool = False`.
- Xác nhận kiểm chuẩn: `seed` nằm trong khoảng $[0, 4294967295]$ hoặc `None`.
- Chế độ `stable_variants=True` được Desktop GUI, CLI và Web Client truyền thống nhất vào `WriteOptions`.

### WriteResult
- Lưu trữ trường `seed_used: int | None`.
- Báo cáo kết xuất `write_report_lines()` tự động định dạng dòng tái tạo:
  `"Seed đã dùng: {seed_used} (chạy lại với --seed {seed_used} để có đúng kết quả này)"` khi `seed_used is not None`.
