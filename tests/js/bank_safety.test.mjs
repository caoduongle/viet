import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { escapeHtml } from "../../webapp/js/html-utils.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");

test("escapeHtml: xử lý an toàn các ký tự HTML nguy hiểm", () => {
  assert.strictEqual(escapeHtml("<script>alert(1)</script>"), "&lt;script&gt;alert(1)&lt;/script&gt;");
  assert.strictEqual(escapeHtml('a & b "quoted" \'single\''), "a &amp; b &quot;quoted&quot; &#39;single&#39;");
});

test("escapeHtml: giữ nguyên ký tự an toàn và chuỗi rỗng / null / undefined", () => {
  assert.strictEqual(escapeHtml(""), "");
  assert.strictEqual(escapeHtml(null), "");
  assert.strictEqual(escapeHtml(undefined), "");
  assert.strictEqual(escapeHtml("Xin chào Việt Nam 123"), "Xin chào Việt Nam 123");
});

test("escapeHtml: xử lý ký tự toán học và ký hiệu so sánh", () => {
  assert.strictEqual(escapeHtml("<"), "&lt;");
  assert.strictEqual(escapeHtml(">"), "&gt;");
  assert.strictEqual(escapeHtml("&"), "&amp;");
  assert.strictEqual(escapeHtml("x < y && y > z"), "x &lt; y &amp;&amp; y &gt; z");
});

test("bank.js: tuân thủ hợp đồng bảo mật DOM (escapeHtml) và dựng SVG xem thử thật (missing_grid: false)", () => {
  const bankJs = fs.readFileSync(path.join(repoRoot, "webapp/js/bank.js"), "utf-8");
  assert.ok(bankJs.includes('import { escapeHtml } from "./html-utils.js"'));
  assert.ok(bankJs.includes("decompressXoppBase64"));
  assert.ok(bankJs.includes("parseXoppXml"));
  assert.ok(bankJs.includes("renderPageSvgElement"));
  assert.ok(bankJs.includes("missing_grid: false"));
  assert.ok(bankJs.includes('background: "plain"'));
  assert.ok(!bankJs.includes("${item.label}"), "Không được nội suy trực tiếp item.label chưa escape vào innerHTML");
  assert.ok(!bankJs.includes("Lỗi tải mẫu: ${err.message}"), "Không được nội suy trực tiếp err.message chưa escape vào innerHTML");
});
