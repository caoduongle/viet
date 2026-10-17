# Contract: Atomic Offline Service Worker Cache

**Location**: `specs/042-sync-concurrency-worker-recovery/contracts/offline-cache-contract.md`  
**Target Module**: `webapp/sw.js` & `scripts/build_web.py`

---

## 1. Precache Resource Separation & Naming Compatibility

### Core Assets (`PRECACHE_URLS`)
Giữ nguyên tên hằng số `PRECACHE_URLS` để tương thích 100% với `scripts/build_web.py` và các bài kiểm thử hiện có, nhưng **chỉ chứa các tài nguyên cốt lõi bắt buộc** lúc khởi động:
- Shell: `./`, `./index.html`, `./manifest.webmanifest`, `./version.json`
- CSS: `./css/style.css`, `./css/print.css`
- Core JavaScript: `./js/app.js`, `./js/bank.js`, `./js/canvas.js`, `./js/export.js`, `./js/i18n.js`, `./js/paper.js`, `./js/storage.js`, `./js/teach.js`, `./js/write.js`, `./js/worker/py-worker.js`
- Pyodide Runtime & Core Packages:
  - `./pyodide/pyodide.js`
  - `./pyodide/pyodide.mjs`
  - `./pyodide/pyodide.asm.js`
  - `./pyodide/pyodide.asm.mjs`
  - `./pyodide/pyodide.asm.wasm`
  - `./pyodide/python_stdlib.zip`
  - `./pyodide/pyodide-lock.json`
  - `./pyodide/chuviettay.zip`
- Startup Markdown Wheels (`stage == "startup"` trong `scripts/vendor_lock.json`):
  - `./pyodide/wheels/mdurl-0.1.2-py3-none-any.whl`
  - `./pyodide/wheels/mdit_py_plugins-0.6.1-py3-none-any.whl`
  - `./pyodide/wheels/markdown_it_py-4.2.0-py3-none-any.whl`

### Lazy Optional Assets (`OPTIONAL_LAZY_URLS`)
Tài nguyên nạp lười theo nhu cầu (`stage == "lazy"` trong `scripts/vendor_lock.json`), tách riêng vào hằng số `OPTIONAL_LAZY_URLS` và **không** nằm trong `PRECACHE_URLS`:
- `./pyodide/wheels/python_docx-1.1.2-py3-none-any.whl`
- `./pyodide/wheels/lxml-6.1.3-cp314-cp314-pyemscripten_2026_0_wasm32.whl`
- `./pyodide/wheels/typing_extensions-4.15.0-py3-none-any.whl`

### Build Script Integration (`scripts/build_web.py`)
- `generate_sw_js(dist_dir)`:
  - Tính mã băm tổng hợp 12 ký tự (`content_hash_12`) trên **toàn bộ** các tệp trong `dist_dir` (bao gồm cả core và lazy wheels) để tạo `CACHE_NAME = f"chuviettay-cache-{content_hash_12}"`.
  - Đọc danh sách wheel có `"stage": "lazy"` từ `scripts/vendor_lock.json`:
    - Các tệp thuộc nhóm lazy wheel được đưa vào `OPTIONAL_LAZY_URLS`.
    - Các tệp còn lại được đưa vào `PRECACHE_URLS`.

---

## 2. Atomic Install Lifecycle Contract

### Install Event Protocol
```javascript
self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      try {
        // 1. Fetch và xác thực toàn bộ PRECACHE_URLS trong bộ nhớ TRƯỚC khi chạm vào CacheStorage
        const entries = await Promise.all(
          PRECACHE_URLS.map(async (url) => {
            const resp = await fetch(url, { cache: "no-cache" });
            if (!resp || !resp.ok) {
              throw new Error(
                `[SW] Không thể nạp tài nguyên bắt buộc lúc install: ${url} (status: ${resp?.status})`
              );
            }
            return { url, resp: resp.clone() };
          })
        );

        // 2. Chỉ mở cache và ghi khi TẤT CẢ các tệp bắt buộc đã tải thành công 100%
        const cache = await caches.open(CACHE_NAME);
        await Promise.all(entries.map(({ url, resp }) => cache.put(url, resp)));

        // 3. Chỉ gọi skipWaiting() bên trong waitUntil sau khi cache mới đã hoàn tất nguyên tử
        await self.skipWaiting();
      } catch (err) {
        console.error("[SW Install Error] Hủy bỏ cài đặt cache dở dang:", err);
        await caches.delete(CACHE_NAME);
        throw err;
      }
    })()
  );
});
```

### Runtime Fetch Event Protocol
- Với `version.json`: Network-First, fallback sang cache khi offline.
- Với mọi tài nguyên tĩnh khác (bao gồm cả `PRECACHE_URLS` và `OPTIONAL_LAZY_URLS` khi người dùng nhập DOCX): Cache-First; nếu chưa có trong cache thì fetch từ mạng, kiểm tra `networkResponse.status === 200`, clone và lưu vào `CACHE_NAME`.
