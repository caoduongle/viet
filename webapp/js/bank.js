/**
 * bank.js -- Quản lý tab Kho mẫu và tương tác nạp / xuất / duyệt kho chữ.
 *
 * Tuân thủ T060, T061, T062, T063:
 *   - Lưới nhãn có tìm kiếm tức thì, lọc danh mục (tất cả / từ / chữ cái / chữ số / dấu câu / ký hiệu).
 *   - Thumbnail SVG vector cho từng nhãn và từng biến thể mẫu nét.
 *   - Thư viện mẫu chi tiết: xem các kiểu, "Thêm kiểu mới", "Xem thử ngẫu nhiên", chỉ báo độ phủ (< 2 mẫu).
 *   - Xoá nhãn an toàn với xác nhận rõ ràng.
 *   - Xuất file kiểm tra .xopp (export_check), sao lưu / nạp kho .json.gz.
 *   - Chip tên kho và đổi tên hồ sơ IndexedDB.
 */

import * as storage from "./storage.js";
import { switchTab } from "./app.js";
import { notifyBankUpdated } from "./write.js";
import { escapeHtml } from "./html-utils.js";
import { decompressXoppBase64, parseXoppXml, renderPageSvgElement } from "./paper.js";

let sendWorkerFn = null;

let allBankItems = []; // Danh sách tất cả nhãn: [{ label, count, category, sample }]
let currentCategoryFilter = "all";
let currentSearchQuery = "";
let currentDetailLabel = null;
let currentDetailCategory = "letters";
let modalSelectedIndices = new Set();
let isDeletingVariants = false;
let currentModalTotalSamples = 0;
const selectedLabels = new Set(); // Nhãn các ký tự được chọn để thao tác hàng loạt

function bindBankEvent(el, evt, fn, options = {}) {
  if (!el) return;
  const key = `__bank_bound_${evt}_${fn.name || "anon"}`;
  if (el[key]) return;
  el.addEventListener(evt, fn, options);
  el[key] = true;
  if (options && options.signal) {
    options.signal.addEventListener("abort", () => {
      delete el[key];
    });
  }
}

export function initBankTab(sendWorkerMessage, options = {}) {
  sendWorkerFn = sendWorkerMessage;
  const opts = options || {};

  // 1. Nút xuất / nhập / kiểm tra
  const btnExport = document.getElementById("btn-export-bank");
  const btnImport = document.getElementById("btn-import-bank");
  const fileInput = document.getElementById("input-import-bank");
  const btnExportCheck = document.getElementById("btn-export-check");
  const btnBankImportGrid = document.getElementById("btn-bank-import-grid");
  const btnRenameProfile = document.getElementById("btn-rename-profile");

  if (btnExport) bindBankEvent(btnExport, "click", exportCurrentBank, opts);
  if (btnImport && fileInput) {
    bindBankEvent(btnImport, "click", () => fileInput.click(), opts);
    bindBankEvent(fileInput, "change", handleFileInput, opts);
  }
  if (btnBankImportGrid) {
    bindBankEvent(btnBankImportGrid, "click", () => {
      const gridInput = document.getElementById("input-grid-file");
      if (gridInput) {
        gridInput.click();
      }
    }, opts);
  }
  if (btnExportCheck) bindBankEvent(btnExportCheck, "click", exportCheckFile, opts);
  if (btnRenameProfile) bindBankEvent(btnRenameProfile, "click", handleRenameProfile, opts);

  // 2. Tìm kiếm tức thì & Bộ lọc phân loại
  const searchInput = document.getElementById("input-search-bank");
  if (searchInput) {
    bindBankEvent(searchInput, "input", (e) => {
      currentSearchQuery = e.target.value.trim().toLowerCase();
      applyFiltersAndRender();
    }, opts);
  }

  const filterContainer = document.getElementById("bank-category-filters");
  if (filterContainer) {
    bindBankEvent(filterContainer, "click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const cat = btn.getAttribute("data-cat");
      if (!cat) return;

      currentCategoryFilter = cat;
      filterContainer.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      applyFiltersAndRender();
    }, opts);
  }

  // 3. Thanh thao tác xóa hàng loạt
  const chkSelectAll = document.getElementById("chk-bank-select-all");
  const btnDeleteSelected = document.getElementById("btn-bank-delete-selected");

  if (chkSelectAll) {
    bindBankEvent(chkSelectAll, "change", (e) => {
      toggleSelectAll(e.target.checked);
    }, opts);
  }

  if (btnDeleteSelected) {
    bindBankEvent(btnDeleteSelected, "click", handleDeleteSelected, opts);
  }

  // 4. Modal chi tiết nhãn
  setupDetailModal(opts);
}

