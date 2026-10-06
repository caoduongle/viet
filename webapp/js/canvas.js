/**
 * canvas.js -- Xử lý vùng vẽ chữ viết tay bằng Pointer Events trên Web Client.
 *
 * Tuân thủ T055 & T056:
 *   - Nhận đặc tả hình học từ BrowserBridge (get_canvas_spec), không hard-code.
 *   - Hỗ trợ Pointer Events: chuột, bút cảm ứng (pen), chạm (touch).
 *   - touch-action: none, getCoalescedEvents để thu thập toạ độ mượt nhất.
 *   - Từ chối lòng bàn tay cơ bản (palm rejection: kích thước tiếp xúc lớn, đa điểm).
 *   - Toạ độ logic chuẩn (760 x 230), tự co giãn theo tỷ lệ Retina (devicePixelRatio).
 *   - Lọc khoảng cách tối thiểu giữa 2 điểm liên tiếp (min_point_dist = 2.5 px).
 *   - Bỏ áp lực (chỉ lưu toạ độ toạ độ logic (x, y) phẳng).
 *   - Dựng các đường dóng có nhãn: baseline, xh, 4 dòng hw3.
 *   - Hiển thị chữ mẫu mờ tham chiếu (ghost letter) bật/tắt được.
 */

export class TeachCanvas {
  constructor(canvasElement, options = {}) {
    this.canvas = canvasElement;
    this.ctx = this.canvas.getContext("2d");
    this.options = options;

    // Thông số mặc định (sẽ cập nhật từ bridge qua setSpec)
    this.spec = {
      width: 760,
      height: 230,
      base_px: 170,
      zoom: 10.0,
      min_point_dist: 2.5,
      xh: 7.94,
      guidelines: {
        baseline: 170.0,
        xh_line: 90.6,
        hw3_lines: {
          top: 30.0,
          mean: 90.6,
          base: 170.0,
          bottom: 210.0,
        },
      },
    };

    this.strokes = []; // Các nét đã vẽ: list[list<[x, y]>]
    this.redoStack = []; // Stack phục vụ Redo
    this.currentStroke = null; // Nét đang vẽ dở
    this.activePointerId = null; // ID của con trỏ đang tương tác

    // Tuỳ chọn vẽ
    this.tool = "pen"; // "pen" hoặc "eraser"
    this.penWidth = 2.5; // Độ dày nét hiển thị
    this.eraserRadius = 15; // Bán kính tẩy
    this.showGhost = true; // Bật/tắt chữ mẫu mờ
    this.currentLabel = ""; // Nhãn đang dạy
    this.isHw3Mode = false; // Chế độ 4 đường dóng hw3

    this.onChange = options.onChange || null;

    this._bindEvents();
    if (typeof window !== "undefined") {
      window.addEventListener("themechange", () => this.redraw());
    }
    this.resize();
  }

  setSpec(spec) {
    if (!spec) return;
    this.spec = { ...this.spec, ...spec };
    this.redraw();
  }

  setLabel(label, { isHw3 = false } = {}) {
    this.currentLabel = label || "";
    this.isHw3Mode = Boolean(isHw3);
    this.clear();
  }

  setTool(tool) {
    this.tool = tool === "eraser" ? "eraser" : "pen";
    this.canvas.style.cursor = this.tool === "eraser" ? "cell" : "crosshair";
  }

  setPenWidth(width) {
    this.penWidth = Math.max(1, Math.min(8, width || 2.5));
    this.redraw();
  }

  toggleGhost(show) {
    this.showGhost = show !== undefined ? Boolean(show) : !this.showGhost;
    this.redraw();
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const w = this.spec.width;
    const h = this.spec.height;

    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);

