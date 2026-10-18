import test from "node:test";
import assert from "node:assert/strict";
import { MockIDBDatabase } from "./helpers/mock_idb.mjs";
import * as storage from "../../webapp/js/storage.js";
import {
  sendWorkerMessage,
  setWorkerInstance,
  handleWorkerFatalError,
  getPendingRequestsCount,
  recoverWorker,
  getWorkerGeneration,
  getIsRecovering,
  getIsUiInitialized,
  resetUiInitializedForTesting,
  onWorkerReady,
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

function setupMockDocument() {
  const knownIds = new Set([
    "btn-worker-retry",
    "splash-screen",
    "splash-status",
    "status-indicator",
    "status-text",
    "quota-warning-banner",
    "backup-reminder-toast",
  ]);
  const elements = new Map();
  const getOrCreate = (id) => {
    if (!knownIds.has(id)) {
      return null;
    }
    if (!elements.has(id)) {
      elements.set(id, {
        id,
        style: { display: "none" },
        disabled: false,
        textContent: "",
        className: "",
        addEventListener: () => {},
      });
    }
    return elements.get(id);
  };
  globalThis.document = {
    getElementById: (id) => getOrCreate(id),
    addEventListener: () => {},
  };
  const hadWindow = typeof globalThis.window !== "undefined";
  if (!hadWindow) {
    globalThis.window = {
      addEventListener: () => {},
      removeEventListener: () => {},
    };
  }
  return {
    btnRetry: getOrCreate("btn-worker-retry"),
    splash: getOrCreate("splash-screen"),
    cleanup: () => {
      delete globalThis.document;
      if (!hadWindow) {
        delete globalThis.window;
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

