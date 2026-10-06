/**
 * write.js -- Quản lý tab Viết chữ: soạn thảo, debounce, xem trước SVG, toolbar Markdown,
 * bảng ký hiệu LaTeX, tuỳ chọn kết xuất, xử lý từ thiếu và xuất file.
 */

import { sendWorkerMessage } from "./app.js";
import { decompressXoppBase64, parseXoppXml, renderPageSvgElement, renderPageSvgString } from "./paper.js";
import { exportXopp, exportSvg, exportPng, createZipArchive, downloadBlob } from "./export.js";
import { t } from "./i18n.js";

// Trạng thái cục bộ của tab Viết
let currentDoc = null;         // Kết quả parse XML từ xopp
let currentPageIndex = 0;      // Trang đang xem (0-indexed)
let currentMissingBoxes = [];  // Toạ độ từ thiếu mẫu (D2)
let currentXoppBase64 = "";    // Dữ liệu xopp thô để xuất
let isComposing = false;       // Cờ gõ bộ gõ tiếng Việt Telex/VNI
let debounceTimer = null;
let isRendering = false;
let hasPendingRequest = false;
let pendingParams = null;

// Tùy chọn viết chữ mặc định
const writeOptions = {
  scale: 1.0,
  line: null,
  space: 1.0,
  jitter: 1.0,
  wscale: 1.0,
  color: "#000000ff",
  seed: 42,
  paper: "a4",
  orientation: "portrait",
  background: "plain",
  stable_variants: true,
};

let currentFormat = "md"; // "md" hoặc "txt"

/**
 * Khởi tạo toàn bộ sự kiện cho Tab Viết.
 */
export function initWriteTab() {
  const textarea = document.getElementById("editor-text");
  const selectFormat = document.getElementById("select-format");

  if (!textarea) return;

  // 1. Lắng nghe IME (Bộ gõ tiếng Việt Telex / VNI)
  textarea.addEventListener("compositionstart", () => {
    isComposing = true;
  });

  textarea.addEventListener("compositionend", () => {
    isComposing = false;
    triggerPreviewWithDebounce();
  });

  // 2. Debounce 250ms khi gõ
  textarea.addEventListener("input", () => {
    if (!isComposing) {
      triggerPreviewWithDebounce();
    }
  });

  // 3. Đổi định dạng Markdown / Text
  selectFormat.addEventListener("change", (e) => {
    currentFormat = e.target.value;
    triggerPreviewImmediate();
  });

  // 4. Các nút Toolbar Markdown
  setupMarkdownToolbar(textarea);

  // 5. Kéo thả file (.txt, .md, .docx)
  setupFileDropAndOpen(textarea);

  // 6. Điều hướng trang và Zoom
  setupPreviewNavigation();

  // 7. Modal Tùy chọn viết
  setupOptionsModal();

  // 8. Modal Ký hiệu LaTeX
  setupLatexModal(textarea);

  // 9. Các nút Xuất file
  setupExportButtons();

  // Kích hoạt render lần đầu nếu đã có sẵn chữ
  if (textarea.value.trim()) {
    triggerPreviewImmediate();
  }
}

function triggerPreviewWithDebounce() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    triggerPreviewImmediate();
  }, 250);
}

export function triggerPreviewImmediate() {
  const textarea = document.getElementById("editor-text");
  if (!textarea) return;

  const text = textarea.value;
  if (!text.trim()) {
    clearPreview();
    return;
  }

  const params = {
    text,
    format: currentFormat,
    options: { ...writeOptions },
  };

  requestRender(params);
}

/**
 * Thực hiện yêu cầu render với mô hình "Một request chờ" (One Pending Request).
 */
