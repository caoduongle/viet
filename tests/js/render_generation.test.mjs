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
  getRenderedSnapshotForTesting,
  getImportGenerationForTesting,
  getWriteOptionsForTesting,
  setWriteOptionsForTesting,
  setCurrentFormatForTesting,
  setXoppDecompressorForTesting,
  installRenderBarrierForTesting,
  canExport,
  handleFileImport,
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

test("US1: canExport() từ chối khi sửa writeOptions (scale, seed, color, paper) hoặc format", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  mockEditor.value = "Nội dung kiểm thử tùy chọn";
  triggerPreviewImmediate();
  const writeCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  const reqId = writeCalls[0].id;
  mockWorker.simulateResponse(reqId, true, {
    ok: true,
    xopp_base64: createValidXoppBase64("Nội dung kiểm thử tùy chọn"),
    missing_token_boxes: [],
    requestId: writeCalls[0].params.requestId,
  });

  await new Promise((r) => setTimeout(r, 40));
  assert.strictEqual(canExport(), true, "Sau khi render thành công với snapshot ban đầu, canExport() phải true");

  // 1. Đổi cỡ chữ scale
  const originalOpts = getWriteOptionsForTesting();
  setWriteOptionsForTesting({ scale: 1.5 });
  assert.strictEqual(canExport(), false, "Sửa scale phải làm canExport() trả về false");
  setWriteOptionsForTesting({ scale: originalOpts.scale });
  assert.strictEqual(canExport(), true, "Khôi phục scale phải cho phép xuất lại");

  // 2. Đổi seed
  setWriteOptionsForTesting({ seed: 99999 });
  assert.strictEqual(canExport(), false, "Sửa seed phải làm canExport() trả về false");
  setWriteOptionsForTesting({ seed: originalOpts.seed });
  assert.strictEqual(canExport(), true, "Khôi phục seed phải cho phép xuất lại");

  // 3. Đổi màu mực
  setWriteOptionsForTesting({ color: "#ff0000ff" });
  assert.strictEqual(canExport(), false, "Sửa màu mực phải làm canExport() trả về false");
  setWriteOptionsForTesting({ color: originalOpts.color });
  assert.strictEqual(canExport(), true, "Khôi phục màu mực phải cho phép xuất lại");

  // 4. Đổi khổ giấy paper
  setWriteOptionsForTesting({ paper: "a5" });
  assert.strictEqual(canExport(), false, "Sửa khổ giấy phải làm canExport() trả về false");
  setWriteOptionsForTesting({ paper: originalOpts.paper });
  assert.strictEqual(canExport(), true, "Khôi phục khổ giấy phải cho phép xuất lại");

  // 5. Đổi currentFormat
  setCurrentFormatForTesting("txt");
  assert.strictEqual(canExport(), false, "Đổi format khác với renderedSnapshot phải làm canExport() false");
  setCurrentFormatForTesting("md");
  assert.strictEqual(canExport(), true, "Khôi phục format phải cho phép xuất lại");
});

test("US1: canExport() từ chối xuất khi yêu cầu render mới nhất bị thất bại (Worker error)", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  // 1. Render tài liệu A thành công
  mockEditor.value = "Tài liệu A ban đầu";
  triggerPreviewImmediate();
  const writeCalls1 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  const reqAId = writeCalls1[0].id;
  mockWorker.simulateResponse(reqAId, true, {
    ok: true,
    xopp_base64: createValidXoppBase64("Tài liệu A ban đầu"),
    missing_token_boxes: [],
    requestId: writeCalls1[0].params.requestId,
  });
  await new Promise((r) => setTimeout(r, 40));
  assert.strictEqual(canExport(), true, "Tài liệu A render thành công thì cho phép xuất");

  // 2. Người dùng sửa văn bản kích hoạt render B
  mockEditor.value = "Tài liệu B có lỗi";
  triggerPreviewImmediate();
  assert.strictEqual(isRenderStaleForTesting(), true, "Bắt đầu render B phải đánh dấu isRenderStale = true");
  assert.strictEqual(canExport(), false, "Khi đang render B thì canExport() phải false");

  const writeCalls2 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  const reqBId = writeCalls2[1].id;

  // 3. Worker trả về lỗi kết xuất cho B
  mockWorker.simulateResponse(reqBId, true, {
    ok: false,
    error: "Lỗi cú pháp toán học LaTeX",
  });
  await new Promise((r) => setTimeout(r, 40));

  // 4. Khẳng định: isRendering = false, nhưng isRenderStale vẫn true và renderedGeneration vẫn là của A
  const state = getWritePreviewSyncState();
  assert.strictEqual(state.isRendering, false);
  assert.strictEqual(isRenderStaleForTesting(), true, "Render thất bại phải giữ isRenderStale = true");
  assert.strictEqual(canExport(), false, "canExport() phải từ chối xuất tài liệu cũ A khi render B thất bại");
});

