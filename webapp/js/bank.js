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

let sendWorkerFn = null;

let allBankItems = []; // Danh sách tất cả nhãn: [{ label, count, category, sample }]
let currentCategoryFilter = "all";
let currentSearchQuery = "";
let currentDetailLabel = null;
let currentDetailCategory = "words";

export function initBankTab(sendWorkerMessage) {
  sendWorkerFn = sendWorkerMessage;

  // 1. Nút xuất / nhập / kiểm tra
  const btnExport = document.getElementById("btn-export-bank");
  const btnImport = document.getElementById("btn-import-bank");
  const fileInput = document.getElementById("input-import-bank");
  const btnExportCheck = document.getElementById("btn-export-check");
  const btnBankImportGrid = document.getElementById("btn-bank-import-grid");
  const btnRenameProfile = document.getElementById("btn-rename-profile");

  if (btnExport) btnExport.addEventListener("click", exportCurrentBank);
  if (btnImport && fileInput) {
    btnImport.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", handleFileInput);
  }
  if (btnBankImportGrid) {
    btnBankImportGrid.addEventListener("click", () => {
      const gridInput = document.getElementById("input-grid-file");
      if (gridInput) {
        gridInput.click();
      }
    });
  }
  if (btnExportCheck) btnExportCheck.addEventListener("click", exportCheckFile);
  if (btnRenameProfile) btnRenameProfile.addEventListener("click", handleRenameProfile);

  // 2. Tìm kiếm tức thì & Bộ lọc phân loại
  const searchInput = document.getElementById("input-search-bank");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      currentSearchQuery = e.target.value.trim().toLowerCase();
      applyFiltersAndRender();
    });
  }

  const filterContainer = document.getElementById("bank-category-filters");
  if (filterContainer) {
    filterContainer.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      const cat = btn.getAttribute("data-cat");
      if (!cat) return;

      currentCategoryFilter = cat;
      filterContainer.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      applyFiltersAndRender();
    });
  }

  // 3. Modal chi tiết nhãn
  setupDetailModal();
}

function setupDetailModal() {
  const modal = document.getElementById("modal-label-detail");
  const btnClose = document.getElementById("btn-close-label-detail");
  const btnTeachMore = document.getElementById("btn-label-teach-more");
  const btnPreviewRandom = document.getElementById("btn-label-preview-random");
  const btnDelete = document.getElementById("btn-label-delete");

  if (btnClose && modal) {
    btnClose.addEventListener("click", () => {
      modal.style.display = "none";
    });
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.style.display = "none";
    });
  }

  if (btnTeachMore) {
    btnTeachMore.addEventListener("click", () => {
      if (!currentDetailLabel) return;
      if (modal) modal.style.display = "none";
      switchTab("teach");
      if (window.__teachController) {
        window.__teachController.teachWordDirectly(currentDetailLabel);
      }
    });
  }

  if (btnPreviewRandom) {
    btnPreviewRandom.addEventListener("click", handleRandomPreview);
  }

  if (btnDelete) {
    btnDelete.addEventListener("click", handleDeleteLabel);
  }
}

