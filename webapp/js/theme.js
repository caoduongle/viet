/**
 * theme.js -- Quản lý chủ đề giao diện Sáng / Tối (Light / Dark mode).
 *
 * Hỗ trợ:
 *   - Nhận diện `prefers-color-scheme` tự động khi chưa có tùy chọn.
 *   - Lưu trữ tùy chọn vào localStorage ("chuviettay_theme").
 *   - Gắn thuộc tính data-theme="light" hoặc data-theme="dark" lên :root (document.documentElement).
 *   - Cập nhật biểu tượng nút bấm (☀️ cho theme sáng, 🌙 cho theme tối).
 *   - Phát CustomEvent "themechange" khi chuyển đổi để các module canvas (teach.js, write.js) cập nhật màu vẽ.
 */

const STORAGE_KEY = "chuviettay_theme";

export function getSavedTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") {
      return saved;
    }
  } catch (_) {}

  // Mặc định dựa trên hệ thống
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

export function applyTheme(theme) {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);

  const btn = document.getElementById("btn-theme-toggle");
  if (btn) {
    btn.textContent = theme === "dark" ? "🌙" : "☀️";
    btn.title = theme === "dark" ? "Chuyển sang giao diện Sáng" : "Chuyển sang giao diện Tối";
  }

  // Cập nhật meta theme-color
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute("content", theme === "dark" ? "#0f172a" : "#1976d2");
  }

  // Phát sự kiện themechange
  window.dispatchEvent(new CustomEvent("themechange", { detail: { theme } }));
}

export function setTheme(theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch (_) {}
  applyTheme(theme);
}

export function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || getSavedTheme();
  const next = current === "dark" ? "light" : "dark";
  setTheme(next);
  return next;
}

export function initTheme() {
  const current = getSavedTheme();
  applyTheme(current);

  const btn = document.getElementById("btn-theme-toggle");
  if (btn) {
    btn.addEventListener("click", () => {
      toggleTheme();
    });
  }

  // Lắng nghe thay đổi hệ điều hành nếu người dùng chưa đặt cứng tùy chọn
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) {
          applyTheme(e.matches ? "dark" : "light");
        }
      } catch (_) {}
    });
  }
}
