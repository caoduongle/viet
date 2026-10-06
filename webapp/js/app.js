/**
 * app.js -- Entrypoint chính của Web Client.
 * Điều phối kết nối Worker, giao diện người dùng, lưu trữ và các tabs.
 * Tuân thủ nghiêm ngặt contracts/storage-protocol.md và User Story 5.
 */
import * as storage from "./storage.js";
import { t } from "./i18n.js";
import { initBankTab, loadBankFromBytes, refreshBankView, exportCurrentBank } from "./bank.js";
import { initWriteTab } from "./write.js";
import { TeachController } from "./teach.js";

let worker = null;
let reqId = 1;
const pendingRequests = new Map();

let saveDebounceTimer = null;
let reminderDismissed = false;

export function sendWorkerMessage(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = reqId++;
    pendingRequests.set(id, { resolve, reject });
    worker.postMessage({ id, method, params });
  });
}

// -------------------------------------------------------------
// 1. Quản lý lưu trữ tự động & Đồng bộ đa tab (T065, T066)
// -------------------------------------------------------------
export function scheduleAutoSave() {
  if (saveDebounceTimer) clearTimeout(saveDebounceTimer);
  setStatus("status_saving", false, true);
  saveDebounceTimer = setTimeout(async () => {
    await triggerSyncSave();
  }, 2000);
}

export async function triggerSyncSave() {
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer);
    saveDebounceTimer = null;
  }
  try {
    setStatus("status_saving", false, true);
    await storage.syncAndSaveActiveProfile(sendWorkerMessage);
    setStatus("status_saved");
    setTimeout(() => setStatus("status_ready"), 2000);
    // Kiểm tra dung lượng lưu trữ sau khi lưu thành công
    await checkQuotaStatus();
  } catch (err) {
    console.error("Lỗi khi lưu đồng bộ kho mẫu:", err);
    if (err.name === "QuotaExceededError") {
      showQuotaWarning();
    }
    setStatus("status_error", true);
  }
}

async function checkQuotaStatus() {
  const quota = await storage.checkStorageQuota();
  if (quota && quota.isNearLimit) {
    showQuotaWarning();
  }
}

function showQuotaWarning() {
  const banner = document.getElementById("storage-quota-warning");
  if (banner) banner.style.display = "flex";
}

export async function notifySampleTaught(label) {
  const activeId = await storage.getSetting("active_profile_id", "default_profile");
  const count = await storage.incrementTeachCount(activeId);

  // Hiển thị toast nếu vượt ngưỡng 20 mẫu và chưa bị tắt trong phiên (T067)
  if (count >= 20 && !reminderDismissed) {
    const toastEl = document.getElementById("backup-reminder-toast");
    if (toastEl) toastEl.style.display = "block";
  }

  scheduleAutoSave();
}
window.__notifySampleTaught = notifySampleTaught;

// -------------------------------------------------------------
// 2. Khởi tạo Worker
// -------------------------------------------------------------
function initWorker() {
  worker = new Worker("js/worker/py-worker.js", { type: "module" });

  worker.onmessage = (e) => {
    const data = e.data;
    if (data.type === "PROGRESS") {
      const { percent, message } = data.payload;
      const bar = document.getElementById("splash-bar");
      const status = document.getElementById("splash-status");
      if (bar) bar.style.width = `${percent}%`;
      if (status) status.textContent = message;
    } else if (data.type === "READY") {
      onWorkerReady();
    } else if (data.type === "ERROR") {
      console.error("Lỗi Worker:", data.payload);
      const status = document.getElementById("splash-status");
      if (status) status.textContent = `Lỗi khởi tạo: ${data.payload.message}`;
    } else if (data.id) {
      const req = pendingRequests.get(data.id);
      if (req) {
        pendingRequests.delete(data.id);
        if (data.ok) {
          req.resolve(data.result);
        } else {
          req.reject(new Error(data.error));
        }
      }
    }
  };
}

