# Contract: Render Static Site Deployment Blueprint

**Status**: Defined  
**Version**: 1.0.0  
**Target Platform**: Render Static Site (via `render.yaml`)

---

## 1. Bản thiết kế Blueprint (`render.yaml`)

```yaml
services:
  - type: web
    runtime: static
    name: chuviettay-web
    branch: main
    buildCommand: "npm ci && python scripts/build_web.py"
    staticPublishPath: "./webapp/dist"
    pullRequestPreviewsEnabled: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.5
      - key: NODE_VERSION
        value: 24.16.0
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    headers:
      # File tĩnh có băm tên (content hashed) -> cache vĩnh viễn 1 năm
      - path: /assets/*
        name: Cache-Control
        value: public, max-age=31536000, immutable
      - path: /pyodide/*
        name: Cache-Control
        value: public, max-age=31536000, immutable
      
      # Entrypoints và Manifest -> không cache để nhận bản cập nhật ngay lập tức
      - path: /index.html
        name: Cache-Control
        value: no-cache, no-store, must-revalidate
      - path: /sw.js
        name: Cache-Control
        value: no-cache, no-store, must-revalidate
      - path: /version.json
        name: Cache-Control
        value: no-cache, no-store, must-revalidate
      - path: /manifest.webmanifest
        name: Cache-Control
        value: no-cache, no-store, must-revalidate

      # Header bảo mật toàn trang
      - path: /*
        name: X-Content-Type-Options
        value: nosniff
      - path: /*
        name: Referrer-Policy
        value: strict-origin-when-cross-origin
      - path: /*
        name: Content-Security-Policy
        value: "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; worker-src 'self'; connect-src 'self'; font-src 'self';"
```

> [!NOTE]
> - `repo`: Không gán cứng URL repository trong file `render.yaml` vì Render tự động liên kết với kho lưu trữ khi kết nối qua dashboard hoặc Blueprint.
> - `buildCommand`: Chạy `npm ci` trước để cài đặt gói `pyodide` và các công cụ đóng gói theo `package-lock.json`, sau đó chạy `python scripts/build_web.py` để trích xuất file Pyodide và đóng gói mã nguồn sang `webapp/dist`.
> - `pullRequestPreviewsEnabled`: Dùng `pullRequestPreviewsEnabled: true` theo đúng chuẩn Render Blueprint hiện hành cho Static Site (hoặc cấu trúc `previews.generation: automatic` nếu dùng định dạng YAML schema mới).
> - `worker-src`: Thiết lập nghiêm ngặt `'self'`. Chỉ nới lỏng thêm `blob:` nếu kết quả đo lường và kiểm thử thực tế trên browser yêu cầu tạo worker từ blob URL.

---

## 2. Tiêu chuẩn Đóng gói bản Build (`scripts/build_web.py`)

Bản build xuất ra tại `webapp/dist` phải tuân thủ nghiêm ngặt các quy tắc:
1. **Lọc sạch mã Desktop/CLI/Test**:
   - Thư mục `webapp/dist` KHÔNG ĐƯỢC CHỨA bất kỳ file nào có định dạng: `*.json.gz` (kho mẫu thật), `tests/`, `specs/`, `docs/`, `.git/`, `chuviettay/view/`, `chuviettay/gui.py`, `chuviettay/cli.py`, `chuviettay/fidelity/`.
   - CI sẽ chạy bước kiểm tra và FAIL ngay lập tức nếu phát hiện các file vi phạm.
2. **Vendor Wheels đầy đủ**:
   - `markdown-it-py` (v4.2.0), `mdit-py-plugins` (v0.6.1), `mdurl` (v0.1.2) nằm trong `webapp/dist/pyodide/wheels/`.
   - `lxml` (v6.1.3 wasm wheel) và `python-docx` được lưu sẵn để nạp lười.
3. **Content Hashing**:
   - Mọi file JS/CSS trong `assets/` đều có hậu tố hash (ví dụ: `app.a1b2c3d4.js`).
   - Tạo file `webapp/dist/version.json` chứa:
     ```json
     {
       "version": "1.0.0",
       "git_commit": "e517636",
       "build_timestamp": 1728192000,
       "pyodide_version": "314.0.7"
     }
     ```
