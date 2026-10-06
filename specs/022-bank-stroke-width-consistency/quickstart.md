# Quickstart & Verification Guide: Bank Stroke Width Consistency

## Scenario: Xác minh Nét Chữ Số "2" Giữ Được Độ Thanh Mảnh trong Kho Mẫu

### 1. Khởi động Web Client Local

```bash
# Build lại mã nguồn dist
py -3.10 scripts/build_web.py

# Khởi chạy server kiểm thử
node scripts/serve.mjs
```

### 2. Kịch bản xác minh thủ công

1. Mở trình duyệt tại `http://localhost:8000`.
2. Vào tab **Dạy chữ**:
   - Nhập từ `2` vào ô hàng đợi, bấm **Thêm**.
   - Chọn độ dày nét: **Nét mảnh** (`1.5`).
   - Vẽ chữ số `2` trên Canvas.
   - Bấm **Lưu & tiếp theo**.
3. Chuyển sang tab **Kho mẫu**:
   - Tìm kiếm nhãn `2` trong danh sách.
   - Quan sát hình thu nhỏ thẻ `bank-card`: Nét chữ số `2` thanh mảnh, tỷ lệ cân đối giữa thẻ.
   - Bấm vào thẻ để mở modal **Chi tiết nhãn**:
   - Quan sát ô **Mẫu #1**: Nét chữ số `2` sắc nét, độ dày nét tương đồng với lúc vẽ trên Canvas (không bị phình to đen kịt).

### 3. Kịch bản kiểm thử tự động (Playwright E2E)

Chạy kịch bản kiểm thử E2E:

```bash
npx playwright test tests/e2e/bank.spec.ts
```

Khẳng định thuộc tính `vector-effect="non-scaling-stroke"` và `stroke-width` của phần tử polyline trong `#modal-label-samples-grid .sample-item-thumb svg polyline`.
