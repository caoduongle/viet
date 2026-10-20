import test from "node:test";
import assert from "node:assert/strict";
import { MockIDBDatabase } from "./helpers/mock_idb.mjs";
import * as storage from "../../webapp/js/storage.js";
import { initBankTab } from "../../webapp/js/bank.js";
import { initWriteTab } from "../../webapp/js/write.js";
import { TeachController } from "../../webapp/js/teach.js";
import {
  sendWorkerMessage,
  setWorkerInstance,
  handleWorkerFatalError,
  getPendingRequestsCount,
  recoverWorker,
  getWorkerGeneration,
  getIsRecovering,
  getRecoveryPromise,
  getIsUiInitialized,
  getIsDomListenersAttached,
  resetUiInitializedForTesting,
  onWorkerReady,
  initQuotaAndBackupReminders,
} from "../../webapp/js/app.js";

test.beforeEach(() => {
  const mockDb = new MockIDBDatabase();
  storage.setDBInstance(mockDb);
  storage.setLocalSyncedTimestamp(0);
});

class MockWorker {
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

  simulateResponse(id, ok, result, error) {
    if (this.onmessage) {
      this.onmessage({ data: { id, ok, result, error } });
    }
  }

  simulateReady() {
    if (this.onmessage) {
      this.onmessage({ data: { type: "READY" } });
    }
  }

  simulateErrorType(message = "Lỗi khởi tạo Worker") {
    if (this.onmessage) {
      this.onmessage({ data: { type: "ERROR", payload: { message } } });
    }
  }

  simulateError(message = "Lỗi runtime trong Web Worker") {
    if (this.onerror) {
      this.onerror({ message });
    }
  }

  terminate() {
    this.terminated = true;
  }

  simulateMessageError(error = new Error("Message deserialization error")) {
    if (this.onmessageerror) {
      this.onmessageerror({ data: error });
    }
  }
}

test("sendWorkerMessage gửi thông điệp và resolve khi nhận phản hồi hợp lệ", async () => {
  const worker = new MockWorker();
  setWorkerInstance(worker);

  const promise = sendWorkerMessage("render", { text: "hello" });
  assert.equal(worker.messagesSent.length, 1);
  const sentId = worker.messagesSent[0].id;

  worker.simulateResponse(sentId, true, { base64: "dummy" });
  const result = await promise;
  assert.deepEqual(result, { base64: "dummy" });
  assert.equal(getPendingRequestsCount(), 0);
});

test("sendWorkerMessage tự động timeout, chấm dứt vật lý worker và reject với WorkerTimeoutError", async () => {
  const worker = new MockWorker();
  setWorkerInstance(worker);
  const genBefore = getWorkerGeneration();

  // Gọi với timeout rất ngắn 30ms
  const promise = sendWorkerMessage("heavy_task", {}, 30);
  assert.equal(getPendingRequestsCount(), 1);

  await assert.rejects(
    promise,
    (err) => {
      return err.name === "WorkerTimeoutError" && err.message.includes("quá thời gian chờ");
    }
  );

  assert.equal(getPendingRequestsCount(), 0);
  assert.equal(worker.terminated, true, "Worker phải bị terminate() vật lý khi timeout");
  assert.ok(getWorkerGeneration() > genBefore, "workerGeneration phải tăng sau khi Worker bị hủy");

  // Phản hồi đến muộn sau khi đã timeout phải được bỏ qua mà không ném lỗi
  assert.doesNotThrow(() => {
    worker.simulateResponse(worker.messagesSent[0].id, true, { late: true });
  });
});

test("handleWorkerFatalError reject tất cả pendingRequests và dọn dẹp hàng đợi", async () => {
  const worker = new MockWorker();
  setWorkerInstance(worker);

  const p1 = sendWorkerMessage("task_1", {}, 5000);
  const p2 = sendWorkerMessage("task_2", {}, 5000);
  assert.equal(getPendingRequestsCount(), 2);

  handleWorkerFatalError("Pyodide out of memory");

  await assert.rejects(p1, /Sự cố Web Worker: Pyodide out of memory/);
  await assert.rejects(p2, /Sự cố Web Worker: Pyodide out of memory/);
  assert.equal(getPendingRequestsCount(), 0);
});

test("T016: onmessageerror kích hoạt handleWorkerFatalError và reject các yêu cầu đang chờ", async () => {
  const worker = new MockWorker();
  setWorkerInstance(worker);

  const p = sendWorkerMessage("render_latex", {}, 5000);
  assert.equal(getPendingRequestsCount(), 1);

  worker.simulateMessageError();

  await assert.rejects(p, /Lỗi giải mã thông điệp/);
  assert.equal(getPendingRequestsCount(), 0);
});

