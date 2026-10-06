import { test, expect } from "@playwright/test";
import path from "node:path";

test.describe("User Story 5: Đa tab đồng bộ không mất dữ liệu (E2E)", () => {
  test("hai page cùng context, dạy và xoá xen kẽ, kiểm tra hội tụ và không hồi sinh", async ({ browser }) => {
    test.setTimeout(90000);
    const context = await browser.newContext();
    const externalRequests: string[] = [];

    // Tạo Page 1
    const page1 = await context.newPage();
    page1.on("console", (msg) => console.log(`[PAGE1] ${msg.type()}: ${msg.text()}`));
    page1.on("pageerror", (err) => console.error(`[PAGE1 ERROR] ${err}`));
    page1.on("request", (req) => {
      const url = new URL(req.url());
      if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
        externalRequests.push(req.url());
      }
    });

    await page1.goto("/");
    await expect(page1.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

    // Nạp kho mẫu ban đầu ở Page 1 (lần đầu luôn hiện welcome-modal)
    const welcome1 = page1.locator("#welcome-modal");
    await expect(welcome1).toBeVisible({ timeout: 15000 });
    const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
    const fileChooserPromise = page1.waitForEvent("filechooser");
    await page1.click("#btn-welcome-import");
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(bankFilePath);
    await expect(welcome1).toBeHidden({ timeout: 20000 });

    // Tạo Page 2 trong cùng context (dùng chung IndexedDB)
    const page2 = await context.newPage();
    page2.on("console", (msg) => console.log(`[PAGE2] ${msg.type()}: ${msg.text()}`));
    page2.on("pageerror", (err) => console.error(`[PAGE2 ERROR] ${err}`));
    page2.on("request", (req) => {
      const url = new URL(req.url());
      if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
        externalRequests.push(req.url());
      }
    });

    await page2.goto("/");
    await expect(page2.locator("#splash-screen")).toBeHidden({ timeout: 45000 });
    // Page 2 không hiện welcome modal vì IndexedDB đã có hồ sơ từ Page 1
    await expect(page2.locator("#welcome-modal")).toBeHidden({ timeout: 10000 });

    // Helper vẽ nét bút vào canvas
    async function drawStroke(page: any) {
      const canvas = page.locator("#teach-canvas");
      await expect(canvas).toBeVisible();
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
    }

    // 1. Page 1: Dạy từ "hoa"
    await page1.click('[data-tab="teach"]');
    await page1.fill("#input-teach-add", "hoa");
    await page1.click("#btn-teach-add");
    await expect(page1.locator("#teach-target-word")).toHaveText(/hoa/);
    await drawStroke(page1);

    const saveBtn1 = page1.locator("#btn-teach-save");
    await expect(saveBtn1).toBeEnabled();
    await saveBtn1.click();

    // Đợi Page 1 hoàn tất lưu và đồng bộ (chờ debounce 2s + lưu)
    await page1.waitForTimeout(3000);

    // 2. Page 2: Dạy từ "la"
    await page2.click('[data-tab="teach"]');
    await page2.fill("#input-teach-add", "la");
    await page2.click("#btn-teach-add");
    await expect(page2.locator("#teach-target-word")).toHaveText(/la/);
    await drawStroke(page2);

    const saveBtn2 = page2.locator("#btn-teach-save");
    await expect(saveBtn2).toBeEnabled();
    await saveBtn2.click();

    // Đợi Page 2 hoàn tất lưu và đồng bộ
    await page2.waitForTimeout(3000);

    // 3. Kiểm tra Hội tụ: Cả Page 1 và Page 2 đều phải có cả "hoa" và "la"
    // Kiểm tra trên Page 1
    await page1.click('[data-tab="bank"]');
    await page1.fill("#input-search-bank", "hoa");
    await expect(page1.locator("#bank-cards-grid .bank-card-title", { hasText: "hoa" })).toBeVisible({ timeout: 10000 });

    await page1.fill("#input-search-bank", "la");
    await expect(page1.locator("#bank-cards-grid .bank-card-title", { hasText: "la" })).toBeVisible({ timeout: 10000 });

    // Kiểm tra trên Page 2
    await page2.click('[data-tab="bank"]');
    await page2.fill("#input-search-bank", "hoa");
    await expect(page2.locator("#bank-cards-grid .bank-card-title", { hasText: "hoa" })).toBeVisible({ timeout: 10000 });

    await page2.fill("#input-search-bank", "la");
    await expect(page2.locator("#bank-cards-grid .bank-card-title", { hasText: "la" })).toBeVisible({ timeout: 10000 });

    // 4. Xoá nhãn "hoa" ở Page 1
    page1.on("dialog", async (dialog) => {
      await dialog.accept();
    });

    await page1.fill("#input-search-bank", "hoa");
    const hoaCard1 = page1.locator("#bank-cards-grid .bank-card", { hasText: "hoa" });
    await expect(hoaCard1).toBeVisible();
    await hoaCard1.click();

    const detailModal1 = page1.locator("#modal-label-detail");
    await expect(detailModal1).toBeVisible();
    await page1.click("#btn-label-delete");
    await expect(detailModal1).toBeHidden({ timeout: 10000 });

    // Đợi thông điệp broadcast đồng bộ sang Page 2
    await page1.waitForTimeout(3000);

    // 5. Kiểm tra Hội tụ sau khi xoá: "hoa" phải biến mất ở cả 2 tab, "la" vẫn còn nguyên
    // Trên Page 1:
    await page1.fill("#input-search-bank", "hoa");
    await expect(page1.locator("#bank-cards-grid .bank-card-title", { hasText: "hoa" })).toBeHidden();
    await page1.fill("#input-search-bank", "la");
    await expect(page1.locator("#bank-cards-grid .bank-card-title", { hasText: "la" })).toBeVisible();

    // Trên Page 2:
    await page2.fill("#input-search-bank", "hoa");
    await expect(page2.locator("#bank-cards-grid .bank-card-title", { hasText: "hoa" })).toBeHidden();
    await page2.fill("#input-search-bank", "la");
    await expect(page2.locator("#bank-cards-grid .bank-card-title", { hasText: "la" })).toBeVisible();

    // 6. Zero Remote CDN
    expect(externalRequests).toHaveLength(0);

    await context.close();
  });
});
