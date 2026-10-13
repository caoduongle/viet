import test from "node:test";
import assert from "node:assert/strict";
import { parseSeed } from "../webapp/js/write.js";

test("parseSeed: chấp nhận 0 là seed hợp lệ (không bị fallback về 42)", () => {
  const res = parseSeed("0", 42);
  assert.strictEqual(res.seed, 0);
  assert.strictEqual(res.valid, true);
  assert.strictEqual(res.message, null);
});

test("parseSeed: chấp nhận các số nguyên hợp lệ trong [0, 4294967295]", () => {
  assert.deepStrictEqual(parseSeed("1", 42), { seed: 1, valid: true, message: null });
  assert.deepStrictEqual(parseSeed("99999", 42), { seed: 99999, valid: true, message: null });
  assert.deepStrictEqual(parseSeed("  100  ", 42), { seed: 100, valid: true, message: null });
  assert.deepStrictEqual(parseSeed("4294967295", 42), { seed: 4294967295, valid: true, message: null });
});

test("parseSeed: từ chối số âm, số thực, vượt giới hạn 2^32-1 và giữ seed hiện tại", () => {
  const neg = parseSeed("-5", 42);
  assert.strictEqual(neg.seed, 42);
  assert.strictEqual(neg.valid, false);

  const floatVal = parseSeed("3.14", 42);
  assert.strictEqual(floatVal.seed, 42);
  assert.strictEqual(floatVal.valid, false);

  const overflow = parseSeed("4294967296", 42);
  assert.strictEqual(overflow.seed, 42);
  assert.strictEqual(overflow.valid, false);

  const nanVal = parseSeed("abc", 42);
  assert.strictEqual(nanVal.seed, 42);
  assert.strictEqual(nanVal.valid, false);
});

test("parseSeed: ô rỗng hoặc null/undefined giữ nguyên seed hiện tại và cảnh báo nhẹ", () => {
  const empty = parseSeed("", 42);
  assert.strictEqual(empty.seed, 42);
  assert.strictEqual(empty.valid, false);

  const spaces = parseSeed("   ", 42);
  assert.strictEqual(spaces.seed, 42);
  assert.strictEqual(spaces.valid, false);

  const nullVal = parseSeed(null, 42);
  assert.strictEqual(nullVal.seed, 42);
  assert.strictEqual(nullVal.valid, false);

  const undefinedVal = parseSeed(undefined, 42);
  assert.strictEqual(undefinedVal.seed, 42);
  assert.strictEqual(undefinedVal.valid, false);
});

test("DOM: index.html và write.js có phần tử và xử lý lỗi trực quan #opt-seed-error", async () => {
  const fs = await import("node:fs/promises");
  const path = await import("node:path");

  const indexPath = path.resolve("webapp/index.html");
  const indexHtml = await fs.readFile(indexPath, "utf-8");
  assert.ok(indexHtml.includes('id="opt-seed-error"'), "webapp/index.html phải có thẻ #opt-seed-error");

  const writeJsPath = path.resolve("webapp/js/write.js");
  const writeJs = await fs.readFile(writeJsPath, "utf-8");
  assert.ok(writeJs.includes("optSeedError"), "webapp/js/write.js phải có xử lý optSeedError");
  assert.ok(writeJs.includes("is-invalid"), "webapp/js/write.js phải thêm/bỏ class is-invalid");
});

