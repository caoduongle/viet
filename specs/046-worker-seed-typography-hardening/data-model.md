# Data Model & State Transitions: Worker Resilience, Seed Integrity & Typography Hardening

**Feature**: `046-worker-seed-typography-hardening`  
**Date**: 2026-10-20

## 1. Entities & Structural Models

### `WorkerRecoverySession` (Client-Side State)
Mô hình hóa phiên phục hồi của Web Worker, đảm bảo tính tất định và chống rò rỉ Promise khi thế hệ thay đổi.

```typescript
interface WorkerRecoverySession {
  generation: number;            // Thế hệ Worker tương ứng với phiên phục hồi
  resolve: (success: boolean) => void; // Hàm giải quyết Promise của recoverWorker
  timer: NodeJS.Timeout | number | null; // Bộ đếm thời gian bao bọc toàn bộ chu trình phục hồi
  startTime: number;             // Dấu thời gian bắt đầu phục hồi
}
```

**Vòng đời & Chuyển đổi trạng thái (State Machine)**:
```
[Idle] 
  │
  ▼ (recoverWorker() gọi)
[Recovering: generation = N]
  ├── (Timeout vượt quá timeoutMs) ──► terminate Worker ──► resolve(false) ──► [Idle]
  ├── (recoverWorker() gọi lần nữa) ──► terminate old Worker ──► resolve(false) ──► [Recovering: generation = N+1]
  ├── (Worker READY -> onWorkerReady hoàn tất) ──► resolve(true) ──► [Idle]
  └── (Worker ERROR hoặc onWorkerReady lỗi) ──► resolve(false) ──► [Idle]
```

---

### `UiListenerRegistry` (DOM Binding Safety)
Quản lý việc đăng ký và dọn dẹp các bộ lắng nghe sự kiện DOM có thể hủy (abortable listeners).

```typescript
interface UiListenerRegistry {
  controller: AbortController | null;
  isAttached: boolean;
  attach(signal: AbortSignal): void;
  teardown(): void; // Gọi controller.abort() và dọn dẹp cờ
}
```

---

### `IsolatedSeedContext` (Document IR & Layout)
Cấu trúc ngữ cảnh hạt giống đảm bảo phân định rõ ràng giữa các loại khối và vị trí phân đoạn.

```python
@dataclass(frozen=True, slots=True)
class SeedContext:
    content_type: str        # "text", "heading", "cell", "sym", "math_inline", "math_block"
    element_id: str          # Token string, symbol, formula
    occurrence: int = 0      # Thứ tự xuất hiện trong phạm vi content_type
    purpose: str = "variant" # "variant", "geom", "jitter", "dgap"
    sub_index: int = 0       # Vị trí ký tự hoặc phân đoạn chunk

    @property
    def token_id(self) -> str:
        """Định danh cơ sở cho biến thể mẫu chữ."""
        return f"{self.content_type}:{self.element_id}#{self.occurrence}"

    @property
    def render_id(self) -> str:
        """Định danh hình học duy nhất bao gồm chỉ số phân đoạn chunk."""
        return f"{self.content_type}:{self.element_id}#{self.occurrence}:{self.sub_index}"
```

---

### `RobustDigitModel` (Typography & Geometry)
Mô hình chuẩn hóa kích thước chữ số và khoảng cách quang học chịu lỗi cao.

```python
@dataclass
class RobustDigitModel:
    char: str
    raw_height: float
    target_height: float     # 1.20 * xh
    scale_y: float           # Hệ số co giãn dọc
    scale_x: float           # Hệ số co giãn ngang
    is_fallback: bool        # True nếu mẫu dị biệt cực đoan kích hoạt vector fallback
    advance_width: float     # Độ rộng tiến sau chuẩn hóa
```

**Quy tắc chuẩn hóa co giãn chữ số (`Writer._normalize_digit_sample`)**:
1. Chiều cao thô: `sample_h = raw_max_y - raw_min_y`.
2. Kiểm tra điều kiện cực đoan:
   - Nếu `sample_h < 0.35 * xh` hoặc `sample_h > 3.0 * xh`:
     Kích hoạt `get_vector_glyph_fallback(ch, xh=eff_xh)`, trả về nét vector chuẩn lining `1.20 * xh`.
   - Ngược lại:
     `scale_y = clamp(target_h / sample_h, 0.30, 2.85)`
     `scale_x = clamp(scale_y ** 0.5, 0.70, 1.35)`.
3. Căn chỉnh đường cơ sở:
   `dy = -raw_max_y * scale_y` (hoặc tâm dọc `y = -0.45 * xh` cho dấu `-`).

---

## 2. Invariant Rules

| Rule ID | Tiêu chuẩn bất biến | Phạm vi kiểm tra |
| :--- | :--- | :--- |
| **INV-REC-001** | `isRecovering` luôn trả về `false` trong thời gian `<= timeoutMs` | Toàn bộ các nhánh thoát của `recoverWorker()` |
| **INV-DOM-001** | Số lượng event listener trên các nút bấm chính không bao giờ vượt quá 1 | DOM elements sau nhiều lần khởi tạo thất bại / thử lại |
| **INV-SEED-001** | `Heading` luôn sở hữu `content_type="heading"` độc lập với `Paragraph` | `align_document_seeds` và `render_paragraph_inlines` |
| **INV-SEED-002** | `MathBlock` trong ô bảng bảo toàn `occurrence` và `stable_id` khi đổi sang `MathInline` | Bố cục bảng trong `engine.py` |
| **INV-SEED-003** | Các chunk trong token dài có `render_id` phân biệt theo `sub_index` | `RenderItem` và tính khoảng cách từ `wgap` |
| **INV-TYPO-001** | Mọi chữ số (kể cả mẫu cực đoan) hiển thị trong dải `[1.05 * xh, 1.30 * xh]` | Kết xuất qua `Writer.number()` và `Writer.token()` |
| **INV-TYPO-002** | Khoảng cách sau dấu âm ở đầu số đạt `0.05 * xh .. 0.12 * xh` | Chuỗi số âm dạng `-25`, `-0,39` |
| **INV-TYPO-003** | Độ lệch độ rộng giữa `measure_text_width()` và `number()` cho số `<= 0.05 * xh` | Mọi chuỗi số nguyên và số thập phân |
