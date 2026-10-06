import test from "node:test";
import assert from "node:assert/strict";
import { createSvgFromStrokes } from "../../webapp/js/bank.js";

test("createSvgFromStrokes: trả về rỗng khi không có nét", () => {
  assert.equal(createSvgFromStrokes([]), "");
  assert.equal(createSvgFromStrokes(null), "");
});

test("createSvgFromStrokes: chữ số 2 (ký tự hẹp) có vector-effect non-scaling-stroke và viewBox chuẩn", () => {
  // Mẫu nét chữ số 2: chiều ngang hẹp ~3pt, chiều cao ~8pt (y từ -8 đến 0 trên baseline)
  const strokesDigit2 = [
    [0.0, -8.0, 1.5, -8.0, 3.0, -6.0, 0.0, 0.0, 3.2, 0.0]
  ];

  const svg = createSvgFromStrokes(strokesDigit2, 140, 56, { showBaseline: true });
  assert.ok(svg.startsWith("<svg"), "Phải sinh thẻ <svg>");
  assert.ok(svg.includes('vector-effect="non-scaling-stroke"'), "Phải có thuộc tính non-scaling-stroke để nét không bị zoom đậm");
  assert.ok(svg.includes('stroke-width="1.8"'), "Phải có stroke-width=1.8");

  // Kiểm tra viewBox có chiều cao tham chiếu tối thiểu (ít nhất 20pt)
  const vbMatch = svg.match(/viewBox="([^"]+)"/);
  assert.ok(vbMatch, "Phải có thuộc tính viewBox");
  const [vbX, vbY, vbW, vbH] = vbMatch[1].split(/\s+/).map(Number);

  assert.ok(vbH >= 20.0, `Chiều cao viewBox (${vbH}) phải đủ lớn để không làm méo nét`);
  assert.ok(vbW >= vbH * (140 / 56) * 0.9, "Chiều rộng viewBox phải cân xứng với tỷ lệ card");

  // Kiểm tra có vạch mốc chân chữ
  assert.ok(svg.includes('<line'), "Phải có đường mốc chân chữ baseline");
});

test("createSvgFromStrokes: từ dài nhiều nét ('nghiên cứu') mở rộng viewBox ngang mà không cắt nét", () => {
  // Bounding box rộng từ x=0 đến x=60
  const strokesLong = [
    [0.0, -8.0, 20.0, -8.0, 40.0, 0.0, 60.0, 0.0]
  ];

  const svg = createSvgFromStrokes(strokesLong, 140, 56);
  assert.ok(svg.includes('vector-effect="non-scaling-stroke"'));
  const vbMatch = svg.match(/viewBox="([^"]+)"/);
  const [vbX, vbY, vbW, vbH] = vbMatch[1].split(/\s+/).map(Number);

  assert.ok(vbW >= 60.0, "ViewBox phải bao trọn chiều rộng của từ dài");
  assert.ok(vbX <= 0.0, "Gốc vbX phải bao phủ điểm đầu của nét");
});