function setupDetailModal(options = {}) {
  const modal = document.getElementById("modal-label-detail");
  const btnClose = document.getElementById("btn-close-label-detail");
  const btnTeachMore = document.getElementById("btn-label-teach-more");
  const btnPreviewRandom = document.getElementById("btn-label-preview-random");
  const btnDelete = document.getElementById("btn-label-delete");

  if (btnClose && modal) {
    bindBankEvent(btnClose, "click", () => {
      modal.style.display = "none";
    }, options);
    bindBankEvent(modal, "click", (e) => {
      if (e.target === modal) modal.style.display = "none";
    }, options);
  }

  if (btnTeachMore) {
    bindBankEvent(btnTeachMore, "click", () => {
      if (!currentDetailLabel) return;
      if (modal) modal.style.display = "none";
      switchTab("teach");
      if (window.__teachController) {
        window.__teachController.teachWordDirectly(currentDetailLabel);
      }
    }, options);
  }

  if (btnPreviewRandom) {
    bindBankEvent(btnPreviewRandom, "click", handleRandomPreview, options);
  }

  if (btnDelete) {
    bindBankEvent(btnDelete, "click", handleDeleteLabel, options);
  }

  const chkModalSelectAll = document.getElementById("chk-modal-select-all");
  const btnDeleteSelected = document.getElementById("btn-label-delete-selected");

  if (chkModalSelectAll) {
    bindBankEvent(chkModalSelectAll, "change", handleToggleModalSelectAll, options);
  }

  if (btnDeleteSelected) {
    bindBankEvent(btnDeleteSelected, "click", handleDeleteSelectedVariants, options);
  }
}

// -------------------------------------------------------------
// Nạp kho & Cập nhật Giao diện
// -------------------------------------------------------------
let lastBankSnapshotCache = { epoch: null, revision: null, profileId: null };

export function showBankErrorBanner(message) {
  let banner = document.getElementById("bank-error-banner");
  if (!banner) {
    const summary = document.getElementById("bank-summary");
    if (summary && summary.parentNode) {
      banner = document.createElement("div");
      banner.id = "bank-error-banner";
      banner.className = "alert alert-danger";
      banner.style.cssText = "margin-top: 0.5rem; padding: 0.5rem 0.75rem; background: #ffebee; color: #c62828; border-radius: 4px; font-size: 0.88rem; display: flex; justify-content: space-between; align-items: center;";
      summary.parentNode.appendChild(banner);
    }
  }
  if (banner) {
    if (message) {
      banner.replaceChildren();
      const span = document.createElement("span");
      span.textContent = `⚠️ ${message}`;
      const closeBtn = document.createElement("button");
      closeBtn.className = "btn btn-sm btn-link";
      closeBtn.style.cssText = "color: inherit; text-decoration: underline; background: none; border: none; cursor: pointer;";
      closeBtn.textContent = "Đóng";
      closeBtn.onclick = () => {
        banner.style.display = "none";
      };
      banner.appendChild(span);
      banner.appendChild(closeBtn);
      banner.style.display = "flex";
    } else {
      banner.style.display = "none";
    }
  }
}

export async function refreshBankView(force = false) {
  if (!sendWorkerFn) return;

  try {
    // 1. Cập nhật thông tin hồ sơ
    await updateProfileChip();
    const activeProfileId = (await storage.getSetting("active_profile_id", "default_profile")) || "default_profile";

    // 2. Lấy toàn bộ snapshot kho mẫu trong 1 lượt gọi duy nhất
    const snapRes = await sendWorkerFn("get_bank_snapshot", { profileId: activeProfileId });
    if (!snapRes || !snapRes.ok) {
      const err = snapRes?.error || "Không thể nạp dữ liệu kho mẫu";
      showBankErrorBanner(`Lỗi tải kho mẫu: ${err}`);
      console.error("Lỗi get_bank_snapshot:", snapRes);
      return;
    }
    showBankErrorBanner(null);

    const snapshot = snapRes.data || {};
    const rev = snapshot.revision;
    const epoch = snapshot.worker_epoch || "";

    // Kiểm tra cache nếu không force và epoch + revision + profileId không đổi
    if (
      !force &&
      lastBankSnapshotCache.epoch === epoch &&
      lastBankSnapshotCache.revision === rev &&
      lastBankSnapshotCache.profileId === activeProfileId
    ) {
      return;
    }
    const pendingCacheKey = { epoch, revision: rev, profileId: activeProfileId };

    const stats = snapshot.stats || {};
    const summary = document.getElementById("bank-summary");
    if (summary) {
      summary.textContent = `Kho mẫu hiện có ${stats.n_letters || 0} chữ cái, ${stats.n_samples || 0} mẫu nét.`;
    }
    const statusText = document.getElementById("status-text");
    if (statusText) {
      statusText.textContent = `${stats.n_letters || 0} chữ cái / ${stats.n_samples || 0} mẫu`;
    }

    // 3. Tổng hợp danh sách nhãn từ snapshot
    allBankItems = [];

    // Chữ cái (letters)
    if (Array.isArray(snapshot.letters)) {
      for (const [ch, count] of snapshot.letters) {
        allBankItems.push({ label: ch, count, category: "letters" });
      }
    }

    // Chữ số (digits)
    const digitCounts = snapshot.digits || stats.digit_counts || {};
    for (const [d, count] of Object.entries(digitCounts)) {
      allBankItems.push({ label: d, count, category: "digits" });
    }

    // Dấu câu (punct)
    const punctCounts = snapshot.punct || stats.punct_counts || {};
    for (const [p, count] of Object.entries(punctCounts)) {
      allBankItems.push({ label: p, count, category: "punct" });
    }

    // Ký hiệu (symbols)
    if (Array.isArray(snapshot.symbols)) {
      for (const [sym, count] of snapshot.symbols) {
        allBankItems.push({ label: sym, count, category: "symbols" });
      }
    }

    // Dấu thanh (marks)
    if (Array.isArray(snapshot.marks)) {
      for (const [m, count] of snapshot.marks) {
        allBankItems.push({ label: m, count, category: "marks" });
      }
    } else {
      const toneCounts = stats.tone_mark_counts || {};
      for (const [t, count] of Object.entries(toneCounts)) {
        if (count > 0) {
          allBankItems.push({ label: t, count, category: "marks" });
        }
      }
    }

    // Cập nhật số lượng trên các nút lọc
    updateCategoryCounts();

    // 4. Render danh sách ra lưới
    applyFiltersAndRender();
    lastBankSnapshotCache = pendingCacheKey;
  } catch (err) {
    lastBankSnapshotCache = { epoch: null, revision: null, profileId: null };
    showBankErrorBanner(`Lỗi hệ thống khi tải kho mẫu: ${err.message}`);
    console.error("Lỗi cập nhật kho mẫu:", err);
  }
}

