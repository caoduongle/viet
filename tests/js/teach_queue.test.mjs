/**
 * teach_queue.test.mjs -- Kiểm thử logic quản lý hàng đợi dạy chữ trên Web Client.
 * Tuân thủ contracts/web-teach-queue-contract.md và Task T013.
 */
import test from "node:test";
import assert from "node:assert/strict";
import {
  TeachController,
  parseCharactersFromText,
  parseCatalogLabels,
} from "../../webapp/js/teach.js";

test("parseCharactersFromText: tách code point và bỏ qua khoảng trắng", () => {
  const result = parseCharactersFromText("cà phê");
  assert.deepEqual(result, ["c", "à", "p", "h", "ê"]);

  const repeated = parseCharactersFromText("a a a b b");
  assert.deepEqual(repeated, ["a", "b"]);

  const empty = parseCharactersFromText("   ");
  assert.deepEqual(empty, []);
});

test("parseCatalogLabels: bảo toàn nhãn nguyên tử của 5 dấu thanh rời", () => {
  const rawCatalog = [
    "dấu sắc",
    "dấu huyền",
    "dấu hỏi",
    "dấu ngã",
    "dấu nặng",
  ];
  const result = parseCatalogLabels(rawCatalog);
  assert.deepEqual(result, rawCatalog);
  assert.equal(result.length, 5);

  // Kiểm tra chuẩn hoá trim & deduplicate
  const dirty = ["  dấu sắc  ", "dấu sắc", "dấu hỏi"];
  assert.deepEqual(parseCatalogLabels(dirty), ["dấu sắc", "dấu hỏi"]);
});

test("TeachController: addCharactersFromText tách rời từng chữ cái", () => {
  const controller = new TeachController(null);
  controller.addCharactersFromText("xin");
  assert.deepEqual(controller.queue, ["x", "i", "n"]);

  // Thêm tiếp ký tự trùng lặp không bị nhân đôi
  controller.addCharactersFromText("in");
  assert.deepEqual(controller.queue, ["x", "i", "n"]);
});

test("TeachController: addCatalogLabels giữ nguyên 5 nhãn dấu thanh danh mục", () => {
  const controller = new TeachController(null);
  const tones = ["dấu huyền", "dấu sắc", "dấu hỏi", "dấu ngã", "dấu nặng"];
  controller.addCatalogLabels(tones);

  assert.deepEqual(controller.queue, tones);
  assert.ok(controller.queue.includes("dấu sắc"));
  assert.ok(!controller.queue.includes("d"));
  assert.ok(!controller.queue.includes("ấ"));
  assert.ok(!controller.queue.includes("u"));
});

test("TeachController: loadQueue phân biệt isCatalog true và false", () => {
  const controller = new TeachController(null);

  // isCatalog = true -> giữ nguyên nhãn
  controller.loadQueue(["dấu hỏi", "dấu nặng"], true);
  assert.deepEqual(controller.queue, ["dấu hỏi", "dấu nặng"]);

  // isCatalog = false -> phân rã ký tự
  controller.loadQueue(["ba"], false);
  assert.deepEqual(controller.queue, ["dấu hỏi", "dấu nặng", "b", "a"]);
});

test("TeachController: teachWordDirectly bảo toàn nhãn dấu thanh và phân rã từ thông thường", () => {
  const controller = new TeachController(null);
  controller.queue = ["x", "y"];

  // Dạy trực tiếp dấu thanh -> giữ nguyên 1 nhãn đưa lên đầu
  controller.teachWordDirectly("dấu hỏi");
  assert.equal(controller.queue[0], "dấu hỏi");
  assert.deepEqual(controller.queue, ["dấu hỏi", "x", "y"]);

  // Dạy trực tiếp từ thông thường -> phân rã các ký tự đưa lên đầu
  controller.teachWordDirectly("ca");
  assert.equal(controller.queue[0], "c");
  assert.equal(controller.queue[1], "a");
});
