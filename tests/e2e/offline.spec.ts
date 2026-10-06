import { test, expect } from "@playwright/test";
import path from "node:path";

test.describe("User Story 6: Hoạt động Ngoại tuyến & PWA (Offline-first E2E)", () => {
  test("mở một lần, ngắt mạng setOffline(true), tải lại, viết và dạy chữ thành công", async ({ browser }) => {
    test.setTimeout(90000);
    const context = await browser.newContext();
    const externalRequests: string[] = [];

    const page = await context.newPage();
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
        externalRequests.push(req.url());
      }
    });

    page.on("console", (msg) => console.log(`[PAGE LOG] ${msg.type()}: ${msg.text()}`));
    page.on("pageerror", (err) => console.error(`[PAGE ERROR]: ${err}`));

    // 1. Tải trang lần đầu (Online)
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

    // Nạp kho mẫu ban đầu (chờ modal chào hiển thị)
    const welcomeModal = page.locator("#welcome-modal");
    await expect(welcomeModal).toBeVisible({ timeout: 15000 });
    const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-welcome-import");
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(bankFilePath);
    await expect(welcomeModal).toBeHidden({ timeout: 20000 });

    // 2. Chờ Service Worker đăng ký và active
    await page.evaluate(async () => {
      if ("serviceWorker" in navigator) {
        await navigator.serviceWorker.ready;
      }
    });

    // Chờ 3 giây để Service Worker hoàn tất precache toàn bộ tài nguyên
    await page.waitForTimeout(3000);

    // 3. Ngắt kết nối mạng hoàn toàn (Offline mode)
    await context.setOffline(true);

    // 4. Tải lại trang khi đang ngoại tuyến
    await page.reload();

    // Trang vẫn phải nạp thành công từ Cache Storage
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });
    await expect(page.locator("#status-indicator")).toBeVisible();

    // 5. Kiểm thử chức năng Viết chữ khi Offline
    await page.click('[data-tab="write"]');
    const editor = page.locator("#editor-text");
    await expect(editor).toBeVisible();

    await editor.fill("Kiểm tra ngoại tuyến offline.");
    const svgWrapper = page.locator("#paper-svg-wrapper");
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#page-indicator")).toHaveText(/1\s*\/\s*1/);

    // 6. Kiểm thử chức năng Dạy chữ khi Offline
    await page.click('[data-tab="teach"]');
    const canvas = page.locator("#teach-canvas");
    await expect(canvas).toBeVisible();

    const testWord = "nắng";
    await page.fill("#input-teach-add", testWord);
    await page.click("#btn-teach-add");
    await expect(page.locator("#teach-target-word")).toHaveText(new RegExp(testWord));

    // Vẽ nét bút vào canvas
    const canvasBox = await canvas.boundingBox();
    expect(canvasBox).not.toBeNull();
    const cx = canvasBox!.x + 100;
    const cy = canvasBox!.y + 100;

    await canvas.evaluate((el: HTMLElement, { x, y }: { x: number; y: number }) => {
      el.dispatchEvent(
        new PointerEvent("pointerdown", {
          pointerId: 1,
          pointerType: "pen",
          isPrimary: true,
          clientX: x,
          clientY: y,
          button: 0,
          buttons: 1,
        })
      );
      el.dispatchEvent(
        new PointerEvent("pointermove", {
          pointerId: 1,
          pointerType: "pen",
          isPrimary: true,
          clientX: x + 40,
          clientY: y - 30,
          button: 0,
          buttons: 1,
        })
      );
      el.dispatchEvent(
        new PointerEvent("pointerup", {
          pointerId: 1,
          pointerType: "pen",
          isPrimary: true,
          clientX: x + 40,
          clientY: y - 30,
          button: 0,
          buttons: 0,
        })
      );
    }, { x: cx, y: cy });

    const saveBtn = page.locator("#btn-teach-save");
    await expect(saveBtn).toBeEnabled();
    await saveBtn.click();

    // Chờ debounce lưu xuống IndexedDB khi offline
    await page.waitForTimeout(3000);

    // 7. Kiểm tra trong Tab Kho mẫu xem từ "nắng" đã được lưu chưa
    await page.click('[data-tab="bank"]');
    await page.fill("#input-search-bank", testWord);
    await expect(page.locator("#bank-cards-grid .bank-card-title", { hasText: testWord })).toBeVisible({ timeout: 10000 });

    // 8. Khẳng định Zero Remote CDN
    expect(externalRequests).toHaveLength(0);

    await context.close();
  });
});
