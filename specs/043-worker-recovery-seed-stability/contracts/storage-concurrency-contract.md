# Contract: Storage Concurrency & Teach Count Protection (CTR-043-STORAGE-CONCURRENCY)

**Scope**: Atomic metadata updates, teach count tracking, and multi-tab synchronization in [`webapp/js/storage.js`](file:///d:/viet/app/webapp/js/storage.js).

---

## 1. Interface Signatures

```javascript
/**
 * Atomically increments the teach count for a profile within a single IndexedDB readwrite transaction.
 * Guarantees monotonic timestamp update, localSyncedTimestamp coherence, and zero unconditioned overwrites.
 *
 * @param {string} profileId
 * @returns {Promise<number>} The updated teach count (or 0 if profile does not exist).
 */
export function incrementTeachCount(profileId);

/**
 * Atomically resets the teach count for a profile to 0 upon backup within a single IndexedDB readwrite transaction.
 *
 * @param {string} profileId
 * @returns {Promise<void>}
 */
export function resetTeachCount(profileId);
```

---

## 2. Invariants & Rules

1. **Single-Transaction Read-Modify-Write**:
   - Updates to `teach_count_since_backup` MUST occur inside `executeTransaction(db, PROFILES_STORE, "readwrite", (store, tx, onError) => ...)` without calling `getProfile()` + `saveProfile()` in separate transactions.
   - Inside `getReq.onsuccess`:
     - Mutate `existing.teach_count_since_backup` and `existing.updated_at = Math.max(Date.now(), (existing.updated_at || 0) + 1)` directly on the `existing` object retrieved from `store.get(profileId)`.
     - Preserve `existing.data` untouched so another tab's concurrent bank update is never overwritten.

2. **Anti-Resurrection Guard**:
   - If `store.get(profileId)` returns `undefined` (profile was deleted by another tab), the transaction MUST NOT call `store.put(...)` and resolves cleanly (`0` for `incrementTeachCount`).

3. **`localSyncedTimestamp` Coherence (Zero False-Positive Merges)**:
   - Before writing, check `const wasInSync = (localSyncedTimestamp > 0 && localSyncedTimestamp === existing.updated_at)`.
   - After `executeTransaction` commits:
     - If `wasInSync` is `true`, update `localSyncedTimestamp = newUpdatedAt` so that `scheduleAutoSave()` -> `syncAndSaveActiveProfile()` in the same tab knows its bank data is still in sync with IndexedDB and does not perform a redundant self-merge.
     - If `wasInSync` is `false` (e.g. `localSyncedTimestamp < existing.updated_at` because another tab saved new bank data), leave `localSyncedTimestamp` unchanged so `syncAndSaveActiveProfile()` still merges the other tab's `diskGzBytes`.
