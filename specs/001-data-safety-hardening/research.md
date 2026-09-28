# Research: Data Safety and Core Reliability Hardening

**Feature**: `001-data-safety-hardening` | **Date**: 2026-09-29

## R1. Cross-Platform File Locking for Atomic Bank Persistence

### Decision: Use `filelock` library with separate `.lock` file

### Rationale
- `filelock` is the most maintained, pure-Python cross-platform file locking library. Works on Windows (`msvcrt`), Linux/macOS (`fcntl`).
- Simple context-manager API: `with FileLock(path, timeout=10):`.
- OS automatically releases locks on process crash — no stale lock handling needed at the application level.
- Lock file existence alone doesn't indicate a held lock; `filelock` checks the OS-level lock, so stale `.lock` files on disk are harmless.

### Alternatives Considered
- **`portalocker`**: More features but heavier; `filelock` is simpler and matches KISS principle.
- **Rolling our own with `fcntl`/`msvcrt`**: Duplicates effort; `filelock` handles the cross-platform abstraction already.
- **Locking the data file itself**: Rejected because `os.replace()` removes the original inode, invalidating any lock held on the original file handle.

### Recommended Pattern
```
acquire lock (bank.json.gz.lock)
  → write to unique temp file (bank.json.gz.<pid>.<random>.tmp)
  → flush
  → fsync (raw file descriptor, not the gzip wrapper)
  → os.replace(tmp, target)
  → fsync parent directory (POSIX only)
release lock
```

### Key Details
- **Unique temp file**: Use `tempfile.mkstemp(dir=same_dir)` to prevent inter-process collision.
- **fsync with gzip**: Close the gzip stream first, then `flush()` + `os.fsync()` on the raw `open()` handle underneath.
- **fsync parent directory**: Required on Linux (ext4) for durability of the rename; not needed on Windows (NTFS).
- **New dependency**: `filelock` added to both runtime dependencies and `requirements-dev.txt`.

---

## R2. Bank Schema Validation and Migration System

### Decision: Lightweight `bank_schema.py` module with integer versioning and sequential migration chain

### Rationale
- Zero external dependencies (no `jsonschema`, `pydantic`). A simple `validate_bank_dict()` function with `isinstance` checks is ~40 lines and runs in microseconds.
- Explicit integer `schema_version` field at the top level. Absence implies legacy v1.
- Sequential migration chain (`v1→v2→v3...`) — each step is a pure function modifying the dict in-place. Easy to test, easy to add new versions.
- In-memory migration on load; `schema_version` written to disk only on next genuine save (per Q2 decision).

### Alternatives Considered
- **`jsonschema` / `pydantic`**: Overkill for a flat dictionary with ~10 keys. Adds dependency for no real benefit.
- **Semantic versioning for schema**: Unnecessarily complex; monotonic integer is sufficient for structural changes.
- **Auto-save on load**: Rejected (Q2 decision) — read-only usage must not modify user's file.

### Error Hierarchy
```
BankError (base)
├── BankNotFoundError (extends FileNotFoundError) — file missing
├── BankCorruptedError — 0 bytes, bad gzip, bad JSON
├── BankValidationError (extends ValueError) — missing keys, wrong types
└── BankSchemaError
    ├── UnsupportedSchemaVersionError — version too new
    └── BankMigrationError — migration step failed
```

### Loading Pipeline
```
File existence check → empty file check → gzip decompress → JSON parse
→ pre-validate (is dict?) → detect version → migrate chain → full validate
→ Bank instance ready
```

---

## R3. GitHub Actions CI/CD Workflow

### Decision: Single unified `.github/workflows/ci.yml` with test matrix + gated release

### Rationale
- Consolidated workflow is easier to maintain than split CI/release files.
- Test matrix: `{ubuntu-latest, windows-latest} × {Python 3.10, 3.12}` — covers minimum supported version and developer-tested version.
- Release gated behind `needs: test` and `if: startsWith(github.ref, 'refs/tags/v')`.
- Two-phase release architecture (build artifacts → single publish job) avoids GitHub API race conditions.

### Alternatives Considered
- **Split `ci.yml` + `release.yml`**: More files to maintain for marginal benefit.
- **macOS runner**: Not needed — the app is primarily Windows/Linux. Add later if requested.
- **Python 3.14**: Too new, potential compatibility issues. Defer until stable.

### Tkinter on Headless CI
- **Linux**: `xvfb-run -a python -m pytest` provides a virtual X11 display. `python3-tk` system package required.
- **Windows**: Native desktop session available on GitHub runners. No special handling needed.

### Key Workflow Steps
1. Checkout → Setup Python (with pip cache) → Install deps
2. `python -m compileall -q .` (syntax check)
3. `pytest` (wrapped in `xvfb-run` on Linux)
4. On tag push: PyInstaller build → archive binary + data file → single publish job creates GitHub Release

---

## R4. WriteOptions and Color Validation

### Decision: Centralized `WriteOptions.validate()` method + strict hex color parser

### Rationale
- Current codebase has zero validation of numeric options — `float("nan")`, `float("inf")`, negative values all parse successfully.
- GUI and CLI must share the same validation logic; having it in the dataclass itself (or a standalone function) prevents duplication.
- Color validation must reject anything not matching `#RRGGBB` or `#RRGGBBAA` — prevents XML attribute injection in `stroke_xml()`.

### Validation Rules
| Field | Constraint |
|-------|-----------|
| `scale` | `> 0`, finite |
| `line` | `None` or `> 0`, finite |
| `width` | `None` or `> 0`, finite |
| `space` | `> 0`, finite |
| `jitter` | `>= 0`, finite |
| `wscale` | `> 0`, finite |
| `color` | `None` or matches `^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$` |

### Color Parser
A standalone `parse_color(s: str) -> str` utility that:
1. Strips whitespace
2. Validates against `^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$`
3. Raises `ValueError` with descriptive message on failure
4. Returns the validated string (lowercase normalized)

---

## R5. Synthetic Test Fixture Generation

### Decision: Script-generated synthetic bank fixture with geometric pseudo-strokes

### Rationale
- Current `tests/data/kho_mau_chup_lai.json.gz` is byte-identical to the personal `chu_cua_ban.json.gz` (same Git blob SHA `9a6a420a...`).
- Replace with a fixture generated by a Python script that creates geometric shapes (rectangles, zigzags) as stroke data.
- Script committed to repo; fixture can be regenerated deterministically at any time.
- Must contain enough variety: words with tones, digits, punctuation, multiple samples per word — to exercise all Bank/Writer code paths without relying on `tiny_bank_dict()` alone.

### Alternatives Considered
- **Extend `tiny_bank_dict()`**: Already used for deterministic golden-master tests; the synthetic fixture serves a different purpose (exercising the full pipeline with realistic-scale data).
- **Anonymized real data**: Requires manual curation; not reproducibly regenerable.

---

## R6. Logging Fallback Strategy

### Decision: Platform-aware fallback path hierarchy

### Rationale
- Current code silently swallows `OSError` when log file creation fails, then UI claims logs were written to a non-existent file.
- Fallback hierarchy: `app_base_dir() → platform user data dir → None` (no file handler, stderr only).

### Fallback Order
1. Application directory (current behavior — works for dev, portable installs)
2. OS user data directory:
   - Windows: `%LOCALAPPDATA%/Chuviettay/`
   - Linux: `~/.local/state/chuviettay/`
   - macOS: `~/Library/Logs/Chuviettay/`
3. No file logging (stderr only if available; update `log_path()` return to reflect actual location)