test("T015: recoverWorker khởi tạo lại Worker, cô lập generation và nạp lại kho mẫu an toàn", async () => {
  resetUiInitializedForTesting();
  storage.setDBInstance(new MockIDBDatabase());

  // Tạo sẵn hồ sơ mẫu trong IndexedDB
  await storage.setSetting("active_profile_id", "test_profile");
  await storage.saveProfile({
    id: "test_profile",
    name: "Kho phục hồi",
    data: [100, 200, 255],
    updated_at: 1000,
  });

  let createdWorkers = [];
  class TrackingMockWorker extends MockWorker {
    constructor() {
      super();
      createdWorkers.push(this);
    }

    postMessage(msg) {
      super.postMessage(msg);
      if (msg.method === "load_bank") {
        queueMicrotask(() => {
          this.simulateResponse(msg.id, true, { ok: true, stats: {} });
        });
      }
    }
  }

  // Khởi tạo worker ban đầu
  const initialWorker = new TrackingMockWorker();
  setWorkerInstance(initialWorker);
  const gen0 = getWorkerGeneration();

  // Gửi một tác vụ đang chờ
  const pendingTask = sendWorkerMessage("old_task", {}, 5000);
  const pendingRejection = assert.rejects(pendingTask, /Bộ xử lý nền đã được khởi động lại/);
  assert.equal(getPendingRequestsCount(), 1);

  // Kích hoạt phục hồi
  const recoveryPromise = recoverWorker(TrackingMockWorker);
  // Kiểm tra chống bấm đúp: lần gọi thứ 2 trả về cùng promise
  const secondCallPromise = recoverWorker(TrackingMockWorker);
  assert.equal(recoveryPromise, secondCallPromise);

  // 1. Worker cũ phải bị chấm dứt vật lý
  assert.equal(initialWorker.terminated, true, "Worker cũ phải bị terminate()");
  // 2. Yêu cầu cũ phải bị hủy
  await pendingRejection;
  assert.equal(getPendingRequestsCount(), 0);

  // 3. Worker mới đã được tạo và thế hệ mới đã tăng
  assert.equal(createdWorkers.length, 2);
  const newWorker = createdWorkers[1];
  assert.ok(getWorkerGeneration() > gen0);

  // Giả lập worker mới gửi tín hiệu READY để hoàn tất phục hồi
  newWorker.onmessage({ data: { type: "READY" } });

  await recoveryPromise;

  // 4. Worker mới phải nhận được lệnh load_bank với gzBytes và createIfMissing: false
  const loadBankMsg = newWorker.messagesSent.find((m) => m.method === "load_bank");
  assert.ok(loadBankMsg, "Worker mới phải nhận được thông điệp load_bank");
  assert.deepEqual(loadBankMsg.params.gzBytes, [100, 200, 255]);
  assert.equal(loadBankMsg.params.createIfMissing, false);

  // 5. isUiInitialized đã chuyển sang true
  assert.equal(getIsUiInitialized(), true);

  // 6. Phản hồi muộn từ Worker cũ (generation cũ) không ảnh hưởng tới Worker mới
  assert.doesNotThrow(() => {
    initialWorker.simulateResponse(999, true, { zombie: true });
  });
});

