# Contract: Web-Only DOCX Import Boundary and Fidelity Deprecation

**Contract ID**: `CTR-039-DOCX-BOUNDARY`  
**Status**: Enforced  
**Applies to**: `webapp/`, `chuviettay/browser/bridge.py`, `chuviettay/fidelity/`, `README.md`

---

## 1. Mục đích

Hợp đồng này phân định ranh giới chức năng rõ ràng cho tính năng xử lý tệp `.docx` trong môi trường Web Client (chạy tĩnh trên trình duyệt), đồng thời quy định quy chế lưu trữ đối với module `chuviettay/fidelity/`.

---

## 2. Ranh giới Web Client (Client-Side Import Boundary)

1. **Phạm vi hỗ trợ (Supported Scope)**:
   - Web Client hỗ trợ nạp tệp `.docx` theo phương thức **Content-First Import**: trích xuất cấu trúc ngữ nghĩa gồm các đoạn văn bản (Paragraphs), tiêu đề (Headings), bảng dữ liệu (Tables) và công thức toán học (OMML / Math Equations), sau đó chuyển thành định dạng soạn thảo Markdown.
   - Tài liệu sau khi nhập sẽ được dàn trang viết tay theo khổ giấy và phông chữ của ứng dụng thông qua `DocumentLayoutEngine`.

2. **Phạm vi không hỗ trợ (Unsupported Scope)**:
   - Web Client **tuyệt đối không hỗ trợ** và **không cam kết** giữ nguyên toạ độ không gian, vị trí tương đối của hình ảnh hoặc bố cục in cố định (Fidelity Layout) của Microsoft Word.

3. **Giao tiếp người dùng (UX Guarantees)**:
   - Giao diện người dùng Web khi mở tệp DOCX phải thể hiện rõ thông điệp nhập nội dung chuyển đổi sang Markdown.
   - Tài liệu giới thiệu sản phẩm (`README.md`) không được quảng bá tính năng giữ nguyên bố cục Word trên Web Client tĩnh.

---

## 3. Quy chế Lưu trữ Module `chuviettay/fidelity/` (Legacy Status)

1. Module `chuviettay/fidelity/` được phân loại là **Mã nguồn lưu trữ (Archived / Legacy Code)**.
2. Tệp `chuviettay/fidelity/__init__.py` phải có ghi chú cảnh báo rõ ràng: module chỉ có thể thực thi trong môi trường cục bộ có cài đặt Microsoft Word COM hoặc LibreOffice; không được đóng gói và không chạy được trên Web Client / Pyodide.
3. Script `scripts/build_web.py` tiếp tục loại bỏ hoàn toàn `chuviettay/fidelity/` khỏi gói Web.
