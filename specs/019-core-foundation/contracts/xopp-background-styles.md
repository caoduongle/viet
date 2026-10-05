# Contract: Xournal++ Background Style Format Mapping

**Scope**: `chuviettay/document/page_format.py`, `chuviettay/layout/engine.py`  

## 1. Valid Style Names & Attribute Serialization

| Internal/CLI Style | Serialized XML Attribute `<background style="...">` | Deserialization Accepted Values |
| :--- | :--- | :--- |
| `plain` | `plain` | `plain` |
| `lined` | `lined` | `lined` |
| `ruled` | `ruled` | `ruled` |
| `graph` | `graph` | `graph` |
| `dotted` | `dotted` | `dotted` |
| `iso_graph` | `isograph` | `isograph`, `iso_graph` |
| `iso_dotted` | `isodotted` | `isodotted`, `iso_dotted` |
| `music` | `staves` | `staves`, `music` |

## 2. Invariants & Source Reference

- **Upstream Source**: Aligned with Xournal++ official source `PageTypeHandler::getPageTypeFormatForString` (commit `9882ffaaf2`).
- **User Interface Stability**: CLI and GUI retain user-friendly Vietnamese and international strings (`iso_graph`, `iso_dotted`, `music`).
- **Bidirectional Fidelity**: XML written by `chuviettay` renders rulings natively in Xournal++; XML read by `chuviettay` normalizes legacy or canonical tokens consistently.
