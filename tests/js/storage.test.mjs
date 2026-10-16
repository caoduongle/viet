import test from "node:test";
import assert from "node:assert/strict";
import { MockIDBDatabase } from "./helpers/mock_idb.mjs";
import {
  setDBInstance,
  saveProfile,
  getProfile,
  deleteProfile,
  setSetting,
  getSetting,
  requestProfileLock,
  setLocalSyncedTimestamp,
  getLocalSyncedTimestamp,
  syncAndSaveActiveProfile,
} from "../../webapp/js/storage.js";

test.beforeEach(() => {
  const mockDb = new MockIDBDatabase();
  setDBInstance(mockDb);
  setLocalSyncedTimestamp(0);
});

test("saveProfile chỉ resolve khi transaction commit (tx.oncomplete)", async () => {
  const profile = { id: "p1", name: "Profile 1", data: [1, 2, 3] };
  const saved = await saveProfile(profile);

  assert.equal(saved.id, "p1");
  assert.equal(saved.name, "Profile 1");
  assert.equal(typeof saved.updated_at, "number");

  const retrieved = await getProfile("p1");
  assert.equal(retrieved.id, "p1");
  assert.equal(retrieved.updated_at, saved.updated_at);
});

test("saveProfile bảo toàn QuotaExceededError khi transaction abort", async () => {
  const mockDb = new MockIDBDatabase();
  mockDb.simulateQuotaExceeded(true);
  setDBInstance(mockDb);

  const profile = { id: "p_quota", name: "Full" };
  await assert.rejects(
    async () => {
      await saveProfile(profile);
    },
    (err) => {
      return err.name === "QuotaExceededError";
    }
  );
});

test("setSetting và deleteProfile hoàn tất qua commit transaction", async () => {
  await setSetting("test_key", "test_val");
  const val = await getSetting("test_key");
  assert.equal(val, "test_val");

  await saveProfile({ id: "p_del", name: "To Delete" });
  let p = await getProfile("p_del");
  assert.ok(p);

  await deleteProfile("p_del");
  p = await getProfile("p_del");
  assert.equal(p, null);
});

test("syncAndSaveActiveProfile cập nhật localSyncedTimestamp trùng khớp với savedProfile.updated_at", async () => {
  // Giả lập worker nhận sync_save và trả về bytes
  const fakeWorker = async (method, params) => {
    if (method === "sync_save") {
      return [10, 20, 30];
    }
    return null;
  };

  const saved = await syncAndSaveActiveProfile(fakeWorker);
  assert.ok(saved);
  assert.equal(typeof saved.updated_at, "number");
  assert.equal(getLocalSyncedTimestamp(), saved.updated_at, "localSyncedTimestamp phải khớp chính xác với savedProfile.updated_at");
});

test("requestProfileLock fallback tuần tự hoá các tác vụ khi navigator.locks không khả dụng", async () => {
  const log = [];
  const task1 = () =>
    new Promise((resolve) => {
      setTimeout(() => {
        log.push("task1");
        resolve();
      }, 50);
    });

  const task2 = () =>
    new Promise((resolve) => {
      log.push("task2");
      resolve();
    });

  // Chạy cả 2 tác vụ song song
  await Promise.all([
    requestProfileLock("test_lock", task1),
    requestProfileLock("test_lock", task2),
  ]);

  // Với cơ chế tuần tự hoá, task1 bắt đầu trước thì phải hoàn thành trước task2
  assert.deepEqual(log, ["task1", "task2"]);
});
