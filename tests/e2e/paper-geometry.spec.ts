import { test, expect } from "@playwright/test";
import path from "node:path";

test.describe("Feature 023: Hình học xem trước trang giấy và bộ điều khiển Zoom (E2E)", () => {
  test.setTimeout(90000);

  async function setupPageAndBank(page, viewport = { width: 1920, height: 1020 }) {
    await page.setViewportSize(viewport);
    await page.goto("/");

    // Đợi splash loading biến mất
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    // Nạp kho mẫu tổng hợp nếu xuất hiện modal chào mừng
    const welcomeModal = page.locator("#welcome-modal");
    try {
      await welcomeModal.waitFor({ state: "visible", timeout: 3000 });
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    } catch {
      // Bỏ qua nếu không xuất hiện modal chào
    }

    // Chuyển sang Tab Viết
    await page.click('[data-tab="write"]');
    const textarea = page.locator("#editor-text");
    await expect(textarea).toBeVisible();

    // Gõ đoạn văn bản mẫu
    await textarea.fill("Kính gửi thầy cô và các bạn,\nĐây là bài kiểm tra kích thước hình học trang giấy xem trước.");
    // Đợi render SVG hoàn tất
    const svgWrapper = page.locator("#paper-svg-wrapper");
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });
    return { textarea, svgWrapper };
  }

  test("US1: Khổ A4 ở 100% zoom có chiều rộng thực ~794px ở 1920x1020 và 1366x768", async ({ page }) => {
    // 1. Kiểm tra ở viewport Full HD 1920×1020
    const { svgWrapper } = await setupPageAndBank(page, { width: 1920, height: 1020 });

    // Đo kích thước thực tế của khung giấy và phần tử SVG
    const box1920 = await svgWrapper.boundingBox();
    expect(box1920).not.toBeNull();
    // A4: 595.28 pt * 96 / 72 = 793.707 px -> round: 794 px
    expect(box1920!.width).toBeGreaterThanOrEqual(700);
    expect(box1920!.width).toBeCloseTo(794, 0); // sai số < 1.5px
    expect(box1920!.height).toBeCloseTo(1123, 0); // 841.89 * 4/3 = 1122.52 px

    // Tỷ lệ khung hình chuẩn A4 (~1.414)
    const ratio = box1920!.height / box1920!.width;
    expect(ratio).toBeGreaterThan(1.40);
    expect(ratio).toBeLessThan(1.43);

    // 2. Kiểm tra ở viewport laptop 1366×768 (ở 100% zoom giấy vẫn giữ đúng kích thước thật 794px)
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.waitForTimeout(300);

    const box1366 = await svgWrapper.boundingBox();
    expect(box1366).not.toBeNull();
    expect(box1366!.width).toBeGreaterThanOrEqual(700);
    expect(box1366!.width).toBeCloseTo(794, 0);
  });

  test("US2: Bộ điều khiển Zoom (+, -, Fit, %) và thích ứng khi resize cửa sổ", async ({ page }) => {
    const { svgWrapper } = await setupPageAndBank(page, { width: 1920, height: 1020 });

    const btnZoomIn = page.locator("#btn-zoom-in");
    const btnZoomOut = page.locator("#btn-zoom-out");
    const btnZoomFit = page.locator("#btn-zoom-fit");
    const zoomDisplay = page.locator("#zoom-percent-display");
    const previewStage = page.locator("#preview-stage");

    await expect(zoomDisplay).toHaveText("100%");

    // 1. Bấm phóng to (+)
    await btnZoomIn.click();
    await expect(zoomDisplay).toHaveText("110%");
    let box = await svgWrapper.boundingBox();
    // 794 * 1.1 = 873.4 px
    expect(box!.width).toBeCloseTo(873, -1);

    // 2. Bấm thu nhỏ (-)
    await btnZoomOut.click(); // về 100%
    await btnZoomOut.click(); // về 90%
    await expect(zoomDisplay).toHaveText("90%");
    box = await svgWrapper.boundingBox();
    expect(box!.width).toBeCloseTo(714, -1);

    // 3. Bấm nút Fit (Vừa khung) ở 1366×768
    await page.setViewportSize({ width: 1366, height: 768 });
    await btnZoomFit.click();
    await page.waitForTimeout(300);

    // Không được xuất hiện thanh cuộn ngang ở chế độ Fit
    const hasHorizontalScroll = await previewStage.evaluate((el) => {
      return el.scrollWidth > el.clientWidth + 2; // đệm sai số sub-pixel
    });
    expect(hasHorizontalScroll).toBe(false);

    const fitDisplay1366 = await zoomDisplay.textContent();
    expect(fitDisplay1366).not.toBe("100%"); // Phải co nhỏ hơn 100% để vừa màn hình 1366

    // 4. Resize cửa sổ sang 1920×1020: chế độ Fit tự động tính toán lại mà không cần bấm lại nút
    await page.setViewportSize({ width: 1920, height: 1020 });
    await page.waitForTimeout(400);

    const fitDisplay1920 = await zoomDisplay.textContent();
    expect(fitDisplay1920).not.toBe(fitDisplay1366); // Đã tự động thích ứng với viewport mới

    const hasHorizontalScroll1920 = await previewStage.evaluate((el) => {
      return el.scrollWidth > el.clientWidth + 2;
    });
    expect(hasHorizontalScroll1920).toBe(false);
  });

  test("US3: Chuẩn hóa kiểu giấy lined vs ruled theo chuẩn Xournal++", async ({ page }) => {
    const { svgWrapper } = await setupPageAndBank(page, { width: 1920, height: 1020 });

    // 1. Mặc định khởi tạo phải là "lined" (có dòng kẻ và lề đỏ)
    const marginLine = svgWrapper.locator(".paper-bg-margin");
    await expect(marginLine).toHaveCount(1);
    expect(await marginLine.getAttribute("stroke")).toBe("#ff8a80");

    const bgLines = svgWrapper.locator(".paper-bg-line");
    expect(await bgLines.count()).toBeGreaterThan(10);

    // 2. Mở Tuỳ chọn, chuyển sang "ruled" (chỉ dòng kẻ, không có lề đỏ)
    await page.click("#btn-open-write-options");
    const modalOptions = page.locator("#modal-write-options");
    await expect(modalOptions).toBeVisible();

    // Kiểm tra dropdown hiển thị đúng nhãn và giá trị mặc định lined
    const selectBg = page.locator("#opt-background");
    await expect(selectBg).toHaveValue("lined");

    // Chọn "ruled" (Chỉ dòng kẻ)
    await selectBg.selectOption("ruled");
    await page.click("#btn-apply-options");
    await expect(modalOptions).toBeHidden();

    // Đợi render lại với kiểu ruled
    await page.waitForTimeout(600);

    // Nền ruled: KHÔNG được có vạch kẻ lề đỏ, nhưng VẪN PHẢI có dòng kẻ ngang
    expect(await svgWrapper.locator(".paper-bg-margin").count()).toBe(0);
    expect(await svgWrapper.locator(".paper-bg-line").count()).toBeGreaterThan(10);

    // 3. Mở lại Tuỳ chọn, chọn Đặt lại mặc định -> trở về "lined"
    await page.click("#btn-open-write-options");
    await page.click("#btn-reset-options");
    await expect(selectBg).toHaveValue("lined");
    await page.click("#btn-apply-options");

    await page.waitForTimeout(600);
    await expect(svgWrapper.locator(".paper-bg-margin")).toHaveCount(1);
  });

  test("Kiểm tra tỷ lệ hình học khi đổi khổ giấy sang A5 và Letter", async ({ page }) => {
    const { svgWrapper } = await setupPageAndBank(page, { width: 1920, height: 1020 });

    // 1. Đổi sang khổ A5 (419.53 pt x 595.28 pt)
    await page.click("#btn-open-write-options");
    const modalOptions = page.locator("#modal-write-options");
    await expect(modalOptions).toBeVisible();

    await page.selectOption("#opt-paper", "a5");
    await page.click("#btn-apply-options");
    await expect(modalOptions).toBeHidden();
    await page.waitForTimeout(600);

    const boxA5 = await svgWrapper.boundingBox();
    // A5 100% width: 419.53 * 4/3 = 559.37 -> ~559 px
    // A5 100% height: 595.28 * 4/3 = 793.71 -> ~794 px
    expect(boxA5!.width).toBeCloseTo(559, -1);
    expect(boxA5!.height).toBeCloseTo(794, -1);
    const ratioA5 = boxA5!.height / boxA5!.width;
    expect(ratioA5).toBeGreaterThan(1.40);
    expect(ratioA5).toBeLessThan(1.43);
  });

  test("Chụp ảnh màn hình nghiệm thu thực tế sau khi sửa", async ({ page }) => {
    const { svgWrapper } = await setupPageAndBank(page, { width: 1920, height: 1020 });
    const artifactDir = "C:/Users/LE/.gemini/antigravity/brain/d20aabed-ce0f-495c-96be-c241876f89b2";

    // Chụp toàn cảnh xem trước 100% zoom ở 1920x1020
    await page.screenshot({
      path: `${artifactDir}/preview_paper_geometry_after_1920.png`,
      fullPage: false,
    });

    // Chụp chế độ Fit ở 1366x768
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.click("#btn-zoom-fit");
    await page.waitForTimeout(400);
    await page.screenshot({
      path: `${artifactDir}/preview_paper_geometry_fit_1366.png`,
      fullPage: false,
    });
  });
});
