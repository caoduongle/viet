# Interface Contract: Pyodide Golden Master Test Protocol

**Document**: `golden-test-contract.md`  
**Feature**: `041-ci-pyodide-storage-hardening`  
**Consumer**: CI Workflow (`.github/workflows/ci.yml`), Local Developers (`node scripts/test_golden_pyodide.mjs`)  

---

## 1. Schema Kết quả Kiểm thử Pyodide (`GoldenTestResult`)

Đối tượng kết quả từ Python Pyodide runtime chuyển sang JavaScript runtime qua `pyodide.globals.get("test_results").toJs()`:

```typescript
interface FileDetail {
  path: string;
  exists: boolean;
  actual_sha: string | null;
  expected_sha: string;
  byte_length: number;
  status: "MATCH" | "MISMATCH" | "MISSING" | "SKIPPED";
}

interface TestCaseResult {
  name: string;
  passed: boolean;
  main: FileDetail;
  grid?: FileDetail;
  error?: string;
}

type PyodideGoldenResults = TestCaseResult[];
```

---

## 2. Tiêu chuẩn Đánh giá Ca kiểm thử (Pass/Fail Evaluation)

1. **Ca kiểm thử đơn (chỉ có tệp chính .xopp)**:
   - Ví dụ: `co_ban`, `strict_case`, `tuy_chon`, `nhieu_trang`, `assemble_letters`, `math`, `table`.
   - Điều kiện ĐẠT (`passed === true`):
     - `main.exists === true`
     - `main.actual_sha === main.expected_sha`
     - `grid.status === 'SKIPPED'` hoặc `grid === undefined`.

2. **Ca kiểm thử kép (tệp chính .xopp và lưới phụ _thieu.xopp)**:
   - Ví dụ: `markdown_list` (kích hoạt `missing_grid=True`).
   - Điều kiện ĐẠT (`passed === true`):
     - `main.exists === true && main.actual_sha === main.expected_sha`
     - `grid.exists === true && grid.actual_sha === grid.expected_sha`

---

## 3. Tiêu chuẩn Nhật ký Chẩn đoán Lỗi (Console Diagnostic Output)

Khi bất kỳ ca kiểm thử nào thất bại, hệ thống MUST xuất định dạng chẩn đoán chuẩn hóa sau:

```text
[FAIL] <test_name>:
  - Tệp chính (<main_path>):
      Trạng thái: [THIẾU TỆP / KHÔNG KHỚP MÃ BĂM]
      Kỳ vọng:    <expected_sha>
      Nhận:       <actual_sha> (kích thước: <byte_length> bytes)
  - Tệp lưới phụ (<grid_path>):
      Trạng thái: [THIẾU TỆP / KHÔNG KHỚP MÃ BĂM]
      Kỳ vọng:    <expected_sha>
      Nhận:       <actual_sha> (kích thước: <byte_length> bytes)
```

**Ràng buộc bất biến**:
- Tuyệt đối không in mã băm của tệp chính vào vị trí lỗi của tệp phụ.
- Nếu tệp không tồn tại, mã băm nhận được hiển thị là `(không tồn tại)` thay vì chuỗi rỗng gây hiểu lầm.
