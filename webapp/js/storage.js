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
  }
  if (onMessageCallback) {
    broadcastChannel.onmessage = (event) => {
      onMessageCallback(event.data);
    };
  }
  return broadcastChannel;
}

export function broadcastBankSync(profileId) {
  const channel = getSyncChannel();
  channel.postMessage({
    type: "BANK_SYNCHRONIZED",
    profileId,
    timestamp: Date.now(),
  });
}

export async function requestProfileLock(profileId, taskFn) {
  if (navigator.locks && navigator.locks.request) {
    return navigator.locks.request(`chuviettay_lock_${profileId}`, async () => {
      return await taskFn();
    });
  }
  // Dự phòng nếu trình duyệt không hỗ trợ Web Locks API
  return await taskFn();
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

export async function saveProfile(profile) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("profiles", "readwrite");
    const store = tx.objectStore("profiles");
    const payload = {
      ...profile,
      updated_at: Date.now(),
    };
    const req = store.put(payload);
    req.onsuccess = () => resolve(payload);
    req.onerror = () => reject(req.error);
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
  return new Promise((resolve, reject) => {
    const tx = db.transaction("profiles", "readwrite");
    const store = tx.objectStore("profiles");
    const req = store.delete(profileId);
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
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
  return new Promise((resolve, reject) => {
    const tx = db.transaction("app_settings", "readwrite");
    const store = tx.objectStore("app_settings");
    const req = store.put({ key, value });
    req.onsuccess = () => resolve(true);
    req.onerror = () => reject(req.error);
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
export async function syncAndSaveActiveProfile(sendWorkerFn) {
  const activeId = await getSetting("active_profile_id", "default_profile");
  return await requestProfileLock(activeId, async () => {
    const currentProfile = await getProfile(activeId);
    let diskGzBytes = null;

    // Chỉ merge nếu IndexedDB có bản mới hơn bản tab hiện tại từng đọc
    if (currentProfile && currentProfile.data && currentProfile.updated_at > localSyncedTimestamp) {
      console.log("[Storage] Phát hiện thay đổi từ tab khác trong IndexedDB, tiến hành hợp nhất...");
      diskGzBytes = Array.from(new Uint8Array(currentProfile.data));
    }

    const mergedBytes = await sendWorkerFn("sync_save", { diskGzBytes });
    if (!mergedBytes) {
      throw new Error("Không nhận được dữ liệu kho sau khi đồng bộ.");
    }

    const now = Date.now();
    const updatedProfile = {
      id: activeId,
      name: currentProfile ? currentProfile.name : "Kho của tôi",
      data: mergedBytes,
      teach_count_since_backup: currentProfile ? (currentProfile.teach_count_since_backup || 0) : 0,
      updated_at: now,
    };
    await saveProfile(updatedProfile);
    localSyncedTimestamp = now;
    broadcastBankSync(activeId);
    return updatedProfile;
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
