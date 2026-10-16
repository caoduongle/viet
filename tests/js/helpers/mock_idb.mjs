/**
 * mock_idb.mjs -- Bộ giả lập IndexedDB tối giản và trung thực cho Node.js test runner.
 * Mô phỏng chính xác vòng đời: request.onsuccess -> tx.oncomplete, tx.onabort, tx.onerror.
 */

export class MockIDBRequest {
  constructor() {
    this.onsuccess = null;
    this.onerror = null;
    this.result = undefined;
    this.error = null;
  }
}

export class MockIDBTransaction {
  constructor(db, storeNames, mode) {
    this.db = db;
    this.storeNames = Array.isArray(storeNames) ? storeNames : [storeNames];
    this.mode = mode;
    this.oncomplete = null;
    this.onerror = null;
    this.onabort = null;
    this.error = null;
    this._aborted = false;
    this._completed = false;
    this._activeRequests = 0;

    queueMicrotask(() => {
      if (this._activeRequests === 0 && !this._aborted && !this._completed) {
        this._commit();
      }
    });
  }

  _requestStarted() {
    this._activeRequests++;
  }

  _requestFinished() {
    this._activeRequests--;
    if (this._activeRequests === 0 && !this._aborted && !this._completed) {
      queueMicrotask(() => this._commit());
    }
  }

  objectStore(name) {
    if (!this.storeNames.includes(name)) {
      throw new Error(`NotFoundError: Object store "${name}" không nằm trong transaction.`);
    }
    return new MockIDBObjectStore(this, name);
  }

  abort() {
    if (this._completed || this._aborted) return;
    this._aborted = true;
    if (!this.error) {
      this.error = new DOMException("Giao dịch đã bị hủy bỏ.", "AbortError");
    }
    queueMicrotask(() => {
      if (this.onabort) {
        this.onabort({ target: this });
      }
    });
  }

  _commit() {
    if (this._aborted || this._completed) return;
    this._completed = true;
    if (this.oncomplete) {
      this.oncomplete({ target: this });
    }
  }

  _fail(error) {
    if (this._completed || this._aborted) return;
    this._aborted = true;
    this.error = error;
    queueMicrotask(() => {
      if (this.onerror) {
        this.onerror({ target: this, error });
      }
      if (this.onabort) {
        this.onabort({ target: this, error });
      }
    });
  }
}

export class MockIDBObjectStore {
  constructor(tx, name) {
    this.tx = tx;
    this.name = name;
  }

  get storeData() {
    return this.tx.db._data[this.name] || (this.tx.db._data[this.name] = new Map());
  }

  get(key) {
    const req = new MockIDBRequest();
    this.tx._requestStarted();
    queueMicrotask(() => {
      if (this.tx._aborted) {
        this.tx._requestFinished();
        return;
      }
      const val = this.storeData.get(key);
      req.result = val !== undefined ? JSON.parse(JSON.stringify(val)) : undefined;
      if (req.onsuccess) req.onsuccess({ target: req });
      this.tx._requestFinished();
    });
    return req;
  }

  getAll() {
    const req = new MockIDBRequest();
    this.tx._requestStarted();
    queueMicrotask(() => {
      if (this.tx._aborted) {
        this.tx._requestFinished();
        return;
      }
      const list = Array.from(this.storeData.values()).map((v) => JSON.parse(JSON.stringify(v)));
      req.result = list;
      if (req.onsuccess) req.onsuccess({ target: req });
      this.tx._requestFinished();
    });
    return req;
  }

  put(val) {
    const req = new MockIDBRequest();
    this.tx._requestStarted();
    queueMicrotask(() => {
      if (this.tx._aborted) {
        this.tx._requestFinished();
        return;
      }

      // Hỗ trợ mô phỏng lỗi dung lượng QuotaExceededError
      if (this.tx.db._shouldFailQuota) {
        const quotaErr = new DOMException("The quota has been exceeded.", "QuotaExceededError");
        req.error = quotaErr;
        if (req.onerror) req.onerror({ target: req, error: quotaErr });
        this.tx._fail(quotaErr);
        this.tx._requestFinished();
        return;
      }

      const key = val.id || val.key;
      if (!key) {
        const err = new Error("DataError: Thiếu key hoặc id");
        req.error = err;
        if (req.onerror) req.onerror({ target: req, error: err });
        this.tx._fail(err);
        this.tx._requestFinished();
        return;
      }

      this.storeData.set(key, JSON.parse(JSON.stringify(val)));
      req.result = key;
      if (req.onsuccess) req.onsuccess({ target: req });
      this.tx._requestFinished();
    });
    return req;
  }

  delete(key) {
    const req = new MockIDBRequest();
    this.tx._requestStarted();
    queueMicrotask(() => {
      if (this.tx._aborted) {
        this.tx._requestFinished();
        return;
      }
      this.storeData.delete(key);
      req.result = undefined;
      if (req.onsuccess) req.onsuccess({ target: req });
      this.tx._requestFinished();
    });
    return req;
  }
}

export class MockIDBDatabase {
  constructor(name = "chuviettay_web") {
    this.name = name;
    this._data = {
      profiles: new Map(),
      app_settings: new Map(),
    };
    this._shouldFailQuota = false;
  }

  transaction(storeNames, mode = "readonly") {
    return new MockIDBTransaction(this, storeNames, mode);
  }

  simulateQuotaExceeded(enabled = true) {
    this._shouldFailQuota = enabled;
  }
}

export function createMockIndexedDB() {
  const db = new MockIDBDatabase();
  return {
    db,
    openDB: async () => db,
  };
}
