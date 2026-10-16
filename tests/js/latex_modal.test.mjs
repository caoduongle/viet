import test from "node:test";
import assert from "node:assert/strict";
import { loadLatexSymbols } from "../../webapp/js/write.js";

// Mock container element
class MockElement {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.style = {};
    this.textContent = "";
    this._innerHTML = "";
    this.className = "";
    this.title = "";
    this.onclick = null;
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set innerHTML(val) {
    this._innerHTML = val;
    this._innerHTMLAssigned = true;
  }

  appendChild(child) {
    this.children.push(child);
  }

  replaceChildren(...newChildren) {
    this.children = [...newChildren];
    this.textContent = "";
    this._innerHTML = "";
  }
}

// Giả lập global document.createElement nếu chạy trong Node.js thuần
if (typeof globalThis.document === "undefined") {
  globalThis.document = {
    createElement: (tag) => new MockElement(tag),
  };
}

test("loadLatexSymbols dựng DOM bằng createElement và textContent, tuyệt đối không dùng innerHTML", async () => {
  const container = new MockElement("div");
  const textarea = new MockElement("textarea");
  const modal = new MockElement("div");

  const mockFetch = async () => ({
    ok: true,
    symbols: {
      "<img src=x onerror=alert(1)>Toán học": [
        { display: "α", latex: "\\alpha" },
        { display: "β", latex: "\\beta" },
      ],
    },
  });

  await loadLatexSymbols(container, textarea, modal, mockFetch);

  // Kiểm tra không có bất kỳ lệnh gán innerHTML nào được thực hiện
  assert.equal(container._innerHTMLAssigned, undefined, "container không được gán qua innerHTML");

  // Kiểm tra cấu trúc children
  assert.equal(container.children.length, 1);
  const catDiv = container.children[0];
  const headerDiv = catDiv.children[0];
  assert.equal(headerDiv.textContent, "<img src=x onerror=alert(1)>Toán học");
  assert.equal(headerDiv._innerHTMLAssigned, undefined, "headerDiv không được gán qua innerHTML");

  const btnGrid = catDiv.children[1];
  assert.equal(btnGrid.children.length, 2);
  assert.equal(btnGrid.children[0].textContent, "α");
  assert.equal(btnGrid.children[0].title, "\\alpha");
});

test("loadLatexSymbols xử lý lỗi và dựng thông báo an toàn qua replaceChildren / textContent", async () => {
  const container = new MockElement("div");
  const textarea = new MockElement("textarea");
  const modal = new MockElement("div");

  const mockFailFetch = async () => {
    throw new Error("<script>alert(1)</script>Mất kết nối");
  };

  await loadLatexSymbols(container, textarea, modal, mockFailFetch);

  assert.equal(container._innerHTMLAssigned, undefined, "container không được gán qua innerHTML khi có lỗi");
  assert.equal(container.children.length, 1);
  assert.equal(container.children[0].textContent, "Lỗi tải ký hiệu: <script>alert(1)</script>Mất kết nối");
});