async function requestRender(params) {
  if (isRendering) {
    hasPendingRequest = true;
    pendingParams = params;
    return;
  }

  isRendering = true;
  showRenderingIndicator(true);

  try {
    const res = await sendWorkerMessage("write_text", params);
    if (res && res.ok) {
      currentXoppBase64 = res.xopp_base64;
      currentMissingBoxes = res.missing_token_boxes || [];

      // Giải nén XML từ xopp
      const xml = await decompressXoppBase64(res.xopp_base64);
      currentDoc = parseXoppXml(xml);

      // Cập nhật giao diện
      updatePaginationControls();
      renderCurrentPage();
      updateInfoPanel(res);
    } else {
      console.warn("Lỗi render:", res?.error);
      showWarning(res?.error || "Lỗi không xác định khi kết xuất văn bản.");
    }
  } catch (err) {
    console.error("Lỗi khi gửi yêu cầu render:", err);
    showWarning(err.message);
  } finally {
    isRendering = false;
    showRenderingIndicator(false);

    // Nếu có request mới gửi đến trong lúc đang render -> chạy ngay bản mới nhất
    if (hasPendingRequest) {
      hasPendingRequest = false;
      const nextParams = pendingParams;
      pendingParams = null;
      requestRender(nextParams);
    }
  }
}

function clearPreview() {
  const wrapper = document.getElementById("paper-svg-wrapper");
  const placeholder = document.getElementById("preview-placeholder");
  if (wrapper) wrapper.innerHTML = "";
  if (placeholder) placeholder.style.display = "block";
  const indicator = document.getElementById("page-indicator");
  if (indicator) indicator.textContent = "Trang 0 / 0";
  currentDoc = null;
  currentXoppBase64 = "";
}

function showRenderingIndicator(loading) {
  const statusIndicator = document.getElementById("status-indicator");
  const statusText = document.getElementById("status-text");
  if (statusIndicator) {
    if (loading) {
      statusIndicator.className = "status-dot loading";
      if (statusText) statusText.textContent = "Đang kết xuất...";
    } else {
      statusIndicator.className = "status-dot";
      if (statusText) statusText.textContent = "Sẵn sàng";
    }
  }
}

function renderCurrentPage() {
  const wrapper = document.getElementById("paper-svg-wrapper");
  const placeholder = document.getElementById("preview-placeholder");
  if (!wrapper || !currentDoc || !currentDoc.pages.length) return;

  if (placeholder) placeholder.style.display = "none";

  if (currentPageIndex >= currentDoc.pages.length) {
    currentPageIndex = currentDoc.pages.length - 1;
  }
  if (currentPageIndex < 0) {
    currentPageIndex = 0;
  }

  const page = currentDoc.pages[currentPageIndex];
  const svgEl = renderPageSvgElement(page, {
    missingBoxes: currentMissingBoxes,
  });

  // Thay thế nội dung wrapper an toàn
  wrapper.replaceChildren(svgEl);
}

function updatePaginationControls() {
  const total = currentDoc ? currentDoc.pages.length : 0;
  const current = total > 0 ? currentPageIndex + 1 : 0;
  const indicator = document.getElementById("page-indicator");
  if (indicator) {
    indicator.textContent = `Trang ${current} / ${total}`;
  }

  const btnPrev = document.getElementById("btn-page-prev");
  const btnNext = document.getElementById("btn-page-next");
  if (btnPrev) btnPrev.disabled = currentPageIndex <= 0;
  if (btnNext) btnNext.disabled = currentPageIndex >= total - 1;
}

function updateInfoPanel(res) {
  const warningsBox = document.getElementById("editor-warnings");
  const missingBox = document.getElementById("missing-tokens-box");
  const missingList = document.getElementById("missing-tokens-list");

  // Warnings
  if (warningsBox) {
    if (res.warnings && res.warnings.length > 0) {
      warningsBox.innerHTML = res.warnings.map((w) => `<div>⚠️ ${escapeHtml(w)}</div>`).join("");
      warningsBox.style.display = "block";
    } else {
      warningsBox.style.display = "none";
    }
  }

  // Missing tokens
  if (missingBox && missingList) {
    if (res.missing_sorted && res.missing_sorted.length > 0) {
      missingList.innerHTML = "";
      for (const [word, count] of res.missing_sorted) {
        const chip = document.createElement("span");
        chip.className = "chip-missing";
        chip.textContent = `${word} (${count})`;
        chip.title = `Bấm để chuyển sang tab Dạy chữ và học từ "${word}"`;
        chip.onclick = () => {
          navigateToTeach(word);
        };
        missingList.appendChild(chip);
      }
      missingBox.style.display = "block";
    } else {
      missingBox.style.display = "none";
    }
  }
}

