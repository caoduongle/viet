/**
 * paper.js -- Module dựng SVG an toàn từ tài liệu Xournal++ (.xopp XML).
 *
 * Tính năng:
 *   - Giải nén gzip bằng DecompressionStream (Web Standard).
 *   - Phân tích XML bằng DOMParser.
 *   - Dựng SVG an toàn qua createElementNS, tránh chớp trắng khi đổi trang.
 *   - Hỗ trợ đầy đủ các kiểu nền giấy: plain, lined, ruled, graph, dotted.
 *   - Vẽ đường gạch chân màu đỏ cho các từ thiếu mẫu (D2).
 */

const SVG_NS = "http://www.w3.org/2000/svg";

/** Hệ số quy đổi PostScript point (pt) sang CSS pixel (px): 1 pt = 96/72 px = 4/3 px */
export const PT_TO_PX = 96 / 72;

/**
 * Tính toán kích thước pixel hiển thị chuẩn theo khổ trang (pt) và hệ số zoom.
 * @param {number} widthPt - Chiều rộng khổ giấy theo pt
 * @param {number} heightPt - Chiều cao khổ giấy theo pt
 * @param {number} zoom - Hệ số thu phóng (mặc định 1.0)
 * @returns {{ widthPx: number, heightPx: number }}
 */
export function getPaperPixelDimensions(widthPt, heightPt, zoom = 1.0) {
  return {
    widthPx: Math.round(widthPt * PT_TO_PX * zoom),
    heightPx: Math.round(heightPt * PT_TO_PX * zoom),
  };
}

/**
 * Giải nén chuỗi base64 của file .xopp thành chuỗi XML.
 * @param {string} base64Str
 * @returns {Promise<string>}
 */
export async function decompressXoppBase64(base64Str) {
  const binaryString = atob(base64Str);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  if (typeof DecompressionStream !== "undefined") {
    const ds = new DecompressionStream("gzip");
    const writer = ds.writable.getWriter();
    writer.write(bytes);
    writer.close();
    const response = new Response(ds.readable);
    return await response.text();
  }

  // Dự phòng cho môi trường Node test nếu cần
  const zlib = await import("node:zlib");
  return zlib.gunzipSync(bytes).toString("utf-8");
}

/**
 * Phân tích cấu trúc XML XOPP thành đối tượng JS.
 * @param {string} xmlText
 * @returns {{ creator: string, pages: Array<any> }}
 */
export function parseXoppXml(xmlText) {
  // 1. Phân tích qua DOMParser nếu có
  if (typeof DOMParser !== "undefined") {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlText, "application/xml");
    const parserError = xmlDoc.querySelector("parsererror");
    if (parserError) {
      throw new Error(`Lỗi cú pháp XML XOPP: ${parserError.textContent}`);
    }

    const pages = [];
    const pageNodes = xmlDoc.querySelectorAll("page");
    pageNodes.forEach((pNode, pIndex) => {
      const width = parseFloat(pNode.getAttribute("width") || "595.28");
      const height = parseFloat(pNode.getAttribute("height") || "841.89");

      const bgNode = pNode.querySelector("background");
      const bg = parseBackgroundNode(bgNode);

      const strokes = [];
      const strokeNodes = pNode.querySelectorAll("stroke");
      strokeNodes.forEach((sNode) => {
        const tool = sNode.getAttribute("tool") || "pen";
        const color = sNode.getAttribute("color") || "#000000ff";
        const width = parseFloat(sNode.getAttribute("width") || "1.41");
        const capStyle = sNode.getAttribute("capStyle") || "round";
        const textContent = sNode.textContent.trim();
        const rawCoords = textContent.split(/\s+/).map(Number);

        const points = [];
        for (let i = 0; i < rawCoords.length; i += 2) {
          if (!isNaN(rawCoords[i]) && !isNaN(rawCoords[i + 1])) {
            points.push({ x: rawCoords[i], y: rawCoords[i + 1] });
          }
        }

        if (points.length > 0) {
          strokes.push({ tool, color, width, capStyle, points });
        }
      });

      pages.push({ index: pIndex, width, height, background: bg, strokes });
    });

    return { creator: "hw_note", pages };
  }

  // 2. Parser Regex dự phòng cho môi trường Node không có DOMParser
  return parseXoppXmlRegex(xmlText);
}

