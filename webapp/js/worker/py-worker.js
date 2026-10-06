/**
 * py-worker.js -- Web Worker chạy Pyodide 314.0.7 độc lập với Main Thread.
 *
 * Nhiệm vụ:
 *   1. Tự host toàn bộ runtime Pyodide và wheels, không gọi bất kỳ CDN ngoài nào.
 *   2. Báo cáo tiến trình khởi động chi tiết theo 4 bước thật (runtime -> stdlib -> gói -> wheels).
 *   3. Giao tiếp hai chiều với Main Thread qua định dạng chuẩn {id, method, params}.
 */

// Nạp loader Pyodide qua ESM
import { loadPyodide } from "../../pyodide/pyodide.mjs";
const PYODIDE_BASE = new URL("../../pyodide/", import.meta.url).href;

let pyodide = null;
let bridge = null;
const loadedWheels = new Set();

function postProgress(stage, percent, message) {
  self.postMessage({
    type: "PROGRESS",
    payload: { stage, percent, message },
  });
}

async function initPyodide() {
  try {
    postProgress("runtime", 25, "Đang nạp môi trường tính toán WebAssembly...");
    pyodide = await loadPyodide({
      indexURL: PYODIDE_BASE,
    });

    postProgress("stdlib", 50, "Đang nạp thư viện chuẩn Python...");
    // stdlib tự động được load bởi Pyodide từ python_stdlib.zip

    postProgress("package", 75, "Đang nạp lõi thuật toán Chữ Viết Tay...");
    // Tải và giải nén chuviettay.zip vào site-packages
    const zipUrl = new URL("chuviettay.zip", PYODIDE_BASE).href;
    const zipResp = await fetch(zipUrl);
    if (!zipResp.ok) {
      throw new Error(`Không thể nạp chuviettay.zip: ${zipResp.statusText}`);
    }
    const zipBuf = await zipResp.arrayBuffer();
    pyodide.FS.writeFile("/tmp/chuviettay.zip", new Uint8Array(zipBuf));

    pyodide.runPython(`
import sys
import os
import zipfile
import site

site_packages = site.getsitepackages()[0]
os.makedirs(site_packages, exist_ok=True)
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

with zipfile.ZipFile("/tmp/chuviettay.zip") as z:
    z.extractall(site_packages)
`);

    postProgress("wheels", 90, "Đang nạp các gói phân tích công thức toán & bảng...");
    const startupWheels = [
      "mdurl-0.1.2-py3-none-any.whl",
      "mdit_py_plugins-0.6.1-py3-none-any.whl",
      "markdown_it_py-4.2.0-py3-none-any.whl",
    ];

    for (const whl of startupWheels) {
      const whlUrl = new URL(`wheels/${whl}`, PYODIDE_BASE).href;
      const resp = await fetch(whlUrl);
      if (!resp.ok) {
        throw new Error(`Không thể nạp wheel ${whl}: ${resp.statusText}`);
      }
      const buf = await resp.arrayBuffer();
      pyodide.FS.writeFile(`/tmp/${whl}`, new Uint8Array(buf));
      pyodide.runPython(`
with zipfile.ZipFile("/tmp/${whl}") as z:
    z.extractall(site_packages)
`);
    }

    // Khởi tạo BrowserBridge
    pyodide.runPython(`
from chuviettay.browser.bridge import BrowserBridge
_bridge = BrowserBridge()
_bridge.init()
`);

    postProgress("ready", 100, "Khởi tạo thành công! Sẵn sàng phục vụ.");
    self.postMessage({ type: "READY" });
  } catch (err) {
    self.postMessage({
      type: "ERROR",
      payload: { message: err.message, stack: err.stack },
    });
  }
}

