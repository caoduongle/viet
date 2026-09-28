"""Lớp View: giao diện Tkinter. Đây là nơi DUY NHẤT trong dự án được import tkinter.

Quy tắc:
  - View chỉ nói chuyện với AppController (controller/app_controller.py): gọi phương
    thức của Controller, hiển thị kết quả trả về. KHÔNG tự thao tác thẳng vào Bank,
    Writer hay bất kỳ thứ gì trong model/ (bản gốc làm vậy ở nhiều chỗ, ví dụ
    `bank.words.pop(...)`, `bank.rebuild()`, `bank.save()` ngay trong hàm xử lý nút bấm).
  - Các tab KHÔNG tự gọi nhau. Việc phối hợp giữa các tab (ví dụ "Dạy các từ này →" chuyển
    từ tab Viết chữ sang tab Dạy từ mới) do MainWindow làm trung gian, qua callback.
  - Mọi lỗi bắt được đều đi qua dialogs.report_error() để ghi traceback đầy đủ vào file
    log TRƯỚC khi hiện hộp thoại -- không còn cảnh chỉ thấy đúng một dòng str(e).
"""