function parseConfigString(config, bg) {
  const parts = config.split(/[,;]/);
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx === -1) continue;
    const k = trimmed.slice(0, eqIdx).trim();
    const v = trimmed.slice(eqIdx + 1).trim();
    if (k === "r1") bg.spacing = parseFloat(v);
    else if (k === "m1") bg.margin = parseFloat(v);
    else if (k === "lw") bg.lineWidth = parseFloat(v);
    else if (k === "f1") bg.primaryColor = v;
    else if (k === "f2") bg.secondaryColor = v;
    else if (k === "af1") bg.attachmentPrimaryColor = v;
    else if (k === "af2") bg.attachmentSecondaryColor = v;
    else if (k === "rm") bg.roundMargin = v === "1" || v === "true";
    else if (k === "bli") bg.boldLineInterval = parseInt(v, 10);
    else if (k === "blw") bg.boldLineWidth = parseFloat(v);
  }
}

export function parseBackgroundNode(bgNode) {
  if (!bgNode) {
    return { type: "solid", color: "#ffffffff", style: "plain", spacing: 24.0, margin: 72.0 };
  }
  const type = bgNode.getAttribute("type") || "solid";
  const color = bgNode.getAttribute("color") || "#ffffffff";
  let style = (bgNode.getAttribute("style") || "plain").trim().toLowerCase();
  const config = bgNode.getAttribute("config") || "";

  if (style === "music") style = "staves";
  if (style === "isograph") style = "iso_graph";
  if (style === "isodotted") style = "iso_dotted";

  const bg = { type, color, style, spacing: 24.0, margin: 72.0 };
  if (config) {
    parseConfigString(config, bg);
  }
  return bg;
}

function parseXoppXmlRegex(xmlText) {
  const pages = [];
  const pageRegex = /<page\s+width="([\d.]+)"\s+height="([\d.]+)">([\s\S]*?)<\/page>/g;
  let pageMatch;
  let pIndex = 0;

  while ((pageMatch = pageRegex.exec(xmlText)) !== null) {
    const width = parseFloat(pageMatch[1]);
    const height = parseFloat(pageMatch[2]);
    const pageContent = pageMatch[3];

    // Background
    const bgMatch = /<background\s+([^>]+)\/>/.exec(pageContent);
    let bg = { type: "solid", color: "#ffffffff", style: "plain", spacing: 24.0, margin: 72.0 };
    if (bgMatch) {
      const attrs = bgMatch[1];
      const colorM = /color="([^"]+)"/.exec(attrs);
      const styleM = /style="([^"]+)"/.exec(attrs);
      const configM = /config="([^"]+)"/.exec(attrs);
      if (colorM) bg.color = colorM[1];
      if (styleM) {
        let st = styleM[1].trim().toLowerCase();
        if (st === "music") st = "staves";
        if (st === "isograph") st = "iso_graph";
        if (st === "isodotted") st = "iso_dotted";
        bg.style = st;
      }
      if (configM) {
        parseConfigString(configM[1], bg);
      }
    }

    // Strokes
    const strokes = [];
    const strokeRegex = /<stroke\s+tool="([^"]+)"\s+color="([^"]+)"\s+capStyle="([^"]+)"\s+width="([\d.]+)">([\s\S]*?)<\/stroke>/g;
    let sMatch;
    while ((sMatch = strokeRegex.exec(pageContent)) !== null) {
      const tool = sMatch[1];
      const color = sMatch[2];
      const capStyle = sMatch[3];
      const width = parseFloat(sMatch[4]);
      const rawCoords = sMatch[5].trim().split(/\s+/).map(Number);
      const points = [];
      for (let i = 0; i < rawCoords.length; i += 2) {
        if (!isNaN(rawCoords[i]) && !isNaN(rawCoords[i + 1])) {
          points.push({ x: rawCoords[i], y: rawCoords[i + 1] });
        }
      }
      if (points.length > 0) {
        strokes.push({ tool, color, width, capStyle, points });
      }
    }

    pages.push({ index: pIndex++, width, height, background: bg, strokes });
  }

  return { creator: "hw_note", pages };
}

export function parseHexColor(hex8) {
  let hex = (hex8 || "#000000ff").trim().toLowerCase();
  if (hex.startsWith("#")) hex = hex.slice(1);
  if (hex.length === 6) {
    return { color: `#${hex}`, opacity: 1.0 };
  }
  if (hex.length === 8) {
    const rgb = hex.slice(0, 6);
    const alpha = parseInt(hex.slice(6, 8), 16) / 255;
    return { color: `#${rgb}`, opacity: Number(alpha.toFixed(3)) };
  }
  return { color: "#000000", opacity: 1.0 };
}