test("US1: Sự kiện thay đổi trên options modal đánh dấu isRenderStale = true và khóa canExport()", async () => {
  const { mockEditor, elements } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  mockEditor.value = "Văn bản thử nghiệm modal";
  triggerPreviewImmediate();
  const writeCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  mockWorker.simulateResponse(writeCalls[0].id, true, {
    ok: true,
    xopp_base64: createValidXoppBase64("Văn bản thử nghiệm modal"),
    missing_token_boxes: [],
    requestId: writeCalls[0].params.requestId,
  });
  await new Promise((r) => setTimeout(r, 40));
  assert.strictEqual(canExport(), true, "Trước khi đổi modal thì canExport() true");

  // Mô phỏng người dùng kéo slider opt-scale
  const sliderScale = elements.get("opt-scale");
  assert.ok(sliderScale, "Slider opt-scale phải tồn tại trong mock DOM");
  sliderScale.value = "1.8";
  sliderScale.dispatchEvent({ type: "input", target: sliderScale });

  assert.strictEqual(isRenderStaleForTesting(), true, "Kéo slider phải lập tức đánh dấu isRenderStale = true");
  assert.strictEqual(canExport(), false, "canExport() phải trả về false ngay khi tùy chọn bị sửa trong modal");
});

test("US2: handleFileImport chống ghi đè khi mở 2 tệp liên tiếp (.docx chậm hơn .txt)", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  const fileDocx = {
    name: "tai_lieu_word.docx",
    arrayBuffer: async () => new ArrayBuffer(64),
  };
  const fileTxt = {
    name: "tai_lieu_moi.txt",
    text: async () => "Nội dung tệp TXT mới nhất",
  };

  // 1. Bắt đầu nhập file Word (A)
  const promiseA = handleFileImport(fileDocx, mockEditor);
  const genAfterA = getImportGenerationForTesting();

  // Đợi microtask để fileDocx.arrayBuffer() hoàn tất và thông điệp import_docx gửi xuống Worker
  await new Promise((r) => setTimeout(r, 10));

  // 2. Trong lúc Worker đang xử lý Word (A), người dùng mở tiếp file Text (B)
  const promiseB = handleFileImport(fileTxt, mockEditor);
  const genAfterB = getImportGenerationForTesting();
  assert.ok(genAfterB > genAfterA, "Thế hệ nhập tệp của B phải lớn hơn A");

  // B hoàn tất trước
  const resultB = await promiseB;
  assert.strictEqual(resultB, true, "Tệp B mở sau phải hoàn tất thành công");
  assert.strictEqual(mockEditor.value, "Nội dung tệp TXT mới nhất", "Textarea phải hiển thị nội dung tệp B");

  // 3. Worker hoàn tất trả về kết quả cho A (đã lỗi thời)
  const docxCalls = mockWorker.messagesSent.filter((m) => m.method === "import_docx");
  assert.strictEqual(docxCalls.length, 1);
  mockWorker.simulateResponse(docxCalls[0].id, true, {
    ok: true,
    markdown_text: "Nội dung cũ của file Word A",
  });

  const resultA = await promiseA;
  assert.strictEqual(resultA, false, "Tệp A hoàn tất muộn phải bị từ chối");
  assert.strictEqual(mockEditor.value, "Nội dung tệp TXT mới nhất", "Textarea KHÔNG được bị file A ghi đè");
});

