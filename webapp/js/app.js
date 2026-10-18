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
import { initTheme } from "./theme.js";

let worker = null;
let reqId = 1;
const pendingRequests = new Map();
let saveDebounceTimer = null;
let reminderDismissed = false;

let workerGeneration = 0;
let isRecovering = false;
let isUiInitialized = false;
let isDomListenersAttached = false;
let recoveryPromise = null;

export function getWorkerGeneration() {
  return workerGeneration;
}

export function getIsRecovering() {
  return isRecovering;
}

export function getIsUiInitialized() {
  return isUiInitialized;
}

export function resetUiInitializedForTesting() {
  isUiInitialized = false;
  isDomListenersAttached = false;
  isRecovering = false;
  workerGeneration = 0;
  recoveryPromise = null;
}

export function setWorkerInstance(w) {
  worker = w;
  if (worker) {
    attachWorkerHandlers(worker, workerGeneration);
  }
}

export function getPendingRequestsCount() {
  return pendingRequests.size;
}

export function handleWorkerFatalError(errorMsg) {
  console.error("[Worker Fatal Error]", errorMsg);
  for (const [id, req] of pendingRequests.entries()) {
    if (req.timer) clearTimeout(req.timer);
    req.reject(new Error(`Sự cố Web Worker: ${errorMsg}`));
  }
  pendingRequests.clear();
  try {
    setStatus("status_error", true);
  } catch (e) {
    // ignore in tests without full DOM
  }
  if (typeof document !== "undefined") {
    const splashStatus = document.getElementById("splash-status");
    if (splashStatus) {
      splashStatus.textContent = `Lỗi hệ thống: ${errorMsg}. Vui lòng thử lại.`;
    }
    const btnRetry = document.getElementById("btn-worker-retry");
    if (btnRetry) {
      btnRetry.style.display = "inline-block";
      btnRetry.disabled = false;
      if (!btnRetry.__hasRetryListener) {
        btnRetry.__hasRetryListener = true;
        btnRetry.addEventListener("click", () => {
          recoverWorker();
        });
      }
    }
  }
}

export function sendWorkerMessage(method, params = {}, timeoutMs = 60000) {
  return new Promise((resolve, reject) => {
    if (!worker) {
      reject(new Error("Web Worker chưa được khởi tạo."));
      return;
    }
    const id = reqId++;
    const timer = setTimeout(() => {
      if (pendingRequests.has(id)) {
        pendingRequests.delete(id);
        const timeoutErr = new Error(`Yêu cầu '${method}' sang Web Worker đã quá thời gian chờ (${timeoutMs}ms).`);
        timeoutErr.name = "WorkerTimeoutError";

        // T020: Chấm dứt vật lý Worker bị treo để ngăn duplicate execution
        if (worker && typeof worker.terminate === "function") {
          try {
            worker.terminate();
          } catch (_) {}
        }
        workerGeneration++;
        worker = null;

        handleWorkerFatalError(`Tác vụ '${method}' bị quá hạn chờ (${timeoutMs}ms)`);
        reject(timeoutErr);
      }
    }, timeoutMs);

    pendingRequests.set(id, { resolve, reject, timer, method });
    worker.postMessage({ id, method, params });
  });
}

let workerReadyResolve = null;