// -------------------------------------------------------------
// 3. Xử lý sau khi Pyodide Worker đã sẵn sàng
// -------------------------------------------------------------
async function onWorkerReady() {
  // Ẩn màn hình splash
  const splash = document.getElementById("splash-screen");
  if (splash) splash.style.display = "none";

  // Xin quyền lưu trữ bền vững (T037)
  if (navigator.storage && navigator.storage.persist) {
    try {
      const isPersisted = await navigator.storage.persist();
      console.log("[Storage] Persisted storage:", isPersisted);
    } catch (e) {
      console.warn("[Storage] Persist request error:", e);
    }
  }

  // Khởi tạo tab Kho mẫu, Tab Viết chữ & Tab Dạy mẫu
  initBankTab(sendWorkerMessage);
  initWriteTab();
  const teachController = new TeachController(
    { request: sendWorkerMessage },
    { onSampleSaved: notifySampleTaught }
  );
  await teachController.init();
  window.__teachController = teachController;

  // Lắng nghe đồng bộ đa tab qua BroadcastChannel (T066)
  storage.getSyncChannel(async (msg) => {
    if (msg.type === "BANK_SYNCHRONIZED") {
      const activeId = await storage.getSetting("active_profile_id", "default_profile");
      if (msg.profileId === activeId) {
        console.log("[Multi-Tab] Nhận tín hiệu đồng bộ từ tab khác cho hồ sơ:", activeId);
        storage.setLocalSyncedTimestamp(msg.timestamp || Date.now());
        setStatus("status_syncing", false, true);
        const profile = await storage.getProfile(activeId);
        if (profile && profile.data) {
          await sendWorkerMessage("load_bank", {
            gzBytes: Array.from(new Uint8Array(profile.data)),
            createIfMissing: false,
          });
          await refreshBankView();
          if (window.__teachController) {
            await window.__teachController.refresh();
          }
        }
        setStatus("status_ready");
      }
    }
  });

  // Gắn hook tự động flush lưu khi người dùng chuyển tab trình duyệt hoặc đóng trang (T066)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      triggerSyncSave();
    }
  });
  window.addEventListener("pagehide", () => {
    triggerSyncSave();
  });

  // Thiết lập sự kiện cho Cảnh báo dung lượng & Nhắc nhở sao lưu (T067)
  initQuotaAndBackupReminders();
  initGuideModal();

  // Kiểm tra hồ sơ trong IndexedDB (T035, T036)
  const profiles = await storage.listProfiles();
  if (!profiles || profiles.length === 0) {
    // Chưa có kho nào -> Hiện màn hình chào (T035)
    showWelcomeModal();
  } else {
    // Đã có kho -> Nạp hồ sơ đang kích hoạt
    const activeId = await storage.getSetting("active_profile_id", profiles[0].id);
    const profile = await storage.getProfile(activeId);
    if (profile && profile.data) {
      storage.setLocalSyncedTimestamp(profile.updated_at || Date.now());
      await sendWorkerMessage("load_bank", {
        gzBytes: Array.from(new Uint8Array(profile.data)),
        createIfMissing: false,
      });
      await refreshBankView();
    }
  }

  // Kiểm tra hạn ngạch bộ nhớ lần đầu
  await checkQuotaStatus();

  setStatus("status_ready");
}

function initQuotaAndBackupReminders() {
  const btnQuotaBackup = document.getElementById("btn-quota-backup");
  if (btnQuotaBackup) {
    btnQuotaBackup.addEventListener("click", () => {
      exportCurrentBank();
    });
  }

  const btnToastDismiss = document.getElementById("btn-toast-dismiss");
  const btnToastBackup = document.getElementById("btn-toast-backup");
  const toastEl = document.getElementById("backup-reminder-toast");

  if (btnToastDismiss && toastEl) {
    btnToastDismiss.addEventListener("click", () => {
      reminderDismissed = true;
      toastEl.style.display = "none";
    });
  }

  if (btnToastBackup && toastEl) {
    btnToastBackup.addEventListener("click", () => {
      exportCurrentBank();
      toastEl.style.display = "none";
    });
  }
}

export function setStatus(statusKey, isError = false, isBusy = false) {
  const indicator = document.getElementById("status-indicator");
  const statusText = document.getElementById("status-text");
  if (indicator) {
    indicator.className = "status-dot" + (isError ? " error" : isBusy ? " loading" : "");
  }
  if (statusText) {
    statusText.textContent = t(statusKey);
  }
}

