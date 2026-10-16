/**
 * Script kiểm tra 8 ca Golden Master trong Pyodide 314.0.7 (Node.js).
 * Đảm bảo 100% SHA-256 của .xopp và _thieu.xopp trùng khớp tuyệt đối với CPython.
 */
import { loadPyodide } from "pyodide";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const VENDOR_LOCK_PATH = path.resolve("scripts/vendor_lock.json");
const CACHE_WHEEL_DIR = path.resolve(".cache/wheels");

function sha256File(filePath) {
  const data = fs.readFileSync(filePath);
  return crypto.createHash("sha256").update(data).digest("hex");
}

async function ensureVendorWheel(pkgName, meta) {
  fs.mkdirSync(CACHE_WHEEL_DIR, { recursive: true });
  const localPath = path.join(CACHE_WHEEL_DIR, meta.file_name);
  if (fs.existsSync(localPath)) {
    const hash = sha256File(localPath);
    if (hash === meta.sha256) {
      return localPath;
    }
    fs.unlinkSync(localPath);
  }

  console.log(`[Pyodide Golden] Tải wheel vendor ${pkgName}@${meta.version}...`);
  const res = await fetch(meta.url);
  if (!res.ok) {
    throw new Error(`Không thể tải ${meta.url}: ${res.statusText}`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  const hash = crypto.createHash("sha256").update(buf).digest("hex");
  if (hash !== meta.sha256) {
    throw new Error(`Sai mã băm SHA-256 cho ${pkgName}: kỳ vọng ${meta.sha256}, nhận được ${hash}`);
  }
  fs.writeFileSync(localPath, buf);
  return localPath;
}

async function runGoldenTests() {
  console.log("[Pyodide Golden] Đang chuẩn bị wheels từ scripts/vendor_lock.json...");
  const vendorLock = JSON.parse(fs.readFileSync(VENDOR_LOCK_PATH, "utf-8"));
  
  // Tải 3 wheel cho Markdown và Math
  const mditPath = await ensureVendorWheel("markdown-it-py", vendorLock.packages["markdown-it-py"]);
  const mditPluginsPath = await ensureVendorWheel("mdit-py-plugins", vendorLock.packages["mdit-py-plugins"]);
  const mdurlPath = await ensureVendorWheel("mdurl", vendorLock.packages["mdurl"]);

  console.log("[Pyodide Golden] Đang khởi tạo Pyodide 314.0.7...");
  const pyodide = await loadPyodide();

  console.log("[Pyodide Golden] Đang mount mã nguồn repo vào Pyodide filesystem...");
  pyodide.FS.mkdir("/repo");
  pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: process.cwd() }, "/repo");

  // Mount thư mục cache wheel
  pyodide.FS.mkdir("/cache_wheels");
  pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: CACHE_WHEEL_DIR }, "/cache_wheels");

  console.log("[Pyodide Golden] Đang cài đặt các wheel vendor vào site-packages...");
  pyodide.runPython(`
import sys
import os
import zipfile
import site

site_packages = site.getsitepackages()[0]
os.makedirs(site_packages, exist_ok=True)
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

wheels = [
    "mdurl-0.1.2-py3-none-any.whl",
    "mdit_py_plugins-0.6.1-py3-none-any.whl",
    "markdown_it_py-4.2.0-py3-none-any.whl",
]
for whl in wheels:
    whl_path = f"/cache_wheels/{whl}"
    with zipfile.ZipFile(whl_path) as z:
        z.extractall(site_packages)
`);

  pyodide.runPython(`
import sys
import os
import gzip
import hashlib
from pathlib import Path

# Đưa /repo lên đầu sys.path
sys.path.insert(0, "/repo")

# Shim pytest tối thiểu để import test_golden_master_real_path an toàn
import types
pytest_shim = types.ModuleType("pytest")
pytest_shim.mark = types.SimpleNamespace(
    parametrize=lambda *a, **k: (lambda f: f),
    gui=lambda f: f,
)
pytest_shim.fixture = lambda *a, **k: (lambda f: f)
sys.modules["pytest"] = pytest_shim

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.importer.markdown_importer import MarkdownImporter
from tests.test_golden_master_real_path import CASES, GOLDEN_REAL
from tests.test_letter_assembly_quality import _create_quality_test_bank
from tests.conftest import tiny_bank_dict
import json

def sha(path: str) -> str:
    return hashlib.sha256(gzip.decompress(Path(path).read_bytes())).hexdigest()

os.makedirs("/tmp/golden_run", exist_ok=True)

# Tạo tiny_bank_path
tiny_path = "/tmp/golden_run/tiny_bank.json.gz"
with gzip.open(tiny_path, "wt", encoding="utf-8") as f:
    json.dump(tiny_bank_dict(), f)

test_results = []

def check_file(path_str, expected_sha):
    p = Path(path_str) if path_str else None
    if not p or not p.exists():
        return {
            "path": str(path_str) if path_str else "",
            "exists": False,
            "actual_sha": None,
            "expected_sha": expected_sha,
            "byte_length": 0,
            "status": "MISSING",
        }
    actual_hash = sha(str(p))
    size = p.stat().st_size
    is_match = (actual_hash == expected_sha)
    return {
        "path": str(p),
        "exists": True,
        "actual_sha": actual_hash,
        "expected_sha": expected_sha,
        "byte_length": size,
        "status": "MATCH" if is_match else "MISMATCH",
    }

def record_test(name, main_file_dict, grid_file_dict=None):
    main_ok = (main_file_dict["status"] == "MATCH")
    grid_ok = True
    if grid_file_dict is not None and grid_file_dict.get("required"):
        grid_ok = (grid_file_dict["status"] == "MATCH")
    passed = main_ok and grid_ok
    test_results.append({
        "name": name,
        "passed": passed,
        "main": main_file_dict,
        "grid": grid_file_dict,
    })

# 4 ca tiêu chuẩn
for name in sorted(CASES):
    ctl = AppController(tiny_path)
    ctl.load_bank()
    text, opts = CASES[name]
    out = f"/tmp/golden_run/{name}.xopp"
    res = ctl.write_text(text, opts, out)
    main_res = check_file(out, GOLDEN_REAL[name]["xopp"])
    
    grid_res = None
    expected_thieu = GOLDEN_REAL[name].get("thieu")
    if expected_thieu:
        grid_res = check_file(res.missing_grid_path, expected_thieu)
        grid_res["required"] = True
    record_test(name, main_res, grid_res)

# Ca assemble_letters
qbank = _create_quality_test_bank(Path("/tmp/golden_run"))
qbank.save()
ctl_asm = AppController(qbank.path)
ctl_asm.load_bank()
out_asm = "/tmp/golden_run/assemble_letters.xopp"
res_asm = ctl_asm.write_text("pipeline", WriteOptions(seed=42, assemble_letters=True, auto_xh=True), out_asm)
record_test("assemble_letters", check_file(out_asm, GOLDEN_REAL["assemble_letters"]["xopp"]))

# Ca math
ctl_m = AppController(tiny_path)
ctl_m.load_bank()
doc_m = MarkdownImporter().import_text("xin ba $1,2$\\n\\n$$\\\\frac{1}{2}$$").document
out_m = "/tmp/golden_run/math.xopp"
res_m = ctl_m.write_document(doc_m, WriteOptions(seed=13), out_m)
record_test("math", check_file(out_m, GOLDEN_REAL["math"]["xopp"]))

# Ca table
ctl_t = AppController(tiny_path)
ctl_t.load_bank()
doc_t = MarkdownImporter().import_text("| xin | ba |\\n|---|---|\\n| 1 | 2 |").document
out_t = "/tmp/golden_run/table.xopp"
res_t = ctl_t.write_document(doc_t, WriteOptions(seed=17), out_t)
record_test("table", check_file(out_t, GOLDEN_REAL["table"]["xopp"]))

# Ca markdown_list
ctl_l = AppController(tiny_path)
ctl_l.load_bank()
doc_l = MarkdownImporter().import_text("# xin\\n\\n- ba\\n- chào\\n\\n1. xin\\n2. ba").document
out_l = "/tmp/golden_run/markdown_list.xopp"
res_l = ctl_l.write_document(doc_l, WriteOptions(seed=19, missing_grid=True), out_l)
main_l = check_file(out_l, GOLDEN_REAL["markdown_list"]["xopp"])
grid_l = check_file(res_l.missing_grid_path, GOLDEN_REAL["markdown_list"]["thieu"])
grid_l["required"] = True
record_test("markdown_list", main_l, grid_l)
`);

  const results = pyodide.globals.get("test_results").toJs({ dict_converter: Object.fromEntries });
  console.log("\n================ KẾT QUẢ GOLDEN MASTER TRONG PYODIDE ================");
  let allPassed = true;
  for (const item of results) {
    const { name, passed, main, grid } = item;
    if (passed) {
      if (grid && grid.required) {
        console.log(`  [PASS] ${name}: SHA-256 trùng khớp 100% (tệp chính & lưới phụ)`);
      } else {
        console.log(`  [PASS] ${name}: SHA-256 trùng khớp 100%`);
      }
    } else {
      allPassed = false;
      console.error(`  [FAIL] ${name}:`);
      if (main.status !== "MATCH") {
        console.error(`    - Tệp chính (${main.path}):`);
        if (!main.exists) {
          console.error(`      Trạng thái: [THIẾU TỆP KHÔNG TỒN TẠI]`);
        } else {
          console.error(`      Trạng thái: [KHÔNG KHỚP MÃ BĂM]`);
          console.error(`      Kỳ vọng:    ${main.expected_sha}`);
          console.error(`      Nhận:       ${main.actual_sha} (${main.byte_length} bytes)`);
        }
      }
      if (grid && grid.required && grid.status !== "MATCH") {
        console.error(`    - Tệp lưới phụ (${grid.path || "chưa tạo"}):`);
        if (!grid.exists) {
          console.error(`      Trạng thái: [THIẾU TỆP KHÔNG TỒN TẠI]`);
        } else {
          console.error(`      Trạng thái: [KHÔNG KHỚP MÃ BĂM]`);
          console.error(`      Kỳ vọng:    ${grid.expected_sha}`);
          console.error(`      Nhận:       ${grid.actual_sha} (${grid.byte_length} bytes)`);
        }
      }
    }
  }
  console.log("====================================================================\n");

  if (!allPassed) {
    process.exit(1);
  }
  console.log("Tất cả 8 ca Golden Master trong Pyodide 314.0.7 đã VƯỢT QUA thành công!");
}

runGoldenTests().catch((err) => {
  console.error("Lỗi khi chạy Pyodide Golden Tests:", err);
  process.exit(1);
});
