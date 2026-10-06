/**
 * Script kiểm tra xác nhận G1:
 *   1. Kết nối HTTP tới server http://localhost:8000
 *   2. Kiểm tra tải index.html, pyodide.js, chuviettay.zip, version.json
 *   3. Nạp kho tổng hợp tests/data/kho_mau_tong_hop.json.gz qua BrowserBridge trong Pyodide
 *   4. Xác nhận thống kê kho mẫu hiển thị chính xác.
 */
import fs from "node:fs";
import { loadPyodide } from "pyodide";

async function verifyG1() {
  console.log("[Verify G1] 1. Kiểm tra HTTP Server phản hồi...");
  const endpoints = [
    "/index.html",
    "/version.json",
    "/pyodide/pyodide.js",
    "/pyodide/chuviettay.zip",
    "/pyodide/wheels/markdown_it_py-4.2.0-py3-none-any.whl",
  ];

  for (const ep of endpoints) {
    const url = `http://localhost:8000${ep}`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Endpoint ${url} trả về lỗi HTTP ${res.status}: ${res.statusText}`);
    }
    const buf = await res.arrayBuffer();
    console.log(`  [OK] ${ep} (${buf.byteLength} bytes)`);
  }

  console.log("[Verify G1] 2. Nạp kho tổng hợp tests/data/kho_mau_tong_hop.json.gz vào Pyodide...");
  const gzData = fs.readFileSync("tests/data/kho_mau_tong_hop.json.gz");
  console.log(`  Kho tổng hợp dung lượng: ${gzData.length} bytes`);

  const pyodide = await loadPyodide();
  pyodide.FS.mkdir("/repo");
  pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: process.cwd() }, "/repo");

  pyodide.runPython(`
import sys
sys.path.insert(0, "/repo")

from chuviettay.browser.bridge import BrowserBridge
bridge = BrowserBridge("/tmp/g1_bank.json.gz")

with open("/repo/tests/data/kho_mau_tong_hop.json.gz", "rb") as f:
    gz_bytes = f.read()

res = bridge.load_bank(gz_bytes)
assert res["ok"] is True, f"Nạp kho thất bại: {res}"
stats = bridge.get_stats()
assert stats["ok"] is True
data = stats["data"]
print("  Thống kê kho tổng hợp:", data["n_words"], "từ,", data["n_samples"], "mẫu,", data["n_letters"], "chữ cái.")
assert data["n_words"] >= 13, "Kho tổng hợp phải có ít nhất 13 từ"
assert data["n_samples"] >= 13, "Kho tổng hợp phải có ít nhất 13 mẫu"
`);

  console.log("[Verify G1] 3. Toàn bộ tiêu chí Checkpoint G1 MVP Kỹ thuật đã ĐẠT!");
}

verifyG1().catch((err) => {
  console.error("[Verify G1] [FAIL]:", err);
  process.exit(1);
});
