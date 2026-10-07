import { test, expect } from "@playwright/test";
import path from "node:path";

test.describe("User Story 4: Quản lý Kho mẫu chữ (E2E)", () => {
  test("lưới nhãn, tìm kiếm, xem thư viện biến thể, xuất file kiểm tra .xopp và sao lưu kho", async ({ page }) => {
    const externalRequests: string[] = [];
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
        externalRequests.push(req.url());
      }
    });

    page.on("console", (msg) => console.log(`[PAGE LOG] ${msg.type()}: ${msg.text()}`));
    page.on("pageerror", (err) => console.error(`[PAGE ERROR]: ${err}`));

    await page.goto("/");

    // 1. Đợi splash loading hoàn tất
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    // 2. Nạp kho mẫu tổng hợp để có sẵn nhiều từ
    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    // 3. Chuyển sang Tab Kho mẫu
    await page.click('[data-tab="bank"]');

    // 4. Kiểm tra lưới thẻ nhãn và thống kê
    const summary = page.locator("#bank-summary");
    await expect(summary).toContainText("Kho mẫu hiện có", { timeout: 10000 });

    const cardsGrid = page.locator("#bank-cards-grid");
    await expect(cardsGrid.locator(".bank-card").first()).toBeVisible({ timeout: 5000 });
    const initialCardCount = await cardsGrid.locator(".bank-card").count();
    expect(initialCardCount).toBeGreaterThan(0);

    // 5. Thử tìm kiếm tức thì
    const searchInput = page.locator("#input-search-bank");
    await searchInput.fill("a");
    await page.waitForTimeout(300);

    // Thẻ chứa ký tự "a" xuất hiện
    await expect(cardsGrid.locator(".bank-card-title", { hasText: "a" }).first()).toBeVisible();

    // 6. Bấm vào thẻ "a" để mở Modal chi tiết thư viện mẫu
    await cardsGrid.locator(".bank-card", { hasText: "a" }).first().click();

    const detailModal = page.locator("#modal-label-detail");
    await expect(detailModal).toBeVisible();
    await expect(page.locator("#modal-label-title")).toContainText(/a/i);

    // Kiểm tra các biến thể mẫu nét xuất hiện với SVG thumbnail
    const samplesGrid = page.locator("#modal-label-samples-grid");
    await expect(samplesGrid.locator(".sample-item-card").first()).toBeVisible({ timeout: 5000 });
    const sampleCount = await samplesGrid.locator(".sample-item-card").count();
    expect(sampleCount).toBeGreaterThan(0);

    // Khẳng định thuộc tính vector-effect="non-scaling-stroke" và stroke-width trong thumbnail
    const firstPolyline = samplesGrid.locator(".sample-item-card svg polyline").first();
    await expect(firstPolyline).toHaveAttribute("vector-effect", "non-scaling-stroke");
    await expect(firstPolyline).toHaveAttribute("stroke-width", "1.8");

    // Khẳng định có đường kẻ chân chữ mờ tham chiếu
    const baselineLine = samplesGrid.locator(".sample-item-card svg line");
    await expect(baselineLine.first()).toHaveAttribute("stroke-dasharray", "2,2");

    // Đóng modal chi tiết
    await page.click("#btn-close-label-detail");
    await expect(detailModal).toBeHidden();

    // 7. Xoá ô tìm kiếm để hiện lại toàn bộ
    await searchInput.fill("");
    await page.waitForTimeout(300);

    // 8. Xuất file kiểm tra .xopp (export_check)
    const checkDownloadPromise = page.waitForEvent("download");
    await page.click("#btn-export-check");
    const checkDownload = await checkDownloadPromise;
    expect(checkDownload.suggestedFilename()).toBe("kiem_tra_kho.xopp");

    // 9. Tải bản sao lưu kho mẫu .json.gz
    const backupDownloadPromise = page.waitForEvent("download");
    await page.click("#btn-export-bank");
    const backupDownload = await backupDownloadPromise;
    expect(backupDownload.suggestedFilename()).toBe("chu_cua_ban.json.gz");

    // 10. Khẳng định tuyệt đối Zero Remote CDN
    expect(externalRequests).toHaveLength(0);
  });
});
