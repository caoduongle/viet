/**
 * sw.js -- Service Worker phục vụ ứng dụng ngoại tuyến (Offline-first / PWA).
 * Tuân thủ nghiêm ngặt User Story 6 và tiêu chuẩn Zero Remote CDN.
 */

const CACHE_NAME = "chuviettay-cache-v1";

const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./version.json",
  "./css/style.css",
  "./css/print.css",
  "./js/app.js",
  "./js/bank.js",
  "./js/canvas.js",
  "./js/export.js",
  "./js/i18n.js",
  "./js/paper.js",
  "./js/storage.js",
  "./js/teach.js",
  "./js/write.js",
  "./js/worker/py-worker.js",
  "./pyodide/pyodide.js",
  "./pyodide/pyodide.mjs",
  "./pyodide/pyodide.asm.js",
  "./pyodide/pyodide.asm.mjs",
  "./pyodide/pyodide.asm.wasm",
  "./pyodide/python_stdlib.zip",
  "./pyodide/pyodide-lock.json",
  "./pyodide/chuviettay.zip",
  "./pyodide/wheels/mdurl-0.1.2-py3-none-any.whl",
  "./pyodide/wheels/mdit_py_plugins-0.6.1-py3-none-any.whl",
  "./pyodide/wheels/markdown_it_py-4.2.0-py3-none-any.whl",
  "./pyodide/wheels/python_docx-1.1.2-py3-none-any.whl",
  "./pyodide/wheels/lxml-6.1.3-cp314-cp314-pyemscripten_2026_0_wasm32.whl",
];

// 1. Cài đặt Service Worker và nạp trước toàn bộ tài nguyên (B5: bắt buộc thành công)
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // Dùng Promise.all để fail fast nếu bất kỳ core asset nào lỗi
      await Promise.all(
        PRECACHE_URLS.map(async (url) => {
          const resp = await fetch(url, { cache: "no-cache" });
          if (!resp || !resp.ok) {
            throw new Error(`[SW] Không thể nạp tài nguyên bắt buộc lúc install: ${url} (status: ${resp?.status})`);
          }
          await cache.put(url, resp);
        })
      );
    })
  );
  self.skipWaiting();
});

// 2. Kích hoạt và dọn dẹp các phiên bản cache cũ
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log(`[SW] Đang dọn dẹp cache cũ: ${name}`);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Xử lý yêu cầu tài nguyên (Cache-First cho tĩnh, Network-First cho version.json)
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);

  // Đối với version.json: ưu tiên kiểm tra mạng để phát hiện cập nhật
  if (url.pathname.endsWith("version.json")) {
    event.respondWith(
      fetch(event.request)
        .then((networkResp) => {
          if (networkResp && networkResp.status === 200) {
            const copy = networkResp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return networkResp;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Đối với các tài nguyên tĩnh khác: Cache-First
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(event.request)
        .then((networkResponse) => {
          if (!networkResponse || networkResponse.status !== 200) {
            return networkResponse;
          }

          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });

          return networkResponse;
        })
        .catch(() => {
          // Fallback điều hướng cho SPA offline
          if (event.request.mode === "navigate") {
            return caches.match("./index.html");
          }
        });
    })
  );
});

// 4. Nhận thông điệp điều khiển từ Main Thread
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