function updateCategoryCounts() {
  const counts = { all: allBankItems.length, letters: 0, digits: 0, punct: 0, symbols: 0, marks: 0 };
  for (const item of allBankItems) {
    if (counts[item.category] !== undefined) {
      counts[item.category]++;
    }
  }

  for (const [cat, cnt] of Object.entries(counts)) {
    const el = document.getElementById(`cat-count-${cat}`);
    if (el) el.textContent = String(cnt);
  }
}

function applyFiltersAndRender() {
  const grid = document.getElementById("bank-cards-grid");
  if (!grid) {
    throw new Error("Không tìm thấy vùng hiển thị thẻ mẫu (#bank-cards-grid).");
  }

  grid.innerHTML = "";

  const filtered = allBankItems.filter((item) => {
    if (currentCategoryFilter !== "all" && item.category !== currentCategoryFilter) {
      return false;
    }
    if (currentSearchQuery && !item.label.toLowerCase().includes(currentSearchQuery)) {
      return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<p style="grid-column: 1 / -1; color: var(--text-secondary); text-align: center; padding: 2rem;">Không tìm thấy nhãn nào phù hợp với bộ lọc hiện tại.</p>`;
    return;
  }

  const visibleLabels = filtered.map((item) => item.label);
  updateBatchBar(visibleLabels);

  for (const item of filtered) {
    const card = document.createElement("div");
    card.className = "bank-card";
    const isChecked = selectedLabels.has(item.label);
    if (isChecked) {
      card.classList.add("selected");
    }

    // Phân loại độ phủ
    const isLow = item.count < 2;
    const badgeClass = isLow ? "coverage-low" : "coverage-good";
    const badgeText = isLow ? `${item.count} mẫu (ít)` : `${item.count} mẫu`;
    const escapedLabel = escapeHtml(item.label);

    card.innerHTML = `
      <div style="position: absolute; top: 8px; left: 8px; z-index: 2;">
        <input type="checkbox" class="chk-card-item" data-label="${encodeURIComponent(item.label)}" ${isChecked ? "checked" : ""} style="cursor: pointer; width: 16px; height: 16px;">
      </div>
      <div class="bank-card-thumb" id="thumb-${encodeURIComponent(item.label)}">
        <span style="font-size: 1.4rem; color: #94a3b8;">${escapedLabel}</span>
      </div>
      <div class="bank-card-title">${escapedLabel}</div>
      <div class="bank-card-meta">
        <span class="coverage-badge ${badgeClass}">${badgeText}</span>
      </div>
    `;

    // Bắt sự kiện checkbox riêng biệt, không mở modal detail
    const chk = card.querySelector(".chk-card-item");
    if (chk) {
      chk.addEventListener("click", (e) => {
        e.stopPropagation();
      });
      chk.addEventListener("change", (e) => {
        if (e.target.checked) {
          selectedLabels.add(item.label);
          card.classList.add("selected");
        } else {
          selectedLabels.delete(item.label);
          card.classList.remove("selected");
        }
        updateBatchBar(visibleLabels);
      });
    }

    card.addEventListener("click", () => {
      openLabelDetail(item.label, item.category, item.count);
    });

    grid.appendChild(card);
  }

  // Nạp lười thumbnail mẫu đầu tiên cho các thẻ nhìn thấy
  loadThumbnailsLazy(filtered.slice(0, 40));
}

function updateBatchBar(visibleLabels = []) {
  const chkSelectAll = document.getElementById("chk-bank-select-all");
  const countLabel = document.getElementById("bank-selected-count-label");
  const btnDeleteSelected = document.getElementById("btn-bank-delete-selected");

  const totalSelected = selectedLabels.size;
  if (countLabel) {
    countLabel.textContent = `(Đã chọn ${totalSelected})`;
  }

  if (btnDeleteSelected) {
    btnDeleteSelected.disabled = totalSelected === 0;
    btnDeleteSelected.textContent = `🗑 Xoá đã chọn (${totalSelected})`;
  }

  if (chkSelectAll && visibleLabels.length > 0) {
    const allVisibleSelected = visibleLabels.every((lbl) => selectedLabels.has(lbl));
    chkSelectAll.checked = allVisibleSelected;
  } else if (chkSelectAll) {
    chkSelectAll.checked = false;
  }
}

function toggleSelectAll(selectAll) {
  const filtered = allBankItems.filter((item) => {
    if (currentCategoryFilter !== "all" && item.category !== currentCategoryFilter) {
      return false;
    }
    if (currentSearchQuery && !item.label.toLowerCase().includes(currentSearchQuery)) {
      return false;
    }
    return true;
  });

  for (const item of filtered) {
    if (selectAll) {
      selectedLabels.add(item.label);
    } else {
      selectedLabels.delete(item.label);
    }
  }

  applyFiltersAndRender();
}

async function handleDeleteSelected() {
  const count = selectedLabels.size;
  if (count === 0 || !sendWorkerFn) return;

  const labelsToDelete = Array.from(selectedLabels);

  // Tính tổng số mẫu nét bị ảnh hưởng
  let totalSamples = 0;
  for (const item of allBankItems) {
    if (selectedLabels.has(item.label)) {
      totalSamples += item.count || 0;
    }
  }

  const promptText = (
    `Bạn có chắc chắn muốn xoá ${count} ký tự đã chọn ` +
    `(tổng cộng ${totalSamples} mẫu nét) khỏi kho mẫu không?\n\n` +
    `Lưu ý: Toàn bộ mẫu nét này sẽ bị gỡ bỏ và kho mẫu sẽ được cập nhật vĩnh viễn.`
  );

  if (!confirm(promptText)) {
    return;
  }

  try {
    const res = await sendWorkerFn("drop_chars", { chars: labelsToDelete });
    if (!res || !res.ok) {
      throw new Error((res && res.error) || "Không thể xoá hàng loạt.");
    }

    selectedLabels.clear();

    // Đồng bộ lưu ngay xuống IndexedDB và phát sóng đa tab theo storage-protocol
    try {
      await storage.syncAndSaveActiveProfile(sendWorkerFn);
    } catch (saveErr) {
      console.warn("Lỗi lưu trữ sau khi xoá hàng loạt:", saveErr);
    }

    await refreshBankView();
    notifyBankUpdated({ reason: "deleted", immediate: false });
  } catch (err) {
    alert("Lỗi khi xoá hàng loạt: " + err.message);
  }
}

async function loadThumbnailsLazy(items) {
  for (const item of items) {
    try {
      const res = await sendWorkerFn("list_label_samples", { label: item.label, category: item.category });
      if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
        const firstSample = res.data[0];
        const thumbEl = document.getElementById(`thumb-${encodeURIComponent(item.label)}`);
        if (thumbEl && firstSample.s) {
          thumbEl.innerHTML = createSvgFromStrokes(firstSample.s, 110, 50);
        }
      }
    } catch (_) {}
  }
}

// -------------------------------------------------------------
// Xem chi tiết nhãn & Thư viện biến thể (T061)
// -------------------------------------------------------------
function updateModalBatchBar(totalCount = currentModalTotalSamples) {
  currentModalTotalSamples = totalCount;
  const count = modalSelectedIndices.size;
  const chkSelectAll = document.getElementById("chk-modal-select-all");
  const btnDeleteSelected = document.getElementById("btn-label-delete-selected");
  const countEl = document.getElementById("modal-selected-count");

  if (countEl) countEl.textContent = String(count);

  if (btnDeleteSelected) {
    btnDeleteSelected.style.display = count > 0 ? "inline-flex" : "none";
  }

  if (chkSelectAll) {
    if (totalCount > 0 && count === totalCount) {
      chkSelectAll.checked = true;
      chkSelectAll.indeterminate = false;
    } else if (count > 0 && count < totalCount) {
      chkSelectAll.checked = false;
      chkSelectAll.indeterminate = true;
    } else {
      chkSelectAll.checked = false;
      chkSelectAll.indeterminate = false;
    }
  }
}

function handleToggleModalSelectAll(e) {
  const shouldSelectAll = e.target.checked;
  const samplesGrid = document.getElementById("modal-label-samples-grid");
  if (!samplesGrid) return;

  const cards = samplesGrid.querySelectorAll(".sample-item-card");
  modalSelectedIndices.clear();

  cards.forEach((card, idx) => {
    const chk = card.querySelector(".sample-item-checkbox");
    if (shouldSelectAll) {
      modalSelectedIndices.add(idx);
      card.classList.add("selected");
      if (chk) chk.checked = true;
    } else {
      card.classList.remove("selected");
      if (chk) chk.checked = false;
    }
  });

  updateModalBatchBar(cards.length);
}

function toggleSampleCardSelection(idx, card, chk) {
  if (modalSelectedIndices.has(idx)) {
    modalSelectedIndices.delete(idx);
    card.classList.remove("selected");
    if (chk) chk.checked = false;
  } else {
    modalSelectedIndices.add(idx);
    card.classList.add("selected");
    if (chk) chk.checked = true;
  }
  updateModalBatchBar();
}

async function loadAndRenderModalSamples(label, category) {
  const samplesGrid = document.getElementById("modal-label-samples-grid");
  const countEl = document.getElementById("modal-label-sample-count");
  const coverage = document.getElementById("modal-label-coverage");
  const randomBox = document.getElementById("modal-random-preview-box");
  if (!samplesGrid) return;

  modalSelectedIndices.clear();
  updateModalBatchBar(0);
  if (randomBox) randomBox.style.display = "none";

  samplesGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-secondary); padding: 1rem;">Đang tải các mẫu nét...</div>`;

  try {
    const res = await sendWorkerFn("list_label_samples", { label, category });
    if (!res.ok || !Array.isArray(res.data) || res.data.length === 0) {
      samplesGrid.innerHTML = `<div style="grid-column: 1 / -1; color: var(--text-secondary); text-align: center;">Chưa có dữ liệu mẫu nét cho nhãn này.</div>`;
      if (countEl) countEl.textContent = "0";
      if (coverage) {
        coverage.textContent = "⚠️ Độ phủ thấp (< 2 mẫu): Nên dạy thêm để nét chữ tự nhiên hơn.";
        coverage.style.color = "#ca8a04";
      }
      return;
    }

    const samples = res.data;
    const count = samples.length;
    currentModalTotalSamples = count;
    if (countEl) countEl.textContent = String(count);
    if (coverage) {
      const isLow = count < 2;
      coverage.textContent = isLow ? "⚠️ Độ phủ thấp (< 2 mẫu): Nên dạy thêm để nét chữ tự nhiên hơn." : "✓ Độ phủ tốt: Đã có đủ biến thể ngẫu nhiên.";
      coverage.style.color = isLow ? "#ca8a04" : "#16a34a";
    }

    samplesGrid.innerHTML = "";
    samples.forEach((sample, idx) => {
      const itemCard = document.createElement("div");
      itemCard.className = "sample-item-card";
      itemCard.dataset.index = String(idx);

      const svgHtml = sample.s ? createSvgFromStrokes(sample.s, 140, 56, { showBaseline: true }) : "";
      const widthVal = sample.w ? `${escapeHtml(sample.w)} pt` : "";

      itemCard.innerHTML = `
        <input type="checkbox" class="sample-item-checkbox" title="Chọn biến thể này">
        <button class="sample-item-delete-btn" title="Xoá biến thể này">🗑</button>
        <div class="sample-item-thumb">${svgHtml}</div>
        <div style="font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between; width: 100%;">
          <span>Mẫu #${idx + 1}</span>
          <span>${widthVal}</span>
        </div>
      `;

      const chk = itemCard.querySelector(".sample-item-checkbox");
      const btnDel = itemCard.querySelector(".sample-item-delete-btn");

      if (chk) {
        chk.addEventListener("click", (e) => {
          e.stopPropagation();
          toggleSampleCardSelection(idx, itemCard, chk);
        });
      }

      if (btnDel) {
        btnDel.addEventListener("click", (e) => {
          e.stopPropagation();
          handleQuickDeleteVariant(idx);
        });
      }

      itemCard.addEventListener("click", (e) => {
        if (e.target === chk || e.target === btnDel) return;
        toggleSampleCardSelection(idx, itemCard, chk);
      });

      samplesGrid.appendChild(itemCard);
    });

    updateModalBatchBar(count);
  } catch (err) {
    samplesGrid.innerHTML = `<div style="grid-column: 1 / -1; color: #dc2626;">Lỗi tải mẫu: ${escapeHtml(err.message)}</div>`;
  }
}

async function handleQuickDeleteVariant(idx) {
  if (isDeletingVariants || !currentDetailLabel || !sendWorkerFn) return;

  const label = currentDetailLabel;
  const category = currentDetailCategory;
  const isLast = currentModalTotalSamples <= 1;

  const confirmMsg = isLast
    ? `Bạn có chắc chắn muốn xoá biến thể cuối cùng của nhãn "${label}" không?\n(Hành động này sẽ xóa nhãn khỏi kho mẫu)`
    : `Bạn có chắc chắn muốn xoá Mẫu #${idx + 1} của nhãn "${label}" không?\n(Lưu ý: Hành động này không thể hoàn tác)`;

  if (!confirm(confirmMsg)) return;

  await executeDeleteVariants(label, category, [idx]);
}

async function handleDeleteSelectedVariants() {
  if (isDeletingVariants || !currentDetailLabel || !sendWorkerFn) return;
  const count = modalSelectedIndices.size;
  if (count === 0) return;

  const label = currentDetailLabel;
  const category = currentDetailCategory;
  const isAll = count >= currentModalTotalSamples;

  const confirmMsg = isAll
    ? `Bạn có chắc chắn muốn xoá toàn bộ ${count} biến thể của nhãn "${label}" không?\n(Hành động này sẽ xóa nhãn khỏi kho mẫu)`
    : `Bạn có chắc chắn muốn xoá ${count} biến thể đã chọn của nhãn "${label}" không?\n(Lưu ý: Hành động này không thể hoàn tác)`;

  if (!confirm(confirmMsg)) return;

  const indices = Array.from(modalSelectedIndices);
  await executeDeleteVariants(label, category, indices);
}

async function executeDeleteVariants(label, category, indices) {
  isDeletingVariants = true;
  const btnDeleteSelected = document.getElementById("btn-label-delete-selected");
  if (btnDeleteSelected) btnDeleteSelected.disabled = true;

  try {
    const res = await sendWorkerFn("drop_label_samples", { label, indices, category });
    if (!res || !res.ok) {
      throw new Error((res && res.error) || "Không thể xoá biến thể mẫu.");
    }

    const data = res.data || {};
    try {
      await storage.syncAndSaveActiveProfile(sendWorkerFn);
    } catch (saveErr) {
      console.warn("Lỗi đồng bộ sau khi xoá biến thể:", saveErr);
    }

    if (data.label_deleted) {
      const modal = document.getElementById("modal-label-detail");
      if (modal) modal.style.display = "none";
      currentDetailLabel = null;
      currentDetailCategory = "letters";
      modalSelectedIndices.clear();
      await refreshBankView();
      notifyBankUpdated({ reason: "deleted", immediate: false });
      alert(`Đã xoá toàn bộ biến thể và gỡ nhãn "${label}" khỏi kho mẫu.`);
    } else {
      await refreshBankView();
      notifyBankUpdated({ reason: "deleted", immediate: false });
      await loadAndRenderModalSamples(label, category);
    }
  } catch (err) {
    alert(`Lỗi khi xoá biến thể: ${err.message}`);
  } finally {
    isDeletingVariants = false;
    if (btnDeleteSelected) btnDeleteSelected.disabled = false;
  }
}

async function openLabelDetail(label, category, count) {
  currentDetailLabel = label;
  currentDetailCategory = category;

  const modal = document.getElementById("modal-label-detail");
  const title = document.getElementById("modal-label-title");
  const randomBox = document.getElementById("modal-random-preview-box");

  if (!modal) return;
  modal.style.display = "flex";
  if (randomBox) randomBox.style.display = "none";

  title.textContent = `Nhãn: "${label}"`;
  await loadAndRenderModalSamples(label, category);
}

async function handleRandomPreview() {
  if (!currentDetailLabel || !sendWorkerFn) return;

  const targetLabel = currentDetailLabel;
  const box = document.getElementById("modal-random-preview-box");
  const content = document.getElementById("modal-random-preview-content");
  if (!box || !content) return;

  box.style.display = "block";
  content.innerHTML = `<div style="color: var(--text-secondary); font-size: 0.85rem;">Đang kết xuất thử ngẫu nhiên...</div>`;

  try {
    const seeds = [7, 42, 99];
    const previews = [];

    for (const seed of seeds) {
      if (currentDetailLabel !== targetLabel) return;
      const res = await sendWorkerFn("write_text", {
        text: targetLabel,
        options: {
          seed,
          strict_case: false,
          missing_grid: false,
          background: "plain",
        },
        format: "txt",
      });
      if (res && res.ok && res.xopp_base64) {
        previews.push({ seed, xopp_base64: res.xopp_base64 });
      }
    }

    if (currentDetailLabel !== targetLabel) return;

    content.innerHTML = "";
    for (const p of previews) {
      const pBox = document.createElement("div");
      pBox.style.padding = "0.5rem";
      pBox.style.background = "#fff";
      pBox.style.border = "1px solid var(--border-color)";
      pBox.style.borderRadius = "4px";
      pBox.style.fontSize = "0.8rem";

      const seedTitle = document.createElement("div");
      seedTitle.style.marginBottom = "0.35rem";
      seedTitle.style.color = "var(--text-secondary)";
      seedTitle.innerHTML = `Hạt giống seed: <b>${p.seed}</b>`;
      pBox.appendChild(seedTitle);

      try {
        const xml = await decompressXoppBase64(p.xopp_base64);
        if (currentDetailLabel !== targetLabel) return;
        const doc = parseXoppXml(xml);
        if (doc && doc.pages && doc.pages.length > 0) {
          const page = doc.pages[0];
          // Tính toán bounding box của toàn bộ nét vẽ để cắt gọn viewBox
          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          for (const s of page.strokes || []) {
            for (const pt of s.points || []) {
              if (pt.x < minX) minX = pt.x;
              if (pt.x > maxX) maxX = pt.x;
              if (pt.y < minY) minY = pt.y;
              if (pt.y > maxY) maxY = pt.y;
            }
          }

          const svgEl = renderPageSvgElement(page);
          if (minX !== Infinity) {
            const pad = 10;
            const w = Math.max(maxX - minX, 2) + pad * 2;
            const h = Math.max(maxY - minY, 2) + pad * 2;
            svgEl.setAttribute("viewBox", `${minX - pad} ${minY - pad} ${w} ${h}`);
          }
          svgEl.style.height = "70px";
          svgEl.style.width = "100%";
          svgEl.style.display = "block";
          pBox.appendChild(svgEl);
        }
      } catch (renderErr) {
        console.warn("Lỗi dựng SVG xem thử:", renderErr);
      }

      content.appendChild(pBox);
    }
  } catch (err) {
    if (currentDetailLabel === targetLabel) {
      content.innerHTML = `<div style="color: #dc2626; font-size: 0.85rem;">Lỗi kết xuất: ${escapeHtml(err.message)}</div>`;
    }
  }
}

// -------------------------------------------------------------
// Xoá nhãn an toàn (T062)
// -------------------------------------------------------------
async function handleDeleteLabel() {
  if (!currentDetailLabel || !sendWorkerFn) return;

  const label = currentDetailLabel;
  const category = currentDetailCategory;

  const confirmed = confirm(`Bạn có chắc chắn muốn xoá toàn bộ mẫu của nhãn "${label}" khỏi kho không?\n(Lưu ý: Hành động này không thể hoàn tác)`);
  if (!confirmed) return;

  try {
    const res = await sendWorkerFn("drop_label", { label, category });
    if (!res || !res.ok) {
      throw new Error((res && res.error) || "Không thể xoá nhãn.");
    }

    // Đóng modal và làm mới kho
    const modal = document.getElementById("modal-label-detail");
    if (modal) modal.style.display = "none";

    // Đồng bộ lưu ngay xuống IndexedDB và phát sóng đa tab theo storage-protocol
    try {
      await storage.syncAndSaveActiveProfile(sendWorkerFn);
    } catch (saveErr) {
      console.warn("Lỗi đồng bộ sau khi xoá:", saveErr);
    }

    alert(`Đã xoá nhãn "${label}" thành công.`);
    await refreshBankView();
    notifyBankUpdated({ reason: "deleted", immediate: false });
  } catch (err) {
    alert(`Lỗi khi xoá: ${err.message}`);
  }
}

// -------------------------------------------------------------
// Xuất file kiểm tra .xopp (T063)
// -------------------------------------------------------------
async function exportCheckFile() {
  if (!sendWorkerFn) return;

  try {
    const res = await sendWorkerFn("export_check");
    if (!res || !res.ok || !res.xopp_base64) {
      throw new Error((res && res.error) || "Không thể xuất file kiểm tra.");
    }

    const binaryString = atob(res.xopp_base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const blob = new Blob([bytes], { type: "application/x-xopp" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "kiem_tra_kho.xopp";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Lỗi xuất file kiểm tra: ${err.message}`);
  }
}

// -------------------------------------------------------------
// Hồ sơ kho mẫu (Profile Management - T063)
// -------------------------------------------------------------
async function updateProfileChip() {
  const nameEl = document.getElementById("profile-name-display");
  if (!nameEl) return;

  const activeId = await storage.getSetting("active_profile_id", "default_profile");
  const profile = await storage.getProfile(activeId);
  nameEl.textContent = (profile && profile.name) ? profile.name : "Kho của tôi";
}

async function handleRenameProfile() {
  const activeId = await storage.getSetting("active_profile_id", "default_profile");
  const profile = await storage.getProfile(activeId);
  const curName = (profile && profile.name) ? profile.name : "Kho của tôi";

  const newName = prompt("Nhập tên mới cho hồ sơ kho mẫu:", curName);
  if (!newName || !newName.trim() || newName.trim() === curName) return;

  if (profile) {
    profile.name = newName.trim();
    await storage.saveProfile(profile);
    await updateProfileChip();
  }
}

// -------------------------------------------------------------
// Nạp / Xuất tệp kho .json.gz
// -------------------------------------------------------------
export async function loadBankFromBytes(gzBytes, profileName = "Kho mẫu cá nhân") {
  if (!sendWorkerFn) return;
  const res = await sendWorkerFn("load_bank", { gzBytes: Array.from(new Uint8Array(gzBytes)), createIfMissing: false });
  if (res.ok) {
    const profileId = "default_profile";
    const saved = await storage.saveProfile({
      id: profileId,
      name: profileName,
      data: gzBytes,
      teach_count_since_backup: 0,
    });
    storage.setLocalSyncedTimestamp(saved.updated_at || Date.now());
    await storage.setSetting("active_profile_id", profileId);
    await refreshBankView();
    notifyBankUpdated({ reason: "loaded", immediate: false });
    return true;
  }
  throw new Error(res.error || "Không thể nạp kho mẫu");
}

export async function exportCurrentBank() {
  if (!sendWorkerFn) return;
  try {
    const bytes = await sendWorkerFn("export_bank");
    if (!bytes || bytes.length === 0) {
      alert("Kho mẫu hiện tại đang rỗng.");
      return;
    }
    const blob = new Blob([new Uint8Array(bytes)], { type: "application/gzip" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "chu_cua_ban.json.gz";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Đặt lại bộ đếm nhắc sao lưu
    const activeId = await storage.getSetting("active_profile_id", "default_profile");
    await storage.resetTeachCount(activeId);
    const toast = document.getElementById("backup-reminder-toast");
    if (toast) toast.style.display = "none";
  } catch (err) {
    console.error("Lỗi khi xuất kho mẫu:", err);
    alert(`Không thể xuất kho: ${err.message}`);
  }
}

async function handleFileInput(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;

  try {
    const arrayBuffer = await file.arrayBuffer();
    await loadBankFromBytes(arrayBuffer, file.name.replace(/\.json\.gz$/, ""));
    alert("Đã nạp kho mẫu thành công!");
  } catch (err) {
    console.error("Lỗi khi nạp file:", err);
    alert(`Lỗi nạp kho: ${err.message}`);
  } finally {
    e.target.value = "";
  }
}

// -------------------------------------------------------------
// Dựng SVG Thumbnail an toàn từ Stroke Coordinates
// -------------------------------------------------------------
export function createSvgFromStrokes(strokes, width = 100, height = 50, options = {}) {
  if (!strokes || strokes.length === 0) return "";

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  for (const st of strokes) {
    for (let i = 0; i < st.length; i += 2) {
      const x = st[i];
      const y = st[i + 1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }

  if (minX === Infinity) return "";

  const pad = 3.0;
  const strokeW = Math.max(0.1, maxX - minX);
  const strokeH = Math.max(0.1, maxY - minY);

  const minVbHeight = options.minVbHeight != null ? options.minVbHeight : 24.0;
  const strokeWidth = options.strokeWidth != null ? options.strokeWidth : 1.8;
  const showBaseline = Boolean(options.showBaseline);

  // Chiều cao khung nhìn tối thiểu (ngăn chặn phóng đại nét đối với chữ ngắn/hẹp)
  let targetH = Math.max(strokeH + pad * 2, minVbHeight);
  const aspect = width / height;
  let targetW = Math.max(strokeW + pad * 2, targetH * aspect);

  if (targetW / aspect > targetH) {
    targetH = targetW / aspect;
  }

  // Căn giữa theo chiều ngang
  const midX = (minX + maxX) / 2;
  const vbX = midX - targetW / 2;

  // Căn theo trục tung:
  // Nếu có toạ độ bao phủ baseline (y=0) hoặc chữ thông thường (y từ -8 đến 0):
  // Neo baseline ở khoảng 2/3 đến 3/4 chiều cao khung nhìn
  let vbY;
  if (minY <= 0 && maxY >= -15) {
    // Ký tự đứng trên baseline: đặt baseline y=0 tại vị trí ~ 70% chiều cao
    const baselineRatio = 0.70;
    vbY = -targetH * baselineRatio;
    // Kiểm tra nếu đỉnh nét (minY) hoặc đáy nét (maxY) vượt ra ngoài khung thì lùi lại
    if (minY < vbY + pad) {
      vbY = minY - pad;
    } else if (maxY > vbY + targetH - pad) {
      vbY = maxY + pad - targetH;
    }
  } else {
    // Căn giữa hình học nếu toạ độ bất thường
    const midY = (minY + maxY) / 2;
    vbY = midY - targetH / 2;
  }

  let guidesHtml = "";
  if (showBaseline) {
    guidesHtml = `<line x1="${vbX}" y1="0" x2="${vbX + targetW}" y2="0" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2,2" vector-effect="non-scaling-stroke"/>`;
  }

  let polylines = "";
  for (const st of strokes) {
    const pts = [];
    for (let i = 0; i < st.length; i += 2) {
      pts.push(`${st[i]},${st[i + 1]}`);
    }
    polylines += `<polyline points="${pts.join(" ")}" fill="none" stroke="#0f172a" stroke-width="${strokeWidth}" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round"/>`;
  }

  return `<svg viewBox="${vbX} ${vbY} ${targetW} ${targetH}" width="${width}" height="${height}" style="max-width: 100%; max-height: 100%; display: block; margin: auto;">${guidesHtml}${polylines}</svg>`;
}

export function getBankSnapshotCacheForTesting() {
  return { ...lastBankSnapshotCache };
}

export function resetBankSnapshotCacheForTesting() {
  lastBankSnapshotCache = { epoch: null, revision: null, profileId: null };
}
