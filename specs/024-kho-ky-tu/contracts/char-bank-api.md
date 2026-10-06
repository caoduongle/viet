# Contract: Char Bank & Grid Import API

**Feature**: `specs/024-kho-ky-tu`

---

## 1. Controller & Bridge Contract

### 1.1. `AppController`
Lớp điều phối trung tâm giữa UI (Desktop & Web Worker) và Domain Model:

```python
class AppController:
    def import_grid(self, xopp_content_or_path: Union[str, bytes]) -> GridImportResult:
        """Nạp file lưới .xopp vào kho mẫu hiện tại. Idempotent.
        
        Args:
            xopp_content_or_path: Đường dẫn file (trên desktop/cli) hoặc bytes/str (trên web)
        Returns:
            GridImportResult chứa thống kê chi tiết kết quả nạp.
        """
        ...

    def get_char_catalog(self, group_id: str = "co_ban") -> List[str]:
        """Lấy danh sách ký tự theo nhóm danh mục chuẩn."""
        ...

    def get_missing_chars(self, group_id: str = "co_ban") -> List[str]:
        """Lấy danh sách các ký tự trong nhóm còn thiếu trong kho hiện tại."""
        ...

    def teach_char(self, label: str, strokes: List[List[Tuple[float, float]]]) -> bool:
        """Dạy một ký tự đơn vào kho hiện tại (thay thế teach_letter và teach_word)."""
        ...
```

### 1.2. `browser/bridge.py`
Endpoints dành cho Web Client (Pyodide Worker):

```python
def handle_bridge_call(action: str, payload: dict) -> dict:
    # 1. import_grid:
    # payload: {"file_bytes": ...} hoặc {"file_base64": ...}
    # return: {"success": True, "result": asdict(grid_import_result)}
    
    # 2. get_char_catalog:
    # payload: {"group": "co_ban"}
    # return: {"success": True, "chars": [...]}
    
    # 3. get_missing_chars:
    # payload: {"group": "co_ban"}
    # return: {"success": True, "missing": [...]}
    
    # 4. teach_char:
    # payload: {"label": "a", "strokes": [...]}
    # return: {"success": True}
```

---

## 2. CLI Contract

### 2.1. Lệnh `grid` (sinh file lưới)
```bash
# Sinh lưới tập viết theo bộ ký tự chuẩn:
python -m chuviettay.cli grid --set co_ban -o luoi_co_ban.xopp
python -m chuviettay.cli grid --set toan_hy_lap -o luoi_toan.xopp
python -m chuviettay.cli grid --set day_du -o luoi_full.xopp

# Tuỳ chọn sinh thêm các cụm từ cũ (chỉ dành cho tương thích ngược nếu cần):
python -m chuviettay.cli grid --set co_ban --with-clusters -o luoi_legacy.xopp
```

### 2.2. Lệnh `learn` (nạp file lưới vào kho)
```bash
# Nạp file lưới người dùng đã viết vào kho mẫu:
python -m chuviettay.cli learn --grid luoi_da_viet.xopp -k kho_mau.json.gz

# Đầu ra console:
# === KẾT QUẢ NẠP LƯỚI ===
# Tổng số ô quét: 140
# Ô có nét viết: 138
# Mẫu mới thêm: 135
# Mẫu trùng: 3
# Ô bỏ qua (cụm nhiều chữ): 0
# Ô trống: 2
# Đã cập nhật x-height kho: 16.50 pt
```

---

## 3. Web UI Event Contract (`webapp/js`)

### 3.1. Tab "Dạy chữ" (`teach.js`)
- Xóa nút "Từ thông dụng…".
- Đổi nút "Bộ tối thiểu" thành menu/dialog "Bộ ký tự…":
  - Chọn bộ: "Cơ bản (chữ, số, dấu)", "Toán học & Hy Lạp", "Mở rộng", "Tất cả".
  - Thao tác: "Nạp các ký tự còn thiếu vào hàng đợi dạy".
- Nút "Nạp file lưới (.xopp)…":
  - Mở file picker chọn file `.xopp`.
  - Gửi tới Worker thực thi `import_grid`.
  - Hiển thị modal tóm tắt `GridImportResult`.

### 3.2. Tab "Kho mẫu" (`bank.js`)
- Bỏ danh mục "Từ nguyên khối (`words`)".
- Chỉ hiển thị và quản lý các tab: "Chữ cái", "Chữ số", "Dấu câu", "Ký hiệu", "Dấu thanh".
