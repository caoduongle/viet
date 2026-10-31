# Quickstart Validation Guide: Hoàn thiện Đối chiếu Hạt giống Đa bước, Đồng bộ Phiên bản Kho mẫu và Khắc phục Kiểm thử E2E (068-seed-bank-e2e-hardening)

Tài liệu này hướng dẫn cách thiết lập môi trường, thực thi các kịch bản kiểm thử độc lập và kiểm chứng các mục tiêu thành công của tính năng `068-seed-bank-e2e-hardening`.

---

## 1. Chuẩn bị môi trường & Điều kiện tiên quyết

- **Hệ điều hành**: Windows 11 / Linux / macOS.
- **Python**: Phiên bản 3.10 trở lên đã cài đặt các phụ thuộc trong `requirements.txt`.
- **Node.js**: Phiên bản 18+ đã cài đặt `@playwright/test` cho bộ kiểm thử E2E.
- **Thư mục làm việc**: Gốc repository `d:\viet\app`.

Kiểm tra trạng thái môi trường:
```powershell
python --version
npm --version
npx playwright --version
```

---

## 2. Kịch bản kiểm chứng 1: Đối chiếu hạt giống với tiền tố ngắn và từ lặp (P1 - SC-001)

### Mục tiêu
Xác nhận thuật toán `align_document_seeds` không bị lỗi chồng lấn hậu tố lên tiền tố ngắn ($p < 3$) khi có từ lặp ở đầu và cuối câu (ví dụ `"là là đi học"` $\to$ `"là là mới là đi học"`).

### Lệnh thực thi
```powershell
pytest tests/test_stable_variants.py -k "prefix_overlap or short_prefix" -v
```

### Kỳ vọng (Expected Outcome)
- Hai từ `"là"` đầu tiên giữ nguyên hoàn toàn `occurrence` gốc (`0` và `1`).
- Cụm từ `"đi học"` ở cuối giữ nguyên `occurrence` gốc.
- Từ `"là"` mới được chèn ở giữa nhận `occurrence = 2` (không đè lên 0 hoặc 1).
- Kiểm tra hình thái nét chữ của kết quả kết xuất: sai lệch hình học $\le 0.02$ pt.

---

## 3. Kịch bản kiểm chứng 2: Bảo toàn biến thể qua chuỗi nhiều lượt chỉnh sửa liên tiếp (P1 - SC-001)

### Mục tiêu
Xác nhận qua chuỗi thao tác $D_0 \to D_1 \to D_2 \to D_3$, hàm `extract_doc_elements` đọc và bảo toàn `token_occurrences` đã gắn từ lượt trước, không đánh số lại từ 0, và luồng `AppController.write_document` tự động căn chỉnh hạt giống giữa các lần gọi liên tiếp khi bật `stable_variants=True`.

### Lệnh thực thi
```powershell
pytest tests/test_stable_variants.py -k "multi_step or consecutive_edits" -v
```

### Kỳ vọng (Expected Outcome)
- Các token kế thừa từ $D_0$ và $D_1$ giữ nguyên `token_occurrences` ban đầu sau khi tiếp tục chèn thêm văn bản ở $D_2$.
- Không có hiện tượng chữ cũ bị đổi kiểu nét (biến thể) khi gõ thêm câu chữ mới.

---

## 4. Kịch bản kiểm chứng 3: Bộ kiểm thử Playwright E2E trên trình duyệt (P1 - SC-002)

### Mục tiêu
Xác nhận sửa lỗi `ReferenceError: currentProfileId` trong `bank.js`, đưa toàn bộ 19 bài kiểm thử E2E (trong đó có 6 bài kiểm thử từng bị lỗi: `bank.spec.ts`, `grid-import.spec.ts`, `multitab.spec.ts`, `offline.spec.ts`) về trạng thái PASS 100%.

### Lệnh thực thi
```powershell
# Chạy toàn bộ 19 bài test E2E Playwright với máy chủ cục bộ
npx playwright test
```

Hoặc chạy riêng các file bị ảnh hưởng:
```powershell
npx playwright test tests/e2e/bank.spec.ts tests/e2e/grid-import.spec.ts tests/e2e/multitab.spec.ts tests/e2e/offline.spec.ts
```

