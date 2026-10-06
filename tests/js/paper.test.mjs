/**
 * paper.test.mjs -- Kiểm thử module dựng SVG từ dữ liệu .xopp (Node.js thuần, không framework).
 */
import assert from "node:assert";
import { parseXoppXml, renderPageSvgString } from "../../webapp/js/paper.js";

console.log("[Test Paper] Bắt đầu kiểm tra parser và renderer SVG...");

// 1. Mẫu XML XOPP đơn giản có 2 trang, 1 nét bút, nền lined
const sampleXoppXml = `<?xml version="1.0" standalone="no"?>
<xournal creator="hw_note" fileversion="4">
<title>Xournal++ document</title>
<page width="595.28" height="841.89">
<background type="solid" color="#ffffffff" style="lined" config="r1=24.0,m1=72.0"/>
<layer>
<stroke tool="pen" color="#1a237eff" capStyle="round" width="1.414">34.5 64.2 38.6 59.3 42.5 64.3</stroke>
</layer>
</page>
<page width="595.28" height="841.89">
<background type="solid" color="#ffffffff" style="graph" config="r1=14.17"/>
<layer>
<stroke tool="pen" color="#000000ff" capStyle="round" width="1.2">10.0 20.0 30.0 40.0</stroke>
<stroke tool="pen" color="#000000ff" capStyle="round" width="1.2">50.0 60.0 70.0 80.0</stroke>
</layer>
</page>
</xournal>`;

// Test 1: Parser phân tích XML
const doc = parseXoppXml(sampleXoppXml);
assert.strictEqual(doc.pages.length, 2, "Tài liệu phải có đúng 2 trang");

const page1 = doc.pages[0];
assert.strictEqual(page1.width, 595.28, "Bề ngang trang 1 phải là 595.28 pt");
assert.strictEqual(page1.height, 841.89, "Bề dọc trang 1 phải là 841.89 pt");
assert.strictEqual(page1.background.style, "lined", "Nền trang 1 phải là lined");
assert.strictEqual(page1.background.spacing, 24.0, "Spacing trang 1 phải là 24.0 pt");
assert.strictEqual(page1.strokes.length, 1, "Trang 1 phải có đúng 1 nét bút");
assert.strictEqual(page1.strokes[0].width, 1.414, "Độ dày nét bút trang 1 phải là 1.414");
assert.strictEqual(page1.strokes[0].color, "#1a237eff", "Màu nét bút trang 1 phải là #1a237eff");

const page2 = doc.pages[1];
assert.strictEqual(page2.background.style, "graph", "Nền trang 2 phải là graph");
assert.strictEqual(page2.strokes.length, 2, "Trang 2 phải có 2 nét bút");

// Test 2: Dựng SVG chuỗi cho trang 1 (nền lined)
const missingBoxes = [
  { page: 0, token: "chua_co", x: 30, y: 50, width: 40, height: 20, missing: ["chua_co"] },
];
const svg1 = renderPageSvgString(page1, { missingBoxes });
assert.ok(svg1.includes('<svg viewBox="0 0 595.28 841.89"'), "SVG phải có đúng viewBox");
assert.ok(svg1.includes('stroke="#1a237e"'), "SVG phải chứa màu mực chính xác");
assert.ok(svg1.includes('stroke-width="1.414"'), "SVG phải có độ dày nét chính xác");
assert.ok(svg1.includes('stroke-linecap="round"'), "SVG phải có bo tròn nét bút");
assert.ok(svg1.includes('class="paper-bg-line"'), "SVG lined phải có các đường kẻ ngang");
assert.ok(svg1.includes('class="missing-token-underline"'), "SVG phải có đường gạch đỏ từ thiếu mẫu");

// Test 3: Dựng SVG cho nền ruled (có đường lề đỏ)
const ruledPage = {
  width: 500,
  height: 700,
  background: { style: "ruled", color: "#ffffffff", spacing: 25, margin: 70 },
  strokes: [],
};
const svgRuled = renderPageSvgString(ruledPage);
assert.ok(svgRuled.includes('class="paper-bg-margin"'), "Nền ruled phải có đường lề đứng");

// Test 4: Dựng SVG cho nền dotted (có các chấm mờ)
const dottedPage = {
  width: 500,
  height: 700,
  background: { style: "dotted", color: "#ffffffff", spacing: 20 },
  strokes: [],
};
const svgDotted = renderPageSvgString(dottedPage);
assert.ok(svgDotted.includes('class="paper-bg-dot"'), "Nền dotted phải có các chấm mờ");

console.log("[Test Paper] PASS 100%! Toàn bộ các phép kiểm tra SVG đều chính xác.");
