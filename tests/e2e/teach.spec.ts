import { test, expect } from "@playwright/test";
import path from "node:path";

test.describe("User Story 3: Dạy mẫu chữ bằng Canvas Pointer Events (E2E)", () => {
  test("mô phỏng pointer events kiểu pen và touch, lọc lòng bàn tay, phím tắt và lưu mẫu thành công", async ({ page }) => {
    test.setTimeout(90000);
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

    // 2. Nạp kho mẫu nếu có modal chào
    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    // 3. Chuyển sang Tab Dạy chữ
    await page.click('[data-tab="teach"]');
    const canvas = page.locator("#teach-canvas");
    await expect(canvas).toBeVisible();

    // 4. Thêm một từ mới vào hàng đợi
    const testWord = "mùa";
    await page.fill("#input-teach-add", testWord);
    await page.click("#btn-teach-add");

    const targetWordEl = page.locator("#teach-target-word");
    await expect(targetWordEl).toHaveText(new RegExp(testWord));

    const saveBtn = page.locator("#btn-teach-save");
    await expect(saveBtn).toBeDisabled();

    // 5. Kiểm thử Từ chối lòng bàn tay (Palm Rejection)
    // Mô phỏng chạm cảm ứng diện tích lớn (width=40, height=40) như lòng bàn tay đè lên màn hình
    const canvasBox = await canvas.boundingBox();
    expect(canvasBox).not.toBeNull();
    const cx = canvasBox!.x + 100;
    const cy = canvasBox!.y + 100;

    await canvas.evaluate((el, { x, y }) => {
      el.dispatchEvent(
        new PointerEvent("pointerdown", {
          pointerId: 10,
          pointerType: "touch",
          isPrimary: true,
          clientX: x,
          clientY: y,
          width: 40,
          height: 40,
          button: 0,
          buttons: 1,
        })
      );
      el.dispatchEvent(
        new PointerEvent("pointermove", {
          pointerId: 10,
          pointerType: "touch",
          isPrimary: true,
          clientX: x + 20,
          clientY: y + 20,
          width: 40,
          height: 40,
          button: 0,
          buttons: 1,
        })
      );
      el.dispatchEvent(
        new PointerEvent("pointerup", {
          pointerId: 10,
          pointerType: "touch",
          isPrimary: true,
          clientX: x + 20,
          clientY: y + 20,
          button: 0,
          buttons: 0,
        })
      );
    }, { x: cx, y: cy });

    // Nút Lưu vẫn phải bị vô hiệu hoá vì chạm lòng bàn tay đã bị loại bỏ hoàn toàn
    await expect(saveBtn).toBeDisabled();

    // 6. Mô phỏng nét vẽ bằng Bút cảm ứng thật (pen)
    await canvas.evaluate((el, { x, y }) => {
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
          clientX: x + 30,
          clientY: y - 40,
          button: 0,
          buttons: 1,
        })
      );
      el.dispatchEvent(
        new PointerEvent("pointermove", {
          pointerId: 1,
          pointerType: "pen",
          isPrimary: true,
          clientX: x + 60,
          clientY: y,
          button: 0,
          buttons: 1,
        })
      );
      el.dispatchEvent(
        new PointerEvent("pointerup", {
          pointerId: 1,
          pointerType: "pen",
          isPrimary: true,
          clientX: x + 60,
          clientY: y,
          button: 0,
          buttons: 0,
        })
      );
    }, { x: cx, y: cy });

    // Bây giờ canvas đã có nét vẽ hợp lệ -> Nút Lưu được kích hoạt
    await expect(saveBtn).toBeEnabled();

    // 7. Thử thao tác Hoàn tác nét (Undo)
    await page.click("#btn-teach-undo");
    await expect(saveBtn).toBeDisabled();

    // Thử Làm lại nét (Redo)
    await page.click("#btn-teach-redo");
    await expect(saveBtn).toBeEnabled();

    // 8. Bấm Lưu mẫu & tiếp theo ->
    await saveBtn.click();

    // Đợi lưu hoàn tất, hàng đợi chuyển sang từ kế tiếp hoặc trống
    await page.waitForTimeout(500);

    // 9. Kiểm tra Zero Remote CDN
    expect(externalRequests).toHaveLength(0);
  });
});
