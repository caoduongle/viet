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

function parseBackgroundNode(bgNode) {
  if (!bgNode) {
    return { type: "solid", color: "#ffffffff", style: "plain", spacing: 24.0, margin: 72.0 };
  }
  const type = bgNode.getAttribute("type") || "solid";
  const color = bgNode.getAttribute("color") || "#ffffffff";
  const style = bgNode.getAttribute("style") || "plain";
  const config = bgNode.getAttribute("config") || "";

  let spacing = 24.0;
  let margin = 72.0;

  if (config) {
    const parts = config.split(",");
    for (const part of parts) {
      const [k, v] = part.split("=");
      if (k === "r1") spacing = parseFloat(v);
      if (k === "m1") margin = parseFloat(v);
    }
  }

  return { type, color, style, spacing, margin };
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
      if (styleM) bg.style = styleM[1];
      if (configM) {
        const parts = configM[1].split(",");
        for (const p of parts) {
          const [k, v] = p.split("=");
          if (k === "r1") bg.spacing = parseFloat(v);
          if (k === "m1") bg.margin = parseFloat(v);
        }
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

function parseHexColor(hex8) {
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

  const spacing = background.spacing || 24.0;
  const margin = background.margin || 72.0;
  const style = background.style || "plain";

  if (style === "lined" || style === "ruled") {
    for (let y = spacing; y < height; y += spacing) {
      lines.push(`  <line class="paper-bg-line" x1="0" y1="${y}" x2="${width}" y2="${y}" stroke="#cfd8dc" stroke-width="0.5"/>`);
    }
    if (style === "ruled") {
      lines.push(`  <line class="paper-bg-margin" x1="${margin}" y1="0" x2="${margin}" y2="${height}" stroke="#ff8a80" stroke-width="1"/>`);
    }
  } else if (style === "graph") {
    for (let y = spacing; y < height; y += spacing) {
      lines.push(`  <line class="paper-bg-line" x1="0" y1="${y}" x2="${width}" y2="${y}" stroke="#e0e0e0" stroke-width="0.5"/>`);
    }
    for (let x = spacing; x < width; x += spacing) {
      lines.push(`  <line class="paper-bg-line" x1="${x}" y1="0" x2="${x}" y2="${height}" stroke="#e0e0e0" stroke-width="0.5"/>`);
    }
  } else if (style === "dotted") {
    for (let y = spacing; y < height; y += spacing) {
      for (let x = spacing; x < width; x += spacing) {
        lines.push(`  <circle class="paper-bg-dot" cx="${x}" cy="${y}" r="0.75" fill="#b0bec5"/>`);
      }
    }
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

  // Kẻ nền
  const spacing = background.spacing || 24.0;
  const margin = background.margin || 72.0;
  const style = background.style || "plain";

  if (style === "lined" || style === "ruled") {
    for (let y = spacing; y < height; y += spacing) {
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("x1", "0");
      line.setAttribute("y1", String(y));
      line.setAttribute("x2", String(width));
      line.setAttribute("y2", String(y));
      line.setAttribute("stroke", "#cfd8dc");
      line.setAttribute("stroke-width", "0.5");
      svg.appendChild(line);
    }
    if (style === "ruled") {
      const mLine = document.createElementNS(SVG_NS, "line");
      mLine.setAttribute("x1", String(margin));
      mLine.setAttribute("y1", "0");
      mLine.setAttribute("x2", String(margin));
      mLine.setAttribute("y2", String(height));
      mLine.setAttribute("stroke", "#ff8a80");
      mLine.setAttribute("stroke-width", "1");
      svg.appendChild(mLine);
    }
  } else if (style === "graph") {
    for (let y = spacing; y < height; y += spacing) {
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("x1", "0");
      line.setAttribute("y1", String(y));
      line.setAttribute("x2", String(width));
      line.setAttribute("y2", String(y));
      line.setAttribute("stroke", "#e0e0e0");
      line.setAttribute("stroke-width", "0.5");
      svg.appendChild(line);
    }
    for (let x = spacing; x < width; x += spacing) {
      const line = document.createElementNS(SVG_NS, "line");
      line.setAttribute("x1", String(x));
      line.setAttribute("y1", "0");
      line.setAttribute("x2", String(x));
      line.setAttribute("y2", String(height));
      line.setAttribute("stroke", "#e0e0e0");
      line.setAttribute("stroke-width", "0.5");
      svg.appendChild(line);
    }
  } else if (style === "dotted") {
    for (let y = spacing; y < height; y += spacing) {
      for (let x = spacing; x < width; x += spacing) {
        const dot = document.createElementNS(SVG_NS, "circle");
        dot.setAttribute("cx", String(x));
        dot.setAttribute("cy", String(y));
        dot.setAttribute("r", "0.75");
        dot.setAttribute("fill", "#b0bec5");
        svg.appendChild(dot);
      }
    }
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
