import { test, expect } from "@playwright/test";

test.describe("Màn hình chào lần đầu (First Run / Onboarding)", () => {
  test("kho trống hiển thị màn hình chào với 3 lựa chọn và không request ra ngoài", async ({ page }) => {
    const externalRequests: string[] = [];

    // Lắng nghe network requests
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
        externalRequests.push(req.url());
      }
    });

    page.on("console", (msg) => console.log(`[PAGE LOG] ${msg.type()}: ${msg.text()}`));
    page.on("pageerror", (err) => console.error(`[PAGE ERROR]: ${err}`));

    await page.goto("/");

    // Đợi splash screen biến mất
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    // Kiểm tra màn hình chào xuất hiện khi chưa có kho
    const welcomeModal = page.locator("#welcome-modal");
    await expect(welcomeModal).toBeVisible();

    // Kiểm tra 3 lựa chọn cốt lõi (theo Quyết định D7 đã duyệt)
    await expect(page.locator("#btn-welcome-import")).toBeVisible();
    await expect(page.locator("#btn-welcome-create")).toBeVisible();
    await expect(page.locator("#btn-welcome-guide")).toBeVisible();

    // Khẳng định 100% không có request tới domain bên ngoài (Zero Remote CDN)
    expect(externalRequests).toHaveLength(0);
  });
});