export function getPaperContrastColors(bg) {
  const bgParsed = parseHexColor(bg.color || "#ffffffff");
  const hex = bgParsed.color.replace("#", "");
  const r = parseInt(hex.substring(0, 2), 16) / 255;
  const g = parseInt(hex.substring(2, 4), 16) / 255;
  const b = parseInt(hex.substring(4, 6), 16) / 255;
  const lum = 0.299 * r + 0.587 * g + 0.114 * b;
  const isDark = lum < 0.5;

  const f1 = bg.primaryColor ? (bg.primaryColor.startsWith("#") ? bg.primaryColor : "#" + bg.primaryColor) : null;
  const f2 = bg.secondaryColor ? (bg.secondaryColor.startsWith("#") ? bg.secondaryColor : "#" + bg.secondaryColor) : null;

  return {
    isDark,
    bgParsed,
    strokeRuled: f1 || (isDark ? "#434343" : "#40a0ff"),
    strokeMargin: f2 || (isDark ? "#220080" : "#ff0080"),
    strokeGraph: f1 || (isDark ? "#434343" : "#bdbdbd"),
    strokeStaves: f1 || (isDark ? "#ffffff" : "#000000"),
  };
}

export function getBackgroundDrawingElements(bg, width, height) {
  const elements = [];
  const style = (bg.style || "plain").toLowerCase();
  if (style === "plain" || style === "solid") {
    return elements;
  }

  const { strokeRuled, strokeMargin, strokeGraph, strokeStaves } = getPaperContrastColors(bg);
  const lw = bg.lineWidth !== undefined ? bg.lineWidth : 0.5;

  if (style === "ruled" || style === "lined") {
    const r1 = bg.spacing || 24.0;
    if (height >= 140.0) {
      for (let y = 80.0; y <= height - 60.0 + 1e-4; y += r1) {
        elements.push({
          tag: "line",
          attrs: {
            class: "paper-bg-line",
            x1: "0",
            y1: String(y),
            x2: String(width),
            y2: String(y),
            stroke: strokeRuled,
            "stroke-width": String(lw),
          },
        });
      }
    }
    if (style === "lined") {
      const m1 = bg.margin !== undefined ? bg.margin : 72.0;
      const marginX = m1 >= 0 ? m1 : width + m1;
      elements.push({
        tag: "line",
        attrs: {
          class: "paper-bg-margin",
          x1: String(marginX),
          y1: "0",
          x2: String(marginX),
          y2: String(height),
          stroke: strokeMargin,
          "stroke-width": String(lw),
        },
      });
    }
  } else if (style === "graph") {
    const r1 = bg.spacing || 14.1732;
    const bli = bg.boldLineInterval || 0;
    const blw = bg.boldLineWidth !== undefined ? bg.boldLineWidth : 1.5;
    let xMargin = 0;
    let yMargin = 0;
    if (bg.margin && bg.margin > 0) {
      xMargin = bg.roundMargin ? Math.round(bg.margin / r1) * r1 : bg.margin;
      yMargin = xMargin;
    }
    for (let idx = 0, y = yMargin; y <= height - yMargin + 1e-4; idx++, y += r1) {
      const isBold = bli > 0 && (idx % bli === 0);
      elements.push({
        tag: "line",
        attrs: {
          class: "paper-bg-line",
          x1: String(xMargin),
          y1: String(y),
          x2: String(width - xMargin),
          y2: String(y),
          stroke: strokeGraph,
          "stroke-width": String(isBold ? blw : lw),
        },
      });
    }
    for (let idx = 0, x = xMargin; x <= width - xMargin + 1e-4; idx++, x += r1) {
      const isBold = bli > 0 && (idx % bli === 0);
      elements.push({
        tag: "line",
        attrs: {
          class: "paper-bg-line",
          x1: String(x),
          y1: String(yMargin),
          x2: String(x),
          y2: String(height - yMargin),
          stroke: strokeGraph,
          "stroke-width": String(isBold ? blw : lw),
        },
      });
    }
  } else if (style === "dotted") {
    const r1 = bg.spacing || 14.1732;
    for (let y = r1; y < height; y += r1) {
      for (let x = r1; x < width; x += r1) {
        elements.push({
          tag: "circle",
          attrs: {
            class: "paper-bg-dot",
            cx: String(x),
            cy: String(y),
            r: "0.75",
            fill: strokeGraph,
          },
        });
      }
    }
  } else if (style === "iso_dotted" || style === "isodotted") {
    const r1 = bg.spacing || 14.1732;
    const xstep = (Math.sqrt(3.0) / 2.0) * r1;
    const ystep = r1 / 2.0;
    const margin = r1;
    const cols = Math.floor((width - 2 * margin) / xstep);
    const rows = Math.floor((height - 2 * margin) / ystep);
    const offsetX = (width - cols * xstep) / 2;
    const offsetY = (height - rows * ystep) / 2;

    for (let col = 0; col <= cols; ++col) {
      const x = offsetX + col * xstep;
      const evenCol = col % 2 === 0;
      const yoffset = evenCol ? ystep : 0.0;
      const rowsInCol = evenCol ? rows - 2 : rows;

      for (let row = 0; row <= rowsInCol; row += 2) {
        const y = offsetY + yoffset + row * ystep;
        elements.push({
          tag: "circle",
          attrs: {
            class: "paper-bg-dot",
            cx: String(x),
            cy: String(y),
            r: "0.75",
            fill: strokeGraph,
          },
        });
      }
    }
  } else if (style === "iso_graph" || style === "isograph") {
    const r1 = bg.spacing || 14.1732;
    const isoLw = bg.lineWidth !== undefined ? bg.lineWidth : 1.0;
    const xstep = (Math.sqrt(3.0) / 2.0) * r1;
    const ystep = r1 / 2.0;
    const margin = r1;
    const cols = Math.floor((width - 2 * margin) / xstep);
    const rows = Math.floor((height - 2 * margin) / ystep);
    const contentWidth = cols * xstep;
    const contentHeight = rows * ystep;
    const offsetX = (width - contentWidth) / 2;
    const offsetY = (height - contentHeight) / 2;

    const addIsoLine = (x1, y1, x2, y2) => {
      elements.push({
        tag: "line",
        attrs: {
          class: "paper-bg-line",
          x1: String(offsetX + x1),
          y1: String(offsetY + y1),
          x2: String(offsetX + x2),
          y2: String(offsetY + y2),
          stroke: strokeGraph,
          "stroke-width": String(isoLw),
        },
      });
    };

    addIsoLine(0.0, 0.0, contentWidth, 0.0);
    addIsoLine(0.0, contentHeight, contentWidth, contentHeight);

    for (let col = 0; col <= cols; ++col) {
      const x = col * xstep;
      addIsoLine(x, 0.0, x, contentHeight);
    }

    const hdiags = Math.floor(cols / 2);
    const vdiags = Math.floor(rows / 2);
    const diags = hdiags + vdiags;
    const hcorr = cols - 2 * hdiags;
    const vcorr = rows - 2 * vdiags;

    for (let d = 0; d < diags + hcorr * vcorr; ++d) {
      let x1 = contentWidth, y1 = 0.0;
      if (d < hdiags) {
        x1 = xstep + d * 2 * xstep;
      } else {
        y1 = ystep + (d - hdiags) * 2 * ystep - hcorr * ystep;
      }
      let x2 = 0.0, y2 = contentHeight;
      if (d < vdiags) {
        y2 = ystep + d * 2 * ystep;
      } else {
        x2 = xstep + (d - vdiags) * 2 * xstep - vcorr * xstep;
      }
      addIsoLine(x1, y1, x2, y2);
    }

    for (let d = 0; d < diags; ++d) {
      let x1 = 0.0, y1 = 0.0;
      if (d < hdiags) {
        x1 = contentWidth - (xstep + d * 2 * xstep) - hcorr * xstep;
      } else {
        y1 = ystep + (d - hdiags) * 2 * ystep;
      }
      let x2 = contentWidth, y2 = contentHeight;
      if (d < vdiags) {
        y2 = ystep + d * 2 * ystep + hcorr * ystep;
      } else {
        x2 = contentWidth - (xstep + (d - vdiags) * 2 * xstep) + (vcorr - hcorr) * xstep;
      }
      addIsoLine(x1, y1, x2, y2);
    }
  } else if (style === "staves") {
    if (height >= 140.0) {
      for (let staffY = 80.0; staffY + 20.0 <= height - 60.0 + 1e-4; staffY += 62.5) {
        for (let k = 0; k < 5; k++) {
          const y = staffY + k * 5.0;
          elements.push({
            tag: "line",
            attrs: {
              class: "paper-bg-line",
              x1: "50",
              y1: String(y),
              x2: String(width - 50),
              y2: String(y),
              stroke: strokeStaves,
              "stroke-width": String(lw),
            },
          });
        }
        elements.push({
          tag: "line",
          attrs: {
            class: "paper-bg-line",
            x1: "50",
            y1: String(staffY),
            x2: "50",
            y2: String(staffY + 20.0),
            stroke: strokeStaves,
            "stroke-width": String(lw),
          },
        });
        elements.push({
          tag: "line",
          attrs: {
            class: "paper-bg-line",
            x1: String(width - 50),
            y1: String(staffY),
            x2: String(width - 50),
            y2: String(staffY + 20.0),
            stroke: strokeStaves,
            "stroke-width": String(lw),
          },
        });
      }
    }
  }
  return elements;
}

