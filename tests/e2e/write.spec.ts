import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test.describe("User Story 2: Viết chữ, xem trước SVG và xuất file (E2E)", () => {
  test("soạn thảo văn bản, debounce 250ms, IME, xem trước SVG và tải file .xopp", async ({ page }) => {
    test.setTimeout(90000);
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

  test("chèn bảng qua modal tôn trọng checkbox Has header row", async ({ page }) => {
    test.setTimeout(30000);
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    const welcomeModal = page.locator("#welcome-modal");
    try {
      await welcomeModal.waitFor({ state: "visible", timeout: 4000 });
      await page.click("#btn-welcome-create");
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    } catch {
      // Bỏ qua nếu không xuất hiện modal chào
    }

    await page.click('[data-tab="write"]');
    const textarea = page.locator("#editor-text");
    await expect(textarea).toBeVisible();

    // Mở modal chèn bảng
    await page.click("#btn-md-table");
    const modal = page.locator("#modal-insert-table");
    await expect(modal).toBeVisible();

    // Điền 2 hàng, 3 cột và bỏ chọn header
    await page.fill("#table-input-rows", "2");
    await page.fill("#table-input-cols", "3");
    await page.uncheck("#table-input-header");

    await page.click("#btn-confirm-insert-table");
    await expect(modal).toBeHidden();

    const val = await textarea.inputValue();
    // Bảng không có tiêu đề phải có dòng header trắng |   |   |   |
    expect(val).toContain("|   |   |   |");
    expect(val).toContain("| :--- | :--- | :--- |");
    expect(val).toContain("| R1C1 | R1C2 | R1C3 |");
    expect(val).toContain("| R2C1 | R2C2 | R2C3 |");
  });

  test("xóa trắng hoặc mở file mới tự động đặt lại lịch sử hạt giống, không kế thừa occurrence cũ", async ({ page }) => {
    test.setTimeout(90000);
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    await page.click('[data-tab="write"]');
    const textarea = page.locator("#editor-text");
    await expect(textarea).toBeVisible();

    const svgWrapper = page.locator("#paper-svg-wrapper");

    // 1. Kết xuất từ "xin" độc lập ban đầu làm baseline cho occurrence = 0
    await textarea.fill("xin");
    await page.waitForTimeout(600);
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });
    const strokesXinBaseline = await svgWrapper.locator("polyline").evaluateAll((elements) =>
      elements.map((el) => el.getAttribute("points") || "")
    );
    expect(strokesXinBaseline.length).toBeGreaterThan(0);

    // 2. Gõ văn bản A gồm 2 từ lặp "xin xin chào ba" (từ "xin" thứ 2 nhận occurrence = 1)
    await textarea.fill("xin xin chào ba");
    await page.waitForTimeout(600);
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });

    // Thu thập danh sách stroke điểm vẽ của lượt 1
    const strokesRound1 = await svgWrapper.locator("polyline").evaluateAll((elements) =>
      elements.map((el) => el.getAttribute("points") || "")
    );
    expect(strokesRound1.length).toBeGreaterThan(strokesXinBaseline.length);

    // 3. Xóa sạch ô soạn thảo
    await textarea.fill("");
    await page.waitForTimeout(400);

    // Xác nhận wrapper trống và placeholder hiển thị
    await expect(svgWrapper.locator("svg")).toBeHidden();
    await expect(page.locator("#preview-placeholder")).toBeVisible();

    // 4. Gõ lại y nguyên văn bản A
    await textarea.fill("xin xin chào ba");
    await page.waitForTimeout(600);
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });

    const strokesRound2 = await svgWrapper.locator("polyline").evaluateAll((elements) =>
      elements.map((el) => el.getAttribute("points") || "")
    );

    // Khẳng định hình thái nét chữ của văn bản A sau khi xóa trắng trùng khớp 100% với lần 1
    expect(strokesRound2).toEqual(strokesRound1);

    // 5. Mở tệp mới chỉ chứa từ "xin" (tests/data/sample_word.txt)
    // Nếu hệ thống reset seed thành công, từ "xin" trong tệp mới nhận occurrence = 0
    // và nét vẽ phải trùng khớp 100% với strokesXinBaseline
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-open-file");
    const fileChooser = await fileChooserPromise;
    const sampleWordPath = path.resolve("tests/data/sample_word.txt");
    await fileChooser.setFiles(sampleWordPath);

    await page.waitForTimeout(600);
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });
    await expect(textarea).toHaveValue("xin");

    const strokesAfterImport = await svgWrapper.locator("polyline").evaluateAll((elements) =>
      elements.map((el) => el.getAttribute("points") || "")
    );

    // Chứng minh toán học: Mở tệp mới xóa sạch lịch sử seed và đặt lại occurrence = 0
    expect(strokesAfterImport).toEqual(strokesXinBaseline);
  });

  test("mở tệp Markdown (.md) và Word (.docx) nạp nội dung chính xác và kích hoạt reset seed", async ({ page }) => {
    test.setTimeout(90000);
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    await page.click('[data-tab="write"]');
    const textarea = page.locator("#editor-text");
    await expect(textarea).toBeVisible();
    const svgWrapper = page.locator("#paper-svg-wrapper");
    const selectFormat = page.locator("#select-format");

    // 1. Mở tệp Markdown (.md)
    let fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-open-file");
    let fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(path.resolve("tests/data/sample_import.md"));

    await page.waitForTimeout(600);
    await expect(textarea).toHaveValue("# Tiêu đề Markdown\n\nxin chào ba");
    await expect(selectFormat).toHaveValue("md");
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });
    const polylineCountMd = await svgWrapper.locator("polyline").count();
    expect(polylineCountMd).toBeGreaterThan(0);

    // 2. Mở tệp Word (.docx)
    fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-open-file");
    fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(path.resolve("tests/data/sample_import.docx"));

    // Đợi trích xuất DOCX và nạp vào textarea
    await expect(textarea).toHaveValue(/Tài liệu Word kiểm thử/, { timeout: 20000 });
    await expect(selectFormat).toHaveValue("md");
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });
    const polylineCountDocx = await svgWrapper.locator("polyline").count();
    expect(polylineCountDocx).toBeGreaterThan(0);
  });

  test("xử lý race condition: nạp tệp mới ngay khi đang render dở dang không bị kết quả cũ ghi đè", async ({ page }) => {
    test.setTimeout(90000);
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    await page.click('[data-tab="write"]');
    const textarea = page.locator("#editor-text");
    await expect(textarea).toBeVisible();
    const svgWrapper = page.locator("#paper-svg-wrapper");

    // 1. Lấy baseline nét vẽ của từ "xin"
    await textarea.fill("xin");
    await page.waitForTimeout(600);
    await expect(svgWrapper.locator("svg")).toBeVisible({ timeout: 10000 });
    const baselineXinStrokes = await svgWrapper.locator("polyline").evaluateAll((elements) =>
      elements.map((el) => el.getAttribute("points") || "")
    );
    expect(baselineXinStrokes.length).toBeGreaterThan(0);

    // 2. Kích hoạt render văn bản dài và chủ động đợi debounce 250ms để Worker tiếp nhận yêu cầu
    const longText = "Văn bản rất dài cần kết xuất tốn thời gian: " + "xin chào ba má bạn ".repeat(25);
    await textarea.fill(longText);

    // Chờ 260ms để debounce 250ms kích hoạt và yêu cầu write_text chắc chắn đã gửi xuống Worker
    await page.waitForTimeout(260);

    // 3. Trong khi Worker đang bận xử lý văn bản dài, lập tức mở tệp mới (sample_word.txt chỉ chứa "xin")
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#btn-open-file");
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(path.resolve("tests/data/sample_word.txt"));

    // Đợi đủ lâu để mọi tác vụ nền xử lý xong (1.5 giây)
    await page.waitForTimeout(1500);

    // 4. Khẳng định: Textarea giữ đúng nội dung tệp mới "xin"
    await expect(textarea).toHaveValue("xin");

    // 5. Khẳng định: Bản xem trước SVG hiển thị đúng nét vẽ của "xin", không bị dính văn bản dài cũ
    await expect(svgWrapper.locator("svg")).toBeVisible();
    const finalStrokes = await svgWrapper.locator("polyline").evaluateAll((elements) =>
      elements.map((el) => el.getAttribute("points") || "")
    );

    // Nét vẽ cuối cùng phải khớp hoàn toàn với baseline của "xin"
    expect(finalStrokes).toEqual(baselineXinStrokes);
  });

  test("Export Stale Guard: khóa xuất file khi đang render hoặc khi nội dung ô soạn thảo bị thay đổi", async ({ page }) => {
    test.setTimeout(60000);
    await page.goto("/");
    await expect(page.locator("#splash-screen")).toBeHidden({ timeout: 30000 });

    const welcomeModal = page.locator("#welcome-modal");
    if (await welcomeModal.isVisible()) {
      const bankFilePath = path.resolve("tests/data/kho_mau_tong_hop.json.gz");
      const fileChooserPromise = page.waitForEvent("filechooser");
      await page.click("#btn-welcome-import");
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(bankFilePath);
      await expect(welcomeModal).toBeHidden({ timeout: 15000 });
    }

    await page.click('[data-tab="write"]');
    const textarea = page.locator("#editor-text");
    await expect(textarea).toBeVisible();
    const btnExportXopp = page.locator("#btn-export-xopp");
    const warningsBox = page.locator("#editor-warnings");

    // 1. Soạn thảo văn bản và đợi kết xuất hoàn tất
    await textarea.fill("Nội dung xuất chuẩn");
    await page.waitForTimeout(600);
    await expect(page.locator("#paper-svg-wrapper svg")).toBeVisible({ timeout: 10000 });

    // 2. Tải thử file XOPP khi hợp lệ
    const downloadPromise = page.waitForEvent("download");
    await btnExportXopp.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("chuviet.xopp");

    // 3. Người dùng gõ sửa ô soạn thảo bằng văn bản dài cần thời gian kết xuất -> lập tức stale
    const longStaleText = "Văn bản sửa đổi dài cần kết xuất: " + "chữ viết tay tiếng Việt ".repeat(30);
    await textarea.fill(longStaleText);

    // Nhấn ngay nút xuất file khi đang stale (hoặc đang render)
    await btnExportXopp.click({ force: true });

    // Khẳng định: Cảnh báo hiển thị và chặn không cho xuất file cũ
    await expect(warningsBox).toBeVisible({ timeout: 10000 });
    await expect(warningsBox).toContainText("Bản xem trước đang được cập nhật hoặc nội dung đã thay đổi");
  });
});
