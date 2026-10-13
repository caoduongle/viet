# Data Model: Chuyển sang sản phẩm chỉ có Web — Loại bỏ ứng dụng Desktop & CLI

**Feature**: `038-web-only-remove-desktop`  
**Date**: 2026-10-13  
**Status**: Hoàn thành  

---

## 1. Thực thể còn hiệu lực (Active Entities)

### 1.1. Tệp kho mẫu cá nhân (Personal Bank File)
Tệp nén JSON (`.json.gz`) lưu trữ toàn bộ dữ liệu mẫu chữ viết tay được dạy bởi người dùng. Đây là thực thể dữ liệu trung tâm và là cầu nối duy nhất để người dùng Desktop cũ mang toàn bộ dữ liệu mẫu sang Web Client.

- **Định dạng vật lý**: Tệp nén Gzip chứa chuỗi JSON UTF-8.
- **Phiên bản Schema**: v3 (hỗ trợ tương thích ngược schema v1, v2 thông qua `Bank._migrate_from_older_schema`).
- **Cấu trúc trường dữ liệu chính**:
  ```json
  {
    "schema_version": 3,
    "xh": 7.0,
    "wgaps": [11.0],
    "dgaps": [3.5],
    "line": 24.0,
    "x0": 78.0,
    "width": 500.0,
    "ratio": 6.6,
    "pen": {
      "tool": "pen",
      "color": "#000000ff",
      "width": "1.41",
      "capStyle": "round"
    },
    "letters": {
      "a": [
        { "w": 6.5, "s": [[[0.0, 0.0], [5.0, -3.0], [6.5, 0.0]]], "T": "", "vi": -1, "ti": -1, "ts": 1728000000.0 }
      ]
    },
    "marks": {},
    "digits": {},
    "punct": {},
    "symbols": {},
    "words": {},
    "tombstones": {}
  }
  ```
- **Quy tắc kiểm định (Validation Rules)**:
  - Phải có `schema_version` hợp lệ hoặc cấu trúc tương thích v1/v2 tự động nâng cấp lên v3.
  - Tọa độ nét `s` phải là danh sách các nét bút, mỗi nét là chuỗi các điểm float `[x, y]` hợp lệ.
  - Phải nạp được an toàn trong môi trường WebAssembly / Pyodide (bộ nhớ ảo IndexedDB / Virtual FS).
- **Vòng đời & Lưu trữ trên Web**:
  - Lưu trữ trực tiếp trong `IndexedDB` của trình duyệt dưới key `active_bank`.
  - Có thể xuất ra tệp máy tính bất kỳ lúc nào qua nút "Sao lưu kho mẫu (.json.gz)".
  - Có thể nhập từ tệp máy tính bất kỳ lúc nào qua nút "Nhập kho mẫu (.json.gz)".

---

### 1.2. Cấu trúc dữ liệu yêu cầu & phản hồi Web Bridge (Bridge Data Structures)

Cấu trúc dữ liệu trao đổi giữa giao diện người dùng Web (JavaScript / Web Worker) và tầng xử lý Python WASM (`BrowserBridge`).

#### `WriteOptionsPayload` (JavaScript Object -> Python `WriteOptions`)
```typescript
interface WriteOptionsPayload {
  seed?: number;              // Hạt giống RNG (0 - 4294967295)
  stable_variants?: boolean;  // Bật/tắt chế độ kiểu chữ ổn định khi chỉnh sửa
  scale?: number;             // Hệ số co giãn cỡ chữ (mặc định 1.0)
  line?: number;              // Khoảng cách dòng (mặc định 24.0)
  width?: number;             // Độ dày nét bút (mặc định 1.0)
  color?: string;             // Mã màu hex 8 ký tự (ví dụ "#000000ff")
  paper_size?: string;        // Khổ giấy ("A4", "Letter", v.v.)
  bg_style?: string;          // Kiểu nền giấy ("grid", "lined", "blank")
}
```

#### `WriteResultPayload` (Python `WriteResult` -> JavaScript Object)
```typescript
interface WriteResultPayload {
  ok: boolean;
  xopp_bytes?: string;        // Base64-encoded file .xopp đã tạo
  n_lines: number;            // Số dòng văn bản
  n_strokes: number;          // Tổng số nét bút
  n_tokens: number;           // Tổng số từ/ký tự cần viết
  n_missing_tokens: number;   // Số từ/ký tự thiếu mẫu nét
  missing_tokens: string[];   // Danh sách từ/ký tự thiếu
  assembled_words: string[];  // Danh sách từ được ghép từ chữ cái đơn
  warnings: string[];         // Cảnh báo bố cục (tràn bảng, tràn lề giấy)
  seed_used: number;          // Hạt giống hiệu dụng đã sử dụng
  error?: string;             // Thông báo lỗi nếu ok === false
  error_type?: string;        // Loại ngoại lệ Python nếu có lỗi
}
```

#### `BankStatsPayload` (Python `BankStats` -> JavaScript Object)
```typescript
interface BankStatsPayload {
  ok: boolean;
  n_samples: number;          // Tổng số mẫu nét
  n_letters: number;          // Số chữ cái đơn lẻ có mẫu
  letter_counts: Record<string, number>;
  digit_counts: Record<string, number>;
  punct_counts: Record<string, number>;
  tone_mark_counts: Record<string, number>;
  n_words: number;            // Số mẫu từ nguyên khối cũ (legacy)
  error?: string;
}
```

---

## 2. Thực thể đã gỡ bỏ (Retired / Removed Entities)

Các thực thể sau đã ngừng hoạt động và bị xóa hoàn toàn khỏi mô hình dữ liệu của kho mã:

| Thực thể trước đây | Module gốc | Lý do gỡ bỏ | Thay thế tương đương trên Web |
|---|---|---|---|
| `AppWindow` | `chuviettay.view.app_window` | Desktop Tkinter window | Giao diện HTML5 / CSS3 SPA trong `webapp/` |
| `WriteTab`, `TeachTab`, `BankTab` | `chuviettay.view.*` | Tkinter tabs | Tabs DOM (`#tab-write`, `#tab-teach`, `#tab-bank`) |
| `WordCanvas` | `chuviettay.view.word_canvas` | Tkinter Canvas vẽ nét | HTML5 `<canvas id="teach-canvas">` + Pointer Events |
| `ThemeConfig` | `chuviettay.view.theme` | Tkinter color palettes | Biến CSS (`--bg-primary`, `--text-primary`, v.v.) trong `webapp/css/style.css` |
| `UserConfigFile` | `paths.user_config_path` | Tệp `user_config.json` | Web `localStorage` (`theme_preference`) |
| `CLIParser` | `chuviettay.cli` | Điểm vào argparse dòng lệnh | Không cần thiết; mọi thao tác thực hiện trực tiếp trên Web |
| `HWExecutable` | `hw_gui.exe`, `hw_gui.spec` | Tệp nhị phân PyInstaller | PWA cài đặt offline trực tiếp từ trình duyệt (Service Worker) |