function navigateToTeach(word) {
  const tabTeachBtn = document.querySelector('[data-tab="teach"]');
  if (tabTeachBtn) {
    tabTeachBtn.click();
  }
  if (window.__teachController) {
    window.__teachController.teachWordDirectly(word);
  } else {
    const promptWord = document.getElementById("teach-target-word");
    if (promptWord) {
      promptWord.textContent = word;
    }
  }
}

function showWarning(msg) {
  const warningsBox = document.getElementById("editor-warnings");
  if (warningsBox) {
    warningsBox.innerHTML = `<div>⚠️ ${escapeHtml(msg)}</div>`;
    warningsBox.style.display = "block";
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[m]));
}

// -------------------------------------------------------------
// Markdown Toolbar & Text Editing Helpers
// -------------------------------------------------------------
function insertAtCursor(textarea, prefix, suffix = "") {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const text = textarea.value;
  const selected = text.substring(start, end);
  const replacement = prefix + (selected || "nội dung") + suffix;

  textarea.value = text.substring(0, start) + replacement + text.substring(end);
  textarea.focus();
  textarea.setSelectionRange(start + prefix.length, start + prefix.length + (selected || "nội dung").length);

  triggerPreviewImmediate();
}

function setupMarkdownToolbar(textarea) {
  const btn = (id, fn) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  };

  btn("btn-md-h1", () => insertAtCursor(textarea, "\n# ", "\n"));
  btn("btn-md-h2", () => insertAtCursor(textarea, "\n## ", "\n"));
  btn("btn-md-h3", () => insertAtCursor(textarea, "\n### ", "\n"));
  btn("btn-md-ul", () => insertAtCursor(textarea, "\n- ", "\n"));
  btn("btn-md-ol", () => insertAtCursor(textarea, "\n1. ", "\n"));
  btn("btn-md-math-inline", () => insertAtCursor(textarea, "$", "$"));
  btn("btn-md-math-block", () => insertAtCursor(textarea, "\n$$\n", "\n$$\n"));
  btn("btn-md-pagebreak", () => insertAtCursor(textarea, "\n<!-- pagebreak -->\n", ""));

  btn("btn-md-table", () => {
    const tableTemplate = "\n| Cột 1 | Cột 2 | Cột 3 |\n| :--- | :---: | ---: |\n| A1 | B1 | C1 |\n| A2 | B2 | C2 |\n";
    insertAtCursor(textarea, tableTemplate, "");
  });
}

// -------------------------------------------------------------
// Kéo thả & Mở file (.txt, .md, .docx)
// -------------------------------------------------------------
function setupFileDropAndOpen(textarea) {
  const inputOpen = document.getElementById("input-open-file");
  const btnOpen = document.getElementById("btn-open-file");

  if (btnOpen && inputOpen) {
    btnOpen.addEventListener("click", () => inputOpen.click());
    inputOpen.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (file) handleFileImport(file, textarea);
      inputOpen.value = "";
    });
  }

  // Drag and drop vào textarea
  textarea.addEventListener("dragover", (e) => {
    e.preventDefault();
    textarea.style.borderColor = "var(--primary)";
  });

  textarea.addEventListener("dragleave", () => {
    textarea.style.borderColor = "var(--border-color)";
  });

  textarea.addEventListener("drop", (e) => {
    e.preventDefault();
    textarea.style.borderColor = "var(--border-color)";
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileImport(file, textarea);
  });
}

