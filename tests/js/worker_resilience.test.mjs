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