test("US2: handleFileImport chống ghi đè khi mở 2 tệp liên tiếp (.txt chậm hơn .docx)", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  let resolveTxtRead;
  const txtReadPromise = new Promise((resolve) => {
    resolveTxtRead = resolve;
  });

  const fileTxtSlow = {
    name: "tai_lieu_txt_cham.txt",
    text: () => txtReadPromise,
  };
  const fileDocxFast = {
    name: "tai_lieu_docx_nhanh.docx",
    arrayBuffer: async () => new ArrayBuffer(64),
  };

  // 1. Bắt đầu mở tệp TXT (A) - đang bị treo ở bước đọc text
  const promiseA = handleFileImport(fileTxtSlow, mockEditor);

  // 2. Người dùng mở tiếp tệp DOCX (B)
  const promiseB = handleFileImport(fileDocxFast, mockEditor);

  // Phản hồi cho Worker xử lý DOCX (B) hoàn tất trước
  await new Promise((r) => setTimeout(r, 10));
  const docxCalls = mockWorker.messagesSent.filter((m) => m.method === "import_docx");
  assert.strictEqual(docxCalls.length, 1);
  mockWorker.simulateResponse(docxCalls[0].id, true, {
    ok: true,
    markdown_text: "Nội dung tệp Word B mới nhất",
  });

  const resultB = await promiseB;
  assert.strictEqual(resultB, true, "Tệp B phải được áp dụng");
  assert.strictEqual(mockEditor.value, "Nội dung tệp Word B mới nhất");

  // 3. Cho tệp TXT (A) hoàn tất đọc nội dung sau
  resolveTxtRead("Nội dung tệp TXT cũ A");
  const resultA = await promiseA;
  assert.strictEqual(resultA, false, "Tệp A hoàn tất muộn phải bị từ chối");
  assert.strictEqual(mockEditor.value, "Nội dung tệp Word B mới nhất", "Textarea KHÔNG được bị tệp A ghi đè");
});

test("US2: handleFileImport dừng nạp tệp khi resetDocumentSeedHistory thất bại", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  mockWorker.autoAckReset = false; // Tắt auto ack để chủ động trả lỗi cho clear_document_history
  setWorkerInstance(mockWorker);

  initWriteTab();
  mockEditor.value = "Nội dung hiện tại được bảo toàn";

  const fileTxt = {
    name: "file_moi.txt",
    text: async () => "Nội dung mới bị từ chối",
  };

  const importPromise = handleFileImport(fileTxt, mockEditor);

  // Đợi Worker nhận clear_document_history và trả lỗi
  await new Promise((r) => setTimeout(r, 10));
  const clearCalls = mockWorker.messagesSent.filter((m) => m.method === "clear_document_history");
  assert.ok(clearCalls.length >= 1);
  mockWorker.simulateResponse(clearCalls[clearCalls.length - 1].id, true, { ok: false, error: "Disk full" });

  const success = await importPromise;
  assert.strictEqual(success, false, "Nhập tệp phải thất bại nếu không reset được hạt giống");
  assert.strictEqual(mockEditor.value, "Nội dung hiện tại được bảo toàn", "Textarea không được bị thay đổi");
});

