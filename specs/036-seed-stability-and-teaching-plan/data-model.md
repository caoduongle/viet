# Data Model: Seed Stability, Phân trang Bảng và Kế hoạch Dạy chữ

**Feature**: `036-seed-stability-and-teaching-plan`  
**Date**: 2026-10-13  
**Status**: Hoàn thành thiết kế mô hình dữ liệu Phase 1

---

## 1. Mô hình Hạt giống & Cấu hình Kết xuất (Seed & Render Options)

### Entity: `WriteOptions` (Cập nhật kiểm chuẩn)
- **Vị trí**: `chuviettay/controller/results.py`
- **Các trường liên quan**:
  - `seed: int | None = None`: Hạt giống ngẫu nhiên chỉ định bởi người dùng hoặc CLI/Web.
  - `stable_variants: bool = False`: Chế độ giữ ổn định hình thái chữ viết tay qua các lần chỉnh sửa.
- **Quy tắc kiểm chuẩn (`validate()`)**:
  - `seed is None` HOẶC (`isinstance(seed, int)` và `not isinstance(seed, bool)` và `0 <= seed < 2**32`).
  - Vi phạm $\rightarrow$ ném `ValueError` với thông báo tiếng Việt: `"Hạt giống (seed) phải là số nguyên không âm trong khoảng [0, 4294967295] hoặc None."`

### Entity: `WriteResult` (Bổ sung trường kết quả)
- **Vị trí**: `chuviettay/controller/results.py`
- **Trường bổ sung**:
  - `seed_used: int | None = None`: Hạt giống hiệu dụng 32-bit thực tế đã được sử dụng trong suốt phiên kết xuất.
- **Quy tắc gán giá trị**:
  - Luôn được điền giá trị số nguyên trong khoảng $[0, 2^{32}-1]$ ở cả `DocumentLayoutEngine` và `FidelityLayoutEngine`.
  - Mặc định là `None` để bảo đảm tương thích ngược với các đối tượng kết quả khởi tạo thủ công trong kiểm thử cũ.

---

## 2. Mô hình Sinh số ngẫu nhiên Cục bộ (`chuviettay/model/rng.py`)

### Entity: `ScopedRNG`
- **Mục đích**: Cung cấp luồng số ngẫu nhiên tất định, cô lập cho từng phần tử tài liệu khi bật `stable_variants=True`.
- **Cấu trúc trường**:
  - `master_seed: int`: Hạt giống gốc của phiên kết xuất.
  - `context_keys: tuple[Any, ...]`: Bộ khóa định danh ngữ cảnh.
  - `_derived_seed: int`: Số nguyên 64-bit dẫn xuất từ `hashlib.blake2b(digest_size=8)` trên khóa chính tắc phân tách bằng byte `\x00`.
  - `_rnd: random.Random`: Đối tượng sinh ngẫu nhiên CPython chuẩn, khởi tạo bằng `_derived_seed`.
- **Phương thức & Thuật toán**:
  - `random() -> float`: Trả về `self._rnd.random()` trong khoảng $[0.0, 1.0)$.
  - `uniform(a: float, b: float) -> float`: $a + (b - a) \times \text{self.random()}$.
  - `randrange(start: int, stop: int | None = None) -> int`: $\text{start} + \lfloor \text{self.random()} \times (\text{stop} - \text{start}) \rfloor$.
  - `choice(seq: Sequence[T]) -> T`: `seq[self.randrange(len(seq))]`.
  - `gauss(mu: float = 0.0, sigma: float = 1.0) -> float`: Thuật toán Box-Muller biến đổi trực tiếp, hoàn toàn phi trạng thái (stateless), loại bỏ mọi khác biệt thuật toán polar giữa các phiên bản Python.

