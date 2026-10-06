/**
 * Kiểm thử đảm bảo khi nạp chuviettay.browser.bridge trong Pyodide,
 * tuyệt đối không kéo theo tkinter, chuviettay.view, gui, hay cli vào sys.modules.
 */
import { loadPyodide } from "pyodide";
import path from "node:path";
import fs from "node:fs";

async function testBridgeNoTkinter() {
  console.log("[Test Bridge No Tkinter] Đang khởi tạo Pyodide...");
  const pyodide = await loadPyodide();

  // Mount repo để import mã nguồn
  pyodide.FS.mkdir("/repo");
  pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: process.cwd() }, "/repo");

  // Mount wheels để nạp markdown-it nếu cần
  const cacheWheels = path.resolve(".cache/wheels");
  if (fs.existsSync(cacheWheels)) {
    pyodide.FS.mkdir("/cache_wheels");
    pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: cacheWheels }, "/cache_wheels");
    pyodide.runPython(`
import sys
import os
import zipfile

site_packages = "/lib/python3.14/site-packages"
os.makedirs(site_packages, exist_ok=True)
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

for whl in os.listdir("/cache_wheels"):
    if whl.endswith(".whl"):
        with zipfile.ZipFile(f"/cache_wheels/{whl}") as z:
            z.extractall(site_packages)
`);
  }

  console.log("[Test Bridge No Tkinter] Đang import chuviettay.browser.bridge...");
  pyodide.runPython(`
import sys
sys.path.insert(0, "/repo")

from chuviettay.browser.bridge import BrowserBridge

bridge = BrowserBridge()
spec = bridge.get_canvas_spec()
assert spec["ok"] is True
assert spec["zoom"] == 10.0

defaults = bridge.get_write_defaults()
assert defaults["ok"] is True

forbidden_modules = [
    "tkinter",
    "_tkinter",
    "chuviettay.view",
    "chuviettay.gui",
    "chuviettay.cli",
    "chuviettay.fidelity",
]

loaded_forbidden = [m for m in forbidden_modules if m in sys.modules]
assert not loaded_forbidden, f"Phát hiện module cấm được nạp vào sys.modules: {loaded_forbidden}"
`);

  console.log("[Test Bridge No Tkinter] [PASS] Bridge hoàn toàn độc lập với Tkinter, View, GUI, CLI!");
}

testBridgeNoTkinter().catch((err) => {
  console.error("[Test Bridge No Tkinter] [FAIL]:", err);
  process.exit(1);
});
