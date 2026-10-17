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
  executeTransaction,
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

test("T004: executeTransaction tự động hủy giao dịch khi operationFn ném ngoại lệ đồng bộ", async () => {
  const mockDb = new MockIDBDatabase();
  setDBInstance(mockDb);

  await assert.rejects(
    async () => {
      await executeTransaction(mockDb, "profiles", "readwrite", (store, tx) => {
        store.put({ id: "ghost_profile", name: "Should not persist" });
        throw new Error("Lỗi đồng bộ cố ý trong operationFn");
      });
    },
    /Lỗi đồng bộ cố ý trong operationFn/
  );

  // Khẳng định ghost_profile không được commit vào database
  const p = await getProfile("ghost_profile");
  assert.equal(p, null, "ghost_profile không được phép lưu xuống database khi có ngoại lệ đồng bộ");
});

test("T005: saveProfile kiểm soát cạnh tranh 3 trạng thái và chặn hồi sinh hồ sơ đã xóa", async () => {
  // 1. Trạng thái 1: expectedUpdatedAt === null (Kỳ vọng hồ sơ chưa tồn tại)
  const pNew = { id: "p_new", name: "New Profile" };
  const saved1 = await saveProfile(pNew, null);
  assert.equal(saved1.id, "p_new");

  // Nếu hồ sơ đã tồn tại mà lại gọi với expectedUpdatedAt === null -> ConcurrencyConflictError
  await assert.rejects(
    async () => {
      await saveProfile({ id: "p_new", name: "Conflict New" }, null);
    },
    (err) => err.name === "ConcurrencyConflictError"
  );

  // 2. Trạng thái 2: expectedUpdatedAt là số (Kỳ vọng tồn tại và khớp phiên bản)
  const currentTs = saved1.updated_at;
  const saved2 = await saveProfile({ id: "p_new", name: "Updated Profile" }, currentTs);
  assert.ok(saved2.updated_at > currentTs, "updated_at phải đơn điệu tăng");

  // Sai phiên bản -> ConcurrencyConflictError
  await assert.rejects(
    async () => {
      await saveProfile({ id: "p_new", name: "Stale Update" }, currentTs);
    },
    (err) => err.name === "ConcurrencyConflictError"
  );

  // Xóa hồ sơ -> Khi phiên cũ cố lưu với expectedUpdatedAt là số thì PHẢI BÁO LỖI, KHÔNG ĐƯỢC TÁI TẠO
  await deleteProfile("p_new");
  assert.equal(await getProfile("p_new"), null);

  await assert.rejects(
    async () => {
      await saveProfile({ id: "p_new", name: "Resurrected Profile" }, saved2.updated_at);
    },
    (err) => err.name === "ConcurrencyConflictError"
  );
  assert.equal(await getProfile("p_new"), null, "Hồ sơ đã xóa không được phép hồi sinh");

  // 3. Trạng thái 3: expectedUpdatedAt === undefined (Ghi đè cưỡng bức không điều kiện)
  const forced = await saveProfile({ id: "p_forced", name: "Forced" }, undefined);
  assert.equal(forced.id, "p_forced");
  assert.ok(await getProfile("p_forced"));
});

test("T006: syncAndSaveActiveProfile ném lỗi khi hồ sơ bị xóa trước đó (localSyncedTimestamp > 0)", async () => {
  // Tạo hồ sơ ban đầu
  await setSetting("active_profile_id", "default_profile");
  const initProfile = await saveProfile({ id: "default_profile", name: "Initial", data: [1, 2] });
  setLocalSyncedTimestamp(initProfile.updated_at);

  // Tab khác xóa hồ sơ khỏi IndexedDB
  await deleteProfile("default_profile");
  assert.equal(await getProfile("default_profile"), null);

  const fakeWorker = async () => [1, 2, 3];

  // Tab hiện tại (đang có localSyncedTimestamp > 0) cố gắng sync_save
  await assert.rejects(
    async () => {
      await syncAndSaveActiveProfile(fakeWorker);
    },
    (err) => {
      return (
        err.name === "ConcurrencyConflictError" &&
        (err.codeName === "ProfileDeletedConflictError" || err.message.includes("đã bị xóa"))
      );
    }
  );

  // Khẳng định hồ sơ đã xóa không bị tái tạo lại trong IndexedDB
  assert.equal(await getProfile("default_profile"), null, "Hồ sơ đã xóa không được hồi sinh trong syncAndSaveActiveProfile");
});

test("T010: Cuộc đua ghi đồng thời thực sự tự động phát hiện xung đột, thử lại và hội tụ dữ liệu", async () => {
  await setSetting("active_profile_id", "default_profile");
  const init = await saveProfile({ id: "default_profile", name: "Race Initial", data: [1] });
  setLocalSyncedTimestamp(init.updated_at);

  let worker2Attempts = 0;

  // Caller 1: hoàn tất nhanh sau 10ms
  const worker1 = async (method, params) => {
    await new Promise((r) => setTimeout(r, 10));
    return [1, 10]; // thêm phần tử 10
  };

  // Caller 2: worker mất 20ms, trên attempt đầu cố gắng ghi đè bản gốc, bị xung đột và retry
  const worker2 = async (method, params) => {
    worker2Attempts++;
    if (params.diskGzBytes) {
      // Nhận được dữ liệu mới từ caller 1 sau khi xung đột
      return [...params.diskGzBytes, 20];
    }
    await new Promise((r) => setTimeout(r, 20));
    return [1, 20]; // ban đầu chỉ biết [1] và thêm 20
  };

  // Chạy đồng thời 2 caller mô phỏng 2 tab độc lập (không chia sẻ inMemoryLockChain và cùng khởi đầu từ init.updated_at)
  const [res1, res2] = await Promise.all([
    syncAndSaveActiveProfile(worker1, 3, { skipLock: true, initialSyncedTimestamp: init.updated_at }),
    syncAndSaveActiveProfile(worker2, 3, { skipLock: true, initialSyncedTimestamp: init.updated_at }),
  ]);

  assert.ok(res1);
  assert.ok(res2);
  assert.equal(worker2Attempts, 2, "Caller 2 phải bị xung đột ở lần 1 và thành công ở lần 2");
  const finalProfile = await getProfile("default_profile");
  assert.ok(finalProfile);
  // Cả 2 thay đổi đều được bảo toàn
  assert.deepEqual(finalProfile.data, [1, 10, 20], "Dữ liệu cuối cùng phải hội tụ đủ cả 2 thay đổi");
});


