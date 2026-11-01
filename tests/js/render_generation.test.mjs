import test from "node:test";
import assert from "node:assert/strict";
import zlib from "node:zlib";
import { setWorkerInstance, clearPendingWorkerRequestsForTesting } from "../../webapp/js/app.js";
import {
  initWriteTab,
  triggerPreviewImmediate,
  getWritePreviewSyncState,
  resetDocumentSeedHistory,
  getRenderGenerationForTesting,
  getRenderedGenerationForTesting,
  isRenderStaleForTesting,
  canExport,
  resetWritePreviewForTesting,
} from "../../webapp/js/write.js";

function createValidXoppBase64(customText = "test") {
  const xml = `<?xml version="1.0" standalone="no"?>
<xournal version="0.4.8">
  <page width="595.28" height="841.89">
    <layer>
      <stroke tool="pen" color="#000000ff" width="1.41">100 100 105 105</stroke>
      <text font="Sans" size="12" x="100" y="100" color="#000000ff">${customText}</text>
    </layer>
  </page>
</xournal>`;
  return zlib.gzipSync(Buffer.from(xml, "utf-8")).toString("base64");
}

class SyncMockWorker {
  constructor() {
    this.messagesSent = [];
    this.onmessage = null;
    this.onerror = null;
    this.onmessageerror = null;
    this.terminated = false;
    this.autoAckReset = true;
  }

  postMessage(msg) {
    this.messagesSent.push(msg);
    if (this.autoAckReset && msg.method === "clear_document_history") {
      // Phản hồi tức thời để không giữ timeout 60s trong app.js
      Promise.resolve().then(() => {
        this.simulateResponse(msg.id, true, { ok: true });
      });
    }
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
  const eventListeners = new Map();

  const makeMockElement = (tagOrId) => {
    const el = {
      tag: tagOrId,
      id: tagOrId,
      style: {},
      clientWidth: 800,
      clientHeight: 1000,
      classList: {
        classes: new Set(),
        add(c) { this.classes.add(c); },
        remove(c) { this.classes.delete(c); },
        contains(c) { return this.classes.has(c); },
      },
      attributes: new Map(),
      setAttribute(k, v) { this.attributes.set(k, String(v)); },
      getAttribute(k) { return this.attributes.get(k) || null; },
      removeAttribute(k) { this.attributes.delete(k); },
      setAttributeNS(ns, k, v) { this.attributes.set(k, String(v)); },
      getAttributeNS(ns, k) { return this.attributes.get(k) || null; },
      children: [],
      appendChild(node) { this.children.push(node); },
      replaceChildren(...nodes) { this.children = nodes; },
      querySelector(sel) {
        if (sel === "svg") {
          return this.children.find((c) => c.tag === "svg") || this.children[0] || null;
        }
        return null;
      },
      querySelectorAll(sel) { return []; },
      textContent: "",
      value: "",
      addEventListener(type, fn) {
        if (!eventListeners.has(tagOrId)) eventListeners.set(tagOrId, new Map());
        const idEvents = eventListeners.get(tagOrId);
        if (!idEvents.has(type)) idEvents.set(type, []);
        idEvents.get(type).push(fn);
      },
      removeEventListener(type, fn) {
        const idEvents = eventListeners.get(tagOrId);
        if (!idEvents || !idEvents.has(type)) return;
        const arr = idEvents.get(type).filter((f) => f !== fn);
        idEvents.set(tagOrId, arr);
      },
      dispatchEvent(event) {
        const idEvents = eventListeners.get(tagOrId);
        if (idEvents && idEvents.has(event.type)) {
          for (const fn of idEvents.get(event.type)) {
            fn(event);
          }
        }
      },
    };
    return el;
  };

  const mockEditor = makeMockElement("editor-text");
  mockEditor.value = "Văn bản thử nghiệm ban đầu";
  elements.set("editor-text", mockEditor);

  const mockWrapper = makeMockElement("paper-svg-wrapper");
  elements.set("paper-svg-wrapper", mockWrapper);

  const mockPlaceholder = makeMockElement("preview-placeholder");
  mockPlaceholder.style = { display: "flex" };
  elements.set("preview-placeholder", mockPlaceholder);

  const mockStatusText = makeMockElement("status-text");
  elements.set("status-text", mockStatusText);

  const mockStatusIndicator = makeMockElement("status-indicator");
  elements.set("status-indicator", mockStatusIndicator);

  const mockWarningsBox = makeMockElement("editor-warnings");
  mockWarningsBox.style = { display: "none" };
  elements.set("editor-warnings", mockWarningsBox);

  // Export buttons
  const btnIds = [
    "btn-export-xopp",
    "btn-export-png",
    "btn-export-svg",
    "btn-export-zip",
    "btn-print-pdf",
  ];
  for (const bId of btnIds) {
    elements.set(bId, makeMockElement(bId));
  }

  globalThis.document = {
    getElementById: (id) => {
      if (elements.has(id)) return elements.get(id);
      const el = makeMockElement(id);
      elements.set(id, el);
      return el;
    },
    querySelector: (sel) => {
      if (sel === "#paper-svg-wrapper svg") {
        const wrapper = elements.get("paper-svg-wrapper");
        return wrapper ? wrapper.querySelector("svg") : null;
      }
      return null;
    },
    querySelectorAll: () => [],
    createElement: (tag) => makeMockElement(tag),
    createElementNS: (ns, tag) => makeMockElement(tag),
    addEventListener() {},
    removeEventListener() {},
  };

  globalThis.window = {
    addEventListener() {},
    removeEventListener() {},
    matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
    print: () => {},
  };

  return { mockEditor, mockWrapper, mockPlaceholder, elements };
}

test.beforeEach(() => {
  resetWritePreviewForTesting();
  clearPendingWorkerRequestsForTesting();
});

test.afterEach(() => {
  resetWritePreviewForTesting();
  clearPendingWorkerRequestsForTesting();
});

test("Two-Stage Stale Guard & Atomic State Commit: Giải nén XOPP hợp lệ và cập nhật giao diện thành công cho B", async () => {
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

  // 3. Worker hoàn tất trả về kết quả cho A (stale) với fixture XOPP gzip hợp lệ
  const validXoppA = createValidXoppBase64("Tài liệu A");
  mockWorker.simulateResponse(reqAId, true, {
    ok: true,
    xopp_base64: validXoppA,
    missing_token_boxes: [],
    requestId: writeCalls1[0].params.requestId,
  });

  // Chờ microtasks hoàn tất
  await new Promise((r) => setTimeout(r, 30));

  // Khẳng định: Kết quả A bị hủy bỏ bởi Stale Guard
  const writeCalls2 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  assert.strictEqual(writeCalls2.length, 2, "Yêu cầu render B phải được xếp hàng và kích hoạt tiếp");
  const reqBId = writeCalls2[1].id;

  // 4. Worker hoàn tất trả về kết quả cho B (fresh) với fixture XOPP gzip hợp lệ
  const validXoppB = createValidXoppBase64("Tài liệu B");
  mockWorker.simulateResponse(reqBId, true, {
    ok: true,
    xopp_base64: validXoppB,
    missing_token_boxes: [],
    requestId: writeCalls2[1].params.requestId,
  });

  // Đợi render B và giải nén bất đồng bộ hoàn tất
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 20));
    if (!getWritePreviewSyncState().isRendering) break;
  }

  const stateAfterB = getWritePreviewSyncState();
  assert.strictEqual(stateAfterB.isRendering, false);
  const actualGenB = writeCalls2[1].params.requestId;
  assert.strictEqual(getRenderedGenerationForTesting(), actualGenB, "Thế hệ render đã commit phải khớp với thế hệ của B");
  assert.strictEqual(isRenderStaleForTesting(), false, "Trạng thái render không còn stale sau khi B hoàn tất");
  assert.strictEqual(canExport(), true, "canExport() phải trả về true khi B render thành công và nội dung khớp");
});