test("US3: Two-Stage Stale Guard: Stage 2 từ chối cam kết khi giải nén XOPP của A bị B vượt mặt", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  let resolveDecompressA;
  const decompressAPromise = new Promise((resolve) => {
    resolveDecompressA = resolve;
  });

  let decompressCallCount = 0;
  // Cài đặt custom decompressor để kiểm soát thời gian giải nén của A
  setXoppDecompressorForTesting(async (base64) => {
    decompressCallCount++;
    if (decompressCallCount === 1) {
      // Cuộc gọi giải nén đầu tiên (của A) bị hoãn lại
      return await decompressAPromise;
    }
    // Cuộc gọi thứ 2 (của B) giải nén bình thường
    const xml = `<?xml version="1.0" standalone="no"?><xournal version="0.4.8"><page width="595.28" height="841.89"><layer><text font="Sans" size="12" x="100" y="100" color="#000000ff">B</text></layer></page></xournal>`;
    return xml;
  });

  // 1. Kích hoạt render A
  mockEditor.value = "Văn bản A";
  triggerPreviewImmediate();
  const writeCalls1 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  const reqAId = writeCalls1[0].id;
  const genA = writeCalls1[0].params.requestId;

  // 2. Worker trả kết quả cho A -> bước vào giải nén XOPP của A (bị treo tại decompressAPromise)
  mockWorker.simulateResponse(reqAId, true, {
    ok: true,
    xopp_base64: createValidXoppBase64("Văn bản A"),
    missing_token_boxes: [],
    requestId: genA,
  });

  await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(decompressCallCount, 1, "A đã đi vào bước giải nén XOPP");
  assert.strictEqual(getRenderedGenerationForTesting(), 0, "A chưa được commit vì đang giải nén");

  // 3. Trong lúc A đang giải nén dở, người dùng chuyển sang Văn bản B
  mockEditor.value = "Văn bản B";
  triggerPreviewImmediate();
  const genB = getRenderGenerationForTesting();
  assert.ok(genB > genA, "Thế hệ kết xuất của B phải vượt qua A");

  // 4. Cho A giải nén hoàn tất
  const xmlA = `<?xml version="1.0" standalone="no"?><xournal version="0.4.8"><page width="595.28" height="841.89"><layer><text font="Sans" size="12" x="100" y="100" color="#000000ff">A</text></layer></page></xournal>`;
  resolveDecompressA(xmlA);

  await new Promise((r) => setTimeout(r, 30));

  // Khẳng định: Stage 2 Stale Guard phát hiện genA !== currentRenderGeneration và LOẠI BỎ A!
  assert.notStrictEqual(getRenderedGenerationForTesting(), genA, "A không được phép ghi nhận vào renderedGeneration");

  // 5. Worker trả kết quả cho B
  const writeCalls2 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  const reqBId = writeCalls2[1].id;
  mockWorker.simulateResponse(reqBId, true, {
    ok: true,
    xopp_base64: createValidXoppBase64("Văn bản B"),
    missing_token_boxes: [],
    requestId: writeCalls2[1].params.requestId,
  });

  // Chờ B render và commit
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 20));
    if (!getWritePreviewSyncState().isRendering) break;
  }

  const expectedGenB = writeCalls2[1].params.requestId;
  assert.strictEqual(getRenderedGenerationForTesting(), expectedGenB, "Chỉ B được commit thành công");
  assert.strictEqual(canExport(), true, "canExport() phải true cho B");
  assert.strictEqual(getRenderedSnapshotForTesting()?.text, "Văn bản B");

  // Dọn dẹp decompressor hook
  setXoppDecompressorForTesting(null);
});

test("US3: installRenderBarrierForTesting cung cấp cơ chế one-shot chặn và giải phóng render xác định", async () => {
  const { mockEditor } = setupMockDom();
  const mockWorker = new SyncMockWorker();
  setWorkerInstance(mockWorker);

  initWriteTab();

  const barrier = installRenderBarrierForTesting();
  assert.ok(barrier, "Barrier phải được tạo thành công");

  mockEditor.value = "Chữ cần render qua barrier";
  triggerPreviewImmediate();

  // Chờ yêu cầu bắt đầu
  const startedGen = await barrier.waitForRequestStart();
  assert.strictEqual(startedGen, getRenderGenerationForTesting(), "Gen bắt đầu phải khớp với thế hệ hiện hành");
  assert.strictEqual(getWritePreviewSyncState().isRendering, true, "Worker đang render");

  const writeCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
  assert.strictEqual(writeCalls.length, 1);
  const reqId = writeCalls[0].id;

  // Worker trả về kết quả
  mockWorker.simulateResponse(reqId, true, {
    ok: true,
    xopp_base64: createValidXoppBase64("Chữ cần render qua barrier"),
    missing_token_boxes: [],
    requestId: startedGen,
  });

  // Khi chưa release: Main thread vẫn bị giữ bởi barrier
  await new Promise((r) => setTimeout(r, 30));
  assert.strictEqual(getRenderedGenerationForTesting(), 0, "Chưa commit khi barrier chưa mở");

  // Mở barrier
  barrier.release();

  await new Promise((r) => setTimeout(r, 50));
  assert.strictEqual(getRenderedGenerationForTesting(), startedGen, "Sau khi release thì render được commit");
  assert.strictEqual(canExport(), true);
});