function setupMockDocument(extraIds = []) {
  const knownIds = new Set([
    "btn-worker-retry",
    "splash-screen",
    "splash-status",
    "status-indicator",
    "status-text",
    "quota-warning-banner",
    "backup-reminder-toast",
    "btn-export-bank",
    "btn-import-bank",
    "input-import-bank",
    "btn-export-check",
    "btn-bank-import-grid",
    "btn-rename-profile",
    "input-search-bank",
    "bank-category-filters",
    "chk-bank-select-all",
    "btn-bank-delete-selected",
    "modal-label-detail",
    "btn-close-label-detail",
    "btn-label-teach-more",
    "btn-label-preview-random",
    "btn-label-delete",
    "editor-text",
    "select-format",
    "btn-export-xopp",
    "btn-export-png",
    "btn-export-svg",
    "btn-export-zip",
    "btn-print-pdf",
    "preview-stage",
    "btn-page-prev",
    "btn-page-next",
    "btn-zoom-in",
    "btn-zoom-out",
    "btn-zoom-fit",
    "select-zoom",
    "btn-quota-backup",
    "btn-toast-dismiss",
    "btn-toast-backup",
    "guide-modal",
    "btn-header-guide",
    "btn-close-guide-x",
    "btn-close-guide",
    ...extraIds,
  ]);
  if (extraIds.includes("tab-teach")) {
    const teachIds = [
      "tab-teach",
      "input-teach-add",
      "btn-teach-add",
      "btn-teach-chars",
      "btn-teach-essentials",
      "btn-teach-seed",
      "btn-import-grid",
      "input-grid-file",
      "btn-export-char-grid",
      "btn-teach-clear-queue",
      "btn-teach-calibrate",
      "modal-char-groups",
      "btn-close-char-groups",
      "select-char-group",
      "char-group-desc",
      "btn-char-groups-add-queue",
      "btn-char-groups-export",
      "teach-queue-count",
      "teach-queue-list",
      "btn-teach-skip",
      "teach-target-word",
      "teach-sample-count",
      "teach-scale-info",
      "teach-canvas",
      "btn-teach-tool-pen",
      "btn-teach-tool-eraser",
      "select-teach-pen-width",
      "chk-teach-ghost",
      "btn-teach-undo",
      "btn-teach-redo",
      "btn-teach-clear",
      "btn-teach-save",
    ];
    for (const tid of teachIds) knownIds.add(tid);
  }
  const elements = new Map();
  const getOrCreate = (id) => {
    if (!knownIds.has(id)) {
      return null;
    }
    if (!elements.has(id)) {
      const listeners = new Map();
      elements.set(id, {
        id,
        style: { display: "none" },
        disabled: false,
        textContent: "",
        className: "",
        value: "",
        listeners,
        classList: {
          contains: () => true,
          add: () => {},
          remove: () => {},
        },
        getContext() {
          return {
            resetTransform: () => {},
            scale: () => {},
            clearRect: () => {},
            beginPath: () => {},
            moveTo: () => {},
            lineTo: () => {},
            stroke: () => {},
            save: () => {},
            restore: () => {},
            arc: () => {},
            fill: () => {},
            setLineDash: () => {},
            fillText: () => {},
            measureText: () => ({ width: 10 }),
          };
        },
        getBoundingClientRect() {
          return { left: 0, top: 0, width: 300, height: 150 };
        },
        addEventListener(event, fn, options = {}) {
          if (!listeners.has(event)) {
            listeners.set(event, []);
          }
          listeners.get(event).push(fn);
          if (options && options.signal) {
            options.signal.addEventListener("abort", () => {
              const list = listeners.get(event) || [];
              const idx = list.indexOf(fn);
              if (idx !== -1) list.splice(idx, 1);
            }, { once: true });
          }
        },
        removeEventListener(event, fn) {
          const list = listeners.get(event) || [];
          const idx = list.indexOf(fn);
          if (idx !== -1) list.splice(idx, 1);
        },
        dispatchEvent(event) {
          const type = typeof event === "string" ? event : event.type;
          const list = listeners.get(type) || [];
          for (const fn of [...list]) {
            fn({ target: this, type });
          }
        },
      });
    }
    return elements.get(id);
  };

  const docListeners = new Map();
  globalThis.document = {
    documentElement: {
      getAttribute: () => "light",
    },
    getElementById: (id) => getOrCreate(id),
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener(event, fn, options = {}) {
      if (!docListeners.has(event)) {
        docListeners.set(event, []);
      }
      docListeners.get(event).push(fn);
      if (options && options.signal) {
        options.signal.addEventListener("abort", () => {
          this.removeEventListener(event, fn);
        }, { once: true });
      }
    },
    removeEventListener(event, fn) {
      const list = docListeners.get(event) || [];
      const idx = list.indexOf(fn);
      if (idx !== -1) list.splice(idx, 1);
    },
    getListeners(event) {
      return docListeners.get(event) || [];
    },
  };

  const hadWindow = typeof globalThis.window !== "undefined";
  if (!hadWindow) {
    globalThis.window = {
      addEventListener: () => {},
      removeEventListener: () => {},
      print: () => {},
    };
  }

  const hadResizeObserver = typeof globalThis.ResizeObserver !== "undefined";
  let activeMockResizeObservers = [];
  if (!hadResizeObserver) {
    class MockResizeObserver {
      constructor(callback) {
        this.callback = callback;
        this.observed = [];
        this.disconnected = false;
        activeMockResizeObservers.push(this);
      }
      observe(el) {
        this.observed.push(el);
      }
      unobserve(el) {
        const idx = this.observed.indexOf(el);
        if (idx !== -1) this.observed.splice(idx, 1);
      }
      disconnect() {
        this.disconnected = true;
        this.observed = [];
      }
    }
    MockResizeObserver.instances = activeMockResizeObservers;
    globalThis.ResizeObserver = MockResizeObserver;
  }

  return {
    get: (id) => getOrCreate(id),
    btnRetry: getOrCreate("btn-worker-retry"),
    splash: getOrCreate("splash-screen"),
    cleanup: () => {
      delete globalThis.document;
      if (!hadWindow) {
        delete globalThis.window;
      }
      if (!hadResizeObserver) {
        delete globalThis.ResizeObserver;
      }
    },
  };
}

