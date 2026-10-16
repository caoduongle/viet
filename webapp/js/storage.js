/**
 * storage.js -- Quản lý lưu trữ IndexedDB, Web Locks API và BroadcastChannel đa tab.
 * Tuân thủ nghiêm ngặt contracts/storage-protocol.md và data-model.md.
 */

const DB_NAME = "chuviettay_db";
const DB_VERSION = 1;
const SYNC_CHANNEL_NAME = "chuviettay_sync";

let dbInstance = null;
let broadcastChannel = null;

export async function getDB() {
  if (dbInstance) return dbInstance;
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains("profiles")) {
        const profileStore = db.createObjectStore("profiles", { keyPath: "id" });
        profileStore.createIndex("updated_at", "updated_at", { unique: false });
      }
      if (!db.objectStoreNames.contains("app_settings")) {
        db.createObjectStore("app_settings", { keyPath: "key" });
      }
    };

    request.onsuccess = (event) => {
      dbInstance = event.target.result;
      resolve(dbInstance);
    };

    request.onerror = (event) => {
      reject(new Error(`Lỗi mở IndexedDB: ${event.target.error}`));
    };
  });
}

export function getSyncChannel(onMessageCallback) {
  if (!broadcastChannel) {
    broadcastChannel = new BroadcastChannel(SYNC_CHANNEL_NAME);
    if (broadcastChannel && typeof broadcastChannel.unref === "function") {
      broadcastChannel.unref();
    }
  }
  if (onMessageCallback) {
    broadcastChannel.onmessage = (event) => {
      onMessageCallback(event.data);
    };
  }
  return broadcastChannel;
}

export function closeSyncChannel() {
  if (broadcastChannel) {
    broadcastChannel.close();
    broadcastChannel = null;
  }
}

export function broadcastBankSync(profileId) {
  const channel = getSyncChannel();
  channel.postMessage({
    type: "BANK_SYNCHRONIZED",
    profileId,
    timestamp: Date.now(),
  });
}

export function setDBInstance(db) {
  dbInstance = db;
}

/**
 * Thực thi giao dịch IndexedDB bền vững:
 * - Chỉ resolve khi tx.oncomplete kích hoạt (dữ liệu đã commit bền vững xuống đĩa).
 * - Bắt tx.onerror và tx.onabort, bảo toàn mã lỗi QuotaExceededError từ request.
 */
export function executeTransaction(db, storeNames, mode, operationFn) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeNames, mode);
    let result = undefined;
    let lastRequestError = null;
    let settled = false;

    const safeReject = (err) => {
      if (settled) return;
      settled = true;
      reject(err);
    };

    const safeResolve = (val) => {
      if (settled) return;
      settled = true;
      resolve(val);
    };

    tx.oncomplete = () => safeResolve(result);

    tx.onerror = () => {
      const err = tx.error || lastRequestError || new Error("Lỗi giao dịch IndexedDB");
      safeReject(err);
    };

    tx.onabort = () => {
      const err = tx.error || lastRequestError || new DOMException("Giao dịch IndexedDB bị hủy bỏ", "AbortError");
      safeReject(err);
    };

    try {
      const store = Array.isArray(storeNames) ? null : tx.objectStore(storeNames);
      result = operationFn(store, tx, (reqErr) => {
        lastRequestError = reqErr;
      });
    } catch (err) {
      safeReject(err);
    }
  });
}

let inMemoryLockChain = Promise.resolve();

export async function requestProfileLock(profileId, taskFn) {
  if (typeof navigator !== "undefined" && navigator.locks && navigator.locks.request) {
    return navigator.locks.request(`chuviettay_lock_${profileId}`, async () => {
      return await taskFn();
    });
  }
  // Dự phòng nếu trình duyệt không hỗ trợ Web Locks API:
  // Tuần tự hoá bằng chuỗi Promise trong cùng tab
  const prevChain = inMemoryLockChain;
  let release;
  inMemoryLockChain = new Promise((res) => {
    release = res;
  });
  try {
    await prevChain;
    return await taskFn();
  } finally {
    release();
  }
}

export async function getProfile(profileId) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("profiles", "readonly");
    const store = tx.objectStore("profiles");
    const req = store.get(profileId);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

export async function saveProfile(profile, expectedUpdatedAt) {
  const db = await getDB();
  const payload = {
    ...profile,
    updated_at: typeof profile.updated_at === "number" ? profile.updated_at : Date.now(),
  };

  return executeTransaction(db, "profiles", "readwrite", (store, tx, onError) => {
    if (expectedUpdatedAt !== undefined) {
      const getReq = store.get(payload.id);
      getReq.onsuccess = () => {
        const existing = getReq.result;
        if (existing && existing.updated_at !== expectedUpdatedAt) {
          const conflictErr = new DOMException(
            `Xung đột đồng bộ: hồ sơ đã bị cập nhật bởi phiên khác (kỳ vọng: ${expectedUpdatedAt}, thực tế: ${existing.updated_at}).`,
            "ConcurrencyConflictError"
          );
          onError(conflictErr);
          tx.abort();
          return;
        }
        const putReq = store.put(payload);
        putReq.onerror = () => onError(putReq.error);
      };
      getReq.onerror = () => onError(getReq.error);
    } else {
      const putReq = store.put(payload);
      putReq.onerror = () => onError(putReq.error);
    }
    return payload;
  });
}

