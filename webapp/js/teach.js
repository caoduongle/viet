/**
 * teach.js -- Quản lý nghiệp vụ tab "Dạy mẫu chữ" trên Web Client.
 *
 * Tuân thủ T057:
 *   - Quản lý hàng đợi dạy chữ + đếm tiến độ.
 *   - Hiển thị số lượng mẫu hiện có trong kho của từ/nhãn đang dạy.
 *   - Công cụ: Bút / Gôm, độ dày nét, Hoàn tác (Undo), Làm lại (Redo), Xoá hết nét.
 *   - Phím tắt: Enter (Lưu mẫu), Ctrl+Z (Hoàn tác), Ctrl+Y (Làm lại), Esc (Xoá nét).
 *   - Thêm từ / cụm từ tự do.
 *   - Nạp từ thông dụng còn thiếu (missing_seed_words) & Bộ tối thiểu (missing_minimal_essentials).
 *   - Hiệu chỉnh cỡ tay (pick_calibration_word, calibrating=true, cập nhật session_scale).
 *   - Tự động nạp mẫu thiếu khi người dùng bấm từ bảng thiếu ở tab Soạn thảo.
 */

import { TeachCanvas } from "./canvas.js";

export class TeachController {
  constructor(workerClient, options = {}) {
    this.worker = workerClient;
    this.options = options;
    this.onSampleSaved = options.onSampleSaved || null;
    this.canvas = null;

    // Trạng thái hàng đợi & phiên
    this.queue = [];
    this.current = null;
    this.isCalibrating = false;
    this.calibrated = false;
    this.sessionScale = 1.0;

    // Cache đếm mẫu của nhãn để cập nhật UI nhanh
    this.sampleCounts = new Map();
  }

  async init() {
    this._cacheDom();
    this._initCanvas();
    this._bindEvents();
    await this._fetchCanvasSpec();
    this.refresh();
  }

  _cacheDom() {
    this.dom = {
      section: document.getElementById("tab-teach"),
      inputAdd: document.getElementById("input-teach-add"),
      btnAdd: document.getElementById("btn-teach-add"),
      btnChars: document.getElementById("btn-teach-chars"),
      btnEssentials: document.getElementById("btn-teach-essentials"),
      btnSeed: document.getElementById("btn-teach-seed"),
      btnImportGrid: document.getElementById("btn-import-grid"),
      inputGridFile: document.getElementById("input-grid-file"),
      btnExportCharGrid: document.getElementById("btn-export-char-grid"),
      btnClearQueue: document.getElementById("btn-teach-clear-queue"),
      btnCalibrate: document.getElementById("btn-teach-calibrate"),

      // Modal chọn bộ ký tự
      modalCharGroups: document.getElementById("modal-char-groups"),
      btnCloseCharGroups: document.getElementById("btn-close-char-groups"),
      selectCharGroup: document.getElementById("select-char-group"),
      charGroupDesc: document.getElementById("char-group-desc"),
      btnCharGroupsAddQueue: document.getElementById("btn-char-groups-add-queue"),
      btnCharGroupsExport: document.getElementById("btn-char-groups-export"),

      queueCount: document.getElementById("teach-queue-count"),
      queueList: document.getElementById("teach-queue-list"),
      btnSkip: document.getElementById("btn-teach-skip"),

      targetWord: document.getElementById("teach-target-word"),
      sampleCount: document.getElementById("teach-sample-count"),
      scaleInfo: document.getElementById("teach-scale-info"),

      canvasEl: document.getElementById("teach-canvas"),

      toolPen: document.getElementById("btn-teach-tool-pen"),
      toolEraser: document.getElementById("btn-teach-tool-eraser"),
      selectPenWidth: document.getElementById("select-teach-pen-width"),
      chkGhost: document.getElementById("chk-teach-ghost"),

      btnUndo: document.getElementById("btn-teach-undo"),
      btnRedo: document.getElementById("btn-teach-redo"),
      btnClear: document.getElementById("btn-teach-clear"),
      btnSave: document.getElementById("btn-teach-save"),
    };
  }

