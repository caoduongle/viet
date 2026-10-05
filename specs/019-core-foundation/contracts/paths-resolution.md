# Contract: File System Path Resolution

**Scope**: `chuviettay/paths.py`, `chuviettay/cli.py`  

## 1. Directory Resolution Functions

Module `chuviettay.paths` exposes:

```python
def app_base_dir() -> str:
    """Thư mục gốc của ứng dụng (nơi chứa script hoặc file thực thi)."""

def user_data_dir() -> str:
    """Thư mục lưu trữ dữ liệu người dùng chuẩn theo hệ điều hành:
    - Windows: %APPDATA%/chuviettay
    - macOS:   ~/Library/Application Support/chuviettay
    - Linux:   $XDG_DATA_HOME/chuviettay (mặc định ~/.local/share/chuviettay)
    """

def user_log_dir() -> str:
    """Thư mục ghi log người dùng chuẩn theo hệ điều hành."""

def default_bank_path() -> str:
    """Đường dẫn kho mẫu mặc định (chu_cua_ban.json.gz):
    1. Trả về app_base_dir()/chu_cua_ban.json.gz nếu file ĐÃ TỒN TẠI (chế độ portable).
    2. Ngược lại, trả về user_data_dir()/chu_cua_ban.json.gz (chế độ cài đặt tiêu chuẩn).
    """
```

## 2. Invariants & Guarantees

- **No Third-Party Dependencies**: Resolution is implemented strictly with Python standard library (`os`, `sys`, `pathlib`).
- **Directory Creation**: Resolvers do not implicitly create empty files, but `user_data_dir()` guarantees parent directory existence before write operations.
- **Portability Preservation**: Placing `chu_cua_ban.json.gz` alongside `hw_note.py` or `hw_gui.exe` always overrides user data directory paths.
