/**
 * zip.test.mjs -- Kiểm tra module tạo file ZIP không nén (Stored ZIP).
 * Xác minh tính hợp lệ bằng lệnh chuẩn: python -m zipfile -t <file.zip>
 */
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { createZipArchive } from "../../webapp/js/export.js";

const outDir = path.resolve("tests/scratch");
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const zipPath = path.join(outDir, "test_archive.zip");

// Chuẩn bị dữ liệu mẫu
const files = [
  { name: "trang_1.svg", data: Buffer.from("<svg><text>Trang 1</text></svg>", "utf-8") },
  { name: "trang_2.svg", data: Buffer.from("<svg><text>Trang 2</text></svg>", "utf-8") },
  { name: "readme.txt", data: Buffer.from("Tệp xuất từ ChuVietTay Web Client.", "utf-8") },
];

console.log("[Test ZIP] Đang tạo file ZIP không nén...");
const zipBytes = createZipArchive(files);
fs.writeFileSync(zipPath, zipBytes);

console.log(`[Test ZIP] Đã ghi ${zipBytes.length} bytes vào ${zipPath}`);

// Kiểm tra bằng python -m zipfile -t
try {
  let pythonCmd = process.env.PYTHON;
  if (!pythonCmd) {
    pythonCmd = process.platform === "win32" ? "py -3" : "python3";
  }
  const result = execSync(`${pythonCmd} -m zipfile -t "${zipPath}"`, { encoding: "utf-8" });
  console.log("[Test ZIP] python -m zipfile -t kết quả:", result.trim() || "OK");
  console.log("[Test ZIP] PASS 100%!");
} catch (err) {
  console.error("[Test ZIP] LỖI khi giải nén ZIP bằng Python:", err);
  process.exit(1);
}
