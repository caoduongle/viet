"""
Hằng số dùng chung cho toàn bộ ứng dụng.

QUAN TRỌNG: các giá trị dưới đây được giữ NGUYÊN XI từ bản gốc (hw_note.py cũ).
Đừng đổi giá trị nếu không cố ý -- kho mẫu chu_cua_ban.json.gz hiện có được sinh ra
dựa trên đúng các con số này (đơn vị lưới, ngưỡng nhận dấu thanh...). Đổi một trong
số chúng sẽ làm sai lệch cách đọc/ghi các mẫu chữ đã học trước đó.
"""
import re

# ---------------------------------------------------------------- dấu thanh
# 5 dấu thanh tiếng Việt dạng tổ hợp Unicode (huyền, sắc, ngã, hỏi, nặng)
TONES = "\u0300\u0301\u0303\u0309\u0323"
NANG = "\u0323"  # dấu nặng -- xử lý riêng vì nằm DƯỚI chữ thay vì phía trên

# ---------------------------------------------------------------- màu/kích thước dùng khi vẽ file .xopp
GUIDE = "#c8c8c8"      # màu các đường kẻ mốc (không phải nét chữ thật)
MAXH = 3000.0          # chiều cao tối đa một trang .xopp khi viết văn bản dài, quá thì sang trang mới

# thẻ nhận dạng ẩn trong file .xopp, phân biệt "ô đầu tiên là ô đo cỡ tay" hay không
TAG_PLAIN = "hw2"
TAG_CALIB = "hw2c"

# ---------------------------------------------------------------- regex tách token khi viết văn bản
NUMRE = re.compile(r"^-?\d+(?:[.,]\d+)*%?$")
TOKRE = re.compile(r"^([(\[{\"'“‘]*)(.*?)([)\]}\"'”’.,:;!?…]*)$")

# ---------------------------------------------------------------- lưới ô cho file mẫu
# (dùng khi tạo file cho người dùng viết tay từng từ vào từng ô: lệnh "seed"/"check"/
# các từ còn thiếu sau "write", và khi đọc lại các file đó ở bước "learn")
CW, CH, BASE = 128.0, 46.0, 34.0   # kích thước một ô (rộng, cao) + vị trí đường kẻ chân chữ trong ô
COLS, ROWS = 4, 16                  # số cột / số hàng ô trên một trang
MXT, MYT = 36.6, 50.0                # lề trên-trái của lưới ô trong trang
PAGE_W, PAGE_H = 595.276, 841.89     # kích thước trang .xopp (khổ A4, đơn vị pt)