test("T005: recoverWorker timeout tự động chấm dứt worker mới, giữ nút Thử lại và trả về false", async () => {
  resetUiInitializedForTesting();
  const dom = setupMockDocument();
  try {
    let createdWorker = null;
    class HangingWorker extends MockWorker {
      constructor() {
        super();
        createdWorker = this;
      }
    }

    // Gọi recoverWorker với timeout ngắn 50ms
    const promise = recoverWorker(HangingWorker, 50);
    assert.equal(dom.btnRetry.disabled, true, "Nút Thử lại phải bị disabled trong lúc đang khôi phục");

    const result = await promise;
    assert.equal(result, false, "recoverWorker phải trả về false khi bị timeout");
    assert.equal(createdWorker.terminated, true, "Worker mới bị treo phải bị terminate()");
    assert.notEqual(dom.btnRetry.style.display, "none", "Nút Thử lại phải còn hiển thị khi khôi phục thất bại");
    assert.equal(dom.btnRetry.disabled, false, "Nút Thử lại phải được re-enabled khi khôi phục thất bại");
  } finally {
    dom.cleanup();
  }
});

test("T005: recoverWorker khi nhận ERROR, onerror hoặc onmessageerror từ worker mới thì trả về false và giữ nút Thử lại", async () => {
  resetUiInitializedForTesting();
  const dom = setupMockDocument();
  try {
    // 1. Nhánh type === "ERROR"
    let worker1 = null;
    class ErrorTypeWorker extends MockWorker {
      constructor() {
        super();
        worker1 = this;
      }
    }
    const p1 = recoverWorker(ErrorTypeWorker, 5000);
    worker1.simulateErrorType("Pyodide module load failed");
    const res1 = await p1;
    assert.equal(res1, false);
    assert.notEqual(dom.btnRetry.style.display, "none");
    assert.equal(dom.btnRetry.disabled, false);

    // 2. Nhánh onerror
    let worker2 = null;
    class OnErrorWorker extends MockWorker {
      constructor() {
        super();
        worker2 = this;
      }
    }
    const p2 = recoverWorker(OnErrorWorker, 5000);
    worker2.simulateError("WASM compile error");
    const res2 = await p2;
    assert.equal(res2, false);
    assert.notEqual(dom.btnRetry.style.display, "none");
    assert.equal(dom.btnRetry.disabled, false);

    // 3. Nhánh onmessageerror
    let worker3 = null;
    class MessageErrorWorker extends MockWorker {
      constructor() {
        super();
        worker3 = this;
      }
    }
    const p3 = recoverWorker(MessageErrorWorker, 5000);
    worker3.simulateMessageError();
    const res3 = await p3;
    assert.equal(res3, false);
    assert.notEqual(dom.btnRetry.style.display, "none");
    assert.equal(dom.btnRetry.disabled, false);
  } finally {
    dom.cleanup();
  }
});