### Kỳ vọng (Expected Outcome)
- Toàn bộ 19 bài kiểm thử E2E kết thúc thành công: `19 passed`.
- Bảng điều khiển Console của trình duyệt không ghi nhận bất kỳ `ReferenceError` hoặc `TypeError` nào.
- Dòng tóm tắt kho mẫu `#bank-summary` hiển thị số lượng chữ cái và mẫu nét chuẩn xác ngay sau khi nạp kho.

---

## 5. Kịch bản kiểm chứng 4: Tính nguyên tử bản chụp kho mẫu & An toàn DOM (P2 - SC-003)

### Mục tiêu
Xác nhận `get_bank_snapshot` trả về lỗi tường minh khi một danh mục con bị lỗi (không trả về mảng rỗng giả mạo) và `showBankErrorBanner` triệt tiêu nguy cơ chèn mã đánh dấu HTML độc hại.

### Lệnh thực thi
```powershell
pytest tests/test_browser_bridge.py -k "bank_snapshot" -v
npx playwright test tests/e2e/bank.spec.ts -g "error banner"
```

### Kỳ vọng (Expected Outcome)
- Khi mô phỏng `list_letters` bị lỗi, `get_bank_snapshot` trả về `{"ok": False, "error": ...}`.
- Thông điệp lỗi chứa thẻ HTML (ví dụ `<img src=x onerror=...>`) hiển thị nguyên bản dạng chuỗi ký tự trên UI, không sinh ra phần tử DOM hay thực thi mã script.

---

## 6. Kịch bản kiểm chứng 5: Đo kiểm hiệu năng bản chụp kho mẫu lớn (P3 - SC-004)

### Mục tiêu
Xác nhận tốc độ trích xuất bản chụp kho mẫu với quy mô từ 1.000 nhãn trở lên hoàn tất trong thời gian dưới 200ms.

### Lệnh thực thi
```powershell
pytest tests/test_performance_regression.py -k "bank_snapshot_large_scale" -v -s
```

### Kỳ vọng (Expected Outcome)
- Kiểm thử nạp 1.000+ nhãn đa dạng danh mục và gọi `get_bank_snapshot()`.
- Kết quả `res["ok"] is True`, số lượng nhãn $\ge 1.000$, thời gian thực thi $t < 200$ ms.

---

## 7. Toàn bộ quy trình kiểm chứng hồi quy (Full Regression Verification)

Trước khi đóng tính năng, chạy kiểm thử toàn diện cả Python và Web E2E:
```powershell
# 1. Bộ kiểm thử Python toàn diện (>1410 tests)
pytest

# 2. Bộ kiểm thử E2E Playwright (20 tests)
npx playwright test
```
Tất cả các kiểm thử phải đạt trạng thái xanh (ALL PASS).

---

## 8. Bảng ghi nhận kết quả kiểm chứng thực tế (Verification Record)

| Kịch bản kiểm chứng | Lệnh thực thi | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Kịch bản 1 & 2** (Seed Alignment & Multi-step) | `pytest tests/test_stable_variants.py` | 26 passed in 2.15s (Bảo toàn 100% token_occurrences và hình thái nét vẽ) | ✅ PASS |
| **Kịch bản 3** (Playwright E2E Web Client) | `npx playwright test` | 20 passed in 3.0m (Không có ReferenceError, toàn bộ kịch bản E2E xanh) | ✅ PASS |
| **Kịch bản 4** (Atomic Snapshot & XSS Protection) | `pytest tests/test_bridge.py` & `npx playwright test tests/e2e/bank.spec.ts` | 15 passed in bridge.py, 2 passed in bank.spec.ts (DOM API chống chèn script) | ✅ PASS |
| **Kịch bản 5** (Large-scale Bank Performance) | `pytest tests/test_performance_regression.py -k "large_scale"` | 1 passed in 1.69 ms (Ngưỡng yêu cầu < 200 ms, biên độ an toàn > 100x) | ✅ PASS |
| **Hồi quy toàn diện Python** | `pytest` | 1426 passed | ✅ PASS |

