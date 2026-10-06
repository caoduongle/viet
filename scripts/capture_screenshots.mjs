/**
 * capture_screenshots.mjs -- Chụp ảnh màn hình các tab ở 1280px và 768px (T077).
 * Lưu ảnh vào specs/020-web-client/screenshots/
 */
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const MIME_TYPES = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".mjs": "application/javascript",
  ".json": "application/json",
  ".webmanifest": "application/manifest+json",
  ".wasm": "application/wasm",
  ".zip": "application/zip",
  ".whl": "application/zip",
  ".gz": "application/gzip",
};

function createLocalServer(distDir, port) {
  const server = http.createServer((req, res) => {
    let reqPath = req.url.split("?")[0];
    if (reqPath === "/") reqPath = "/index.html";
    const filePath = path.join(distDir, reqPath);
    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      res.writeHead(404);
      res.end("Not Found");
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "Content-Type": MIME_TYPES[ext] || "application/octet-stream",
      "Access-Control-Allow-Origin": "*",
    });
    fs.createReadStream(filePath).pipe(res);
  });
  return new Promise((resolve) => {
    server.listen(port, () => resolve(server));
  });
}

async function capture() {
  const distDir = path.resolve("webapp/dist");
  const outputDir = path.resolve("specs/020-web-client/screenshots");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const server = await createLocalServer(distDir, 8089);
  const browser = await chromium.launch({ headless: true });

  const viewports = [
    { name: "desktop_1280", width: 1280, height: 800 },
    { name: "tablet_768", width: 768, height: 1024 },
  ];

  for (const vp of viewports) {
    console.log(`Đang chụp màn hình ở độ phân giải ${vp.name} (${vp.width}x${vp.height})...`);
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const page = await context.newPage();

    // Điều hướng vào app
    await page.goto("http://localhost:8089/");

    // Đợi splash ẩn
    await page.waitForSelector("#splash-screen", { state: "hidden", timeout: 25000 });

    // Đóng onboarding modal nếu xuất hiện bằng cách tạo kho mới
    const welcome = page.locator("#welcome-modal");
    if (await welcome.isVisible()) {
      await page.click("#btn-welcome-create");
      await welcome.waitFor({ state: "hidden", timeout: 10000 });
    }

    // Đợi status ready
    await page.waitForFunction(() => {
      const el = document.getElementById("status-text");
      return el && el.textContent.includes("Sẵn sàng");
    }, { timeout: 15000 });

    // 1. Chụp tab Viết chữ (mặc định)
    await page.fill("#editor-text", "Xin chào! Đây là chữ viết tay tự nhiên của bạn trên web.\nChạy 100% bằng WebAssembly Pyodide.");
    await page.waitForTimeout(2000); // Đợi preview render
    await page.screenshot({ path: path.join(outputDir, `${vp.name}_write_tab.png`) });
    console.log(`  -> Đã lưu ${vp.name}_write_tab.png`);

    // 2. Chụp tab Dạy chữ
    await page.click(".tab-btn[data-tab='teach']");
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outputDir, `${vp.name}_teach_tab.png`) });
    console.log(`  -> Đã lưu ${vp.name}_teach_tab.png`);

    // 3. Chụp tab Kho mẫu
    await page.click(".tab-btn[data-tab='bank']");
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outputDir, `${vp.name}_bank_tab.png`) });
    console.log(`  -> Đã lưu ${vp.name}_bank_tab.png`);

    // 4. Mở modal Hướng dẫn & chụp
    await page.click("#btn-header-guide");
    await page.waitForSelector("#guide-modal", { state: "visible", timeout: 5000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(outputDir, `${vp.name}_guide_modal.png`) });
    console.log(`  -> Đã lưu ${vp.name}_guide_modal.png`);

    await context.close();
  }

  await browser.close();
  server.close();
  console.log("Hoàn thành chụp toàn bộ màn hình!");
}

capture().catch((err) => {
  console.error("Lỗi khi chụp màn hình:", err);
  process.exit(1);
});
