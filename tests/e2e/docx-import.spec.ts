import { test, expect } from "@playwright/test";
import path from "node:path";

test.describe("B2 Regression: Mở file .docx trong Web Client", () => {
  test("tải lên sample.docx thành công và hiển thị văn bản trong editor", async ({ page }) => {
    test.setTimeout(90000);

    // 1. Vào trang chính và chờ splash-screen biến mất
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

    // 2. Nếu xuất hiện welcome modal (do kho trống), bấm tạo kho trống hoặc đóng
    const welcomeModal = page.locator("#welcome-modal");
    try {
      await welcomeModal.waitFor({ state: "visible", timeout: 4000 });
      await page.click("#btn-welcome-create");
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    } catch {
      // Bỏ qua nếu không xuất hiện modal chào
    }

    // 3. Tab Viết chữ đã được chọn mặc định
    const editor = page.locator("#editor-text");
    await expect(editor).toBeVisible({ timeout: 15000 });

    // 4. Mở file .docx qua #input-open-file
    const docxPath = path.resolve("tests/fixtures/sample.docx");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-open-file");
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(docxPath);

    // 5. Chờ import hoàn tất: worker nạp lazy wheels (typing_extensions, python_docx, lxml)
    // Sau khi nạp xong, textarea #editor-text phải nhận nội dung từ file docx
    await expect(editor).not.toHaveValue("", { timeout: 30000 });

    const content = await editor.inputValue();
    expect(content.length).toBeGreaterThan(10);
    // Format selector tự chuyển sang 'md'
    const formatSelect = page.locator("#select-format");
    await expect(formatSelect).toHaveValue("md");
  });
});