async function handleFileImport(file, textarea) {
  const name = file.name.toLowerCase();
  if (name.endsWith(".txt") || name.endsWith(".md") || name.endsWith(".markdown")) {
    const text = await file.text();
    textarea.value = text;
    const selectFormat = document.getElementById("select-format");
    if (selectFormat) {
      selectFormat.value = name.endsWith(".txt") ? "txt" : "md";
      currentFormat = selectFormat.value;
    }
    triggerPreviewImmediate();
  } else if (name.endsWith(".docx")) {
    showRenderingIndicator(true);
    try {
      const buffer = await file.arrayBuffer();
      const res = await sendWorkerMessage("import_docx", { bytes: buffer });
      if (res && res.ok) {
        textarea.value = res.markdown_text || res.text || "";
        const selectFormat = document.getElementById("select-format");
        if (selectFormat) {
          selectFormat.value = "md";
          currentFormat = "md";
        }
        triggerPreviewImmediate();
      } else {
        showWarning(`Lỗi mở file .docx: ${res?.error || "Không hỗ trợ"}`);
      }
    } catch (err) {
      showWarning(`Không thể đọc file .docx: ${err.message}`);
    } finally {
      showRenderingIndicator(false);
    }
  }
}

// -------------------------------------------------------------
// Điều hướng trang và Zoom
// -------------------------------------------------------------
function setupPreviewNavigation() {
  const btnPrev = document.getElementById("btn-page-prev");
  const btnNext = document.getElementById("btn-page-next");
  const selectZoom = document.getElementById("select-zoom");
  const wrapper = document.getElementById("paper-svg-wrapper");

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (currentPageIndex > 0) {
        currentPageIndex--;
        updatePaginationControls();
        renderCurrentPage();
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      if (currentDoc && currentPageIndex < currentDoc.pages.length - 1) {
        currentPageIndex++;
        updatePaginationControls();
        renderCurrentPage();
      }
    });
  }

  if (selectZoom && wrapper) {
    selectZoom.addEventListener("change", (e) => {
      const val = e.target.value;
      if (val === "fit") {
        wrapper.style.transform = "scale(0.8)";
      } else {
        wrapper.style.transform = `scale(${val})`;
      }
    });
  }
}

