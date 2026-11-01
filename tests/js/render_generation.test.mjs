import test from "node:test";
import assert from "node:assert/strict";
import { setWorkerInstance } from "../../webapp/js/app.js";
import {
  initWriteTab,
  triggerPreviewImmediate,
  getWritePreviewSyncState,
  resetDocumentSeedHistory,
  getRenderGenerationForTesting,
  resetWritePreviewForTesting,
} from "../../webapp/js/write.js";

class SyncMockWorker {
  constructor() {
    this.messagesSent = [];
    this.onmessage = null;
    this.onerror = null;
    this.onmessageerror = null;
    this.terminated = false;
  }

  postMessage(msg) {
    this.messagesSent.push(msg);
  }

  terminate() {
    this.terminated = true;
  }

  simulateResponse(id, ok, result, error) {
    if (this.onmessage) {
      this.onmessage({ data: { id, ok, result, error } });
    }
  }
}

function setupMockDom() {
  const elements = new Map();

  const mockEditor = {
    id: "editor-text",
    value: "Văn bản thử nghiệm ban đầu",
    style: {},
    classList: { add() {}, remove() {}, contains: () => false },
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {},
  };
  elements.set("editor-text", mockEditor);

  const mockWrapper = {
    id: "paper-svg-wrapper",
    innerHTML: "",
    style: {},
    appendChild() {},
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
    removeEventListener() {},
  };
  elements.set("paper-svg-wrapper", mockWrapper);

  const mockPlaceholder = {
    id: "preview-placeholder",
    style: { display: "flex" },
  };
  elements.set("preview-placeholder", mockPlaceholder);

  const mockStatusText = {
    id: "status-text",
    textContent: "",
  };
  elements.set("status-text", mockStatusText);

  const mockStatusIndicator = {
    id: "status-indicator",
    className: "",
  };
  elements.set("status-indicator", mockStatusIndicator);

  const makeMockElement = (id) => ({
    id,
    style: {},
    classList: { add() {}, remove() {}, contains: () => false },
    addEventListener() {},
    removeEventListener() {},
    appendChild() {},
    setAttribute() {},
    getAttribute: () => null,
    textContent: "",
    value: "",
  });

  globalThis.document = {
    getElementById: (id) => {
      if (elements.has(id)) return elements.get(id);
      const el = makeMockElement(id);
      elements.set(id, el);
      return el;
    },
    querySelector: (sel) => {
      if (sel === "#paper-svg-wrapper svg") return null;
      return null;
    },
    querySelectorAll: () => [],
    createElement: (tag) => makeMockElement(tag),
    addEventListener() {},
    removeEventListener() {},
  };

  globalThis.window = {
    addEventListener() {},
    removeEventListener() {},
    matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
  };

  return { mockEditor, mockWrapper, mockPlaceholder };
}

test.beforeEach(() => {
  resetWritePreviewForTesting();
});

test("Two-Layer Stale Guard: Kết quả render cũ bị hủy khi thế hệ kết xuất mới đã được yêu cầu", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  // 1. Kích hoạt render A
  mockEditor.value = "Tài liệu A ban đầu";
  triggerPreviewImmediate();
  const writeCalls1 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  assert.strictEqual(writeCalls1.length, 1, "Yêu cầu render A phải được gửi xuống Worker");
  const reqAId = writeCalls1[0].id;
  const genA = getRenderGenerationForTesting();

  // 2. Trong khi A đang chạy dở, người dùng đổi sang Tài liệu B
  mockEditor.value = "Tài liệu B mới";
  triggerPreviewImmediate();
  const genB = getRenderGenerationForTesting();
  assert.ok(genB > genA, "Thế hệ kết xuất của B phải lớn hơn A");

  // 3. Worker hoàn tất trả về kết quả cho A (stale)
  const fakeXoppA = "UEsDBBQAAAAIA...";
  mockWorker.simulateResponse(reqAId, true, {
    ok: true,
    xopp_base64: fakeXoppA,
    missing_token_boxes: [],
    requestId: writeCalls1[0].params.requestId,
  });

  // Chờ microtasks hoàn tất
  await new Promise((r) => setTimeout(r, 20));

  // Khẳng định: Kết quả A bị hủy bỏ, SVG wrapper không áp dụng
  const writeCalls2 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  assert.strictEqual(writeCalls2.length, 2, "Yêu cầu render B phải được xếp hàng và kích hoạt tiếp");
  const reqBId = writeCalls2[1].id;

  // 4. Worker hoàn tất trả về kết quả cho B (fresh)
  const fakeXoppB = "UEsDBBQAAAAIB...";
  mockWorker.simulateResponse(reqBId, true, {
    ok: true,
    xopp_base64: fakeXoppB,
    missing_token_boxes: [],
    requestId: writeCalls2[1].params.requestId,
  });

  await new Promise((r) => setTimeout(r, 20));
  const stateAfterB = getWritePreviewSyncState();
  assert.strictEqual(stateAfterB.isRendering, false);
});

test("Two-Layer Stale Guard: clearPreview tăng thế hệ kết xuất và hủy kết quả in-flight", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  mockEditor.value = "Văn bản sắp bị xóa";
  triggerPreviewImmediate();
  const initialGen = getRenderGenerationForTesting();
  const writeCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  assert.strictEqual(writeCalls.length, 1);
  const reqId = writeCalls[0].id;

  // Người dùng xóa sạch ô soạn thảo -> kích hoạt clearPreview
  mockEditor.value = "";
  triggerPreviewImmediate();
  const genAfterClear = getRenderGenerationForTesting();
  assert.ok(genAfterClear > initialGen, "Xóa trắng phải tăng currentRenderGeneration");

  // Worker trả về kết quả muộn của văn bản cũ
  mockWorker.simulateResponse(reqId, true, {
    ok: true,
    xopp_base64: "OLD_DATA",
    missing_token_boxes: [],
  });

  await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(mockEditor.value, "");
});

test("resetDocumentSeedHistory: kiểm tra phản hồi tường minh và xử lý lỗi an toàn", async () => {
  setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  // 1. Phản hồi thành công { ok: true }
  const p1 = resetDocumentSeedHistory();
  const call1 = mockWorker.messagesSent.find((m) => m.method === "clear_document_history");
  assert.ok(call1);
  mockWorker.simulateResponse(call1.id, true, { ok: true });
  const success = await p1;
  assert.strictEqual(success, true);

  // 2. Phản hồi lỗi { ok: false, error: 'Database locked' }
  const p2 = resetDocumentSeedHistory();
  const calls = mockWorker.messagesSent.filter((m) => m.method === "clear_document_history");
  const call2 = calls[calls.length - 1];
  mockWorker.simulateResponse(call2.id, true, { ok: false, error: "Database locked" });
  const failure1 = await p2;
  assert.strictEqual(failure1, false);

  // 3. Worker ném ngoại lệ
  const p3 = resetDocumentSeedHistory();
  const callsAfter = mockWorker.messagesSent.filter((m) => m.method === "clear_document_history");
  const call3 = callsAfter[callsAfter.length - 1];
  mockWorker.simulateResponse(call3.id, false, null, "Worker crashed");
  const failure2 = await p3;
  assert.strictEqual(failure2, false);
});