test("T006: recoverWorker khi onWorkerReady ném lỗi (load_bank thất bại) thì giữ nút Thử lại và trả về false", async () => {
  resetUiInitializedForTesting();
  const dom = setupMockDocument();
  storage.setDBInstance(new MockIDBDatabase());

  // Lưu sẵn một hồ sơ để onWorkerReady gọi load_bank
  await storage.setSetting("active_profile_id", "broken_profile");
  await storage.saveProfile({
    id: "broken_profile",
    name: "Kho lỗi",
    data: [1, 2, 3],
    updated_at: 1000,
  });

  try {
    let workerInstance = null;
    let loadBankCalled = false;
    class RejectingLoadBankWorker extends MockWorker {
      constructor() {
        super();
        workerInstance = this;
      }
      postMessage(msg) {
        super.postMessage(msg);
        if (msg.method === "load_bank") {
          loadBankCalled = true;
          // Trả về lỗi khi load_bank
          queueMicrotask(() => {
            this.simulateResponse(msg.id, false, null, "Corrupted gzip bank stream");
          });
        }
      }
    }

    const promise = recoverWorker(RejectingLoadBankWorker, 5000);
    // Worker gửi READY, kích hoạt onWorkerReady -> gọi load_bank -> nhận lỗi
    workerInstance.simulateReady();

    const result = await promise;
    assert.equal(loadBankCalled, true, "onWorkerReady phải thực sự gọi load_bank");
    assert.equal(result, false, "recoverWorker phải trả về false khi load_bank trong onWorkerReady bị lỗi");
    assert.equal(getIsUiInitialized(), false, "isUiInitialized phải giữ nguyên false khi load_bank thất bại");
    assert.notEqual(dom.btnRetry.style.display, "none", "Nút Thử lại phải còn hiển thị khi nạp kho mẫu thất bại");
    assert.equal(dom.btnRetry.disabled, false, "Nút Thử lại phải re-enabled sau khi nạp kho mẫu thất bại");
  } finally {
    dom.cleanup();
  }
});

test("T005: recoverWorker tách biệt timeout READY: Worker gửi READY sớm nhưng nạp kho kéo dài thì readyTimer không terminate Worker", async () => {
  resetUiInitializedForTesting();
  storage.setDBInstance(new MockIDBDatabase());
  await storage.setSetting("active_profile_id", "large_profile");
  await storage.saveProfile({
    id: "large_profile",
    name: "Kho lớn",
    data: [1, 2, 3],
    updated_at: 1000,
  });

  const dom = setupMockDocument();
  try {
    let workerInstance = null;
    let loadBankCalled = false;
    class DelayedLoadBankWorker extends MockWorker {
      constructor() {
        super();
        workerInstance = this;
      }
      postMessage(msg) {
        super.postMessage(msg);
        if (msg.method === "load_bank") {
          loadBankCalled = true;
          // Giả lập nạp kho mất 100ms (lớn hơn timeout READY là 40ms)
          setTimeout(() => {
            this.simulateResponse(msg.id, true, { ok: true });
          }, 100);
        }
      }
    }

    // timeoutMs = 40ms chỉ áp dụng cho bước chờ READY
    const recoveryPromise = recoverWorker(DelayedLoadBankWorker, 40);

    // Gửi READY gần như ngay lập tức (10ms)
    setTimeout(() => {
      workerInstance.simulateReady();
    }, 10);

    const result = await recoveryPromise;
    assert.equal(loadBankCalled, true, "onWorkerReady phải được gọi và gửi load_bank");
    assert.equal(workerInstance.terminated, false, "Worker không được bị terminate khi load_bank chạy lâu");
    assert.equal(result, true, "recoverWorker phải trả về true khi load_bank thành công");
    assert.equal(getIsUiInitialized(), true, "isUiInitialized phải là true");
  } finally {
    dom.cleanup();
  }
});

test("T006: recoverWorker cô lập workerGeneration: phản hồi muộn từ generation cũ bị bỏ qua trong onWorkerReady", async () => {
  resetUiInitializedForTesting();
  storage.setDBInstance(new MockIDBDatabase());
  await storage.setSetting("active_profile_id", "profile_gen");
  await storage.saveProfile({
    id: "profile_gen",
    name: "Kho gen",
    data: [1, 2, 3],
    updated_at: 1000,
  });

  let createdWorkers = [];
  class TrackingWorker extends MockWorker {
    constructor() {
      super();
      createdWorkers.push(this);
    }
    postMessage(msg) {
      super.postMessage(msg);
      if (msg.method === "load_bank") {
        queueMicrotask(() => {
          this.simulateResponse(msg.id, true, { ok: true });
        });
      }
    }
  }

  // Khởi động phiên 1
  const p1 = recoverWorker(TrackingWorker, 5000);
  const w1 = createdWorkers[0];
  const gen1 = getWorkerGeneration();

  // w1 báo lỗi khởi động khiến phiên 1 kết thúc với false
  w1.simulateErrorType("Failed to boot");
  const res1 = await p1;
  assert.equal(res1, false);

  // Người dùng thử lại kích hoạt khôi phục phiên 2
  const p2 = recoverWorker(TrackingWorker, 5000);
  const w2 = createdWorkers[1];
  const gen2 = getWorkerGeneration();
  assert.ok(gen2 > gen1, "workerGeneration phải tăng sau lần gọi thứ 2");

  // Giờ w1 gửi READY muộn: phải bị bỏ qua và không ảnh hưởng phiên 2
  w1.simulateReady();

  // w2 gửi READY chuẩn: phải hoàn tất thành công
  w2.simulateReady();
  const res2 = await p2;
  assert.equal(res2, true);
  assert.equal(w1.terminated, true, "w1 cũ phải bị terminate");
});

