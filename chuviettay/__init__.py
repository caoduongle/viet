"""
chuviettay -- lõi ứng dụng "Chữ viết tay của bạn".

Cấu trúc gói (kiến trúc MVC):

    model/       Dữ liệu + thuật toán thuần Python, KHÔNG import tkinter/argparse.
                 (kho mẫu, thuật toán ghép nét, đọc/ghi file .xopp, tiện ích chữ Việt)
    controller/  Lớp điều phối giữa Model và giao diện (CLI hoặc GUI). Nhận yêu cầu
                 dạng dữ liệu thuần (str, số, dataclass), gọi Model, trả kết quả dạng
                 dataclass -- không phụ thuộc tkinter, không argparse, không print().
    view/        Giao diện Tkinter (các tab, canvas vẽ, cửa sổ chính). CHỈ được gọi
                 xuống Controller, không tự ý thao tác thẳng vào Model (Bank, Writer...).

    cli.py       Điểm vào dòng lệnh (argparse) -- lớp mỏng, dịch tham số dòng lệnh
                 thành lời gọi Controller rồi in kết quả ra màn hình.
    gui.py       Điểm vào giao diện (Tkinter) -- dựng Controller + MainWindow, chạy
                 mainloop().
    paths.py     Tính đường dẫn mặc định của kho mẫu (xử lý cả trường hợp đã đóng gói
                 thành .exe bằng PyInstaller).
    logging_setup.py  Cấu hình ghi log ra file, dùng chung cho cả CLI lẫn GUI, để khi
                 có lỗi (kể cả bản .exe không có cửa sổ console) vẫn xem lại được.

Xem README.md ở thư mục gốc để biết chi tiết + hướng dẫn chạy/kiểm thử.
"""

__version__ = "2.0.0"
