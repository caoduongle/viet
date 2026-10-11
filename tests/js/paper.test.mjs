/**
 * paper.test.mjs -- Kiểm thử module dựng SVG từ dữ liệu .xopp (Node.js thuần, không framework).
 */
import assert from "node:assert";
import { parseXoppXml, renderPageSvgString, getPaperPixelDimensions, PT_TO_PX } from "../../webapp/js/paper.js";

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

// Test 3: Dựng SVG cho nền lined (có đường lề đỏ) và ruled (chỉ có dòng ngang)
const linedPage = {
  width: 500,
  height: 700,
  background: { style: "lined", color: "#ffffffff", spacing: 25, margin: 70 },
  strokes: [],
};
const svgLined = renderPageSvgString(linedPage);
assert.ok(svgLined.includes('class="paper-bg-margin"'), "Nền lined phải có đường lề đứng");

const ruledPage = {
  width: 500,
  height: 700,
  background: { style: "ruled", color: "#ffffffff", spacing: 25, margin: 70 },
  strokes: [],
};
const svgRuled = renderPageSvgString(ruledPage);
assert.ok(!svgRuled.includes('class="paper-bg-margin"'), "Nền ruled không được có đường lề đứng");
assert.ok(svgRuled.includes('class="paper-bg-line"'), "Nền ruled phải có dòng kẻ ngang");

// Test 4: Dựng SVG cho nền dotted (có các chấm mờ)
const dottedPage = {
  width: 500,
  height: 700,
  background: { style: "dotted", color: "#ffffffff", spacing: 20 },
  strokes: [],
};
const svgDotted = renderPageSvgString(dottedPage);
assert.ok(svgDotted.includes('class="paper-bg-dot"'), "Nền dotted phải có các chấm mờ");

// Test 6: Kiểm tra lề âm m1 và dải biên Xournal++ [80, height - 60]
const rightLinedPage = {
  width: 500,
  height: 700,
  background: { style: "lined", color: "#ffffffff", spacing: 24.0, margin: -72.0 },
  strokes: [],
};
const svgRightLined = renderPageSvgString(rightLinedPage);
assert.ok(svgRightLined.includes('class="paper-bg-margin"'), "Nền lined lề âm phải có đường lề đứng");
assert.ok(svgRightLined.includes('x1="428"'), "Đường lề âm m1=-72 trên trang rộng 500 phải nằm ở x=428 (500 - 72)");
assert.ok(svgRightLined.includes('y1="80"'), "Dòng kẻ ngang đầu tiên phải bắt đầu tại y=80 (HEADER_SIZE)");

// Test 7: Phân tích config hỗ trợ cả dấu phẩy và chấm phẩy, cùng các thuộc tính mở rộng
const xmlWithCustomConfig = `<?xml version="1.0" standalone="no"?>
<xournal creator="hw_note" fileversion="4">
<page width="600" height="800">
<background type="solid" color="#1e1e1eff" style="lined" config="r1=20;m1=-50;lw=0.8;f1=40a0ff;f2=ff0080;bli=5;blw=1.5"/>
<layer/>
</page>
</xournal>`;
const docCustom = parseXoppXml(xmlWithCustomConfig);
const pageCustom = docCustom.pages[0];
assert.strictEqual(pageCustom.background.spacing, 20.0, "spacing r1 phải là 20");
assert.strictEqual(pageCustom.background.margin, -50.0, "margin m1 phải là -50");
assert.strictEqual(pageCustom.background.lineWidth, 0.8, "lineWidth lw phải là 0.8");
assert.strictEqual(pageCustom.background.primaryColor, "40a0ff", "primaryColor f1 phải là 40a0ff");

// Test 8: Nền tối tự động đảo màu nét đảm bảo tương phản
const darkPage = {
  width: 500,
  height: 700,
  background: { style: "lined", color: "#1e1e1eff", spacing: 24.0, margin: 72.0 },
  strokes: [],
};
const svgDark = renderPageSvgString(darkPage);
assert.ok(svgDark.includes('stroke="#434343"'), "Nền tối phải dùng màu nét #434343 cho dòng ngang");
assert.ok(svgDark.includes('stroke="#220080"'), "Nền tối phải dùng màu nét #220080 cho lề dọc");

// Test 9: Khuông nhạc (staves) và lưới tam giác đều (iso_graph)
const stavesPage = {
  width: 500,
  height: 700,
  background: { style: "staves", color: "#ffffffff" },
  strokes: [],
};
const svgStaves = renderPageSvgString(stavesPage);
assert.ok(svgStaves.includes('x1="50"'), "Khuông nhạc phải chừa lề 50pt mỗi bên");
assert.ok(svgStaves.includes('y1="80"'), "Khuông nhạc đầu tiên phải bắt đầu tại y=80");

console.log("[Test Paper] PASS 100%! Toàn bộ các phép kiểm tra SVG đều chính xác.");

