import { test, expect } from "@playwright/test";
import path from "node:path";

test.describe("User Story: Nạp file lưới tập viết .xopp tạo kho ký tự (E2E)", () => {
  test("nạp file lưới .xopp trên web, trích xuất mẫu ký tự, cập nhật kho mẫu và viết chữ", async ({ page }) => {
    test.setTimeout(60000);

    const externalRequests: string[] = [];
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
        externalRequests.push(req.url());
      }
    });

    page.on("console", (msg) => console.log(`[PAGE LOG] ${msg.type()}: ${msg.text()}`));
    page.on("pageerror", (err) => console.error(`[PAGE ERROR]: ${err}`));

    // Bắt alert thông báo kết quả nạp lưới
    let alertMessage = "";
    page.on("dialog", async (dialog) => {
      alertMessage = dialog.message();
      await dialog.accept();
    });

    await page.goto("/");

    // 1. Đợi splash loading hoàn tất
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

    // 2. Nạp kho mẫu ban đầu qua welcome modal
    const welcomeModal = page.locator("#welcome-modal");
    try {
      await welcomeModal.waitFor({ state: "visible", timeout: 4000 });
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 20000 });
    } catch {
      // Bỏ qua nếu không xuất hiện modal chào
    }

    // Đảm bảo welcomeModal đã ẩn
    if (await welcomeModal.isVisible()) {
      await page.click("#btn-welcome-sample");
      await expect(welcomeModal).toBeHidden({ timeout: 10000 });
    }

    // 3. Chuyển sang Tab Dạy chữ
    await page.click('[data-tab="teach"]');
    await expect(page.locator("#tab-teach")).toBeVisible();

    // 4. Bấm "Nạp file lưới…" và chọn file tests/data/sample_char_grid.xopp
    const gridFilePath = path.resolve("tests/data/sample_char_grid.xopp");
    const gridFileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-import-grid");
    const gridFileChooser = await gridFileChooserPromise;
    await gridFileChooser.setFiles(gridFilePath);

    // Đợi xử lý file và alert xuất hiện
    await page.waitForTimeout(4000);
    expect(alertMessage).toContain("Nạp file lưới hoàn tất");
    expect(alertMessage).toContain("Đã thêm mẫu mới");

    // 5. Chuyển sang Tab Kho mẫu để kiểm tra các chữ cái đã nạp
    await page.click('[data-tab="bank"]');
    await expect(page.locator("#tab-bank")).toBeVisible();

    const searchInput = page.locator("#input-search-bank");
    await searchInput.fill("a");
    await page.waitForTimeout(300);

    const cardsGrid = page.locator("#bank-cards-grid");
    await expect(cardsGrid.locator(".bank-card-title").filter({ hasText: /^a$/ })).toBeVisible({ timeout: 10000 });

    // 6. Chuyển sang Tab Viết chữ và kiểm tra render ghép chữ tự động
    await page.click('[data-tab="write"]');
    await expect(page.locator("#tab-write")).toBeVisible();

    const editor = page.locator("#editor-text");
    await editor.fill("abc de");
    await page.waitForTimeout(2000);

    const svgWrapper = page.locator("#paper-svg-wrapper");
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });

    // Đảm bảo không có bất kỳ request ra server ngoài nào
    expect(externalRequests).toHaveLength(0);
  });
});
