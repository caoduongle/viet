/**
 * html-utils.js -- Module tiện ích xử lý và thoát mã chuỗi HTML an toàn cho Web Client.
 *
 * Chống lỗ hổng XSS (Cross-Site Scripting) và bảo vệ cấu trúc DOM khi nội suy
 * các nhãn ký tự toán học (<, >, &), dữ liệu người dùng hoặc thông báo lỗi từ Worker.
 */

/**
 * Mã hóa an toàn chuỗi văn bản thuần thành thực thể HTML (HTML Entities).
 * @param {any} str - Chuỗi cần mã hóa (nếu null/undefined trả về chuỗi rỗng)
 * @returns {string} - Chuỗi an toàn để nội suy vào innerHTML hoặc thuộc tính DOM
 */
export function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