// -------------------------------------------------------------
// Modal Tuỳ chọn viết (T047)
// -------------------------------------------------------------
function setupOptionsModal() {
  const modal = document.getElementById("modal-write-options");
  const btnOpen = document.getElementById("btn-open-write-options");
  const btnClose = document.getElementById("btn-close-options");
  const btnApply = document.getElementById("btn-apply-options");
  const btnReset = document.getElementById("btn-reset-options");
  const btnRandomSeed = document.getElementById("btn-random-seed");

  if (!modal || !btnOpen) return;

  btnOpen.addEventListener("click", () => {
    modal.style.display = "flex";
  });

  const closeModal = () => {
    modal.style.display = "none";
  };

  if (btnClose) btnClose.addEventListener("click", closeModal);

  // Sliders binding
  const bindRange = (rangeId, valId, prop) => {
    const r = document.getElementById(rangeId);
    const v = document.getElementById(valId);
    if (r && v) {
      r.addEventListener("input", (e) => {
        v.textContent = e.target.value;
        writeOptions[prop] = parseFloat(e.target.value);
      });
    }
  };

  bindRange("opt-scale", "val-scale", "scale");
  bindRange("opt-space", "val-space", "space");
  bindRange("opt-jitter", "val-jitter", "jitter");
  bindRange("opt-wscale", "val-wscale", "wscale");

  // Line height
  const optLine = document.getElementById("opt-line");
  if (optLine) {
    optLine.addEventListener("change", (e) => {
      writeOptions.line = e.target.value ? parseFloat(e.target.value) : null;
    });
  }

  // Seed
  const optSeed = document.getElementById("opt-seed");
  if (optSeed) {
    optSeed.addEventListener("change", (e) => {
      writeOptions.seed = parseInt(e.target.value, 10) || 42;
    });
  }

  if (btnRandomSeed) {
    btnRandomSeed.addEventListener("click", () => {
      const nextSeed = Math.floor(Math.random() * 100000);
      if (optSeed) optSeed.value = nextSeed;
      writeOptions.seed = nextSeed;
      triggerPreviewImmediate();
    });
  }

  // Color
  const optColor = document.getElementById("opt-color");
  const optColorHex = document.getElementById("opt-color-hex");
  if (optColor && optColorHex) {
    optColor.addEventListener("input", (e) => {
      optColorHex.value = e.target.value + "ff";
      writeOptions.color = optColorHex.value;
    });
    optColorHex.addEventListener("change", (e) => {
      writeOptions.color = e.target.value;
    });
  }

  // Paper, Orientation, Background
  const bindSelect = (id, prop) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", (e) => {
        writeOptions[prop] = e.target.value;
      });
    }
  };

  bindSelect("opt-paper", "paper");
  bindSelect("opt-orientation", "orientation");
  bindSelect("opt-background", "background");

  if (btnApply) {
    btnApply.addEventListener("click", () => {
      closeModal();
      triggerPreviewImmediate();
    });
  }

  if (btnReset) {
    btnReset.addEventListener("click", () => {
      writeOptions.scale = 1.0;
      writeOptions.line = null;
      writeOptions.space = 1.0;
      writeOptions.jitter = 1.0;
      writeOptions.wscale = 1.0;
      writeOptions.color = "#000000ff";
      writeOptions.seed = 42;
      writeOptions.paper = "a4";
      writeOptions.orientation = "portrait";
      writeOptions.background = "plain";

      // Reset DOM elements
      document.getElementById("opt-scale").value = 1.0;
      document.getElementById("val-scale").textContent = "1.0";
      document.getElementById("opt-line").value = "";
      document.getElementById("opt-space").value = 1.0;
      document.getElementById("val-space").textContent = "1.0";
      document.getElementById("opt-jitter").value = 1.0;
      document.getElementById("val-jitter").textContent = "1.0";
      document.getElementById("opt-wscale").value = 1.0;
      document.getElementById("val-wscale").textContent = "1.0";
      document.getElementById("opt-color-hex").value = "#000000ff";
      document.getElementById("opt-seed").value = 42;
      document.getElementById("opt-paper").value = "a4";
      document.getElementById("opt-orientation").value = "portrait";
      document.getElementById("opt-background").value = "plain";

      triggerPreviewImmediate();
    });
  }
}

// -------------------------------------------------------------
// Modal Ký hiệu LaTeX (T046)
// -------------------------------------------------------------
async function setupLatexModal(textarea) {
  const modal = document.getElementById("modal-latex-symbols");
  const btnOpen = document.getElementById("btn-open-latex-symbols");
  const btnClose = document.getElementById("btn-close-symbols");
  const container = document.getElementById("latex-symbols-container");

  if (!modal || !btnOpen) return;

  btnOpen.addEventListener("click", async () => {
    modal.style.display = "flex";
    if (container && container.children.length === 0) {
      await loadLatexSymbols(container, textarea, modal);
    }
  });

  if (btnClose) {
    btnClose.addEventListener("click", () => {
      modal.style.display = "none";
    });
  }
}

