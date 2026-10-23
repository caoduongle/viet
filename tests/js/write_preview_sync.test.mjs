import test from "node:test";
import assert from "node:assert/strict";
import zlib from "node:zlib";
import { MockIDBDatabase } from "./helpers/mock_idb.mjs";
import * as storage from "../../webapp/js/storage.js";
import { initBankTab, loadBankFromBytes } from "../../webapp/js/bank.js";
import {
  initWriteTab,
  triggerPreviewImmediate,
  notifyBankUpdated,
  markBankDirty,
  getWritePreviewSyncState,
  resetWriteSyncStateForTesting,
} from "../../webapp/js/write.js";
import {
  setWorkerInstance,
  onWorkerReady,
  recoverWorker,
  switchTab,
  notifySampleTaught,
  resetUiInitializedForTesting,
} from "../../webapp/js/app.js";

// Mẫu XOPP tối thiểu hợp lệ dạng XML nén GZIP
const sampleXoppXml = `<?xml version="1.0" standalone="no"?>
<xournal creator="hw_note" fileversion="4">
<title>Preview Document</title>
<page width="595.28" height="841.89">
<background type="solid" color="#ffffffff" style="lined"/>
<layer/>
</page>
</xournal>`;

const mockXoppBase64 = zlib.gzipSync(Buffer.from(sampleXoppXml)).toString("base64");

/**
 * Mock Worker phục vụ kiểm thử chu trình đồng bộ kho mẫu và kết xuất xem trước.
 */
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

  simulateReady() {
    if (this.onmessage) {
      this.onmessage({ data: { type: "READY" } });
    }
  }
}

/**
 * Tạo môi trường DOM giả lập cho Tab Viết và Tab Kho.
 */
function setupMockDom() {
  const elements = new Map();
  const listenersMap = new Map();

  const knownIds = new Set([
    "editor-text",
    "select-format",
    "paper-svg-wrapper",
    "preview-placeholder",
    "page-indicator",
    "status-indicator",
    "status-text",
    "badge-seed-used",
    "missing-tokens-box",
    "editor-warnings",
    "tab-write",
    "tab-bank",
    "btn-worker-retry",
    "splash-screen",
    "splash-status",
    "quota-warning-banner",
    "backup-reminder-toast",
    "btn-export-bank",
    "btn-import-bank",
    "input-import-bank",
    "btn-export-check",
    "btn-rename-profile",
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
    "btn-export-xopp",
    "btn-export-png",
    "btn-export-svg",
    "btn-export-zip",
    "btn-print-pdf",
    "modal-options",
    "btn-options",
    "btn-close-options",
    "btn-apply-options",
    "btn-cancel-options",
    "btn-reset-options",
    "opt-scale",
    "opt-line",
    "opt-space",
    "opt-jitter",
    "opt-wscale",
    "opt-color",
    "opt-seed",
    "opt-paper",
    "opt-orientation",
    "opt-background",
    "opt-stable-variants",
    "opt-assemble-letters",
    "btn-random-seed",
    "btn-latex-symbols",
    "modal-latex-symbols",
    "btn-close-latex",
    "latex-search",
    "latex-category-filters",
    "latex-symbol-grid",
    "latex-empty-state",
    "latex-copied-toast",
  ]);

  const activeClasses = new Map();

  const getOrCreate = (id) => {
    if (!knownIds.has(id)) return null;
    if (!elements.has(id)) {
      const listeners = new Map();
      const el = {
        id,
        style: { display: "" },
        disabled: false,
        textContent: "",
        className: id === "tab-write" ? "tab-panel active" : id.startsWith("tab-") ? "tab-panel" : "",
        value: "",
        innerHTML: "",
        options: [],
        listeners,
        classList: {
          contains: (cls) => {
            const list = activeClasses.get(id) || new Set();
            return list.has(cls);
          },
          add: (cls) => {
            if (!activeClasses.has(id)) activeClasses.set(id, new Set());
            activeClasses.get(id).add(cls);
          },
          remove: (cls) => {
            if (activeClasses.has(id)) activeClasses.get(id).delete(cls);
          },
        },
        replaceChildren: (...children) => {
          el.innerHTML = "";
        },
        appendChild: () => {},
        addEventListener(event, fn, options = {}) {
          if (!listeners.has(event)) listeners.set(event, []);
          listeners.get(event).push(fn);
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
      };
      if (id === "tab-write") {
        el.classList.add("active");
      }
      elements.set(id, el);
    }
    return elements.get(id);
  };

  const tabButtons = [
    { attr: "write", classList: { add: () => {}, remove: () => {} }, getAttribute: () => "write" },
    { attr: "bank", classList: { add: () => {}, remove: () => {} }, getAttribute: () => "bank" },
  ];

  const makeMockElement = (tag) => ({
    tagName: tag,
    setAttribute: () => {},
    getAttribute: () => null,
    appendChild: () => {},
    replaceChildren: () => {},
    classList: { add: () => {}, remove: () => {} },
    style: {},
  });

  globalThis.document = {
    documentElement: { getAttribute: () => "light" },
    getElementById: (id) => getOrCreate(id),
    querySelectorAll: (selector) => {
      if (selector === ".tab-btn") return tabButtons;
      if (selector === ".tab-panel") {
        return [getOrCreate("tab-write"), getOrCreate("tab-bank")].filter(Boolean);
      }
      return [];
    },
    querySelector: () => null,
    createElement: makeMockElement,
    createElementNS: (ns, tag) => makeMockElement(tag),
    addEventListener: (event, fn) => {
      if (!listenersMap.has(event)) listenersMap.set(event, []);
      listenersMap.get(event).push(fn);
    },
    removeEventListener: () => {},
  };

  if (!globalThis.window) {
    globalThis.window = {
      addEventListener: () => {},
      removeEventListener: () => {},
      matchMedia: () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }),
    };
  }

  return {
    elements,
    cleanup: () => {
      delete globalThis.document;
    },
  };
}

