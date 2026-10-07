# Contract: Web Teach Queue API

**Specification Version**: 1.0.0  
**Feature**: 028-char-first-alignment-and-ci-repair  
**Module**: `webapp/js/teach.js`  

---

## 1. Overview
Hợp đồng này quy định hành vi quản lý hàng đợi học chữ trên Web Client (`TeachTab`), đảm bảo phân định rõ ranh giới giữa luồng nhập văn bản tự do của người dùng và luồng nạp nhãn danh mục có sẵn từ hệ thống.

---

## 2. API Specifications

### 2.1 `addCharactersFromText(text: string): void`
Xử lý văn bản do người dùng gõ vào ô nhập liệu (`#input-teach-add`).
- **Mục đích**: Chuyển hoá từ / câu tự do thành danh sách các ký tự đơn lẻ để người dùng dạy chữ cái.
- **Hành vi**:
  1. Chuẩn hoá chuỗi sang Unicode NFC: `text.normalize("NFC")`.
  2. Bỏ qua các ký tự khoảng trắng (`\s`).
  3. Lặp qua từng ký tự code point: nếu ký tự chưa có trong hàng đợi hiện tại, thêm ký tự đó vào cuối hàng đợi.
  4. Cập nhật giao diện (`refresh()`).

### 2.2 `addCatalogLabels(labels: string[]): void`
Nạp các nhãn nghiệp vụ từ bộ ký tự được chọn trong Modal Bộ Ký Tự (`modal-char-groups`) hoặc phản hồi từ worker (`get_missing_chars`).
- **Mục đích**: Thêm các mục học từ danh mục có sẵn mà KHÔNG làm phân rã các nhãn nghiệp vụ (đặc biệt là 5 dấu thanh rời).
- **Hành vi**:
  1. Với mỗi `label` trong `labels`:
     - Chuẩn hoá chuỗi sang Unicode NFC: `String(label).trim().normalize("NFC")`.
     - Giữ nguyên toàn bộ chuỗi làm một mục nguyên tử (atomic item), ví dụ: `"dấu sắc"`, `"dấu huyền"`.
     - Nếu `label` chưa có trong hàng đợi, đưa vào cuối hàng đợi.
  2. Cập nhật giao diện (`refresh()`).

### 2.3 `loadQueue(items: string[], isCatalog: boolean = false): void`
Phương thức nạp hàng đợi tổng quát:
- Nếu `isCatalog === true`: Chuyển tiếp tới logic của `addCatalogLabels(items)`.
- Nếu `isCatalog === false`: Chuyển tiếp tới logic của `addCharactersFromText(items.join(""))`.

---

## 3. Danh Mục Dấu Thanh Chuẩn (Standard Tone Marks Catalog)

Khi nhóm `dau_thanh` được chọn, backend trả về đúng 5 token sau và Web Client giữ nguyên vẹn 100%:
1. `"dấu huyền"` $\to$ tương ứng với mã `\u0300`
2. `"dấu sắc"` $\to$ tương ứng với mã `\u0301`
3. `"dấu hỏi"` $\to$ tương ứng với mã `\u0309`
4. `"dấu ngã"` $\to$ tương ứng với mã `\u0303`
5. `"dấu nặng"` $\to$ tương ứng với mã `\u0323`