/**
 * Sinh chuỗi SVG hoàn chỉnh cho 1 trang (hỗ trợ cả Node.js và export SVG).
 */
export function renderPageSvgString(pageData, options = {}) {
  const { width, height, background, strokes } = pageData;
  const missingBoxes = options.missingBoxes || [];
  const lines = [];

  lines.push(`<svg viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">`);

  // 1. Nền giấy
  const bgParsed = parseHexColor(background.color || "#ffffffff");
  lines.push(`  <rect width="${width}" height="${height}" fill="${bgParsed.color}" fill-opacity="${bgParsed.opacity}"/>`);

  // Kẻ nền dùng chung
  const bgElements = getBackgroundDrawingElements(background, width, height);
  for (const el of bgElements) {
    const attrStr = Object.entries(el.attrs).map(([k, v]) => `${k}="${v}"`).join(" ");
    lines.push(`  <${el.tag} ${attrStr}/>`);
  }

  // 2. Nét bút viết tay
  for (const s of strokes) {
    const { color, opacity } = parseHexColor(s.color);
    const ptsStr = s.points.map((p) => `${p.x},${p.y}`).join(" ");
    lines.push(
      `  <polyline points="${ptsStr}" fill="none" stroke="${color}" stroke-opacity="${opacity}" stroke-width="${s.width}" stroke-linecap="round" stroke-linejoin="round"/>`
    );
  }

  // 3. Gạch đỏ từ thiếu mẫu (D2)
  for (const box of missingBoxes) {
    if (box.page === (pageData.index || 0)) {
      const yBottom = box.y + box.height;
      lines.push(
        `  <line class="missing-token-underline" x1="${box.x}" y1="${yBottom}" x2="${box.x + box.width}" y2="${yBottom}" stroke="#e53935" stroke-width="1.5" stroke-dasharray="3,2"/>`
      );
    }
  }

  lines.push("</svg>");
  return lines.join("\n");
}

