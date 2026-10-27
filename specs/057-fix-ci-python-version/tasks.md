# Tasks: Khắc Phục Lỗi Phân Giải Phiên Bản Python Trên CI (057-fix-ci-python-version)

**Input**: Design documents from `specs/057-fix-ci-python-version/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Tests**: Bao gồm kiểm thử tự động tính hợp lệ của định dạng phiên bản trong `.python-version` và `render.yaml`.  
**Organization**: Tasks được phân chia theo từng User Story để hỗ trợ thực thi độc lập và kiểm chứng tách biệt.

---

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Có thể chạy song song (khác tệp tin, không phụ thuộc vào task chưa hoàn thành)
- **[Story]**: Gắn với User Story tương ứng (`[US1]`, `[US2]`)
- Mô tả công việc luôn đi kèm đường dẫn tệp cụ thể

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Khởi tạo môi trường và xác nhận trạng thái codebase trước khi triển khai

- [X] T001 Kiểm tra nội dung hiện tại của `.python-version`, `render.yaml` và trạng thái `tests/test_version_metadata.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Chuẩn bị các cấu trúc nền tảng và helper dùng chung cho các User Stories

- [X] T002 Chuẩn hóa mẫu biểu thức chính quy kiểm tra định dạng phiên bản `^\d+\.\d+$` dùng chung trong `tests/test_version_metadata.py`

**Checkpoint**: Nền tảng helper hoàn tất - các User Story có thể tiến hành độc lập

---

## Phase 3: User Story 1 - Tự động Phân giải Môi trường Python Hợp lệ trên CI (Priority: P1) 🎯 MVP

**Goal**: Đảm bảo tệp `.python-version` chỉ định `3.13` để `actions/setup-python@v5` tự động phân giải phiên bản 3.13.x mới nhất sẵn có trên mọi runner Ubuntu mà không gặp lỗi `version not found`.

**Independent Test**: Kiểm tra tệp `.python-version` chứa chuỗi `3.13\n` và vượt qua bài test kiểm tra định dạng phiên bản trong `tests/test_version_metadata.py`.

### Tests for User Story 1
- [X] T003 [P] [US1] Thêm bài test kiểm tra `.python-version` tồn tại và chỉ định chính xác `"3.13"` trong `tests/test_version_metadata.py`

### Implementation for User Story 1
- [X] T004 [US1] Cập nhật tệp `.python-version` từ `3.13.5` thành `3.13`

**Checkpoint**: User Story 1 hoàn tất và có thể kiểm chứng độc lập mà không ảnh hưởng tới các module khác

---

## Phase 4: User Story 2 - Đồng bộ hóa Cấu hình Triển khai và Metadata Phiên bản (Priority: P2)

**Goal**: Đồng bộ hóa cấu hình triển khai Render (`render.yaml`) sử dụng `PYTHON_VERSION: 3.13`, bảo đảm tính nhất quán toàn diện trong toàn bộ dự án.

**Independent Test**: Kiểm tra tệp `render.yaml` có biến `PYTHON_VERSION` nhận giá trị `"3.13"` và bài test trong `tests/test_version_metadata.py` vượt qua.

### Tests for User Story 2
- [X] T005 [P] [US2] Bổ sung bài test kiểm tra biến `PYTHON_VERSION` trong `render.yaml` là `"3.13"` trong `tests/test_version_metadata.py`

### Implementation for User Story 2
- [X] T006 [US2] Cập nhật giá trị `PYTHON_VERSION` trong `render.yaml` từ `3.13.5` thành `3.13`

**Checkpoint**: Cấu hình môi trường CI và triển khai Render đồng bộ 100%

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm tra chất lượng tổng thể, format mã nguồn và xác nhận không có bất kỳ hồi quy nào

- [X] T007 [P] Chạy kiểm tra style và linting với `ruff check .`
- [X] T008 [P] Chạy toàn bộ test suite Python với `pytest tests/` (1.300+ tests)
- [X] T009 [P] Chạy toàn bộ test suite JavaScript với `npm run test:unit`
- [X] T010 [P] Chạy xác thực Pyodide Golden Master với `node scripts/test_golden_pyodide.mjs`
- [X] T011 Xác thực kịch bản mẫu từ `specs/057-fix-ci-python-version/quickstart.md` và chạy build web hoàn chỉnh với `python scripts/build_web.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không phụ thuộc - có thể bắt đầu ngay.
- **Foundational (Phase 2)**: Phụ thuộc vào Setup - cung cấp regex helper cho US1 và US2.
- **User Stories (Phase 3 & Phase 4)**:
  - **US1 (P1)**: T003 (test) $\to$ T004 (code).
  - **US2 (P2)**: T005 (test) $\to$ T006 (code). Có thể chạy song song hoặc nối tiếp US1.
- **Polish (Phase 5)**: Chạy sau khi hoàn thành US1 và US2.

### Parallel Opportunities

- T003 [US1] và T005 [US2] có thể viết test cùng lúc.
- T007, T008, T009, T010 có thể chạy song song ở bước thẩm định chất lượng.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Hoàn thành Phase 1 & Phase 2 (T001, T002).
2. Hoàn thành Phase 3 (T003, T004): Khắc phục trực tiếp lỗi CI phân giải phiên bản Python.
3. Xác minh độc lập User Story 1 với `pytest tests/test_version_metadata.py`.

### Incremental Delivery

1. Setup + Foundational $\to$ Foundation sẵn sàng.
2. User Story 1 (P1) $\to$ Sửa `.python-version` thành `3.13` (MVP).
3. User Story 2 (P2) $\to$ Đồng bộ `render.yaml`.
4. Polish $\to$ Linting, Golden Master, 100% test suite pass.
