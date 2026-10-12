# Contract: Layout Warning Propagation

**Domain**: Diagnostics & User Feedback
**Module**: `chuviettay.model.composer`, `chuviettay.layout.engine`, `chuviettay.browser.bridge`, `chuviettay.cli`

---

## 1. Specification

All diagnostic warnings generated during table slicing, row deferral, content clamping, or document conversion must propagate seamlessly through the layout pipeline to `WriteResult`, the CLI reporter, and the Web UI.

## 2. Invariants & Data Flow

```text
TableLayoutData.warnings
         │
         ▼
DocumentLayoutEngine.render()  ──►  WriteResult.warnings
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
          CLI / Desktop Report                           BrowserBridge.write_text()
          (formatting.py)                                (res_data["warnings"])
                                                                  │
                                                                  ▼
                                                          Web UI (#editor-warnings)
```

## 3. Contract Assertions

1. `WriteResult`: Contains `warnings: list[str]`.
2. When any table row or cell triggers a clamping or pagination warning, that warning string is present in `WriteResult.warnings`.
3. `BrowserBridge.write_text()` returns `{ "warnings": [...] }` containing all `WriteResult.warnings` in addition to importer warnings.
4. If `warnings` is non-empty, Web UI displays the `#editor-warnings` notification container.
