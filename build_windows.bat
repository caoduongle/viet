@echo off
REM Chay file nay tren WINDOWS, trong thu muc co hw_gui.py + thu muc chuviettay.
REM Can da cai Python (tick "Add python.exe to PATH" luc cai) - tai o python.org.
cd /d "%~dp0"

echo Dang cai PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo LOI: khong cai duoc PyInstaller. Kiem tra da cai Python + pip chua.
    pause
    exit /b 1
)

echo.
echo Dang dong goi thanh hw_gui.exe...
pyinstaller --noconfirm --onefile --windowed --name hw_gui hw_gui.py
if errorlevel 1 (
    echo LOI: dong goi that bai. Kiem tra thu muc chuviettay co nam CANH hw_gui.py khong.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Xong! File hw_gui.exe nam trong thu muc "dist".
echo Copy hw_gui.exe ra mot thu muc rieng, de CANH no file
echo chu_cua_ban.json.gz (kho mau chu cua ban) - roi bam doi
echo chuot vao hw_gui.exe la chay, khong can cai Python nua.
echo (File log chuviettay.log cung nam canh hw_gui.exe.)
echo ============================================================
pause
