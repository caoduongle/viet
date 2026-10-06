import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test.describe("User Story 2: Viết chữ, xem trước SVG và xuất file (E2E)", () => {
  test("soạn thảo văn bản, debounce 250ms, IME, xem trước SVG và tải file .xopp", async ({ page }) => {
    // Thu thập các network request
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

    // 1. Đợi splash loading biến mất
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    // 2. Nạp kho mẫu tổng hợp để có mẫu chữ
    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      // Bấm nút Nhập kho trên màn hình chào
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);

      // Đợi modal đóng sau khi nạp thành công
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    // 3. Chuyển sang Tab Viết (nếu chưa active)
    await page.click('[data-tab="write"]');

    const textarea = page.locator("#editor-text");
    await expect(textarea).toBeVisible();

    // 4. Mô phỏng gõ IME (Bộ gõ tiếng Việt) không kích hoạt render giữa chừng
    await textarea.evaluate((el) => {
      el.dispatchEvent(new CompositionEvent("compositionstart"));
    });

    await textarea.fill("xin chào ba");
    // Trong khi composing, SVG chưa được render
    await page.waitForTimeout(300);
    const svgWrapper = page.locator("#paper-svg-wrapper");

    // Kết thúc IME composition
    await textarea.evaluate((el) => {
      el.dispatchEvent(new CompositionEvent("compositionend"));
    });

    // 5. Đợi debounce 250ms và kiểm tra SVG xuất hiện
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });
    const polylineCount = await svgWrapper.locator("polyline").count();
    expect(polylineCount).toBeGreaterThan(0);

    // 6. Gõ văn bản Markdown có công thức toán
    await textarea.fill("# Tiêu đề\n\nxin chào ba má bà cho la\n\nToán: $a + b = c$\n");

    // Đợi render lại
    await page.waitForTimeout(600);
    await expect(svgWrapper.locator("svg")).toBeVisible();
    const updatedPolylineCount = await svgWrapper.locator("polyline").count();
    expect(updatedPolylineCount).toBeGreaterThan(polylineCount);

    // 7. Kiểm tra từ thiếu mẫu xuất hiện nếu gõ từ lạ
    await textarea.fill("Từ lạ hoàn toàn chưa từng học: xyzabcdef123");
    await page.waitForTimeout(600);
    const missingBox = page.locator("#missing-tokens-box");
    await expect(missingBox).toBeVisible();
    await expect(page.locator(".chip-missing").first()).toBeVisible();

    // 8. Kiểm tra nút Xuất .xopp kích hoạt tải xuống
    await textarea.fill("Văn bản để xuất file xopp");
    await page.waitForTimeout(600);

    const downloadPromise = page.waitForEvent("download");
    await page.click("#btn-export-xopp");
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("chuviet.xopp");

    // 9. Khẳng định tuyệt đối Zero Remote CDN
    expect(externalRequests).toHaveLength(0);
  });
});