  _initCanvas() {
    if (!this.dom.canvasEl) return;
    this.canvas = new TeachCanvas(this.dom.canvasEl, {
      onChange: (count) => this._onStrokeChange(count),
    });
  }

  async _fetchCanvasSpec() {
    try {
      const res = await this.worker.request("get_canvas_spec");
      if (res && res.ok && this.canvas) {
        this.canvas.setSpec(res);
      }
    } catch (err) {
      console.warn("[Teach] Không thể nạp canvas spec từ worker:", err);
    }
  }

  _bindEvents() {
    // 1. Thêm từ vào hàng đợi
    this.dom.btnAdd.addEventListener("click", () => this.addWordFromInput());
    this.dom.inputAdd.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        this.addWordFromInput();
      }
    });

    // 2. Nạp hàng đợi tự động & Lưới ô
    if (this.dom.btnChars) {
      this.dom.btnChars.addEventListener("click", () => this.openCharGroupsModal());
    }
    if (this.dom.btnEssentials) {
      this.dom.btnEssentials.addEventListener("click", () => this.openCharGroupsModal());
    }
    if (this.dom.btnSeed) {
      this.dom.btnSeed.addEventListener("click", () => this.addSeedWords());
    }
    if (this.dom.btnExportCharGrid) {
      this.dom.btnExportCharGrid.addEventListener("click", () => this.openCharGroupsModal());
    }
    if (this.dom.btnImportGrid && this.dom.inputGridFile) {
      this.dom.btnImportGrid.addEventListener("click", () => this.dom.inputGridFile.click());
      this.dom.inputGridFile.addEventListener("change", (e) => this.handleImportGridFile(e));
    }
    this._bindCharGroupsModalEvents();

    this.dom.btnClearQueue.addEventListener("click", () => this.clearQueue());
    this.dom.btnCalibrate.addEventListener("click", () => this.startCalibration());
    this.dom.btnSkip.addEventListener("click", () => this.skipWord());

    // 3. Công cụ vẽ
    this.dom.toolPen.addEventListener("click", () => {
      this.canvas.setTool("pen");
      this.dom.toolPen.classList.add("active");
      this.dom.toolEraser.classList.remove("active");
    });

    this.dom.toolEraser.addEventListener("click", () => {
      this.canvas.setTool("eraser");
      this.dom.toolEraser.classList.add("active");
      this.dom.toolPen.classList.remove("active");
    });

    this.dom.selectPenWidth.addEventListener("change", (e) => {
      this.canvas.setPenWidth(parseFloat(e.target.value));
    });

    this.dom.chkGhost.addEventListener("change", (e) => {
      this.canvas.toggleGhost(e.target.checked);
    });

    // 4. Các nút thao tác
    this.dom.btnUndo.addEventListener("click", () => this.canvas.undo());
    this.dom.btnRedo.addEventListener("click", () => this.canvas.redo());
    this.dom.btnClear.addEventListener("click", () => this.canvas.clear());
    this.dom.btnSave.addEventListener("click", () => this.saveWord());

    // 5. Phím tắt toàn cục khi đang ở tab Dạy
    document.addEventListener("keydown", (e) => {
      if (!this.dom.section.classList.contains("active")) return;

      // Tránh phím tắt khi đang nhập liệu trong ô input
      const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
      if (tag === "input" || tag === "textarea") return;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) {
          this.canvas.redo();
        } else {
          this.canvas.undo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        this.canvas.redo();
      } else if (e.key === "Escape") {
        e.preventDefault();
        this.canvas.clear();
      } else if (e.key === "Enter") {
        e.preventDefault();
        this.saveWord();
      }
    });
  }

  _onStrokeChange(count) {
    this.dom.btnSave.disabled = count === 0;
  }

  // ------------------------------------------------------------ Hàng đợi
  loadQueue(words) {
    if (!Array.isArray(words)) return;
    for (const w of words) {
      const clean = String(w).trim();
      if (clean && !this.queue.includes(clean)) {
        this.queue.push(clean);
      }
    }
    this.refresh();
  }

  addWordFromInput() {
    const val = this.dom.inputAdd.value.trim();
    if (val) {
      if (!this.queue.includes(val)) {
        this.queue.push(val);
      }
      this.dom.inputAdd.value = "";
      this.refresh();
    }
  }

  teachWordDirectly(word) {
    const clean = String(word).trim();
    if (!clean) return;

    // Đưa lên đầu hàng đợi và chuyển ngay sang
    const idx = this.queue.indexOf(clean);
    if (idx !== -1) {
      this.queue.splice(idx, 1);
    }
    this.queue.unshift(clean);
    this.isCalibrating = false;
    this.refresh();
  }

  // ------------------------------------------------------------ Modal Bộ Ký Tự (R3) & Nạp Lưới (R2)
  _bindCharGroupsModalEvents() {
    if (!this.dom.modalCharGroups) return;

    if (this.dom.btnCloseCharGroups) {
      this.dom.btnCloseCharGroups.addEventListener("click", () => this.closeCharGroupsModal());
    }
    this.dom.modalCharGroups.addEventListener("click", (e) => {
      if (e.target === this.dom.modalCharGroups) {
        this.closeCharGroupsModal();
      }
    });

    if (this.dom.selectCharGroup) {
      this.dom.selectCharGroup.addEventListener("change", () => this._updateCharGroupDesc());
    }

    if (this.dom.btnCharGroupsAddQueue) {
      this.dom.btnCharGroupsAddQueue.addEventListener("click", () => this.addCharGroupToQueue());
    }

    if (this.dom.btnCharGroupsExport) {
      this.dom.btnCharGroupsExport.addEventListener("click", () => this.exportCharGroupGrid());
    }
  }

  openCharGroupsModal() {
    if (this.dom.modalCharGroups) {
      this._updateCharGroupDesc();
      this.dom.modalCharGroups.style.display = "flex";
    }
  }

  closeCharGroupsModal() {
    if (this.dom.modalCharGroups) {
      this.dom.modalCharGroups.style.display = "none";
    }
  }

  _updateCharGroupDesc() {
    if (!this.dom.selectCharGroup || !this.dom.charGroupDesc) return;
    const descriptions = {
      co_ban: "Chữ cái cơ bản tiếng Việt gồm cả chữ thường, chữ hoa và các chữ cái mượn phổ biến (85 chữ cái).",
      chu_hoa: "33 chữ cái viết hoa tiếng Việt và các chữ cái ngoại lai chuẩn (A, Ă, Â... Z).",
      chu_thuong: "33 chữ cái viết thường tiếng Việt và các chữ cái ngoại lai chuẩn (a, ă, â... z).",
      chu_so: "10 chữ số từ 0 đến 9.",
      dau_cau: "Các dấu câu cơ bản tiếng Việt: dấu phẩy, chấm, hai chấm, chấm phẩy, chấm than, hỏi, gạch nối, ba chấm.",
      dau_cau_mo_rong: "Dấu câu mở rộng: các loại ngoặc đơn/kép/vuông/nhọn, gạch chéo, nháy đơn/kép.",
      ky_hieu_toan: "Ký hiệu toán học và đơn vị phổ biến: cộng, trừ, bằng, nhân, chia, phần trăm, tiền tệ...",
      dau_thanh: "5 dấu thanh rời tiếng Việt (huyền, sắc, hỏi, ngã, nặng) dùng để ghép thanh linh hoạt.",
      toan_hy_lap: "Toàn bộ bảng ký tự toán học và chữ cái Hy Lạp thường và hoa.",
      day_du: "Tất cả các bộ ký tự trên gom lại đầy đủ.",
    };
    const val = this.dom.selectCharGroup.value;
    this.dom.charGroupDesc.textContent = descriptions[val] || "Bộ ký tự chọn lọc.";
  }

  async addCharGroupToQueue() {
    if (!this.dom.selectCharGroup) return;
    const groupId = this.dom.selectCharGroup.value;

    try {
      const res = await this.worker.request("get_missing_chars", {
        groupId,
        exclude: this.queue,
      });
      if (res && res.ok && Array.isArray(res.tokens)) {
        if (res.tokens.length === 0) {
          alert("Kho mẫu đã có đủ tất cả các ký tự trong nhóm này.");
          this.closeCharGroupsModal();
          return;
        }
        this.loadQueue(res.tokens);
        this.closeCharGroupsModal();
        alert(`Đã thêm ${res.tokens.length} ký tự còn thiếu vào hàng đợi.`);
      }
    } catch (err) {
      alert("Lỗi khi nạp bộ ký tự: " + err.message);
    }
  }

  async exportCharGroupGrid() {
    if (!this.dom.selectCharGroup) return;
    const groupId = this.dom.selectCharGroup.value;

    try {
      const res = await this.worker.request("export_char_grid", { groupId });
      if (!res || !res.ok || !res.xopp_base64) {
        throw new Error((res && res.error) || "Không thể tạo file lưới.");
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
      a.download = `luoi_tap_viet_${groupId}.xopp`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      this.closeCharGroupsModal();
    } catch (err) {
      alert("Lỗi xuất lưới: " + err.message);
    }
  }

  async handleImportGridFile(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    try {
      const arrayBuffer = await file.arrayBuffer();
      const bytes = Array.from(new Uint8Array(arrayBuffer));

      const res = await this.worker.request("import_grid", { bytes, dedup: true });
      if (!res || !res.ok || !res.data) {
        throw new Error((res && res.error) || "Không thể xử lý file lưới .xopp.");
      }

      const r = res.data;
      const msg = [
        `Nạp file lưới hoàn tất!`,
        `- Đã thêm mẫu mới: ${r.added_samples}`,
        `- Trùng lặp (bỏ qua): ${r.duplicate_samples}`,
        `- Bỏ qua ô đa ký tự: ${r.skipped_multi_char}`,
        `- Loại bỏ (trống/lỗi nét): ${r.rejected_cells}`,
      ].join("\n");
      alert(msg);

      // Thông báo làm mới kho và lưu tự động
      if (typeof window.__notifySampleTaught === "function") {
        window.__notifySampleTaught();
      }
      this.refresh();
    } catch (err) {
      alert("Lỗi nạp file lưới: " + err.message);
    } finally {
      e.target.value = "";
    }
  }

  addMinimalEssentials() {
    this.openCharGroupsModal();
  }

  addSeedWords() {
    this.openCharGroupsModal();
  }

  clearQueue() {
    this.queue = [];
    this.current = null;
    this.isCalibrating = false;
    this.refresh();
  }

  skipWord() {
    this.isCalibrating = false;
    this.refresh(true);
  }

  // ------------------------------------------------------------ Hiệu chỉnh cỡ tay
  async startCalibration() {
    try {
      const res = await this.worker.request("pick_calibration_word");
      if (!res || !res.ok || !res.word) {
        alert("Kho mẫu chưa có từ nào đủ mẫu ổn định để dùng làm mốc hiệu chỉnh.");
        return;
      }
      const calibWord = res.word;
      this.isCalibrating = true;
      const idx = this.queue.indexOf(calibWord);
      if (idx !== -1) {
        this.queue.splice(idx, 1);
      }
      this.queue.unshift(calibWord);
      this.refresh();
      alert(`Hiệu chỉnh cỡ tay: Viết từ '${calibWord}' đúng như bạn viết bình thường (không cần cố to/nhỏ), rồi bấm Lưu.`);
    } catch (err) {
      alert("Lỗi khi kích hoạt hiệu chỉnh: " + err.message);
    }
  }

  _updateScaleLabel() {
    if (this.calibrated) {
      this.dom.scaleInfo.textContent = `Hệ số cỡ tay: ${this.sessionScale.toFixed(2)}x`;
    } else {
      this.dom.scaleInfo.textContent = `Hệ số cỡ tay: 1.00x (chưa hiệu chỉnh)`;
    }
  }

  // ------------------------------------------------------------ Lưu mẫu
  async saveWord() {
    if (!this.current) return;
    if (!this.canvas || !this.canvas.hasInk()) {
      alert("Hãy vẽ từ này trước khi lưu.");
      return;
    }

    const label = this.current;
    const pixelStrokes = this.canvas.getPixelStrokes();
    const wasCalibrating = this.isCalibrating;

    try {
      this.dom.btnSave.disabled = true;
      this.dom.btnSave.textContent = "Đang lưu...";

      let res;
      const isSingleChar = label.length === 1 || ["sắc", "huyền", "hỏi", "ngã", "nặng", "dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng"].includes(label.toLowerCase());
      if (isSingleChar && !wasCalibrating) {
        res = await this.worker.request("teach_char", {
          label,
          pixel_strokes: pixelStrokes,
          deferred_save: true,
        });
      } else {
        res = await this.worker.request("teach_sample", {
          label,
          pixel_strokes: pixelStrokes,
          calibrating: wasCalibrating,
          deferred_save: true,
        });
      }

      if (!res || !res.ok) {
        throw new Error((res && res.error) || "Lỗi không xác định khi lưu mẫu.");
      }

      // Cập nhật hệ số cỡ tay nếu vừa hiệu chỉnh
      if (res.recalibrated) {
        this.calibrated = true;
        this.sessionScale = res.session_scale || this.sessionScale;
      }

      this.isCalibrating = false;
      this._updateScaleLabel();

      // Cập nhật số lượng mẫu đã có trong cache
      const curCount = this.sampleCounts.get(label) || 0;
      this.sampleCounts.set(label, curCount + 1);

      // Chuyển sang từ kế tiếp
      this.refresh(true);

      // Thông báo cho app điều phối lưu tự động và đếm số mẫu
      if (typeof this.onSampleSaved === "function") {
        this.onSampleSaved(label);
      } else if (typeof window.__notifySampleTaught === "function") {
        window.__notifySampleTaught(label);
      }
    } catch (err) {
      alert("Lỗi khi lưu mẫu: " + err.message);
    } finally {
      this.dom.btnSave.disabled = false;
      this.dom.btnSave.textContent = "Lưu & tiếp theo →";
    }
  }

  // ------------------------------------------------------------ Vẽ lại UI
  async refresh(advance = false) {
    if (advance && this.queue.length > 0) {
      this.queue.shift();
    }

    this.current = this.queue.length > 0 ? this.queue[0] : null;

    // 1. Cập nhật danh sách hàng đợi bên trái
    this.dom.queueCount.textContent = String(this.queue.length);
    this.dom.queueList.innerHTML = "";

    this.queue.forEach((w, idx) => {
      const item = document.createElement("div");
      item.className = "teach-queue-item" + (idx === 0 ? " active" : "");
      item.textContent = w;
      item.addEventListener("click", () => {
        if (idx !== 0) {
          const [selected] = this.queue.splice(idx, 1);
          this.queue.unshift(selected);
          this.isCalibrating = false;
          this.refresh();
        }
      });
      this.dom.queueList.appendChild(item);
    });

    // 2. Cập nhật vùng vẽ bên phải
    if (this.current) {
      const isCalibText = this.isCalibrating ? " (từ mốc hiệu chỉnh)" : "";
      this.dom.targetWord.textContent = this.current + isCalibText;
      this.dom.btnSave.disabled = !this.canvas || !this.canvas.hasInk();
      this.dom.btnSkip.disabled = false;

      // Xác định chế độ hw3 (nếu là chữ cái đơn lẻ)
      const isLetter = this.current.length === 1 && !/\d/.test(this.current);
      if (this.canvas) {
        this.canvas.setLabel(this.current, { isHw3: isLetter });
      }

      // Lấy số mẫu đã có
      this._fetchExistingSampleCount(this.current);
    } else {
      this.dom.targetWord.textContent = "(hàng đợi trống -- thêm từ ở trên)";
      this.dom.sampleCount.textContent = "";
      this.dom.btnSave.disabled = true;
      this.dom.btnSkip.disabled = true;
      if (this.canvas) {
        this.canvas.setLabel("");
      }
    }
  }

  async _fetchExistingSampleCount(label) {
    try {
      const res = await this.worker.request("list_label_samples", { label });
      if (res && res.ok && Array.isArray(res.data)) {
        const count = res.data.length;
        this.sampleCounts.set(label, count);
        this.dom.sampleCount.textContent = count > 0 ? `(Đã có ${count} mẫu trong kho)` : "(Chưa có mẫu nào)";
      }
    } catch (_) {}
  }
}