export async function listProfiles() {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("profiles", "readonly");
    const store = tx.objectStore("profiles");
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

export async function deleteProfile(profileId) {
  const db = await getDB();
  return executeTransaction(db, "profiles", "readwrite", (store, tx, onError) => {
    const req = store.delete(profileId);
    req.onerror = () => onError(req.error);
    return true;
  });
}

export async function getSetting(key, defaultValue = null) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("app_settings", "readonly");
    const store = tx.objectStore("app_settings");
    const req = store.get(key);
    req.onsuccess = () => resolve(req.result ? req.result.value : defaultValue);
    req.onerror = () => reject(req.error);
  });
}

export async function setSetting(key, value) {
  const db = await getDB();
  return executeTransaction(db, "app_settings", "readwrite", (store, tx, onError) => {
    const req = store.put({ key, value });
    req.onerror = () => onError(req.error);
    return true;
  });
}

let localSyncedTimestamp = 0;

export function setLocalSyncedTimestamp(ts) {
  localSyncedTimestamp = Number(ts) || 0;
}

export function getLocalSyncedTimestamp() {
  return localSyncedTimestamp;
}

/**
 * Giao thức lưu 4 bước theo contracts/storage-protocol.md:
 * 1. Xin Web Lock
 * 2. Đọc file gz mới nhất từ IndexedDB -> nạp vào MEMFS (nếu có cập nhật từ tab khác)
 * 3. Worker flush_save() -> Bank.save() tự so sánh stat để merge -> export_bank()
 * 4. Ghi lại IndexedDB và phát sóng BroadcastChannel
 */
export async function syncAndSaveActiveProfile(sendWorkerFn, maxRetries = 3) {
  const activeId = await getSetting("active_profile_id", "default_profile");
  return await requestProfileLock(activeId, async () => {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const currentProfile = await getProfile(activeId);
        let diskGzBytes = null;
        const baseUpdatedAt = currentProfile ? currentProfile.updated_at : undefined;

        // Chỉ merge nếu IndexedDB có bản mới hơn bản tab hiện tại từng đọc
        if (currentProfile && currentProfile.data && currentProfile.updated_at > localSyncedTimestamp) {
          console.log("[Storage] Phát hiện thay đổi từ tab khác trong IndexedDB, tiến hành hợp nhất...");
          diskGzBytes = Array.from(new Uint8Array(currentProfile.data));
        }

        const mergedBytes = await sendWorkerFn("sync_save", { diskGzBytes });
        if (!mergedBytes) {
          throw new Error("Không nhận được dữ liệu kho sau khi đồng bộ.");
        }

        const updatedProfile = {
          id: activeId,
          name: currentProfile ? currentProfile.name : "Kho của tôi",
          data: mergedBytes,
          teach_count_since_backup: currentProfile ? (currentProfile.teach_count_since_backup || 0) : 0,
          updated_at: Date.now(),
        };

        const savedProfile = await saveProfile(updatedProfile, baseUpdatedAt);
        localSyncedTimestamp = savedProfile.updated_at;
        broadcastBankSync(activeId);
        return savedProfile;
      } catch (err) {
        if (err.name === "ConcurrencyConflictError" && attempt < maxRetries - 1) {
          console.warn(`[Storage] Xung đột đồng bộ (thử lần ${attempt + 1}/${maxRetries}), thử lại...`);
          continue;
        }
        throw err;
      }
    }
  });
}

/**
 * Tăng bộ đếm số mẫu dạy từ lần sao lưu gần nhất.
 */
export async function incrementTeachCount(profileId) {
  const profile = await getProfile(profileId);
  if (!profile) return 1;
  const current = (profile.teach_count_since_backup || 0) + 1;
  profile.teach_count_since_backup = current;
  await saveProfile(profile);
  return current;
}

/**
 * Đặt lại bộ đếm số mẫu dạy khi người dùng đã sao lưu.
 */
export async function resetTeachCount(profileId) {
  const profile = await getProfile(profileId);
  if (!profile) return;
  profile.teach_count_since_backup = 0;
  await saveProfile(profile);
}

/**
 * Kiểm tra hạn ngạch bộ nhớ lưu trữ trình duyệt (T067).
 */
export async function checkStorageQuota() {
  if (navigator.storage && navigator.storage.estimate) {
    try {
      const estimate = await navigator.storage.estimate();
      const usage = estimate.usage || 0;
      const quota = estimate.quota || 0;
      const ratio = quota > 0 ? usage / quota : 0;
      return {
        usage,
        quota,
        ratio,
        isNearLimit: ratio >= 0.8,
      };
    } catch (err) {
      console.warn("Không thể ước lượng hạn ngạch lưu trữ:", err);
    }
  }
  return { usage: 0, quota: 0, ratio: 0, isNearLimit: false };
}