async function loadLatexSymbols(container, textarea, modal) {
  try {
    const res = await sendWorkerMessage("get_latex_symbols");
    if (!res || !res.ok || !res.symbols) {
      container.innerHTML = "<div>Không tải được bảng ký hiệu.</div>";
      return;
    }

    container.innerHTML = "";
    // Nhóm theo category
    for (const [catName, symbols] of Object.entries(res.symbols)) {
      const catDiv = document.createElement("div");
      catDiv.innerHTML = `<div style="font-weight: 600; margin-bottom: 0.35rem; color: var(--text-primary);">${catName}</div>`;
      const btnGrid = document.createElement("div");
      btnGrid.style.display = "flex";
      btnGrid.style.flexWrap = "wrap";
      btnGrid.style.gap = "0.35rem";

      for (const item of symbols) {
        const symBtn = document.createElement("button");
        symBtn.className = "btn-tool";
        symBtn.style.padding = "0.4rem 0.65rem";
        symBtn.style.fontSize = "1rem";
        symBtn.textContent = item.display || item.symbol || item.latex;
        symBtn.title = item.latex;
        symBtn.onclick = () => {
          insertAtCursor(textarea, item.latex + " ");
          modal.style.display = "none";
        };
        btnGrid.appendChild(symBtn);
      }
      catDiv.appendChild(btnGrid);
      container.appendChild(catDiv);
    }
  } catch (err) {
    container.innerHTML = `<div>Lỗi tải ký hiệu: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------
// Xuất file (.xopp, PNG, SVG, ZIP, In/PDF) (T050)
// -------------------------------------------------------------
function setupExportButtons() {
  const btnXopp = document.getElementById("btn-export-xopp");
  const btnPng = document.getElementById("btn-export-png");
  const btnSvg = document.getElementById("btn-export-svg");
  const btnZip = document.getElementById("btn-export-zip");
  const btnPrint = document.getElementById("btn-print-pdf");

  // Xuất file .xopp gốc
  if (btnXopp) {
    btnXopp.addEventListener("click", () => {
      if (!currentXoppBase64) {
        alert("Chưa có nội dung kết xuất để xuất file .xopp.");
        return;
      }
      exportXopp(currentXoppBase64, "chuviet.xopp");
    });
  }

  // Tải ảnh PNG trang hiện tại
  if (btnPng) {
    btnPng.addEventListener("click", () => {
      const svgEl = document.querySelector("#paper-svg-wrapper svg");
      if (!svgEl) {
        alert("Chưa có trang giấy để xuất ảnh.");
        return;
      }
      exportPng(svgEl, `trang_${currentPageIndex + 1}.png`, 2.0, false);
    });
  }

  // Tải ảnh SVG trang hiện tại
  if (btnSvg) {
    btnSvg.addEventListener("click", () => {
      const svgEl = document.querySelector("#paper-svg-wrapper svg");
      if (!svgEl) {
        alert("Chưa có trang giấy để xuất file SVG.");
        return;
      }
      exportSvg(svgEl, `trang_${currentPageIndex + 1}.svg`);
    });
  }

  // Tải toàn bộ các trang dạng ZIP
  if (btnZip) {
    btnZip.addEventListener("click", () => {
      if (!currentDoc || !currentDoc.pages.length) {
        alert("Chưa có trang nào để xuất ZIP.");
        return;
      }
      const files = [];
      currentDoc.pages.forEach((page, idx) => {
        const svgStr = renderPageSvgString(page, { missingBoxes: currentMissingBoxes });
        const encoder = new TextEncoder();
        files.push({
          name: `trang_${idx + 1}.svg`,
          data: encoder.encode(svgStr),
        });
      });
      const zipBytes = createZipArchive(files);
      const blob = new Blob([zipBytes], { type: "application/zip" });
      downloadBlob(blob, "tailieu_anh.zip");
    });
  }

  // In / Xuất PDF
  if (btnPrint) {
    btnPrint.addEventListener("click", () => {
      if (!currentDoc || !currentDoc.pages.length) {
        alert("Chưa có nội dung để in.");
        return;
      }
      const printContainer = document.getElementById("print-container");
      if (printContainer) {
        printContainer.innerHTML = "";
        currentDoc.pages.forEach((page) => {
          const pageDiv = document.createElement("div");
          pageDiv.className = "print-page-wrapper";
          const svgEl = renderPageSvgElement(page, { missingBoxes: currentMissingBoxes });
          pageDiv.appendChild(svgEl);
          printContainer.appendChild(pageDiv);
        });
        printContainer.style.display = "block";
        window.print();
        setTimeout(() => {
          printContainer.style.display = "none";
          printContainer.innerHTML = "";
        }, 1000);
      }
    });
  }
}