    this.ctx.resetTransform();
    this.ctx.scale(dpr, dpr);
    this.redraw();
  }

  _bindEvents() {
    this.canvas.style.touchAction = "none";

    this.canvas.addEventListener("pointerdown", (e) => this._onPointerDown(e));
    this.canvas.addEventListener("pointermove", (e) => this._onPointerMove(e));
    this.canvas.addEventListener("pointerup", (e) => this._onPointerUp(e));
    this.canvas.addEventListener("pointercancel", (e) => this._onPointerCancel(e));
    this.canvas.addEventListener("contextmenu", (e) => e.preventDefault());

    window.addEventListener("resize", () => this.resize());
  }

  _getLogicalCoords(e) {
    const rect = this.canvas.getBoundingClientRect();
    const scaleX = this.spec.width / rect.width;
    const scaleY = this.spec.height / rect.height;
    return [
      (e.clientX - rect.left) * scaleX,
      (e.clientY - rect.top) * scaleY,
    ];
  }

  _isPalm(e) {
    // 1. Diện tích tiếp xúc kiểu cảm ứng quá lớn (> 26px) -> lòng bàn tay
    if (e.pointerType === "touch") {
      if ((e.width && e.width > 26) || (e.height && e.height > 26)) {
        return true;
      }
    }
    // 2. Chạm đa điểm phụ khi bắt đầu nét (chỉ kiểm tra khi chưa có con trỏ tích cực)
    if (e.isPrimary === false && this.activePointerId === null) {
      return true;
    }
    return false;
  }

  _onPointerDown(e) {
    if (this._isPalm(e)) return;
    if (e.button !== 0 && e.button !== -1 && e.button !== undefined) return; // Chỉ nhận chuột trái / bút

    this.activePointerId = e.pointerId;
    try {
      this.canvas.setPointerCapture(e.pointerId);
    } catch (_) {}

    const pt = this._getLogicalCoords(e);

    if (this.tool === "eraser") {
      this._eraseAt(pt);
      return;
    }

    this.currentStroke = [pt];
    this.redoStack = []; // Xoá redo stack khi có nét mới
    this.redraw();
  }

  _onPointerMove(e) {
    if (this.activePointerId !== e.pointerId) return;

    // Thu thập các sự kiện coalesced nếu trình duyệt hỗ trợ
    let events = [e];
    if (typeof e.getCoalescedEvents === "function") {
      const ce = e.getCoalescedEvents();
      if (ce && ce.length > 0) {
        events = ce;
      }
    }

    for (const ev of events) {
      if (this._isPalm(ev)) continue;
      const pt = this._getLogicalCoords(ev);

      if (this.tool === "eraser") {
        this._eraseAt(pt);
        continue;
      }

      if (!this.currentStroke) {
        this.currentStroke = [pt];
        continue;
      }

      const lastPt = this.currentStroke[this.currentStroke.length - 1];
      const distSq = (pt[0] - lastPt[0]) ** 2 + (pt[1] - lastPt[1]) ** 2;
      const minDist = this.spec.min_point_dist || 2.5;

      // Lọc điểm quá gần nhau
      if (distSq >= minDist * minDist) {
        this.currentStroke.push(pt);
      }
    }

    this.redraw();
  }

  _onPointerUp(e) {
    if (this.activePointerId !== e.pointerId) return;

    if (this.currentStroke && this.currentStroke.length >= 2) {
      this.strokes.push(this.currentStroke);
      if (typeof this.onChange === "function") {
        this.onChange(this.strokes.length);
      }
    }

    this.currentStroke = null;
    this.activePointerId = null;
    try {
      this.canvas.releasePointerCapture(e.pointerId);
    } catch (_) {}

    this.redraw();
  }

  _onPointerCancel(e) {
    if (this.activePointerId === e.pointerId) {
      this.currentStroke = null;
      this.activePointerId = null;
      this.redraw();
    }
  }

  _eraseAt(pt) {
    const rSq = this.eraserRadius * this.eraserRadius;
    const initialLen = this.strokes.length;

    // Lọc bỏ nét chạm vào vùng tẩy
    this.strokes = this.strokes.filter((st) => {
      for (const [x, y] of st) {
        if ((x - pt[0]) ** 2 + (y - pt[1]) ** 2 <= rSq) {
          return false;
        }
      }
      return true;
    });

    if (this.strokes.length !== initialLen) {
      if (typeof this.onChange === "function") {
        this.onChange(this.strokes.length);
      }
      this.redraw();
    }
  }

  undo() {
    if (this.strokes.length > 0) {
      this.redoStack.push(this.strokes.pop());
      if (typeof this.onChange === "function") {
        this.onChange(this.strokes.length);
      }
      this.redraw();
    }
  }

  redo() {
    if (this.redoStack.length > 0) {
      this.strokes.push(this.redoStack.pop());
      if (typeof this.onChange === "function") {
        this.onChange(this.strokes.length);
      }
      this.redraw();
    }
  }

  clear() {
    this.strokes = [];
    this.redoStack = [];
    this.currentStroke = null;
    if (typeof this.onChange === "function") {
      this.onChange(0);
    }
    this.redraw();
  }

  hasInk() {
    return this.strokes.length > 0;
  }

  getPixelStrokes() {
    // Trả về bản sao các nét vẽ logic [[ [x, y], ... ]]
    return this.strokes.map((st) => st.map(([x, y]) => [round2(x), round2(y)]));
  }

  toBankStrokes(scale = 1.0) {
    if (this.strokes.length === 0) {
      throw new Error("Chưa có nét nào để quy đổi.");
    }

    const zoom = this.spec.zoom || 10.0;
    const basePx = this.spec.base_px || 170.0;

    let minX = Infinity;
    let maxX = -Infinity;

    for (const st of this.strokes) {
      for (const [x] of st) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
      }
    }

    const rel = [];
    for (const st of this.strokes) {
      const flat = [];
      for (const [x, y] of st) {
        flat.push(round2(((x - minX) / zoom) * scale));
        flat.push(round2(((y - basePx) / zoom) * scale));
      }
      rel.push(flat);
    }

    const width = round2(((maxX - minX) / zoom) * scale);
    return { rel, width };
  }

  redraw() {
    const ctx = this.ctx;
    const w = this.spec.width;
    const h = this.spec.height;

    ctx.clearRect(0, 0, w, h);

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";

    // 1. Vẽ đường dóng chuẩn
    this._drawGuides(ctx, w, h, isDark);

    // 2. Vẽ chữ mẫu mờ (Ghost sample)
    if (this.showGhost && this.currentLabel) {
      this._drawGhost(ctx, w, isDark);
    }

    // 3. Vẽ các nét chữ đã xác nhận
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = isDark ? "#f8fafc" : "#111827"; // Nét mực tương phản cao theo theme
    ctx.lineWidth = this.penWidth;

    for (const st of this.strokes) {
      this._renderStroke(ctx, st);
    }

    // 4. Vẽ nét đang viết dở
    if (this.currentStroke && this.currentStroke.length > 0) {
      ctx.strokeStyle = isDark ? "#60a5fa" : "#2563eb"; // Nét đang viết hiện xanh dương nhạt phản hồi tức thì
      this._renderStroke(ctx, this.currentStroke);
    }
  }

  _drawGuides(ctx, w, h, isDark = false) {
    const gl = this.spec.guidelines || {};
    const base = gl.baseline || 170.0;
    const xhLine = gl.xh_line || 90.6;
    const hw3 = gl.hw3_lines || {};

    const guideBase = isDark ? "#64748b" : "#94a3b8";
    const guideSub = isDark ? "#475569" : "#cbd5e1";
    const guideDashed = isDark ? "#334155" : "#e2e8f0";
    const guideText = isDark ? "#94a3b8" : "#94a3b8";

    ctx.save();

    if (this.isHw3Mode) {
      // 4 dòng chuẩn hw3
      // Top (Ascender)
      ctx.beginPath();
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = guideDashed;
      ctx.lineWidth = 1;
      ctx.moveTo(15, hw3.top || 30.0);
      ctx.lineTo(w - 15, hw3.top || 30.0);
      ctx.stroke();

      // Mean (x-height)
      ctx.beginPath();
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = guideSub;
      ctx.lineWidth = 1;
      ctx.moveTo(15, hw3.mean || xhLine);
      ctx.lineTo(w - 15, hw3.mean || xhLine);
      ctx.stroke();

      // Base (Chân chữ - đậm)
      ctx.beginPath();
      ctx.setLineDash([]);
      ctx.strokeStyle = guideBase;
      ctx.lineWidth = 1.5;
      ctx.moveTo(15, hw3.base || base);
      ctx.lineTo(w - 15, hw3.base || base);
      ctx.stroke();

      // Bottom (Descender)
      ctx.beginPath();
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = guideDashed;
      ctx.lineWidth = 1;
      ctx.moveTo(15, hw3.bottom || 210.0);
      ctx.lineTo(w - 15, hw3.bottom || 210.0);
      ctx.stroke();

      // Nhãn chú thích bên lề
      ctx.font = "9px sans-serif";
      ctx.fillStyle = guideText;
      ctx.fillText("Ascender", 18, (hw3.top || 30.0) - 4);
      ctx.fillText("x-height", 18, (hw3.mean || xhLine) - 4);
      ctx.fillText("Baseline", 18, (hw3.base || base) + 12);
      ctx.fillText("Descender", 18, (hw3.bottom || 210.0) + 12);
    } else {
      // Chế độ dạy từ thông thường: Dòng chân chữ + vạch mốc chiều cao
      ctx.beginPath();
      ctx.setLineDash([]);
      ctx.strokeStyle = guideSub;
      ctx.lineWidth = 1.25;
      ctx.moveTo(15, base);
      ctx.lineTo(w - 15, base);
      ctx.stroke();

      // Vạch x-height bên trái
      ctx.beginPath();
      ctx.setLineDash([4, 3]);
      ctx.strokeStyle = guideBase;
      ctx.lineWidth = 1;
      ctx.moveTo(15, xhLine);
      ctx.lineTo(160, xhLine);
      ctx.stroke();

      // Nhãn chú thích
      ctx.font = "10px sans-serif";
      ctx.fillStyle = guideText;
      ctx.fillText("Chân chữ (baseline)", 170, base + 12);
      ctx.fillText("Độ cao chữ thường (~8pt)", 15, xhLine - 5);
    }

    ctx.restore();
  }

  _drawGhost(ctx, w, isDark = false) {
    ctx.save();
    ctx.font = "72px 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
    ctx.fillStyle = isDark ? "rgba(148, 163, 184, 0.18)" : "rgba(100, 116, 139, 0.12)";
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";

    const base = this.spec.guidelines ? this.spec.guidelines.baseline : 170.0;
    ctx.fillText(this.currentLabel, w / 2, base);
    ctx.restore();
  }

  _renderStroke(ctx, points) {
    if (!points || points.length === 0) return;
    if (points.length === 1) {
      ctx.beginPath();
      ctx.arc(points[0][0], points[0][1], this.penWidth / 2, 0, Math.PI * 2);
      ctx.fill();
      return;
    }

    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);

    if (points.length === 2) {
      ctx.lineTo(points[1][0], points[1][1]);
    } else {
      for (let i = 1; i < points.length - 1; i++) {
        const xc = (points[i][0] + points[i + 1][0]) / 2;
        const yc = (points[i][1] + points[i + 1][1]) / 2;
        ctx.quadraticCurveTo(points[i][0], points[i][1], xc, yc);
      }
      const last = points[points.length - 1];
      ctx.lineTo(last[0], last[1]);
    }
    ctx.stroke();
  }
}

function round2(v) {
  return Math.round(v * 100) / 100;
}
