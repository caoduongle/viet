#!/usr/bin/env bash
# Chạy trên Linux hoặc macOS, trong thư mục có hw_gui.py + thư mục chuviettay/.
# Cần Python 3 có tkinter (Linux: sudo apt install python3-tk).
set -e
cd "$(dirname "$0")"

# Nếu đang ở bản đầy đủ (có thư mục tests/) và đã cài pytest thì chạy kiểm thử trước khi đóng gói:
# test đỏ thì dừng luôn, khỏi đóng gói ra một file .exe lỗi.
if [ -d tests ] && python3 -c "import pytest" 2>/dev/null; then
    echo "Đang chạy bộ kiểm thử trước khi đóng gói..."
    python3 -m pytest -q
fi

pip3 install --user pyinstaller
python3 -m PyInstaller --noconfirm --onefile --windowed --name hw_gui hw_gui.py
echo
echo "============================================================"
echo "Xong! File thực thi nằm ở dist/hw_gui"
echo "Copy dist/hw_gui ra một thư mục riêng, để CẠNH nó file"
echo "chu_cua_ban.json.gz -- rồi chạy: ./hw_gui"
echo "(kho mẫu và file log chuviettay.log cũng nằm cạnh file này)"
echo "============================================================"