test("T021: onWorkerReady rollback isDomListenersAttached về false khi TeachController.init ném lỗi và thử lại thành công", async () => {
  resetUiInitializedForTesting();
  assert.equal(getIsDomListenersAttached(), false);

  const dom = setupMockDocument(["tab-teach"]);
  const originalInit = TeachController.prototype.init;
  let shouldThrow = true;
  TeachController.prototype.init = async function () {
    if (shouldThrow) {
      throw new Error("TeachController init hardware failure");
    }
  };

  try {
    // 1. Thử gọi onWorkerReady, TeachController.init ném lỗi
    await assert.rejects(onWorkerReady(), /TeachController init hardware failure/);

    // 2. Kiểm tra cờ isDomListenersAttached được rollback về false
    assert.equal(getIsDomListenersAttached(), false, "isDomListenersAttached phải được rollback về false khi init gặp lỗi");

    // 3. Khôi phục trạng thái bình thường và thử lại
    shouldThrow = false;
    await onWorkerReady();
    assert.equal(getIsDomListenersAttached(), true, "isDomListenersAttached phải là true khi khởi tạo thành công");
    assert.equal(getIsUiInitialized(), true, "isUiInitialized phải là true");
  } finally {
    TeachController.prototype.init = originalInit;
    dom.cleanup();
  }
});

// -------------------------------------------------------------
// USER STORY 1 & 2: Feature 046 & 048 Regression Tests
// -------------------------------------------------------------
test("US1 - T006: recoverWorker giải quyết dứt điểm promise cũ khi thế hệ thay đổi giữa chừng", async () => {
  resetUiInitializedForTesting();
  const mockDb = new MockIDBDatabase();
  storage.setDBInstance(mockDb);
  const dom = setupMockDocument();

  try {
    let createdWorkers = [];
    class MultiGenWorker extends MockWorker {
      constructor() {
        super();
        createdWorkers.push(this);
      }
      postMessage(msg) {
        super.postMessage(msg);
        if (msg.method === "load_bank") {
          queueMicrotask(() => {
            this.simulateResponse(msg.id, true, { ok: true, stats: {} });
          });
        }
      }
    }

    // Khởi chạy phục hồi gen 1
    const p1 = recoverWorker(MultiGenWorker, 5000);
    assert.equal(getIsRecovering(), true);
    assert.equal(createdWorkers.length, 1);
    const w1 = createdWorkers[0];

    // Ngay lập tức người dùng hoặc hệ thống kích hoạt phục hồi gen 2 với force: true
    const p2 = recoverWorker(MultiGenWorker, 5000, { force: true });
    assert.equal(createdWorkers.length, 2);
    const w2 = createdWorkers[1];

    // Giờ w1 gửi READY (muộn)
    w1.simulateReady();

    // p1 phải kết thúc (resolve false) chứ không được treo vô hạn!
    const res1 = await p1;
    assert.equal(res1, false, "Phiên thế hệ cũ phải kết thúc với false");

    // T005 [US1]: Khẳng định trạng thái trung gian - p1 đã kết thúc nhưng p2 vẫn đang chạy:
    // isRecovering PHẢI là true, recoveryPromise PHẢI gắn với p2, và nút Thử lại PHẢI vẫn bị khóa!
    assert.equal(getIsRecovering(), true, "isRecovering PHẢI tiếp tục là true vì phiên 2 vẫn đang chạy");
    assert.equal(getRecoveryPromise(), p2, "recoveryPromise PHẢI vẫn tham chiếu tới phiên 2 đang chạy");
    assert.equal(dom.get("btn-worker-retry").disabled, true, "Nút Thử lại PHẢI vẫn bị khóa vì phiên 2 chưa xong");

    // w2 gửi READY hợp lệ
    w2.simulateReady();
    const res2 = await p2;
    assert.equal(res2, true, "Phiên thế hệ mới nhất phải kết thúc với true");
    assert.equal(getIsRecovering(), false, "isRecovering phải được giải phóng về false");
    assert.equal(getRecoveryPromise(), null, "recoveryPromise phải được đặt lại về null khi phiên hiện hành xong");
  } finally {
    dom.cleanup();
  }
});