test("Export Stale Guard: Khóa xuất file khi đang render hoặc khi nội dung ô soạn thảo bị thay đổi", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  // Khi chưa render: canExport() phải là false
  assert.strictEqual(canExport(), false, "Chưa render thì không được phép xuất");

  // Soạn thảo và hoàn tất render
  mockEditor.value = "Nội dung chuẩn";
  triggerPreviewImmediate();
  const writeCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  const reqId = writeCalls[0].id;
  const validXopp = createValidXoppBase64("Nội dung chuẩn");

  mockWorker.simulateResponse(reqId, true, {
    ok: true,
    xopp_base64: validXopp,
    missing_token_boxes: [],
    requestId: writeCalls[0].params.requestId,
  });

  await new Promise((r) => setTimeout(r, 50));
  assert.strictEqual(canExport(), true, "Sau khi render thành công thì cho phép xuất");

  // Người dùng gõ phím thêm nội dung (input event) -> lập tức stale
  mockEditor.value = "Nội dung chuẩn đã bị sửa đổi";
  mockEditor.dispatchEvent({ type: "input" });
  assert.strictEqual(isRenderStaleForTesting(), true, "Gõ phím phải đánh dấu isRenderStale = true");
  assert.strictEqual(canExport(), false, "Khi stale thì canExport() phải trả về false");
});

test("Two-Stage Stale Guard: clearPreview tăng thế hệ kết xuất và hủy kết quả in-flight", async () => {
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
    xopp_base64: createValidXoppBase64("Văn bản cũ"),
    missing_token_boxes: [],
  });

  await new Promise((r) => setTimeout(r, 30));
  assert.strictEqual(mockEditor.value, "");
  assert.strictEqual(canExport(), false, "Sau khi xóa trắng thì canExport() phải là false");
});

test("resetDocumentSeedHistory: kiểm tra phản hồi tường minh và không bị rò rỉ timer", async () => {
  setupMockDom();
  const mockWorker = new SyncMockWorker();
  mockWorker.autoAckReset = false; // Tắt auto ack để kiểm thử từng ca tường minh
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