### Entity: `ContextKey` (Quy ước khóa ngữ cảnh)
- **Cấu trúc khóa theo loại phần tử**:
  1. **Token hình học (`tok`)**:
     `(master_seed, "tok", nfc_text, k, purpose, sub_idx)`
     - `nfc_text`: Chuỗi ký tự Unicode NFC của từ.
     - `k`: Số lần từ này đã xuất hiện trước đó trong tài liệu (bộ đếm tích lũy).
     - `purpose`: Chuỗi mô tả mục đích tiêu thụ ngẫu nhiên (`"variant"`, `"jitter"`, `"dgap"`, `"scale"`, `"rot"`, `"dy"`, `"wscale"`).
     - `sub_idx`: Chỉ số ký tự con trong từ (nếu có).
  2. **Khoảng cách giữa các từ (`wgap`)**:
     `(master_seed, "wgap", prev_tok_text, curr_tok_text, k)`
  3. **Độ lượn sóng của dòng (`line`)**:
     `(master_seed, "line", first_tok_text, line_idx)`
  4. **Viền ô bảng biểu (`tbl_border`)**:
     `(master_seed, "tbl_border", table_idx, start_row, r, c)`
  5. **Công thức toán học inline (`math`)**:
     `(master_seed, "math", latex_str, k)`

---

## 3. Mô hình Hình học Bảng biểu & Cô lập Bố cục

### Entity: `LaidOutCell` (Cập nhật định danh ô)
- **Vị trí**: `chuviettay/layout/table_layout.py`
- **Các trường**:
  - `row: int`: Chỉ số hàng trong lát cắt hiện tại.
  - `col: int`: Chỉ số cột.
  - `x: float`, `y: float`, `width: float`, `height: float`: Tọa độ hình học của ô.
  - `source_cell_id: int`: Định danh duy nhất của ô nguồn sinh bởi bộ đếm tăng đơn điệu của `TableLayoutEngine`.
  - `is_continuation: bool`: Cờ đánh dấu ô là phần tiếp nối của một ô bị tràn từ trang trước.
  - `rendered_lines: list[Any]`: Danh sách các dòng văn bản đã kết xuất.
  - `line_metrics: list[Any]`: Chỉ số hình học tương ứng của từng dòng.
- **Ràng buộc bất biến**:
  - Đối tượng `TableCell` trong `chuviettay/document/ir.py` TUYỆT ĐỐI KHÔNG bị gán trường hay đột biến trạng thái trong quá trình bố cục bảng.

---

## 4. Mô hình Kế hoạch Dạy chữ Cốt lõi (Teaching Plan Core Model)

### Entity: `CORE_ESSENTIALS_38`
- **Vị trí**: `chuviettay/model/seed_words.py`
- **Định nghĩa**:
  - Gồm 33 chữ cái tiếng Việt viết thường (`VIETNAMESE_LOWERCASE`):
    `("a", "ă", "â", "b", "c", "d", "đ", "e", "ê", "g", "h", "i", "k", "l", "m", "n", "o", "ô", "ơ", "p", "q", "r", "s", "t", "u", "ư", "v", "x", "y", "f", "j", "w", "z")`
  - Gồm 5 dấu thanh rời chuẩn hw3 (`TONE_MARKS`):
    `("dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng")`
  - Tổng số lượng: Đúng 38 mục cốt lõi.
- **Tính chất bao phủ**:
  - Tập 38 mục này chứng minh giải mã và ghép được 100% (700/700) các từ trong tập từ điển thông dụng `SEED`.

### Tương quan `Bank.can(w)` và `bank.words`
- **Điều kiện thỏa mãn**:
  1. `w_clean in self.digits or w_clean in self.punct or w_clean in getattr(self, "symbols", {})` $\rightarrow$ `True`.
  2. `w_clean in self.marks and bool(self.marks.get(w_clean))` $\rightarrow$ `True`.
  3. `getattr(self, "words", None) and w_clean in self.words and bool(self.words.get(w_clean))` $\rightarrow$ `True` *(Mới bổ sung: công nhận từ nguyên khối đã dạy)*.
  4. Toàn bộ chữ cái cấu thành có trong `self.letters` và dấu thanh (nếu có) có trong `self.marks` $\rightarrow$ `True`.
  5. Ngược lại $\rightarrow$ `False`.