test("US1 - T008: recoverWorker timeout bảo vệ cả giai đoạn khởi tạo UI sau tín hiệu READY", async () => {
  resetUiInitializedForTesting();
  const mockDb = new MockIDBDatabase();
  storage.setDBInstance(mockDb);
  await storage.setSetting("active_profile_id", "hanging_prof");
  await storage.saveProfile({
    id: "hanging_prof",
    name: "Treo",
    data: [1, 2, 3],
    updated_at: 1000,
  });
  const dom = setupMockDocument();

  try {
    let workerInstance = null;
    class HangingInitWorker extends MockWorker {
      constructor() {
        super();
        workerInstance = this;
      }
      postMessage(msg) {
        super.postMessage(msg);
        // Không phản hồi load_bank để treo onWorkerReady
      }
    }

    const genBefore = getWorkerGeneration();
    // Đặt timeout 60ms
    const p = recoverWorker(HangingInitWorker, 60);

    // Gửi READY sau 10ms
    setTimeout(() => {
      workerInstance.simulateReady();
    }, 10);

    // Promise phải kết thúc sau timeout bảo vệ khởi tạo UI, không bị treo vô hạn
    const res = await p;
    assert.equal(res, false, "recoverWorker phải trả về false khi onWorkerReady bị treo quá hạn");
    assert.equal(getIsRecovering(), false, "isRecovering phải là false");
    assert.equal(dom.get("btn-worker-retry").disabled, false, "Nút Thử lại phải mở khóa");

    // T018 [US4]: Khẳng định Worker bị terminate, generation tăng lên và UI listeners bị thu hồi
    assert.equal(workerInstance.terminated, true, "Worker phải bị terminate() vật lý khi timeout sau READY");
    assert.ok(getWorkerGeneration() > genBefore, "workerGeneration phải tăng sau khi Worker bị hủy do timeout");
    assert.equal(getIsDomListenersAttached(), false, "isDomListenersAttached phải được thu hồi về false sau timeout");
  } finally {
    dom.cleanup();
  }
});

// -------------------------------------------------------------
// USER STORY 2: Idempotent UI Listeners (T010 - T013)
// -------------------------------------------------------------
test("US2 - T010: initBankTab và initWriteTab có tính idempotent, không nhân bản event listeners", () => {
  const dom = setupMockDocument();
  try {
    const btnExport = dom.get("btn-export-bank");
    let exportCallCount = 0;

    // Giả lập mock sendWorkerMessage
    const mockSendWorker = async () => ({ ok: true });

    // Gọi initBankTab 3 lần liên tiếp
    initBankTab(mockSendWorker);
    initBankTab(mockSendWorker);
    initBankTab(mockSendWorker);

    // Kiểm tra số lượng listener gắn trên btn-export-bank
    const clickListeners = btnExport.listeners.get("click") || [];
    assert.equal(clickListeners.length, 1, "Chỉ được gắn đúng 1 click listener trên btn-export-bank sau 3 lần init");

    // Tương tự với initWriteTab
    const textarea = dom.get("editor-text");
    initWriteTab();
    initWriteTab();
    initWriteTab();

    const inputListeners = textarea.listeners.get("input") || [];
    assert.equal(inputListeners.length, 1, "Chỉ được gắn đúng 1 input listener trên editor-text sau 3 lần init");
  } finally {
    dom.cleanup();
  }
});

test("US2 - T013: chu trình khởi tạo UI thất bại rồi thử lại qua AbortController không làm trùng lặp handler", () => {
  const dom = setupMockDocument();
  try {
    const btnExport = dom.get("btn-export-bank");
    const abortCtrl1 = new AbortController();

    // Lần 1: khởi tạo với abortCtrl1
    initBankTab(async () => ({ ok: true }), { signal: abortCtrl1.signal });
    assert.equal((btnExport.listeners.get("click") || []).length, 1);

    // Giả lập bước tiếp theo thất bại -> abortCtrl1 hủy
    abortCtrl1.abort();
    assert.equal((btnExport.listeners.get("click") || []).length, 0, "Listener phải bị dọn dẹp sau khi abort");

    // Lần 2: khởi tạo lại thành công với abortCtrl2
    const abortCtrl2 = new AbortController();
    initBankTab(async () => ({ ok: true }), { signal: abortCtrl2.signal });
    assert.equal((btnExport.listeners.get("click") || []).length, 1, "Listener mới được gắn chính xác 1 lần");
  } finally {
    dom.cleanup();
  }
});

