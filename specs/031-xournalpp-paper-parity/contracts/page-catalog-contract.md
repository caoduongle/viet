# Interface Contract: Page Catalog and CLI Specification

**Feature Branch**: `031-xournalpp-paper-parity` | **Date**: 2026-10-11
**Spec**: [spec.md](../spec.md)

This contract defines the unified catalog schema exposed by `get_page_catalog()` and the command-line options for page background configuration.

---

## 1. Page Catalog Function Contract

### Signature
```python
def get_page_catalog() -> dict[str, Any]:
    ...
```

### Response Schema
```json
{
  "sizes": {
    "a4": {
      "id": "a4",
      "name": "A4 (210 x 297 mm)",
      "width": 595.28,
      "height": 841.89
    },
    "a3": {
      "id": "a3",
      "name": "A3 (297 x 420 mm)",
      "width": 841.89,
      "height": 1190.55
    },
    "a5": {
      "id": "a5",
      "name": "A5 (148 x 210 mm)",
      "width": 419.53,
      "height": 595.28
    },
    "letter": {
      "id": "letter",
      "name": "Letter (8.5 x 11 in)",
      "width": 612.00,
      "height": 792.00
    },
    "legal": {
      "id": "legal",
      "name": "Legal (8.5 x 14 in)",
      "width": 612.00,
      "height": 1008.00
    },
    "16:9": {
      "id": "16:9",
      "name": "Màn hình rộng 16:9",
      "width": 841.89,
      "height": 473.56
    },
    "4:3": {
      "id": "4:3",
      "name": "Màn hình chuẩn 4:3",
      "width": 792.00,
      "height": 594.00
    }
  },
  "presets": {
    "plain": { "name": "Trơn (Plain)", "style": "plain" },
    "lined": { "name": "Kẻ ngang có lề (Lined)", "style": "lined", "spacing": 24.0, "margin": 72.0 },
    "lined_narrow": { "name": "Kẻ ngang hẹp (Narrow)", "style": "lined", "spacing": 18.0, "margin": 72.0 },
    "lined_college": { "name": "Kẻ ngang vừa (College)", "style": "lined", "spacing": 20.0, "margin": 72.0 },
    "lined_wide": { "name": "Kẻ ngang rộng (Wide)", "style": "lined", "spacing": 24.0, "margin": 72.0 },
    "ruled": { "name": "Kẻ ngang không lề (Ruled)", "style": "ruled", "spacing": 24.0 },
    "graph": { "name": "Lưới ô vuông (Graph)", "style": "graph", "spacing": 14.17 },
    "graph_5mm": { "name": "Lưới 5mm (Graph 5mm)", "style": "graph", "spacing": 14.17 },
    "graph_grid": { "name": "Lưới có nét đậm (Graph Grid)", "style": "graph", "spacing": 14.17, "bold_interval": 5, "bold_width": 1.5 },
    "dotted": { "name": "Chấm lưới (Dotted)", "style": "dotted", "spacing": 14.17 },
    "iso_graph": { "name": "Lưới tam giác đều (Iso Graph)", "style": "iso_graph", "spacing": 14.17 },
    "iso_dotted": { "name": "Chấm tam giác đều (Iso Dotted)", "style": "iso_dotted", "spacing": 14.17 },
    "staves": { "name": "Khuông nhạc (Staves)", "style": "staves" }
  },
  "tones": [
    { "id": "white", "name": "Trắng", "color": "#ffffffff", "dark": false },
    { "id": "ivory", "name": "Vàng ngà", "color": "#ffffc8ff", "dark": false },
    { "id": "blue", "name": "Xanh nhạt", "color": "#e8f4f8ff", "dark": false },
    { "id": "dark", "name": "Tối", "color": "#1e1e1eff", "dark": true }
  ]
}
```

---

## 2. CLI Options Specification

In `chuviettay write`:

```text
--bg-preset <PRESET>     Áp dụng mẫu giấy chuẩn Xournal++ (ví dụ: lined_college, graph_5mm, staves).
--bg-r1 <LENGTH>         Ghi đè khoảng cách dòng kẻ / ô li r1 (ví dụ: 20pt, 5mm, 8mm).
--bg-m1 <LENGTH>         Ghi đè vị trí lề đứng m1 (ví dụ: 72pt, -72pt, 25mm). Giá trị âm tính từ mép phải.
--bg-color <HEX>         Mã màu nền hex RGBA (ví dụ: #ffffff, #ffffc8, #1e1e1e).
--no-snap-ruling         Tắt tính năng tự động căn baseline vào dòng kẻ giấy trên nền ruled/lined.
```
