# Contract: Web Worker Recovery Protocol (CTR-043-WORKER-RECOVERY)

**Scope**: Client-side worker failure handling, interactive retry button, and recovery validation in [`webapp/js/app.js`](file:///d:/viet/app/webapp/js/app.js).

---

## 1. Interface Signature

```javascript
/**
 * Initiates an interactive Web Worker recovery attempt.
 * Guaranteed single-flight: returns existing active Promise if recovery is in flight.
 *
 * @param {typeof Worker | null} [WorkerClass=null] Optional Worker constructor for unit testing.
 * @param {number} [timeoutMs=10000] Maximum wait time (ms) for READY + onWorkerReady completion.
 * @returns {Promise<boolean>} Resolves to true ONLY if worker sends READY,
 *                             loads active profile bank, and completes UI sync.
 *                             Resolves to false on any error or timeout.
 */
export function recoverWorker(WorkerClass = null, timeoutMs = 10000);
```

---

## 2. Behavioral Guarantees

1. **Explicit Success Validation**:
   - `recoverWorker()` MUST check the boolean resolved by `readyPromise`:
     ```javascript
     const isReady = await readyPromise;
     if (!isReady) {
       return false;
     }
     ```
   - If `isReady === false` (or if constructing the Worker throws synchronously), `recoverWorker()` MUST return `false` and MUST NOT hide `#btn-worker-retry`.

2. **Deferred Hiding of Retry Affordance in `onWorkerReady()`**:
   - `onWorkerReady()` MUST NOT hide `#btn-worker-retry` or `#splash-screen` at the start of the function.
   - Only after `storage.listProfiles()`, `sendWorkerMessage("load_bank", ...)`, `refreshBankView()`, and `teachController.refresh()` complete without throwing may `onWorkerReady()` hide `#btn-worker-retry`, mark `isUiInitialized = true`, and set `setStatus("status_ready")`.

3. **Timeout Enforcement (`timeoutMs = 10000` by default)**:
   - When launching the replacement Worker, a timer of `timeoutMs` is started.
   - If the timer fires before `readyPromise` settles:
     - Terminates the hung worker (`worker.terminate()`), increments `workerGeneration`, sets `worker = null`.
     - Calls `handleWorkerFatalError(\`Khởi tạo bộ xử lý nền quá thời gian chờ (\${timeoutMs}ms)\`)`.
     - Resolves `readyPromise(false)`.

4. **All Failure Branches Resolve `readyPromise(false)` and Trigger `handleWorkerFatalError`**:
   - `data.type === "ERROR"`: Calls `handleWorkerFatalError(data.payload?.message || "Lỗi khởi tạo Worker")` and resolves `workerReadyResolve(false)`.
   - `targetWorker.onerror`: Calls `handleWorkerFatalError(e.message || "Lỗi runtime trong Web Worker")` and resolves `workerReadyResolve(false)`.
   - `targetWorker.onmessageerror`: Calls `handleWorkerFatalError("Lỗi giải mã thông điệp (message deserialization error)")` and resolves `workerReadyResolve(false)`.
   - `onWorkerReady().catch(err)`: Calls `handleWorkerFatalError(err.message || "Lỗi nạp lại kho mẫu sau khi phục hồi")` and resolves `workerReadyResolve(false)`.
   - Synchronous error in `new TargetWorkerClass(...)`: Caught by `catch (err)` in `recoverWorker()`, calls `handleWorkerFatalError(err.message)`, and returns `false`.