export function recoverWorker(WorkerClass = null, timeoutMs = 10000) {
  if (isRecovering && recoveryPromise) {
    return recoveryPromise;
  }
  isRecovering = true;

  const btnRetry = typeof document !== "undefined" ? document.getElementById("btn-worker-retry") : null;
  if (btnRetry) {
    btnRetry.disabled = true;
  }
  try {
    setStatus("status_loading", false, true);
  } catch (_) {}

  recoveryPromise = (async () => {
    let success = false;
    let timer = null;
    try {
      // 1. Chấm dứt Worker cũ và cô lập generation
      workerGeneration++;
      if (worker && typeof worker.terminate === "function") {
        try {
          worker.terminate();
        } catch (_) {}
      }
      worker = null;

      // 2. Reject toàn bộ pendingRequests
      for (const [id, req] of pendingRequests.entries()) {
        if (req.timer) clearTimeout(req.timer);
        req.reject(new Error("Bộ xử lý nền đã được khởi động lại."));
      }
      pendingRequests.clear();

      // 3. Khởi tạo Worker mới và chờ tín hiệu READY
      const TargetWorkerClass = WorkerClass || (typeof Worker !== "undefined" ? Worker : null);
      if (TargetWorkerClass) {
        const activeGen = workerGeneration;
        const readyPromise = new Promise((resolve) => {
          workerReadyResolve = resolve;
          timer = setTimeout(() => {
            if (workerReadyResolve) {
              const resFn = workerReadyResolve;
              workerReadyResolve = null;
              if (worker && typeof worker.terminate === "function") {
                try {
                  worker.terminate();
                } catch (_) {}
              }
              worker = null;
              workerGeneration++;
              handleWorkerFatalError(`Khởi tạo bộ xử lý nền quá thời gian chờ (${timeoutMs}ms)`);
              resFn(false);
            }
          }, timeoutMs);
        });

        try {
          worker = new TargetWorkerClass("js/worker/py-worker.js", { type: "module" });
          attachWorkerHandlers(worker, activeGen);
          const isReady = await readyPromise;
          success = isReady === true;
        } catch (err) {
          console.error("Lỗi khởi tạo Worker mới:", err);
          handleWorkerFatalError(err.message || "Lỗi khởi tạo Web Worker");
          success = false;
        }
      } else {
        handleWorkerFatalError("Trình duyệt không hỗ trợ Web Worker");
        success = false;
      }

      return success;
    } catch (fatalErr) {
      console.error("Lỗi trong quá trình phục hồi Worker:", fatalErr);
      handleWorkerFatalError(fatalErr.message || "Lỗi không xác định khi phục hồi");
      return false;
    } finally {
      if (timer) clearTimeout(timer);
      if (btnRetry) {
        btnRetry.disabled = false;
        if (success) {
          btnRetry.style.display = "none";
        } else {
          btnRetry.style.display = "inline-block";
        }
      }
      isRecovering = false;
      recoveryPromise = null;
      workerReadyResolve = null;
    }
  })();

  return recoveryPromise;
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
if (typeof window !== "undefined") {
  window.__notifySampleTaught = notifySampleTaught;
}

// -------------------------------------------------------------
// 2. Khởi tạo Worker
// -------------------------------------------------------------
export function attachWorkerHandlers(targetWorker, generation = workerGeneration) {
  targetWorker.onmessage = (e) => {
    if (generation !== workerGeneration) {
      return;
    }
    const data = e.data;
    if (data.type === "PROGRESS") {
      const { percent, message } = data.payload;
      if (typeof document !== "undefined") {
        const bar = document.getElementById("splash-bar");
        const status = document.getElementById("splash-status");
        if (bar) bar.style.width = `${percent}%`;
        if (status) status.textContent = message;
      }
    } else if (data.type === "READY") {
      onWorkerReady().then(() => {
        if (workerReadyResolve) {
          workerReadyResolve(true);
          workerReadyResolve = null;
        }
      }).catch((err) => {
        console.error("Lỗi khi nạp lại kho sau khi phục hồi:", err);
        handleWorkerFatalError(err.message || "Lỗi khởi tạo lại kho mẫu");
        if (workerReadyResolve) {
          workerReadyResolve(false);
          workerReadyResolve = null;
        }
      });
    } else if (data.type === "ERROR") {
      console.error("Lỗi Worker:", data.payload);
      handleWorkerFatalError(data.payload?.message || "Lỗi khởi tạo Worker");
      if (typeof document !== "undefined") {
        const status = document.getElementById("splash-status");
        if (status) status.textContent = `Lỗi khởi tạo: ${data.payload?.message || ""}`;
      }
      if (workerReadyResolve) {
        workerReadyResolve(false);
        workerReadyResolve = null;
      }
    } else if (data.id) {
      const req = pendingRequests.get(data.id);
      if (req) {
        pendingRequests.delete(data.id);
        if (req.timer) clearTimeout(req.timer);
        if (data.ok) {
          req.resolve(data.result);
        } else {
          req.reject(new Error(data.error));
        }
      } else {
        console.warn(`[Worker] Bỏ qua phản hồi muộn cho yêu cầu #${data.id}`);
      }
    }
  };

  targetWorker.onerror = (e) => {
    if (generation !== workerGeneration) {
      return;
    }
    handleWorkerFatalError(e.message || "Lỗi runtime trong Web Worker");
    if (workerReadyResolve) {
      workerReadyResolve(false);
      workerReadyResolve = null;
    }
  };

  targetWorker.onmessageerror = () => {
    if (generation !== workerGeneration) {
      return;
    }
    handleWorkerFatalError("Lỗi giải mã thông điệp (message deserialization error)");
    if (workerReadyResolve) {
      workerReadyResolve(false);
      workerReadyResolve = null;
    }
  };
}

function initWorker() {
  worker = new Worker("js/worker/py-worker.js", { type: "module" });
  attachWorkerHandlers(worker, workerGeneration);
}

// -------------------------------------------------------------
// 3. Xử lý sau khi Pyodide Worker đã sẵn sàng
// -------------------------------------------------------------
export async function onWorkerReady() {
  const isFirstInit = !isUiInitialized;
  // Khởi tạo các event listeners và controller giao diện một lần duy nhất
  if (!isDomListenersAttached) {
    isDomListenersAttached = true;
    // Xin quyền lưu trữ bền vững (T037)
    if (typeof navigator !== "undefined" && navigator.storage && navigator.storage.persist) {
      try {
        const isPersisted = await navigator.storage.persist();
        console.log("[Storage] Persisted storage:", isPersisted);
      } catch (e) {
        console.warn("[Storage] Persist request error:", e);
      }
    }

    // Khởi tạo tab Kho mẫu, Tab Viết chữ & Tab Dạy mẫu khi có DOM
    if (typeof document !== "undefined") {
      initBankTab(sendWorkerMessage);
      initWriteTab();
      if (document.getElementById("tab-teach")) {
        const teachController = new TeachController(
          { request: sendWorkerMessage },
          { onSampleSaved: notifySampleTaught }
        );
        await teachController.init();
        if (typeof window !== "undefined") {
          window.__teachController = teachController;
        }
      }
      initQuotaAndBackupReminders();
      initGuideModal();
    }

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
            if (typeof document !== "undefined" && document.getElementById("bank-summary")) {
              await refreshBankView();
            }
            if (typeof window !== "undefined" && window.__teachController) {
              await window.__teachController.refresh();
            }
          }
          setStatus("status_ready");
        }
      }
    });

    // Gắn hook tự động flush lưu khi người dùng chuyển tab trình duyệt hoặc đóng trang (T066)
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
          triggerSyncSave();
        }
      });
    }
    if (typeof window !== "undefined") {
      window.addEventListener("pagehide", () => {
        triggerSyncSave();
      });
    }
  }

  // Nạp lại / Khởi tạo hồ sơ trong IndexedDB
  const profiles = await storage.listProfiles();
  if (!profiles || profiles.length === 0) {
    if (isFirstInit && typeof document !== "undefined") {
      showWelcomeModal();
    }
  } else {
    const activeId = await storage.getSetting("active_profile_id", profiles[0].id);
    const profile = await storage.getProfile(activeId);
    if (profile && profile.data) {
      storage.setLocalSyncedTimestamp(profile.updated_at || Date.now());
      await sendWorkerMessage("load_bank", {
        gzBytes: Array.from(new Uint8Array(profile.data)),
        createIfMissing: false,
      });
      if (typeof document !== "undefined" && document.getElementById("bank-summary")) {
        await refreshBankView();
      }
      if (typeof window !== "undefined" && window.__teachController) {
        await window.__teachController.refresh();
      }
    }
  }

  // Kiểm tra hạn ngạch bộ nhớ
  if (typeof document !== "undefined") {
    await checkQuotaStatus();
  }

  // Chỉ ẩn màn hình splash và nút thử lại khi toàn bộ quá trình nạp kho mẫu và khởi tạo thành công (T009)
  if (typeof document !== "undefined") {
    const splash = document.getElementById("splash-screen");
    if (splash) splash.style.display = "none";
    const btnRetry = document.getElementById("btn-worker-retry");
    if (btnRetry) {
      btnRetry.style.display = "none";
      btnRetry.disabled = false;
    }
  }

  isUiInitialized = true;
  setStatus("status_ready");
  isRecovering = false;
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
  if (typeof document === "undefined") return;
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
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initTabs();
    initWorker();
    initServiceWorker();
    const btnRetry = document.getElementById("btn-worker-retry");
    if (btnRetry) {
      btnRetry.addEventListener("click", () => {
        recoverWorker();
      });
    }
  });
}