/**
 * Dựng trực tiếp SVG DOM Element bằng createElementNS (cho Web UI, an toàn, không chớp trắng).
 */
export function renderPageSvgElement(pageData, options = {}) {
  const { width, height, background, strokes } = pageData;
  const missingBoxes = options.missingBoxes || [];

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", "100%");

  // Nền
  const bgParsed = parseHexColor(background.color || "#ffffffff");
  const rect = document.createElementNS(SVG_NS, "rect");
  rect.setAttribute("width", String(width));
  rect.setAttribute("height", String(height));
  rect.setAttribute("fill", bgParsed.color);
  rect.setAttribute("fill-opacity", String(bgParsed.opacity));
  svg.appendChild(rect);

  // Kẻ nền dùng chung
  const bgElements = getBackgroundDrawingElements(background, width, height);
  for (const el of bgElements) {
    const node = document.createElementNS(SVG_NS, el.tag);
    for (const [k, v] of Object.entries(el.attrs)) {
      node.setAttribute(k, v);
    }
    svg.appendChild(node);
  }

  // Nét bút
  for (const s of strokes) {
    const { color, opacity } = parseHexColor(s.color);
    const poly = document.createElementNS(SVG_NS, "polyline");
    const ptsStr = s.points.map((p) => `${p.x},${p.y}`).join(" ");
    poly.setAttribute("points", ptsStr);
    poly.setAttribute("fill", "none");
    poly.setAttribute("stroke", color);
    poly.setAttribute("stroke-opacity", String(opacity));
    poly.setAttribute("stroke-width", String(s.width));
    poly.setAttribute("stroke-linecap", "round");
    poly.setAttribute("stroke-linejoin", "round");
    svg.appendChild(poly);
  }

  // Gạch chân đỏ từ thiếu (D2)
  for (const box of missingBoxes) {
    if (box.page === (pageData.index || 0)) {
      const yBottom = box.y + box.height;
      const redLine = document.createElementNS(SVG_NS, "line");
      redLine.setAttribute("x1", String(box.x));
      redLine.setAttribute("y1", String(yBottom));
      redLine.setAttribute("x2", String(box.x + box.width));
      redLine.setAttribute("y2", String(yBottom));
      redLine.setAttribute("stroke", "#e53935");
      redLine.setAttribute("stroke-width", "1.5");
      redLine.setAttribute("stroke-dasharray", "3,2");
      svg.appendChild(redLine);
    }
  }

  return svg;
}