// -------------------------------------------------------------
// USER STORY 3: Full UI Event Listener & Observer Teardown (T011)
// -------------------------------------------------------------
test("US3 - T011: TeachController.destroy() và AbortSignal gỡ bỏ sạch sẽ document keydown listener", async () => {
  const dom = setupMockDocument(["tab-teach", "teach-canvas"]);
  try {
    const abortCtrl = new AbortController();
    const mockWorker = { request: async () => ({ ok: true, width: 300, height: 150 }) };
    const controller = new TeachController(mockWorker, { signal: abortCtrl.signal });

    await controller.init({ signal: abortCtrl.signal });

    // Kiểm tra listener đã được gắn trên document
    const listenersBefore = document.getListeners("keydown");
    assert.equal(listenersBefore.length, 1, "document phải có 1 keydown listener từ TeachController");

    // Khi abort() được gọi, listener trên document phải bị dọn dẹp
    abortCtrl.abort();
    const listenersAfter = document.getListeners("keydown");
    assert.equal(listenersAfter.length, 0, "document keydown listener phải bị gỡ bỏ sau khi abort");
  } finally {
    dom.cleanup();
  }
});

test("US3 - T011: setupPreviewNavigation ngắt kết nối ResizeObserver khi gọi lại hoặc khi abort", () => {
  const dom = setupMockDocument(["preview-stage"]);
  try {
    const abortCtrl1 = new AbortController();

    // Lần 1: gọi initWriteTab
    initWriteTab({ signal: abortCtrl1.signal });
    const instances1 = globalThis.ResizeObserver?.instances || [];
    assert.equal(instances1.length, 1, "Phải có 1 ResizeObserver được tạo");
    assert.equal(instances1[0].disconnected, false, "Observer 1 phải đang active");

    // Lần 2: gọi lại initWriteTab -> observer cũ phải bị disconnect
    const abortCtrl2 = new AbortController();
    initWriteTab({ signal: abortCtrl2.signal });
    const instances2 = globalThis.ResizeObserver?.instances || [];
    assert.equal(instances2.length, 2, "Phải có 2 ResizeObserver được tạo qua 2 lần init");
    assert.equal(instances1[0].disconnected, true, "Observer 1 phải bị disconnect khi init lần 2");
    assert.equal(instances2[1].disconnected, false, "Observer 2 phải đang active");

    // Hủy abortCtrl2 -> observer 2 cũng phải bị disconnect
    abortCtrl2.abort();
    assert.equal(instances2[1].disconnected, true, "Observer 2 phải bị disconnect sau khi abort");
  } finally {
    dom.cleanup();
  }
});

test("US3 - T011: initQuotaAndBackupReminders có tính lũy đẳng và gắn lại đúng sau khi abort", () => {
  const dom = setupMockDocument([
    "btn-quota-backup",
    "btn-toast-dismiss",
    "btn-toast-backup",
    "backup-reminder-toast",
  ]);
  try {
    const btnQuota = dom.get("btn-quota-backup");
    const btnDismiss = dom.get("btn-toast-dismiss");
    const btnBackup = dom.get("btn-toast-backup");

    // Gọi liên tiếp 3 lần với cùng 1 signal -> chỉ có đúng 1 listener trên mỗi nút
    const abortCtrl1 = new AbortController();
    initQuotaAndBackupReminders({ signal: abortCtrl1.signal });
    initQuotaAndBackupReminders({ signal: abortCtrl1.signal });
    initQuotaAndBackupReminders({ signal: abortCtrl1.signal });

    assert.equal((btnQuota.listeners.get("click") || []).length, 1);
    assert.equal((btnDismiss.listeners.get("click") || []).length, 1);
    assert.equal((btnBackup.listeners.get("click") || []).length, 1);

    // Khi abort -> toàn bộ listener phải bị thu hồi và cờ đánh dấu được xóa
    abortCtrl1.abort();
    assert.equal((btnQuota.listeners.get("click") || []).length, 0);
    assert.equal((btnDismiss.listeners.get("click") || []).length, 0);
    assert.equal((btnBackup.listeners.get("click") || []).length, 0);

    // Khởi tạo lại ở chu kỳ mới -> gắn lại chính xác 1 listener hoạt động trên mỗi nút
    const abortCtrl2 = new AbortController();
    initQuotaAndBackupReminders({ signal: abortCtrl2.signal });
    assert.equal((btnQuota.listeners.get("click") || []).length, 1);
    assert.equal((btnDismiss.listeners.get("click") || []).length, 1);
    assert.equal((btnBackup.listeners.get("click") || []).length, 1);
  } finally {
    dom.cleanup();
  }
});



