# Contract: Vòng đời Hạt giống ngẫu nhiên (CTR-036-SEED-LIFECYCLE)

**Mã hợp đồng**: `CTR-036-SEED-LIFECYCLE`  
**Gói công việc**: WP1 - Seed minh bạch và hợp lệ  
**Ngày ban hành**: 2026-10-13  
**Trạng thái**: Ratified

---

## 1. Giao diện Cấu hình & Kiểm chuẩn

### 1.1 `WriteOptions.validate()`
- **Đặc tả**:
  - `seed` phải là `None` hoặc số nguyên `int` thỏa mãn $0 \le \text{seed} < 2^{32}$.
  - Không chấp nhận kiểu `bool` (`isinstance(seed, bool) == False`).
  - Không chấp nhận số âm, số thực (`float`), hoặc chuỗi (`str`).
- **Ngoại lệ**:
  - Ném `ValueError` với thông báo tiếng Việt: `"Hạt giống (seed) phải là số nguyên không âm trong khoảng [0, 4294967295] hoặc None."`

### 1.2 Xác định Hạt giống Hiệu dụng (Effective Seed)
- **Quy tắc duy nhất tại đầu mỗi lượt viết**:
  ```python
  def resolve_effective_seed(seed: int | None, stable_variants: bool) -> int:
      if seed is not None:
          return seed
      if stable_variants:
          return 0
      return secrets.randbits(32)
  ```
- **Tính bất biến**: Giá trị này được xác định một lần duy nhất tại đầu phương thức kết xuất và sử dụng xuyên suốt toàn bộ quá trình vẽ của tài liệu.

### 1.3 `WriteResult.seed_used`
- Cấu trúc kết quả `WriteResult` bổ sung trường:
  ```python
  seed_used: int | None = None
  ```
- Cả `DocumentLayoutEngine` và `FidelityLayoutEngine` đều gán `result.seed_used = effective_seed`.

---

## 2. Giao diện Dòng lệnh & Người dùng

### 2.1 CLI (`chuviettay/cli.py`)
- Cờ `--seed`: Bổ sung mô tả hướng dẫn trong `--help`:
  `--seed SEED: Hạt giống ngẫu nhiên (số nguyên không âm trong khoảng [0, 4294967295]) để tái tạo kết quả viết tay.`
- Khi người dùng chạy CLI không truyền `--seed`:
  In ra dòng thông báo:
  `"Seed đã dùng: <seed_used> (chạy lại với --seed <seed_used> để có đúng kết quả này)"`

### 2.2 Web Client (`webapp/js/write.js`)
- Tách hàm thuần túy `parseSeed`:
  ```javascript
  function parseSeed(inputVal, currentSeed) {
      if (inputVal === null || inputVal === undefined || inputVal.trim() === '') {
          return { seed: currentSeed, valid: false, message: "Để trống; giữ nguyên seed hiện tại." };
      }
      const num = Number(inputVal.trim());
      if (Number.isInteger(num) && num >= 0 && num <= 4294967295) {
          return { seed: num, valid: true, message: null };
      }
      return { seed: currentSeed, valid: false, message: "Seed không hợp lệ; giữ nguyên seed hiện tại." };
  }
  ```
- Loại bỏ hoàn toàn `parseInt(...) || 42` tại dòng 666. Chấp nhận seed `0` là giá trị hợp lệ.

### 2.3 Bridge (`chuviettay/browser/bridge.py`)
- Khi hàm `write_text` hoặc `write_document` nhận các tùy chọn không được hỗ trợ trong `WriteOptions`:
  - Không âm thầm bỏ qua.
  - Thu thập danh sách `ignored_options: list[str]`.
  - Trả về danh sách này trong từ điển kết quả JSON gửi về cho frontend.