// -------------------------------------------------------------
// 4. Màn hình chào Onboarding (T035)
// -------------------------------------------------------------
function showWelcomeModal() {
  const welcome = document.getElementById("welcome-modal");
  const guide = document.getElementById("guide-modal");
  const fileInput = document.getElementById("input-welcome-file");

  if (!welcome) return;
  welcome.style.display = "flex";

  const btnCreate = document.getElementById("btn-welcome-create");
  const btnImport = document.getElementById("btn-welcome-import");
  const btnGuide = document.getElementById("btn-welcome-guide");
  const btnCloseGuide = document.getElementById("btn-close-guide");

  if (btnCreate) {
    btnCreate.onclick = async () => {
      setStatus("status_saving", false, true);
      // Tạo kho rỗng qua bridge
      await sendWorkerMessage("load_bank", { gzBytes: [], createIfMissing: true });
      const bytes = await sendWorkerMessage("export_bank");
      const saved = await storage.saveProfile({
        id: "default_profile",
        name: "Kho của tôi",
        data: bytes,
        teach_count_since_backup: 0,
      });
      storage.setLocalSyncedTimestamp(saved.updated_at || Date.now());
      await storage.setSetting("active_profile_id", "default_profile");
      await refreshBankView();
      welcome.style.display = "none";
      setStatus("status_saved");
      setTimeout(() => setStatus("status_ready"), 2000);
    };
  }

  if (btnImport && fileInput) {
    btnImport.onclick = () => fileInput.click();
    fileInput.onchange = async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      try {
        setStatus("status_loading", false, true);
        const arrayBuf = await file.arrayBuffer();
        await loadBankFromBytes(arrayBuf, file.name.replace(/\.json\.gz$/, ""));
        welcome.style.display = "none";
        setStatus("status_saved");
        setTimeout(() => setStatus("status_ready"), 2000);
      } catch (err) {
        alert(`Lỗi nạp kho: ${err.message}`);
        setStatus("status_ready");
      }
    };
  }

  if (btnGuide && guide) {
    btnGuide.onclick = () => { guide.style.display = "flex"; };
  }
}

function initGuideModal() {
  const guide = document.getElementById("guide-modal");
  const btnHeaderGuide = document.getElementById("btn-header-guide");
  if (btnHeaderGuide && guide) {
    btnHeaderGuide.onclick = () => { guide.style.display = "flex"; };
  }

  const btnCloseGuideX = document.getElementById("btn-close-guide-x");
  if (btnCloseGuideX && guide) {
    btnCloseGuideX.onclick = () => { guide.style.display = "none"; };
  }

  const btnCloseGuide = document.getElementById("btn-close-guide");
  if (btnCloseGuide && guide) {
    btnCloseGuide.onclick = () => { guide.style.display = "none"; };
  }
}

// -------------------------------------------------------------
// 5. Chuyển đổi Tabs
// -------------------------------------------------------------
export function switchTab(targetTab) {
  // Nếu có dữ liệu đang chờ lưu debounce, flush ngay trước khi đổi tab
  if (saveDebounceTimer) {
    triggerSyncSave();
  }

  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    if (btn.getAttribute("data-tab") === targetTab) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.remove("active");
  });

  const activePanel = document.getElementById(`tab-${targetTab}`);
  if (activePanel) {
    activePanel.classList.add("active");
  }

  if (targetTab === "teach" && window.__teachController && window.__teachController.canvas) {
    window.__teachController.canvas.resize();
  } else if (targetTab === "bank") {
    refreshBankView();
  }
}

function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });
}

// -------------------------------------------------------------
// 6. Đăng ký Service Worker & Quản lý Cập nhật (T069)
// -------------------------------------------------------------
function initServiceWorker() {
  if (!("serviceWorker" in navigator)) return;

  const updateToast = document.getElementById("update-available-toast");
  const btnUpdateReload = document.getElementById("btn-update-reload");
  const btnUpdateDismiss = document.getElementById("btn-update-dismiss");

  let waitingWorker = null;

  if (btnUpdateDismiss && updateToast) {
    btnUpdateDismiss.addEventListener("click", () => {
      updateToast.style.display = "none";
    });
  }

  if (btnUpdateReload) {
    btnUpdateReload.addEventListener("click", () => {
      if (waitingWorker) {
        waitingWorker.postMessage({ type: "SKIP_WAITING" });
      } else {
        window.location.reload();
      }
    });
  }

  navigator.serviceWorker.register("sw.js").then((reg) => {
    // Nếu có service worker đang chờ kích hoạt
    if (reg.waiting) {
      waitingWorker = reg.waiting;
      if (updateToast) updateToast.style.display = "block";
    }

    reg.addEventListener("updatefound", () => {
      const newWorker = reg.installing;
      if (newWorker) {
        newWorker.addEventListener("statechange", () => {
          if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
            waitingWorker = newWorker;
            if (updateToast) updateToast.style.display = "block";
          }
        });
      }
    });
  }).catch((err) => {
    console.warn("[SW] Không thể đăng ký Service Worker:", err);
  });

  navigator.serviceWorker.addEventListener("controllerchange", () => {
    window.location.reload();
  });
}

// Khởi chạy ứng dụng khi DOM sẵn sàng
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initWorker();
  initServiceWorker();
});
