# Contract: Tính Bất Biến của Cây Tài Liệu trong Bộ Dàn Trang

**Feature**: [054-repo-audit-hardening](../spec.md)  
**Target Module**: `chuviettay.layout.engine.DocumentLayoutEngine`  

---

## 1. Mục đích
Quy định tính bất biến (immutability) của đối tượng `Document` và các nút con (`Paragraph`, `Text`, `Table`, `MathBlock`, v.v.) trong toàn bộ vòng đời thực thi của `DocumentLayoutEngine`.

## 2. Đặc tả Hành vi & Hợp đồng

```python
class DocumentLayoutEngine:
    def layout(self, document: Document) -> list[PageLayout]:
        """Tính toán bố cục trang in từ cây tài liệu Document.
        
        Bất biến: KHÔNG ĐƯỢC PHÉP thay đổi bất kỳ thuộc tính nào của
        document hoặc các nút con thuộc document."""
```

## 3. Các Ràng buộc Bất biến (Invariants)

1. **Text Node Immutability**:
   - Khi thực hiện gộp các phần tử `Text` liền kề trong `_layout_inlines(inlines, ...)` để xử lý dấu câu và khoảng cách từ, nếu hai nút `Text` được gộp lại, hàm PHẢI tạo một thể hiện `Text` mới.
   - Tuyệt đối không thực hiện thao tác gán nối chuỗi tại chỗ: `inl.text += ...`.
2. **Re-entrancy & Idempotence**:
   - Với cùng một thể hiện `doc = Document(...)`:
     ```python
     pages_1 = engine.layout(doc)
     doc_snapshot_after_1 = repr(doc)
     pages_2 = engine.layout(doc)
     doc_snapshot_after_2 = repr(doc)
     
     assert doc_snapshot_after_1 == doc_snapshot_after_2
     assert pages_1 == pages_2
     ```
   - Việc gọi `layout` lần thứ 2, thứ 3... không làm thay đổi số lượng từ, số nét chữ hay tọa độ kết xuất so với lần chạy đầu tiên.
