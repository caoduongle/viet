# Data Model & Artifact Specifications: 021 — Sửa lỗi CI và hoàn thiện Web Client

**Date**: 2026-10-06  
**Feature**: `specs/021-ci-and-web-client-hardening/`

## 1. Data Structures & File Schemas

### 1.1. `scripts/vendor_lock.json`
Thêm mục gói `typing-extensions`:
```json
{
  "packages": {
    "typing-extensions": {
      "version": "4.15.0",
      "file_name": "typing_extensions-4.15.0-py3-none-any.whl",
      "stage": "lazy",
      "url": "https://files.pythonhosted.org/packages/26/9f/ad63fc0248c5379346306f8668cda6e2e2e9c95e01216d2b8ffd9ff037d0/typing_extensions-4.15.0-py3-none-any.whl",
      "sha256": "4fec68770a05408e668a4fa53d6bf4f0f684b9dacf820c7c5d6e97d3ad225e29",
      "size": 74300
    }
  }
}
```

### 1.2. `dist/version.json`
Sinh động từ `scripts/build_web.py`:
```json
{
  "version": "1.0.0",
  "pyodide_version": "314.0.7",
  "build_timestamp": 1728205000,
  "cache_hash": "a1b2c3d4e5f6",
  "components": {
    "chuviettay_zip": "pyodide/chuviettay.zip",
    "runtime": "pyodide/",
    "wheels": "pyodide/wheels/"
  }
}
```

### 1.3. `dist/sw.js` (Generated Template)
```javascript
const CACHE_NAME = "chuviettay-cache-<12_CHAR_HASH>";
const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./version.json",
  ...
];
```

## 2. Directory Structure State

```text
webapp/dist/ (khi chạy mặc định) hoặc <tmp_dist>/ (khi chạy test)
├── css/
│   ├── print.css
│   └── style.css
├── js/
│   ├── app.js
│   ├── bank.js
│   ├── canvas.js
│   ├── export.js
│   ├── i18n.js
│   ├── paper.js
│   ├── storage.js
│   ├── teach.js
│   ├── write.js
│   └── worker/
│       └── py-worker.js
├── pyodide/
│   ├── chuviettay.zip
│   ├── pyodide-lock.json
│   ├── pyodide.asm.wasm
│   ├── pyodide.js
│   ├── pyodide.mjs
│   ├── python_stdlib.zip
│   └── wheels/
│       ├── lxml-...whl
│       ├── markdown_it_py-...whl
│       ├── mdit_py_plugins-...whl
│       ├── mdurl-...whl
│       ├── python_docx-...whl
│       └── typing_extensions-...whl
├── index.html
├── manifest.webmanifest
├── sw.js
└── version.json
```
