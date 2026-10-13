"""
chuviettay -- lõi ứng dụng "Chữ viết tay của bạn" (Web Client duy nhất).

Cấu trúc gói:

    model/       Dữ liệu + thuật toán thuần Python (kho mẫu, ghép nét, RNG, xử lý tệp .xopp).
    controller/  Lớp điều phối nghiệp vụ lõi (AppController, WriteOptions, teach_geometry).
    browser/     Facade cầu nối Web Worker (Pyodide WebAssembly) và AppController.
    document/    Intermediate Representation (IR) chuẩn hóa tài liệu (Paragraph, Table, Math).
    importer/    Bộ phân tích nạp tài liệu (Markdown, DOCX, TXT).
    layout/      Bố cục trang, bảng biểu, công thức toán học và phân trang.
    math/        Phân tích cú pháp AST công thức toán và sinh nét bút viết tay.
    fidelity/    Lõi chế độ khoá bố cục Word (bảo lưu để đưa lên Web ở feature tiếp theo).

    paths.py     Tính đường dẫn mặc định của kho mẫu và log khi chạy cục bộ.
    logging_setup.py  Cấu hình ghi log dự phòng.

Xem README.md ở thư mục gốc để biết chi tiết hướng dẫn chạy bản Web.
"""

__version__ = "2.1.0"
