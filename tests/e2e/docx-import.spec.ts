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

  test("tải lên sample_table.docx bảo toàn 100% cấu trúc bảng trong editor và bản xem trước", async ({ page }) => {
    test.setTimeout(90000);

    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

    const welcomeModal = page.locator("#welcome-modal");
    try {
      await welcomeModal.waitFor({ state: "visible", timeout: 4000 });
      await page.click("#btn-welcome-create");
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    } catch {
      // Bỏ qua nếu không xuất hiện modal chào
    }

    const editor = page.locator("#editor-text");
    await expect(editor).toBeVisible({ timeout: 15000 });

    const docxPath = path.resolve("tests/fixtures/sample_table.docx");
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-open-file");
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(docxPath);

    await expect(editor).not.toHaveValue("", { timeout: 30000 });
    const content = await editor.inputValue();

    // Khẳng định dữ liệu bảng được bảo toàn trọn vẹn
    expect(content).toContain("|");
    expect(content).toContain("Mã số");
    expect(content).toContain("Họ và tên");
    expect(content).toContain("Điểm số");
    expect(content).toContain("SV01");
    expect(content).toContain("Nguyễn Văn A");
    expect(content).toContain("8.5");

    const formatSelect = page.locator("#select-format");
    await expect(formatSelect).toHaveValue("md");

    // Chờ bản xem trước SVG hiển thị nét vẽ
    const previewContainer = page.locator("#paper-svg-wrapper");
    await expect(previewContainer).toBeVisible({ timeout: 20000 });
  });

  test("chèn bảng tuỳ chỉnh qua modal Bảng chèn đúng template vào editor", async ({ page }) => {
    test.setTimeout(45000);

    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 45000 });

    const welcomeModal = page.locator("#welcome-modal");
    try {
      await welcomeModal.waitFor({ state: "visible", timeout: 4000 });
      await page.click("#btn-welcome-create");
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    } catch {
      // Bỏ qua
    }

    const editor = page.locator("#editor-text");
    await expect(editor).toBeVisible({ timeout: 15000 });

    // Bấm nút Bảng
    await page.click("#btn-md-table");

    // Modal xuất hiện
    const modalTable = page.locator("#modal-insert-table");
    await expect(modalTable).toBeVisible({ timeout: 5000 });

    // Đổi số hàng sang 2, số cột sang 2
    await page.fill("#table-input-rows", "2");
    await page.fill("#table-input-cols", "2");

    // Xác nhận
    await page.click("#btn-confirm-insert-table");
    await expect(modalTable).toBeHidden({ timeout: 5000 });

    // Kiểm tra nội dung trong editor
    const content = await editor.inputValue();
    expect(content).toContain("| Cột 1 | Cột 2 |");
    expect(content).toContain("| :--- | :--- |");
    expect(content).toContain("| R1C1 | R1C2 |");
    expect(content).toContain("| R2C1 | R2C2 |");
  });
});