test.beforeEach(() => {
  resetWriteSyncStateForTesting();
  resetUiInitializedForTesting();
  const mockDb = new MockIDBDatabase();
  storage.setDBInstance(mockDb);
  storage.setLocalSyncedTimestamp(0);
});

test("T001 & T002: Kiểm tra module bindings và trạng thái cờ đồng bộ ban đầu", () => {
  const syncState = getWritePreviewSyncState();
  assert.strictEqual(syncState.hasText, false);
  assert.strictEqual(syncState.isRendering, false);
  assert.strictEqual(syncState.hasRendered, false);
  assert.strictEqual(syncState.isBankHydrated, false);
  assert.strictEqual(syncState.isBankDirty, false);
});

test("T007 [US1]: Hoàn thành load_bank trong onWorkerReady() tự động kích hoạt preview kho đã nạp, không bị render sớm kho rỗng", async () => {
  const dom = setupMockDom();
  try {
    const editor = document.getElementById("editor-text");
    editor.value = "Bài tập toán số 1: Giải phương trình 2x + 1 = 5";

    // Nạp sẵn hồ sơ có 192 ký tự vào IndexedDB
    await storage.saveProfile({
      id: "default_profile",
      name: "Kho đầy đủ",
      data: new Uint8Array([31, 139, 8, 0]),
      updated_at: Date.now(),
      teach_count_since_backup: 0,
    });
    await storage.setSetting("active_profile_id", "default_profile");

    const mockWorker = new SyncMockWorker();
    setWorkerInstance(mockWorker);

    // Kích hoạt onWorkerReady
    const readyPromise = onWorkerReady();

    // Đợi microtask để chu trình nạp IndexedDB gửi message load_bank
    await new Promise((r) => setTimeout(r, 20));

    // 1. Phải không có write_text trước khi load_bank hoàn thành
    const writeCallsBeforeLoad = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(
      writeCallsBeforeLoad.length,
      0,
      "Tuyệt đối không được gọi write_text khi load_bank từ IndexedDB chưa hoàn thành"
    );

    const loadBankMsg = mockWorker.messagesSent.find((m) => m.method === "load_bank");
    assert.ok(loadBankMsg, "Phải gửi load_bank sang Worker");

    // Giả lập worker phản hồi load_bank thành công
    mockWorker.simulateResponse(loadBankMsg.id, true, { ok: true, letters: 66, total_samples: 695 });
    await readyPromise;

    // Chờ microtask để notifyBankUpdated kích hoạt triggerPreviewImmediate
    await new Promise((r) => setTimeout(r, 20));

    // Sau khi load_bank hoàn thành, phải tự động kích hoạt kết xuất xem trước
    const writeCallsAfterLoad = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(
      writeCallsAfterLoad.length,
      1,
      "Phải kích hoạt đúng 1 lần write_text với kho mẫu đã nạp xong"
    );
    assert.strictEqual(writeCallsAfterLoad[0].params.text, editor.value);

    // Giả lập phản hồi render hoàn tất
    mockWorker.simulateResponse(writeCallsAfterLoad[0].id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    // Chờ chu trình render hoàn tất (decompress + parse xopp)
    for (let i = 0; i < 20 && !getWritePreviewSyncState().hasRendered; i++) {
      await new Promise((r) => setTimeout(r, 20));
    }

    const syncState = getWritePreviewSyncState();
    assert.strictEqual(syncState.isBankHydrated, true);
    assert.strictEqual(syncState.hasRendered, true);
    assert.strictEqual(syncState.isBankDirty, false);
  } finally {
    dom.cleanup();
  }
});

test("T008 [US1]: Người dùng lần đầu mở app (profiles rỗng) vẫn kích hoạt preview khởi đầu trên kho mặc định", async () => {
  const dom = setupMockDom();
  try {
    const editor = document.getElementById("editor-text");
    editor.value = "Văn bản thử nghiệm người dùng mới";

    const mockWorker = new SyncMockWorker();
    setWorkerInstance(mockWorker);

    await onWorkerReady();
    await new Promise((r) => setTimeout(r, 20));

    const writeCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(
      writeCalls.length,
      1,
      "Khi không có profile lưu sẵn, hệ thống vẫn kích hoạt render ban đầu cho người dùng"
    );
    // Trả về kết quả render hoàn tất
    mockWorker.simulateResponse(writeCalls[0].id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    await new Promise((r) => setTimeout(r, 20));

    const syncState = getWritePreviewSyncState();
    assert.strictEqual(syncState.isBankHydrated, true);
    assert.strictEqual(syncState.hasRendered, true);
  } finally {
    dom.cleanup();
  }
});

test("T012 [US2]: switchTab('write') chỉ re-render khi isBankDirty là true, không re-render dư thừa", async () => {
  const dom = setupMockDom();
  try {
    const editor = document.getElementById("editor-text");
    editor.value = "Nội dung cần xem";

    const mockWorker = new SyncMockWorker();
    setWorkerInstance(mockWorker);

    // Bắt đầu với kho đã nạp và đã render 1 lần
    notifyBankUpdated({ reason: "hydrated", immediate: true });
    const initialWriteCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(initialWriteCalls.length, 1);

    // Giả lập worker phản hồi render thành công với XOPP gzipped chuẩn
    mockWorker.simulateResponse(initialWriteCalls[0].id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    await new Promise((r) => setTimeout(r, 30));

    const stateAfterRender = getWritePreviewSyncState();
    assert.strictEqual(stateAfterRender.hasRendered, true);
    assert.strictEqual(stateAfterRender.isBankDirty, false);

    // Chuyển sang Tab Kho mẫu
    switchTab("bank");

    // Chuyển lại Tab Viết chữ khi KHÔNG có thay đổi kho
    switchTab("write");
    const writeCallsWithoutDirty = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(
      writeCallsWithoutDirty.length,
      1,
      "Không được gửi thêm write_text nếu kho mẫu không thay đổi (isBankDirty = false)"
    );

    // Bây giờ đánh dấu kho mẫu bị thay đổi trong nền
    markBankDirty();
    assert.strictEqual(getWritePreviewSyncState().isBankDirty, true);

    // Chuyển về Tab Viết chữ
    switchTab("write");
    const writeCallsWithDirty = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(
      writeCallsWithDirty.length,
      2,
      "Phải kích hoạt re-render khi isBankDirty = true lúc switchTab('write')"
    );

    // Trả lời phản hồi render lần 2
    mockWorker.simulateResponse(writeCallsWithDirty[1].id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    await new Promise((r) => setTimeout(r, 20));
  } finally {
    dom.cleanup();
  }
});

test("T013 [US2]: loadBankFromBytes() trong bank.js đánh dấu isBankDirty = true", async () => {
  const dom = setupMockDom();
  try {
    const mockWorker = new SyncMockWorker();
    initBankTab((method, params) => {
      return new Promise((resolve) => {
        if (method === "load_bank") {
          resolve({ ok: true, letters: 66, total_samples: 695 });
        } else {
          resolve({ ok: true });
        }
      });
    });

    const dummyGz = new Uint8Array([31, 139, 8, 0, 1, 2, 3]);
    await loadBankFromBytes(dummyGz, "Kho vừa tải lên");

    const syncState = getWritePreviewSyncState();
    assert.strictEqual(
      syncState.isBankDirty,
      true,
      "loadBankFromBytes phải đánh dấu isBankDirty để Tab Viết chữ làm mới khi được mở"
    );
  } finally {
    dom.cleanup();
  }
});

test("T014 [US2]: Sự kiện đa tab BANK_SYNCHRONIZED làm mới Tab Viết chữ khi đang mở", async () => {
  const dom = setupMockDom();
  try {
    const editor = document.getElementById("editor-text");
    editor.value = "Văn bản đồng bộ từ tab khác";

    const mockWorker = new SyncMockWorker();
    setWorkerInstance(mockWorker);

    // Tab Viết chữ đang active
    const tabWrite = document.getElementById("tab-write");
    tabWrite.classList.add("active");

    // Nhận tín hiệu đồng bộ đa tab
    notifyBankUpdated({ reason: "sync", immediate: true });

    const writeCalls = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(
      writeCalls.length,
      1,
      "BANK_SYNCHRONIZED phải tự động kích hoạt preview khi Tab Viết chữ đang active"
    );

    mockWorker.simulateResponse(writeCalls[0].id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    await new Promise((r) => setTimeout(r, 20));
  } finally {
    dom.cleanup();
  }
});

test("T019 [US3]: Phục hồi Worker (recoverWorker) nạp lại kho và tự động dựng lại bản xem trước Tab Viết", async () => {
  const dom = setupMockDom();
  try {
    const editor = document.getElementById("editor-text");
    editor.value = "Văn bản sau khi worker crash và phục hồi";

    await storage.saveProfile({
      id: "default_profile",
      name: "Kho hồi phục",
      data: new Uint8Array([31, 139, 8, 0]),
      updated_at: Date.now(),
      teach_count_since_backup: 0,
    });
    await storage.setSetting("active_profile_id", "default_profile");

    let createdWorker = null;
    class RecoveredWorker extends SyncMockWorker {
      constructor() {
        super();
        createdWorker = this;
      }
    }

    const recoveryPromise = recoverWorker(RecoveredWorker, 5000, { force: true });

    // Chờ worker mới được tạo
    await new Promise((resolve) => setTimeout(resolve, 20));
    assert.ok(createdWorker, "Worker mới phải được khởi tạo");

    // Phát READY
    createdWorker.simulateReady();

    // Chờ xử lý IndexedDB -> load_bank
    await new Promise((resolve) => setTimeout(resolve, 20));
    const loadMsg = createdWorker.messagesSent.find((m) => m.method === "load_bank");
    assert.ok(loadMsg, "Worker phục hồi phải nạp lại kho từ IndexedDB");

    createdWorker.simulateResponse(loadMsg.id, true, { ok: true, letters: 66, total_samples: 695 });

    const recoveryResult = await recoveryPromise;
    assert.strictEqual(recoveryResult, true, "Phục hồi worker phải thành công");

    // Chờ microtask để notifyBankUpdated kích hoạt triggerPreviewImmediate
    await new Promise((resolve) => setTimeout(resolve, 20));

    // Xác nhận write_text được gọi lại sau khi phục hồi
    const writeCalls = createdWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(
      writeCalls.length,
      1,
      "Tab Viết chữ phải được tự động dựng lại sau khi Worker phục hồi và nạp xong kho"
    );

    createdWorker.simulateResponse(writeCalls[0].id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    await new Promise((r) => setTimeout(r, 20));
  } finally {
    dom.cleanup();
  }
});

test("T015 [US5]: Kiểm soát phiên bản bankRevision đơn điệu, không mất cờ isBankDirty khi render chen ngang hoặc thất bại", async () => {
  const dom = setupMockDom();
  try {
    const mockWorker = new SyncMockWorker();
    setWorkerInstance(mockWorker);

    const editor = document.getElementById("editor-text");
    editor.value = "Kiểm tra race condition bankRevision";

    let state = getWritePreviewSyncState();
    assert.strictEqual(state.bankRevision, 1);
    assert.strictEqual(state.lastRenderedRevision, 0);
    assert.strictEqual(state.isBankDirty, false);

    // Bắt đầu render lượt 1 (tại bankRevision = 1)
    triggerPreviewImmediate();
    const writeCalls1 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(writeCalls1.length, 1);
    const req1Id = writeCalls1[0].id;

    // Trong lúc render 1 đang chạy trong nền, người dùng cập nhật kho mẫu (notifyBankUpdated)
    notifyBankUpdated({ immediate: false });
    state = getWritePreviewSyncState();
    assert.strictEqual(state.bankRevision, 2, "bankRevision phải tăng đơn điệu lên 2");
    assert.strictEqual(state.isBankDirty, true, "isBankDirty phải bật thành true");

    // Render 1 hoàn tất
    mockWorker.simulateResponse(req1Id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    await new Promise((r) => setTimeout(r, 80));

    state = getWritePreviewSyncState();
    assert.strictEqual(state.lastRenderedRevision, 1, "lastRenderedRevision ghi nhận bản vẽ 1");
    assert.strictEqual(
      state.isBankDirty,
      true,
      "isBankDirty PHẢI giữ nguyên true vì bản vẽ trên màn hình là kho cũ (rev 1 < rev 2)"
    );

    // Kích hoạt render lượt 2 (cho revision 2)
    triggerPreviewImmediate();
    const writeCalls2 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(writeCalls2.length, 2);
    const req2Id = writeCalls2[1].id;

    // Giả sử lượt 2 gặp lỗi Worker
    mockWorker.simulateResponse(req2Id, true, {
      ok: false,
      error: "Worker memory pressure",
    });
    await new Promise((r) => setTimeout(r, 80));

    state = getWritePreviewSyncState();
    assert.strictEqual(state.isBankDirty, true, "Render lỗi phải giữ nguyên cờ dirty để người dùng có thể thử lại");

    // Thử lại lần 3 thành công
    triggerPreviewImmediate();
    const writeCalls3 = mockWorker.messagesSent.filter((m) => m.method === "write_text");
    assert.strictEqual(writeCalls3.length, 3);
    const req3Id = writeCalls3[2].id;

    mockWorker.simulateResponse(req3Id, true, {
      ok: true,
      xopp_base64: mockXoppBase64,
      missing_token_boxes: [],
    });
    await new Promise((r) => setTimeout(r, 80));

    state = getWritePreviewSyncState();
    assert.strictEqual(state.lastRenderedRevision, 2);
    assert.strictEqual(state.isBankDirty, false, "Render thành công với đúng revision hiện hành mới xóa cờ dirty");
  } finally {
    dom.cleanup();
  }
});
