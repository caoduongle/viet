import test from "node:test";
import assert from "node:assert/strict";
import {
  sendWorkerMessage,
  setWorkerInstance,
  handleWorkerFatalError,
  getPendingRequestsCount,
} from "../../webapp/js/app.js";

class MockWorker {
  constructor() {
    this.messagesSent = [];
    this.onmessage = null;
    this.onerror = null;
    this.onmessageerror = null;
  }

  postMessage(msg) {
    this.messagesSent.push(msg);
  }

  simulateResponse(id, ok, result, error) {
    if (this.onmessage) {
      this.onmessage({ data: { id, ok, result, error } });
    }
  }

  simulateError(message) {
    if (this.onerror) {
      this.onerror({ message });
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

test("sendWorkerMessage tự động timeout và reject với WorkerTimeoutError", async () => {
  const worker = new MockWorker();
  setWorkerInstance(worker);

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