self.onmessage = async (e) => {
  const { id, method, params } = e.data;
  if (!id) return;

  if (!pyodide) {
    self.postMessage({
      id,
      ok: false,
      error: "Hệ thống Pyodide chưa khởi tạo xong.",
    });
    return;
  }

  try {
    let result = null;
    if (method === "get_canvas_spec") {
      result = pyodide.runPython(`_bridge.get_canvas_spec()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "get_write_defaults") {
      result = pyodide.runPython(`_bridge.get_write_defaults()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "get_stats") {
      result = pyodide.runPython(`_bridge.get_stats()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "load_bank") {
      const { gzBytes, createIfMissing } = params || {};
      const uint8 = new Uint8Array(gzBytes);
      pyodide.FS.writeFile("/tmp/upload_bank.json.gz", uint8);
      pyodide.runPython(`
with open("/tmp/upload_bank.json.gz", "rb") as f:
    _data = f.read()
_res = _bridge.load_bank(_data, create_if_missing=${createIfMissing ? "True" : "False"})
`);
      result = pyodide.globals.get("_res").toJs({ dict_converter: Object.fromEntries });
    } else if (method === "export_bank") {
      pyodide.runPython(`_bank_bytes = _bridge.export_bank()`);
      const pyBytes = pyodide.globals.get("_bank_bytes").toJs();
      result = pyBytes;
    } else if (method === "write_text") {
      const { text, options, format } = params || {};
      pyodide.globals.set("_write_text", text || "");
      pyodide.globals.set("_write_fmt", format || "txt");
      pyodide.globals.set("_write_opts_json", JSON.stringify(options || {}));
      pyodide.runPython(`
import json
_opts = json.loads(_write_opts_json)
_write_res = _bridge.write_text(_write_text, _opts, fmt=_write_fmt)
`);
      result = pyodide.globals.get("_write_res").toJs({ dict_converter: Object.fromEntries });
    } else if (method === "teach_sample") {
      const { label, strokes, width, category, calibrating, pixel_strokes, deferred_save } = params || {};
      pyodide.globals.set("_teach_label", label || "");
      pyodide.globals.set("_teach_strokes_json", JSON.stringify(strokes || null));
      pyodide.globals.set("_teach_px_strokes_json", JSON.stringify(pixel_strokes || null));
      pyodide.globals.set("_teach_width", width != null ? width : null);
      pyodide.globals.set("_teach_cat", category || "words");
      pyodide.globals.set("_teach_calib", Boolean(calibrating));
      pyodide.globals.set("_teach_deferred", deferred_save !== false);
      pyodide.runPython(`
import json
_strokes = json.loads(_teach_strokes_json) if _teach_strokes_json != "null" else None
_px_strokes = json.loads(_teach_px_strokes_json) if _teach_px_strokes_json != "null" else None
_teach_res = _bridge.teach_sample(
    _teach_label,
    strokes=_strokes,
    width=_teach_width,
    category=_teach_cat,
    calibrating=_teach_calib,
    pixel_strokes=_px_strokes,
    deferred_save=_teach_deferred,
)
`);
      result = pyodide.globals.get("_teach_res").toJs({ dict_converter: Object.fromEntries });
    } else if (method === "pick_calibration_word") {
      result = pyodide.runPython(`_bridge.pick_calibration_word()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "get_missing_queue") {
      const { kind, limit, exclude } = params || {};
      pyodide.globals.set("_q_kind", kind || "essentials");
      pyodide.globals.set("_q_limit", limit || 50);
      pyodide.globals.set("_q_ex_json", JSON.stringify(exclude || []));
      pyodide.runPython(`
import json
_q_ex = json.loads(_q_ex_json)
_q_res = _bridge.get_missing_queue(kind=_q_kind, limit=_q_limit, exclude=_q_ex)
`);
      result = pyodide.globals.get("_q_res").toJs({ dict_converter: Object.fromEntries });
    } else if (method === "list_words") {
      result = pyodide.runPython(`_bridge.list_words()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "list_letters") {
      result = pyodide.runPython(`_bridge.list_letters()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "list_label_samples") {
      const { label, category } = params || {};
      pyodide.globals.set("_lbl", label || "");
      pyodide.globals.set("_lbl_cat", category || "words");
      result = pyodide.runPython(`_bridge.list_label_samples(_lbl, category=_lbl_cat)`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "drop_label") {
      const { label, category } = params || {};
      pyodide.globals.set("_drop_lbl", label || "");
      pyodide.globals.set("_drop_cat", category || "words");
      result = pyodide.runPython(`_bridge.drop_label(_drop_lbl, category=_drop_cat)`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "get_latex_symbols") {
      result = pyodide.runPython(`_bridge.get_latex_symbols()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "import_docx") {
      const lazyWheels = [
        "typing_extensions-4.15.0-py3-none-any.whl",
        "python_docx-1.1.2-py3-none-any.whl",
        "lxml-6.1.3-cp314-cp314-pyemscripten_2026_0_wasm32.whl",
      ];
      for (const whl of lazyWheels) {
        if (!loadedWheels.has(whl)) {
          const whlUrl = new URL(`wheels/${whl}`, PYODIDE_BASE).href;
          const resp = await fetch(whlUrl);
          if (resp.ok) {
            const buf = await resp.arrayBuffer();
            pyodide.FS.writeFile(`/tmp/${whl}`, new Uint8Array(buf));
            pyodide.runPython(`
import zipfile
import site
site_packages = site.getsitepackages()[0]
with zipfile.ZipFile("/tmp/${whl}") as z:
    z.extractall(site_packages)
`);
            loadedWheels.add(whl);
          }
        }
      }
      const { bytes } = params || {};
      const uint8 = new Uint8Array(bytes);
      pyodide.FS.writeFile("/tmp/input.docx", uint8);
      pyodide.runPython(`
with open("/tmp/input.docx", "rb") as f:
    _dbytes = f.read()
_docx_res = _bridge.import_docx(_dbytes)
`);
      result = pyodide.globals.get("_docx_res").toJs({ dict_converter: Object.fromEntries });
    } else if (method === "flush_save") {
      result = pyodide.runPython(`_bridge.flush_save()`).toJs({ dict_converter: Object.fromEntries });
    } else if (method === "sync_save") {
      const { diskGzBytes } = params || {};
      if (diskGzBytes && diskGzBytes.length > 0) {
        const uint8 = new Uint8Array(diskGzBytes);
        pyodide.FS.writeFile("/tmp/active_bank.json.gz", uint8);
      }
      pyodide.runPython(`
_bridge.flush_save()
_synced_bytes = _bridge.export_bank()
`);
      const pyBytes = pyodide.globals.get("_synced_bytes").toJs();
      result = pyBytes;
    } else if (method === "export_check") {
      result = pyodide.runPython(`_bridge.export_check()`).toJs({ dict_converter: Object.fromEntries });
    } else {
      throw new Error(`Phương thức không được hỗ trợ: ${method}`);
    }

    self.postMessage({ id, ok: true, result });
  } catch (err) {
    self.postMessage({
      id,
      ok: false,
      error: err.message,
    });
  }
};

initPyodide();
