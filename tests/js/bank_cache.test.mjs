import test from "node:test";
import assert from "node:assert/strict";
import { MockIDBDatabase } from "./helpers/mock_idb.mjs";
import { setDBInstance } from "../../webapp/js/storage.js";
import {
  initBankTab,
  refreshBankView,
  getBankSnapshotCacheForTesting,
  resetBankSnapshotCacheForTesting,
} from "../../webapp/js/bank.js";

test.beforeEach(() => {
  setDBInstance(new MockIDBDatabase());
  resetBankSnapshotCacheForTesting();
});

test("refreshBankView: Two-Phase Cache Commit chỉ ghi nhận cache sau khi render DOM thành công", async () => {
  // Giả lập môi trường DOM có đầy đủ phần tử
  const createdElements = new Map();
  const mockGrid = {
    id: "bank-cards-grid",
    innerHTML: "",
    appendChild() {},
  };
  const mockSummary = {
    id: "bank-summary",
    textContent: "",
    parentNode: {
      appendChild() {},
    },
  };
  const mockStatusText = {
    id: "status-text",
    textContent: "",
  };

  global.document = {
    getElementById: (id) => {
      if (id === "bank-cards-grid") return mockGrid;
      if (id === "bank-summary") return mockSummary;
      if (id === "status-text") return mockStatusText;
      if (id === "profile-active-name") return { textContent: "" };
      if (id.startsWith("cat-count-")) return { textContent: "" };
      return null;
    },
    createElement: (tag) => ({
      tagName: tag.toUpperCase(),
      style: {},
      classList: { add() {} },
      appendChild() {},
      append() {},
      replaceChildren() {},
      addEventListener() {},
      querySelector: () => ({ addEventListener() {} }),
    }),
  };

  const mockWorkerFn = async (action, params) => {
    if (action === "get_bank_snapshot") {
      return {
        ok: true,
        data: {
          revision: 5,
          worker_epoch: "epoch-uuid-1234",
          stats: { n_letters: 10, n_samples: 25 },
          letters: [["a", 2]],
          symbols: [],
          marks: [],
        },
      };
    }
    return { ok: true };
  };

  initBankTab(mockWorkerFn);

  // Lần gọi 1: Dựng thành công
  await refreshBankView();
  const cache1 = getBankSnapshotCacheForTesting();
  assert.strictEqual(cache1.epoch, "epoch-uuid-1234");
  assert.strictEqual(cache1.revision, 5);
  assert.strictEqual(cache1.profileId, "default_profile");
});

test("refreshBankView: Vô hiệu hóa cache khi phần tử #bank-cards-grid bị thiếu và tự động phục hồi ở lần gọi sau", async () => {
  let hasGrid = false;
  const mockGrid = {
    id: "bank-cards-grid",
    innerHTML: "",
    appendChild() {},
  };
  const mockSummary = {
    id: "bank-summary",
    textContent: "",
    parentNode: {
      appendChild() {},
    },
  };

  global.document = {
    getElementById: (id) => {
      if (id === "bank-cards-grid") return hasGrid ? mockGrid : null;
      if (id === "bank-summary") return mockSummary;
      if (id === "status-text") return { textContent: "" };
      if (id === "profile-active-name") return { textContent: "" };
      if (id.startsWith("cat-count-")) return { textContent: "" };
      return null;
    },
    createElement: (tag) => ({
      tagName: tag.toUpperCase(),
      style: {},
      classList: { add() {} },
      appendChild() {},
      append() {},
      replaceChildren() {},
      addEventListener() {},
      querySelector: () => ({ addEventListener() {} }),
    }),
  };

  let snapshotCallCount = 0;
  const mockWorkerFn = async (action) => {
    if (action === "get_bank_snapshot") {
      snapshotCallCount++;
      return {
        ok: true,
        data: {
          revision: 10,
          worker_epoch: "epoch-uuid-5678",
          stats: { n_letters: 5, n_samples: 10 },
          letters: [["b", 1]],
          symbols: [],
          marks: [],
        },
      };
    }
    return { ok: true };
  };

  initBankTab(mockWorkerFn);

  // Lần gọi 1: hasGrid = false -> applyFiltersAndRender ném lỗi
  await refreshBankView();
  const cacheAfterFail = getBankSnapshotCacheForTesting();
  // Khẳng định cache không được lưu phiên bản mới mà bị reset về null
  assert.strictEqual(cacheAfterFail.epoch, null);
  assert.strictEqual(cacheAfterFail.revision, null);
  assert.strictEqual(snapshotCallCount, 1);

  // Lần gọi 2: Giao diện đã sẵn sàng (hasGrid = true)
  hasGrid = true;
  await refreshBankView();
  // Khẳng định không bị cache chặn, get_bank_snapshot được gọi lại lần 2
  assert.strictEqual(snapshotCallCount, 2);
  const cacheAfterSuccess = getBankSnapshotCacheForTesting();
  assert.strictEqual(cacheAfterSuccess.epoch, "epoch-uuid-5678");
  assert.strictEqual(cacheAfterSuccess.revision, 10);
});
