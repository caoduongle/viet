import { test, expect } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync, spawn, type ChildProcess } from "node:child_process";

// Cổng riêng + dist riêng để test này KHÔNG đụng vào webapp/dist đang được
// các worker khác dùng song song (build_web.py xoá sạch thư mục dist rồi tạo lại).
const SW_PORT = 8101;
const SW_ORIGIN = `http://localhost:${SW_PORT}`;

/** Chạy build_web.py bằng Python có sẵn trên mọi nền tảng (không cố định `py -3`). */
function runBuildWeb(distDir: string): void {
  const candidates: Array<[string, string[]]> = [];
  if (process.env.PYTHON) candidates.push([process.env.PYTHON, []]);
  if (process.platform === "win32") candidates.push(["py", ["-3"]]);
  candidates.push(["python3", []], ["python", []]);

  let lastError: unknown;
  for (const [cmd, pre] of candidates) {
    try {
      execFileSync(cmd, [...pre, "scripts/build_web.py", "--dist", distDir], {
        encoding: "utf-8",
        stdio: "pipe",
      });
      return;
    } catch (err) {
      const e = err as NodeJS.ErrnoException;
      if (e.code === "ENOENT") {
        lastError = err;
        continue; // không có interpreter này -> thử cái tiếp theo
      }
      throw err; // build lỗi thật -> báo ngay, không nuốt
    }
  }
  throw new Error(`Không tìm thấy Python để chạy build_web.py: ${String(lastError)}`);
}

async function waitForServer(url: string, timeoutMs = 15000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(url);
      if (r.ok) return;
    } catch {
      /* server chưa sẵn sàng */
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`Server ${url} không khởi động kịp`);
}

test.describe("B1 Regression: Service Worker Update & Cache-Busting", () => {
  test("phát hiện phiên bản mới khi dist thay đổi hash và nạp nội dung mới sau reload", async ({ browser }) => {
    test.setTimeout(240000);

    const tmpDist = fs.mkdtempSync(path.join(os.tmpdir(), "viet-sw-dist-"));
    const srcAppJsPath = path.resolve("webapp/js/app.js");
    const originalAppJs = fs.readFileSync(srcAppJsPath, "utf-8");
    const uniqueToken = `/* SW_UPDATE_TEST_${Date.now()} */`;
    let server: ChildProcess | undefined;

    try {
      // 0. Build bản dist đầu tiên vào thư mục tạm và phục vụ bằng server riêng
      runBuildWeb(tmpDist);
      server = spawn("node", ["scripts/serve.mjs"], {
        env: { ...process.env, PORT: String(SW_PORT), DIST_DIR: tmpDist },
        stdio: "ignore",
      });
      await waitForServer(`${SW_ORIGIN}/index.html`);

      const context = await browser.newContext();
      const page = await context.newPage();

      // 1. Mở trang lần đầu và đợi Service Worker active
      await page.goto(`${SW_ORIGIN}/`);
      await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

      const welcomeModal = page.locator("#welcome-modal");
      if (await welcomeModal.isVisible()) {
        await page.click("#btn-welcome-create");
        await expect(welcomeModal).toBeHidden({ timeout: 15000 });
      }

      await page.evaluate(async () => {
        if ("serviceWorker" in navigator) {
          await navigator.serviceWorker.ready;
        }
      });

      const initialCacheName = await page.evaluate(async () => {
        const keys = await caches.keys();
        return keys.find((k) => k.startsWith("chuviettay-cache-"));
      });
      expect(initialCacheName).toBeTruthy();

      // 2. Mô phỏng bản cập nhật: sửa nguồn rồi build lại vào dist tạm -> sw.js có băm mới
      fs.writeFileSync(srcAppJsPath, `${originalAppJs}\n${uniqueToken}\n`, "utf-8");
      runBuildWeb(tmpDist);

      // 3. Kích hoạt Service Worker kiểm tra cập nhật
      await page.evaluate(async () => {
        if ("serviceWorker" in navigator) {
          const reg = await navigator.serviceWorker.getRegistration();
          if (reg) await reg.update();
        }
      });

      await page.waitForTimeout(3000);

      await page.reload();
      await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

      // 4. Kiểm tra cache mới đã được tạo với băm khác
      const newCacheName = await page.evaluate(async () => {
        const keys = await caches.keys();
        return keys.find((k) => k.startsWith("chuviettay-cache-"));
      });
      expect(newCacheName).toBeTruthy();
      expect(newCacheName).not.toBe(initialCacheName);

      const fetchedContent = await page.evaluate(async () => {
        const resp = await fetch("./js/app.js");
        return resp.text();
      });
      expect(fetchedContent).toContain(uniqueToken);

      await context.close();
    } finally {
      // Luôn khôi phục app.js; mỗi bước dọn dẹp độc lập để không che lỗi gốc của test
      try {
        fs.writeFileSync(srcAppJsPath, originalAppJs, "utf-8");
      } catch (e) {
        console.error("Không khôi phục được app.js:", e);
      }
      server?.kill();
      try {
        fs.rmSync(tmpDist, { recursive: true, force: true });
      } catch {
        /* bỏ qua */
      }
    }
  });
});
