/**
 * Test suite cho Worker Resilience & Idempotent UI Event Listeners (Feature 046)
 * Chạy bằng: node tests/test_worker_resilience.mjs
 */
import test from "node:test";
import assert from "node:assert/strict";
import { MockIDBDatabase } from "./js/helpers/mock_idb.mjs";
import * as storage from "../webapp/js/storage.js";
import { initBankTab } from "../webapp/js/bank.js";
import { initWriteTab } from "../webapp/js/write.js";
import {
  recoverWorker,
  resetUiInitializedForTesting,
  getWorkerGeneration,
  getIsRecovering,
  getIsDomListenersAttached,
  onWorkerReady,
} from "../webapp/js/app.js";

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
}

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
    ...extraIds,
  ]);
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
            });
          }
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
  globalThis.document = {
    getElementById: (id) => getOrCreate(id),
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: () => {},
  };
  const hadWindow = typeof globalThis.window !== "undefined";
  if (!hadWindow) {
    globalThis.window = {
      addEventListener: () => {},
      removeEventListener: () => {},
      print: () => {},
    };
  }
  return {
    get: (id) => getOrCreate(id),
    cleanup: () => {
      delete globalThis.document;
      if (!hadWindow) {
        delete globalThis.window;
      }
    },
  };
}

// -------------------------------------------------------------
// USER STORY 1: Worker Recovery Resilience (T006 - T009)
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

    // w2 gửi READY hợp lệ
    w2.simulateReady();
    const res2 = await p2;
    assert.equal(res2, true, "Phiên thế hệ mới nhất phải kết thúc với true");
    assert.equal(getIsRecovering(), false, "isRecovering phải được giải phóng về false");
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
