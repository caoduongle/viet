# Contract: Web Table Modal Template Generator

**Module**: `webapp/js/write.js`

---

## Behavior Contract: `btnConfirmTable` Click Handler

### Inputs
- `inputRows.value`: string, integer $\ge 1$, default 3
- `inputCols.value`: string, integer $\ge 1$, default 3
- `inputHeader.checked`: boolean

### Outputs
Inserts Markdown table template at cursor in `textarea`:

#### Case 1: `inputHeader.checked === true` (Default)
```markdown
| Cột 1 | Cột 2 | Cột 3 |
| :--- | :--- | :--- |
| R1C1 | R1C2 | R1C3 |
| R2C1 | R2C2 | R2C3 |
```

#### Case 2: `inputHeader.checked === false`
```markdown
|   |   |   |
| :--- | :--- | :--- |
| R1C1 | R1C2 | R1C3 |
| R2C1 | R2C2 | R2C3 |
```
*(Header row is empty, allowing CommonMark / markdown-it table parsing while rendering no title text in the header).*
