/**
 * export.js -- Quản lý xuất file: .xopp, PNG/SVG (1x/2x/3x, nền giấy/trong suốt), ZIP không nén, In/PDF.
 *
 * Tiêu chí:
 *   - Không dùng thư viện ngoài (zero dependency).
 *   - Tạo file ZIP Stored (compression mode 0) tương thích 100% với unzip chuẩn.
 */

// Bảng tra cứu CRC32
const CRC32_TABLE = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  let c = i;
  for (let k = 0; k < 8; k++) {
    c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
  }
  CRC32_TABLE[i] = c >>> 0;
}

export function crc32(bytes) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) {
    crc = (crc >>> 8) ^ CRC32_TABLE[(crc ^ bytes[i]) & 0xFF];
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

/**
 * Đóng gói danh sách file thành file ZIP chuẩn (Store mode 0, không nén).
 * @param {Array<{name: string, data: Uint8Array|ArrayBuffer}>} files
 * @returns {Uint8Array}
 */
export function createZipArchive(files) {
  const encoder = new TextEncoder();
  const fileEntries = [];
  let offset = 0;

  // 1. Tính toán và tạo Local File Headers + dữ liệu
  const chunks = [];
  for (const f of files) {
    const nameBytes = encoder.encode(f.name);
    const dataBytes = f.data instanceof Uint8Array ? f.data : new Uint8Array(f.data);
    const crc = crc32(dataBytes);
    const size = dataBytes.length;

    // Local Header (30 bytes + name length)
    const localHeader = new Uint8Array(30 + nameBytes.length);
    const view = new DataView(localHeader.buffer);

    view.setUint32(0, 0x04034b50, true);  // Local file header signature
    view.setUint16(4, 10, true);          // Version needed (1.0)
    view.setUint16(6, 0, true);           // General purpose bit flag
    view.setUint16(8, 0, true);           // Compression method (0 = Stored)
    view.setUint16(10, 0, true);          // Last mod file time
    view.setUint16(12, 0, true);          // Last mod file date
    view.setUint32(14, crc, true);         // CRC-32
    view.setUint32(18, size, true);        // Compressed size
    view.setUint32(22, size, true);        // Uncompressed size
    view.setUint16(26, nameBytes.length, true); // File name length
    view.setUint16(28, 0, true);          // Extra field length
    localHeader.set(nameBytes, 30);

    chunks.push(localHeader);
    chunks.push(dataBytes);

    fileEntries.push({
      nameBytes,
      crc,
      size,
      offset,
    });

    offset += localHeader.length + dataBytes.length;
  }

  // 2. Tạo Central Directory Headers
  const centralDirStartOffset = offset;
  let centralDirSize = 0;

  for (const entry of fileEntries) {
    const cdHeader = new Uint8Array(46 + entry.nameBytes.length);
    const view = new DataView(cdHeader.buffer);

    view.setUint32(0, 0x02014b50, true);  // Central directory file header signature
    view.setUint16(4, 20, true);          // Version made by (2.0)
    view.setUint16(6, 10, true);          // Version needed to extract (1.0)
    view.setUint16(8, 0, true);           // General purpose bit flag
    view.setUint16(10, 0, true);          // Compression method (0)
    view.setUint16(12, 0, true);          // Last mod file time
    view.setUint16(14, 0, true);          // Last mod file date
    view.setUint32(16, entry.crc, true);   // CRC-32
    view.setUint32(20, entry.size, true);  // Compressed size
    view.setUint32(24, entry.size, true);  // Uncompressed size
    view.setUint16(28, entry.nameBytes.length, true); // File name length
    view.setUint16(30, 0, true);          // Extra field length
    view.setUint16(32, 0, true);          // File comment length
    view.setUint16(34, 0, true);          // Disk number start
    view.setUint16(36, 0, true);          // Internal file attributes
    view.setUint32(38, 0, true);          // External file attributes
    view.setUint32(42, entry.offset, true); // Relative offset of local header
    cdHeader.set(entry.nameBytes, 46);

    chunks.push(cdHeader);
    centralDirSize += cdHeader.length;
  }

  // 3. Tạo End of Central Directory Record (22 bytes)
  const eocd = new Uint8Array(22);
  const eocdView = new DataView(eocd.buffer);

  eocdView.setUint32(0, 0x06054b50, true); // End of central dir signature
  eocdView.setUint16(4, 0, true);          // Number of this disk
  eocdView.setUint16(6, 0, true);          // Disk where central directory starts
  eocdView.setUint16(8, fileEntries.length, true);  // Number of central directory records on this disk
  eocdView.setUint16(10, fileEntries.length, true); // Total number of central directory records
  eocdView.setUint32(12, centralDirSize, true);     // Size of central directory
  eocdView.setUint32(16, centralDirStartOffset, true); // Offset of start of central directory
  eocdView.setUint16(20, 0, true);         // Comment length

  chunks.push(eocd);

  // Gộp toàn bộ chunks thành một Uint8Array
  const totalLength = offset + centralDirSize + eocd.length;
  const result = new Uint8Array(totalLength);
  let pos = 0;
  for (const chunk of chunks) {
    result.set(chunk, pos);
    pos += chunk.length;
  }

  return result;
}

/**
 * Kích hoạt tải xuống Blob từ trình duyệt.
 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Xuất file .xopp từ chuỗi base64.
 */
export function exportXopp(base64Data, filename = "chuviet.xopp") {
  const binaryString = atob(base64Data);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: "application/x-xopp" });
  downloadBlob(blob, filename);
}

/**
 * Xuất một phần tử SVG ra file .svg.
 */
export function exportSvg(svgElement, filename = "trang.svg") {
  const serializer = new XMLSerializer();
  let source = serializer.serializeToString(svgElement);
  if (!source.match(/^<svg[^>]+xmlns="http\:\/\/www\.w3\.org\/2000\/svg"/)) {
    source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
  }
  const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
  downloadBlob(blob, filename);
}

/**
 * Chuyển SVG thành PNG qua Canvas và tải xuống.
 */
export function exportPng(svgElement, filename = "trang.png", scale = 1, transparent = false) {
  const width = parseFloat(svgElement.getAttribute("width") || "595.28") * scale;
  const height = parseFloat(svgElement.getAttribute("height") || "841.89") * scale;

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  const serializer = new XMLSerializer();
  let source = serializer.serializeToString(svgElement);
  const svgBlob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(svgBlob);

  const img = new Image();
  img.onload = () => {
    if (!transparent) {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);
    }
    ctx.drawImage(img, 0, 0, width, height);
    URL.revokeObjectURL(url);

    canvas.toBlob((blob) => {
      if (blob) downloadBlob(blob, filename);
    }, "image/png");
  };
  img.src = url;
}