// -------------------------------------------------------------
// Nạp kho & Cập nhật Giao diện
// -------------------------------------------------------------
export async function refreshBankView() {
  if (!sendWorkerFn) return;

  try {
    // 1. Cập nhật thông tin hồ sơ
    await updateProfileChip();

    // 2. Lấy thống kê tổng quan
    const statsRes = await sendWorkerFn("get_stats");
    let stats = {};
    if (statsRes.ok) {
      stats = statsRes.data || {};
      const summary = document.getElementById("bank-summary");
      if (summary) {
        summary.textContent = `Kho mẫu hiện có ${stats.n_words || 0} từ, ${stats.n_letters || 0} chữ cái, ${stats.n_samples || 0} mẫu nét.`;
      }
      const statusText = document.getElementById("status-text");
      if (statusText) {
        statusText.textContent = `${stats.n_words || 0} từ / ${stats.n_samples || 0} mẫu`;
      }
    }

    // 3. Tổng hợp danh sách tất cả các nhãn
    allBankItems = [];

    // Từ vựng (words)
    const wordsRes = await sendWorkerFn("list_words");
    if (wordsRes.ok && Array.isArray(wordsRes.data)) {
      for (const [w, count] of wordsRes.data) {
        allBankItems.push({ label: w, count, category: "words" });
      }
    }

    // Chữ cái (letters)
    const lettersRes = await sendWorkerFn("list_letters");
    if (lettersRes.ok && Array.isArray(lettersRes.data)) {
      for (const [ch, count] of lettersRes.data) {
        allBankItems.push({ label: ch, count, category: "letters" });
      }
    }

    // Chữ số (digits)
    const digitCounts = stats.digit_counts || {};
    for (const [d, count] of Object.entries(digitCounts)) {
      allBankItems.push({ label: d, count, category: "digits" });
    }

    // Dấu câu (punct)
    const punctCounts = stats.punct_counts || {};
    for (const [p, count] of Object.entries(punctCounts)) {
      allBankItems.push({ label: p, count, category: "punct" });
    }

    // Ký hiệu (symbols)
    try {
      const symRes = await sendWorkerFn("list_category_items", { category: "symbols" });
      if (symRes && symRes.ok && Array.isArray(symRes.data)) {
        for (const [sym, count] of symRes.data) {
          allBankItems.push({ label: sym, count, category: "symbols" });
        }
      }
    } catch (_) {}

    // Dấu thanh (marks)
    try {
      const marksRes = await sendWorkerFn("list_category_items", { category: "marks" });
      if (marksRes && marksRes.ok && Array.isArray(marksRes.data)) {
        for (const [m, count] of marksRes.data) {
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
    } catch (_) {}

    // Cập nhật số lượng trên các nút lọc
    updateCategoryCounts();

    // 4. Render danh sách ra lưới
    applyFiltersAndRender();
  } catch (err) {
    console.error("Lỗi cập nhật kho mẫu:", err);
  }
}

function updateCategoryCounts() {
  const counts = { all: allBankItems.length, words: 0, letters: 0, digits: 0, punct: 0, symbols: 0, marks: 0 };
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
  if (!grid) return;

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

  for (const item of filtered) {
    const card = document.createElement("div");
    card.className = "bank-card";

    // Phân loại độ phủ
    const isLow = item.count < 2;
    const badgeClass = isLow ? "coverage-low" : "coverage-good";
    const badgeText = isLow ? `${item.count} mẫu (ít)` : `${item.count} mẫu`;

    card.innerHTML = `
      <div class="bank-card-thumb" id="thumb-${encodeURIComponent(item.label)}">
        <span style="font-size: 1.4rem; color: #94a3b8;">${item.label}</span>
      </div>
      <div class="bank-card-title">${item.label}</div>
      <div class="bank-card-meta">
        <span class="coverage-badge ${badgeClass}">${badgeText}</span>
      </div>
    `;

    card.addEventListener("click", () => {
      openLabelDetail(item.label, item.category, item.count);
    });

    grid.appendChild(card);
  }

  // Nạp lười thumbnail mẫu đầu tiên cho các thẻ nhìn thấy
  loadThumbnailsLazy(filtered.slice(0, 40));
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
async function openLabelDetail(label, category, count) {
  currentDetailLabel = label;
  currentDetailCategory = category;

  const modal = document.getElementById("modal-label-detail");
  const title = document.getElementById("modal-label-title");
  const coverage = document.getElementById("modal-label-coverage");
  const countEl = document.getElementById("modal-label-sample-count");
  const samplesGrid = document.getElementById("modal-label-samples-grid");
  const randomBox = document.getElementById("modal-random-preview-box");

  if (!modal) return;
  modal.style.display = "flex";
  if (randomBox) randomBox.style.display = "none";

  title.textContent = `Nhãn: "${label}"`;
  const isLow = count < 2;
  coverage.textContent = isLow ? "⚠️ Độ phủ thấp (< 2 mẫu): Nên dạy thêm để nét chữ tự nhiên hơn." : "✓ Độ phủ tốt: Đã có đủ biến thể ngẫu nhiên.";
  coverage.style.color = isLow ? "#ca8a04" : "#16a34a";
  countEl.textContent = String(count);

  samplesGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-secondary); padding: 1rem;">Đang tải các mẫu nét...</div>`;

  try {
    const res = await sendWorkerFn("list_label_samples", { label, category });
    if (!res.ok || !Array.isArray(res.data) || res.data.length === 0) {
      samplesGrid.innerHTML = `<div style="grid-column: 1 / -1; color: var(--text-secondary); text-align: center;">Chưa có dữ liệu mẫu nét cho nhãn này.</div>`;
      return;
    }

    samplesGrid.innerHTML = "";
    res.data.forEach((sample, idx) => {
      const itemCard = document.createElement("div");
      itemCard.className = "sample-item-card";

      const svgHtml = sample.s ? createSvgFromStrokes(sample.s, 140, 56, { showBaseline: true }) : "";
      const widthVal = sample.w ? `${sample.w} pt` : "";

      itemCard.innerHTML = `
        <div class="sample-item-thumb">${svgHtml}</div>
        <div style="font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between; width: 100%;">
          <span>Mẫu #${idx + 1}</span>
          <span>${widthVal}</span>
        </div>
      `;
      samplesGrid.appendChild(itemCard);
    });
  } catch (err) {
    samplesGrid.innerHTML = `<div style="grid-column: 1 / -1; color: #dc2626;">Lỗi tải mẫu: ${err.message}</div>`;
  }
}

async function handleRandomPreview() {
  if (!currentDetailLabel || !sendWorkerFn) return;

  const box = document.getElementById("modal-random-preview-box");
  const content = document.getElementById("modal-random-preview-content");
  if (!box || !content) return;

  box.style.display = "block";
  content.innerHTML = `<div style="color: var(--text-secondary); font-size: 0.85rem;">Đang kết xuất thử ngẫu nhiên...</div>`;

  try {
    const seeds = [7, 42, 99];
    const previews = [];

    for (const seed of seeds) {
      const res = await sendWorkerFn("write_text", {
        text: currentDetailLabel,
        options: { seed, strict_case: false },
        format: "txt",
      });
      if (res && res.ok && res.xopp_base64) {
        previews.push({ seed, xopp_base64: res.xopp_base64 });
      }
    }

    content.innerHTML = "";
    for (const p of previews) {
      const pBox = document.createElement("div");
      pBox.style.padding = "0.4rem 0.6rem";
      pBox.style.background = "#fff";
      pBox.style.border = "1px solid var(--border-color)";
      pBox.style.borderRadius = "4px";
      pBox.style.fontSize = "0.8rem";
      pBox.innerHTML = `<div>Hạt giống seed: <b>${p.seed}</b></div>`;
      content.appendChild(pBox);
    }
  } catch (err) {
    content.innerHTML = `<div style="color: #dc2626; font-size: 0.85rem;">Lỗi kết xuất: ${err.message}</div>`;
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
