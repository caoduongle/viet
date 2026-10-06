import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

test.describe("B1 Regression: Service Worker Update & Cache-Busting", () => {
  test("phát hiện phiên bản mới khi dist thay đổi hash và nạp nội dung mới sau reload", async ({ browser }) => {
    test.setTimeout(90000);
    const context = await browser.newContext();
    const page = await context.newPage();

    // 1. Mở trang lần đầu và đợi Service Worker active
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      await page.click("#btn-welcome-create");
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    // Đảm bảo SW đã đăng ký và active
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

    // 2. Mô phỏng bản cập nhật mới bằng cách sửa file nguồn webapp/js/app.js
    const srcAppJsPath = path.resolve("webapp/js/app.js");
    const originalAppJs = fs.readFileSync(srcAppJsPath, "utf-8");
    const uniqueToken = `/* SW_UPDATE_TEST_${Date.now()} */`;

    try {
      fs.writeFileSync(srcAppJsPath, `${originalAppJs}\n${uniqueToken}\n`, "utf-8");

      // Chạy build_web để cập nhật dist và sinh sw.js với băm mới
      execSync("py -3 scripts/build_web.py", { encoding: "utf-8" });

      // 3. Kích hoạt Service Worker kiểm tra cập nhật (update)
      await page.evaluate(async () => {
        if ("serviceWorker" in navigator) {
          const reg = await navigator.serviceWorker.getRegistration();
          if (reg) await reg.update();
        }
      });

      // Chờ một chút để Service Worker mới được cài đặt (installed) và kích hoạt (skipWaiting/clients.claim)
      await page.waitForTimeout(3000);

      // Reload trang để kiểm tra nội dung mới
      await page.reload();
      await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

      // 4. Kiểm tra cache mới đã được tạo
      const newCacheName = await page.evaluate(async () => {
        const keys = await caches.keys();
        return keys.find((k) => k.startsWith("chuviettay-cache-"));
      });
      expect(newCacheName).toBeTruthy();
      expect(newCacheName).not.toBe(initialCacheName);

      // Khẳng định fetch app.js nhận nội dung mới có token
      const fetchedContent = await page.evaluate(async () => {
        const resp = await fetch("./js/app.js");
        return resp.text();
      });
      expect(fetchedContent).toContain(uniqueToken);
    } finally {
      // Khôi phục lại app.js sạch ban đầu và rebuild lại dist
      fs.writeFileSync(srcAppJsPath, originalAppJs, "utf-8");
      execSync("py -3 scripts/build_web.py", { encoding: "utf-8" });
    }

    await context.close();
  });
});
