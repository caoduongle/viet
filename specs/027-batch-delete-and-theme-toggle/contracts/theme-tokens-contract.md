# Theme Tokens Contract: Bảng Màu Giao Diện Sáng / Tối

**Feature**: `027-batch-delete-and-theme-toggle`

---

## 1. CSS Design Tokens (Web Client)

```css
:root[data-theme="light"] {
  --bg-body: #f8f9fa;
  --bg-surface: #ffffff;
  --bg-card: #ffffff;
  --text-main: #212529;
  --text-muted: #6c757d;
  --border-color: #dee2e6;
  --btn-primary-bg: #228be6;
  --btn-primary-fg: #ffffff;
  --btn-danger-bg: #fa5252;
  --btn-danger-fg: #ffffff;
  --canvas-bg: #ffffff;
  --canvas-guide-baseline: #a0a0a0;
  --canvas-guide-xheight: #c8c8c8;
  --canvas-guide-ascender: #e0e0e0;
}

:root[data-theme="dark"] {
  --bg-body: #121212;
  --bg-surface: #1e1e1e;
  --bg-card: #252525;
  --text-main: #f1f3f5;
  --text-muted: #adb5bd;
  --border-color: #373a40;
  --btn-primary-bg: #1c7ed6;
  --btn-primary-fg: #ffffff;
  --btn-danger-bg: #e03131;
  --btn-danger-fg: #ffffff;
  --canvas-bg: #1e1e1e;
  --canvas-guide-baseline: #707070;
  --canvas-guide-xheight: #505050;
  --canvas-guide-ascender: #3d3d3d;
}
```

---

## 2. Desktop GUI Palette Tokens (Tkinter / ttk)

```python
THEME_PALETTES = {
    "light": {
        "bg_main": "#f0f0f0",
        "bg_panel": "#ffffff",
        "fg_main": "#000000",
        "fg_muted": "#666666",
        "border": "#cccccc",
        "canvas_bg": "#ffffff",
        "canvas_baseline": "#808080",
        "canvas_xheight": "#aaaaaa",
    },
    "dark": {
        "bg_main": "#1e1e1e",
        "bg_panel": "#2d2d2d",
        "fg_main": "#ffffff",
        "fg_muted": "#aaaaaa",
        "border": "#404040",
        "canvas_bg": "#252525",
        "canvas_baseline": "#666666",
        "canvas_xheight": "#444444",
    },
}
```
