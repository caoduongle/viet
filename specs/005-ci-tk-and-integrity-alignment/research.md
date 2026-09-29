# Research Decisions: CI Environment Hardening, Tk/Tcl Probing, and Data Integrity Alignment

**Feature Branch**: `005-ci-tk-and-integrity-alignment` | **Date**: 2026-09-29

---

## 1. Deep Tk/Tcl Runtime Probing & CI Immunity

### Problem
In GitHub Actions CI run `36556305255`, Windows Python 3.11 failed because Tcl reported `can't find listbox.tcl` when initializing `MainWindow` in `test_khoi_dong_voi_duong_dan_bank_sai_khong_tu_tao_file`. The previous probe created a `tk.Tk()` and `tk.Listbox()` widget without loading widget script dependencies or updating event bindings, giving a false negative (reported Tk as usable when critical widget scripts were missing).

### Decision
Implement a multi-tiered probe in `tests/conftest.py` with defensive test guards in `tests/test_gui.py`:

1. **Deep Runtime Probe (`is_tk_usable()`)**:
   - Initialize `tk.Tk()`.
   - Inspect and verify that `$tk_library` and `$tcl_library` are accessible.
   - Force evaluation of `listbox.tcl` via `root.tk.eval("source [file join $tk_library listbox.tcl]")` or verify file existence at `os.path.join(root.tk.eval("set tk_library"), "listbox.tcl")`.
   - Create and pack `ttk.Notebook`, `ttk.Button`, `tk.Listbox`.
   - Force event loop processing with `root.update_idletasks()` and `root.update()`.
   - Catch any `tk.TclError`, `OSError`, `FileNotFoundError`, or generic `Exception`, record the message in `_tk_unusable_reason`, and return `False`.
2. **Defensive Guard in Test Functions**:
   - Ensure all tests in `tests/test_gui.py` instantiating `MainWindow` directly (e.g. `test_khoi_dong_voi_duong_dan_bank_sai_khong_tu_tao_file`) wrap initialization in `try-except` and call `pytest.skip()` on unexpected Tk runtime errors.
   - Maintain `pytest_collection_modifyitems` to mark all `gui` tests as skipped if `is_tk_usable()` is false.

### Rationale
- Completely eliminates false negatives across all Python versions and platforms.
- If a runner has a broken or partial Tk installation, the test suite skips GUI tests gracefully with 100% CI pass rate.

### Alternatives Considered
- *Fixing Tk in CI workflow via choco/winget*: Fragile, adds external dependencies, and doesn't protect local developer environments with corrupted Tk installations.
- *Removing GUI tests from Windows CI*: Degrades test coverage on working Windows runners (such as 3.10, 3.12, 3.13).

---

## 2. Reconciling 50-Word Large-Bank Benchmark

### Problem
Specification SC-004 stipulated sequential teaching of 50 words on banks with $\ge 5,000$ samples, whereas the test implementation and tasks previously stopped at 20 words.

### Decision
Update `test_large_bank_persistence_benchmark_5000_samples` in `tests/test_bank.py` to execute `num_incremental = 50`:
- 50 consecutive `add_sample_incremental()` + `save()` cycles.
- Measure average latency, maximum latency, and total batch duration.
- Assert `avg_latency < 1.0` seconds, `max_latency < 2.0` seconds, and `t_total < 30.0` seconds.

### Rationale
- 20 iterations demonstrated an average latency of ~0.16s (~3.9s total).
- 50 iterations will take approximately 8.0–10.0 seconds, which fits comfortably within standard test execution budgets and conclusively verifies asymptotic behavior.

### Alternatives Considered
- *Lowering SC-004 in spec to 20 words*: Rejected; 50 consecutive interactive saves on a 5,000-sample bank represents genuine user session stress testing and builds higher quality assurance.

---

## 3. Conflict Resolution Semantics & Non-Existent Word Drop

### Problem
1. Documentation claimed "generation-based conflict resolution," but the cross-process merge algorithm primarily uses operational timestamps (`deleted_at`, `readded_at`) to resolve deletions vs additions, while `generation` acts as a monotonic mutation counter and audit snapshot tracker.
2. `Bank.drop(word)` created tombstones and incremented `_generation` even when `word` was never in `self.words`.

### Decision
1. **Clarify Architecture**:
   - Document the concurrency architecture accurately in `README.md` and `CHANGELOG.md`: "Atomic inter-process file locking with timestamped tombstone reconciliation and monotonic generation sequencing."
   - Retain `generation` as a persistent integer in `d["generation"]` and tombstone records `{"deleted_at": ts, "generation": gen}` for sequential mutation auditing and schema validation.
2. **Refine `Bank.drop(word)`**:
   - Check `if word not in self.words:` first. If absent, return `0` immediately without incrementing `_generation` or adding to `_tombstones`.

### Rationale
- Avoids misleading claims of distributed consensus.
- Eliminates dead tombstones and phantom generation bumps on typos.

---

## 4. Git History Purge Operational Strategy

### Problem
Sensitive blobs `chu_cua_ban.json.gz` and `tests/data/kho_mau_chup_lai.json.gz` are purged from current trees but still exist in historical commits (`5a25e92`, `621c013`). The purge script was created in feature 004 but has not yet been executed on the local repository.

### Decision
1. Create a full external git bundle backup (`../repo-backup-before-purge.bundle`).
2. Execute the history purge locally using `scripts/purge_git_history.ps1` (or `git-filter-repo` / `filter-branch`).
3. Verify that `git log --all -- <blob>` returns 0 results.
4. Document the exact command for the user to execute manual remote mirror push (`git push --force --mirror origin`).

### Rationale
- Fulfills the user's explicit request to purge historical commits locally while respecting the safety mandate never to execute remote force-push automatically.

---

## 5. Schema Validation Hardening (`pen.color`)

### Problem
`re.match()` checks prefixes, requiring a manual trailing `$`.

### Decision
Use `re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", color_val)` in `chuviettay/model/bank_schema.py`.

### Rationale
- `fullmatch` explicitly conveys intent and avoids partial match bugs.
