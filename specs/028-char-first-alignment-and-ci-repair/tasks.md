# Tasks: Đồng Bộ Mô Hình Char-First, Khắc Phục Dấu Thanh & Sửa Lỗi CI Toàn Diện

**Feature Branch**: `028-char-first-alignment-and-ci-repair`  
**Input**: Design artifacts from `specs/028-char-first-alignment-and-ci-repair/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Thiết lập môi trường và cấu trúc tiền đề cho tính năng

- [X] T001 Khảo sát và xác nhận trạng thái môi trường phát triển, phụ thuộc và bộ test nền tảng trong repo root
- [X] T002 [P] Tạo bộ test helper và kịch bản chạy xác thực trong `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Hạ tầng lõi BẮT BUỘC phải hoàn thành trước khi triển khai các User Story

> ⚠️ **CRITICAL**: Không bắt đầu triển khai các User Story cho đến khi giai đoạn nền tảng này hoàn tất.

- [X] T003 [P] Chuẩn hóa hợp đồng kiểm tra khả năng viết đơn nguồn (single-source render readiness) trong `chuviettay/model/bank.py` theo `contracts/render-readiness-contract.md`
- [X] T004 [P] Triển khai hàm tính khoảng cách giữa hai đoạn thẳng 2D `segment_distance(p1, p2, q1, q2)` có xử lý đoạn suy biến (degenerate segments: point-to-segment, point-to-point) trong `chuviettay/model/text_utils.py` theo `contracts/stroke-clearance-geometry-contract.md`

**Checkpoint**: Nền tảng thuật toán và hợp đồng sẵn sàng - có thể bắt đầu các User Story.

---

## Phase 3: User Story 1 - Đồng bộ Hợp đồng Char-First & Kiểm tra Khả năng Viết Thống Nhất (Priority: P1) 🎯 MVP

**Goal**: Đảm bảo 100% tính nhất quán giữa bộ kiểm tra kho mẫu (`Bank.can()`) và bộ kết xuất văn bản (`Writer`), loại bỏ hoàn toàn việc kiểm tra `words` và `tl` cũ khi xác định khả năng viết.

**Independent Test**: Nạp kho mẫu chỉ có từ "xin" trong `words` nhưng không có các chữ cái 'x', 'i', 'n'. Hệ thống xác định "xin" không thể viết được (`Bank.can("xin") == False`). Khi nạp đủ các chữ cái thành phần, `Bank.can("xin")` trả về `True`.

### Tests cho User Story 1 🧪

- [X] T005 [P] [US1] Viết unit test kiểm chứng `Bank.can()` char-first (kho chỉ có từ cũ báo False; kho đủ chữ cái + dấu thanh báo True; kiểm tra `strict_case`) trong `tests/test_bank.py`
- [X] T006 [P] [US1] Viết unit test kiểm chứng `missing_letters_ranked` loại bỏ phụ thuộc vào `words_bank` trong `tests/test_letter_assembly.py`

### Implementation cho User Story 1

- [X] T007 [US1] Cập nhật phương thức `can(w, strict_case=False)` trong `chuviettay/model/bank.py`: loại bỏ hoàn toàn kiểm tra `words` và `tl`, triển khai cơ chế kiểm tra Dual-Path theo `contracts/render-readiness-contract.md`
- [X] T008 [US1] Cập nhật hàm `missing_letters_ranked()` trong `chuviettay/model/text_utils.py`: gỡ bỏ nhánh kiểm tra `words_bank[ch]` để đồng bộ hoàn toàn với `Bank.can()`
- [X] T009 [US1] Cập nhật các hàm truy vấn trong `chuviettay/controller/app_controller.py` (`missing_seed_words`, `missing_minimal_essentials`) gọi `Bank.can()` chuẩn hóa
- [X] T010 [US1] Chạy kiểm thử xác nhận độc lập cho User Story 1 với `pytest tests/test_bank.py tests/test_letter_assembly.py`

**Checkpoint**: User Story 1 hoàn thành độc lập - cốt lõi hợp đồng char-first đã được đồng bộ 100%.

---

## Phase 4: User Story 2 - Hoàn thiện Quy Trình Dạy & Kiểm Tra Toàn Diện Cho Dấu Thanh (Priority: P1)

**Goal**: Web Client không phân rã nhãn dấu thanh danh mục thành từng chữ cái rời rạc; bảo toàn đầy đủ các nét của dấu thanh đa nét khi dạy trực tiếp; xuất file kiểm tra `.xopp` bao phủ đầy đủ 5 dấu thanh với nhãn tiếng Việt và tọa độ hiển thị chuẩn.

**Independent Test**: Trên Web Client, nạp bộ ký tự "Dấu thanh rời" $\to$ hàng đợi giữ nguyên 5 nhãn nghiệp vụ (`dấu huyền`, `dấu sắc`, `dấu hỏi`, `dấu ngã`, `dấu nặng`). Vẽ dấu thanh với 2 nét bút rời $\to$ lưu và nạp lại kho vẫn đủ 2 nét. Xuất file kiểm tra `.xopp` $\to$ chứa đầy đủ các ô mẫu dấu thanh ở vị trí chuẩn.

### Tests cho User Story 2 🧪

- [X] T011 [P] [US2] Viết unit test lưu và nạp lại mẫu dấu thanh đa nét ($N \ge 2$ nét bút) trong `tests/test_controller.py`
- [X] T012 [P] [US2] Viết unit test kiểm chứng `export_check()` bao phủ đầy đủ 5 dấu thanh từ `bank.marks` kèm nhãn tiếng Việt và offset $dy$ trong `tests/test_controller.py`
- [X] T013 [P] [US2] Viết unit test JavaScript cho hàng đợi dạy chữ (`tests/js/teach_queue.test.mjs`): kiểm tra `addCatalogLabels` bảo toàn nhãn nguyên tử và `addCharactersFromText` tách code points

### Implementation cho User Story 2

- [X] T014 [US2] Sửa phương thức `teach_char()` trong `chuviettay/controller/app_controller.py`: truyền toàn bộ danh sách `rel_strokes` thay vì `rel_strokes[0]` vào `bank.add_tone_sample()`
- [X] T015 [US2] Cập nhật phương thức `add_tone_sample()` trong `chuviettay/model/bank.py`: chuẩn hóa tính trọng tâm và bảo toàn toàn bộ danh sách nét cho mẫu dấu thanh đa nét
- [X] T016 [US2] Cập nhật phương thức `export_check()` trong `chuviettay/controller/app_controller.py`: đưa 5 dấu thanh từ `bank.marks` vào danh sách xuất kèm nhãn tiếng Việt và tịnh tiến offset $dy$ ($dy = -1.25 \cdot xh$ cho dấu trên, $dy = +0.30 \cdot xh$ cho dấu nặng)
- [X] T017 [US2] Cập nhật module `webapp/js/teach.js`: tách rõ hai hàm `addCharactersFromText(text)` (xử lý ô gõ văn bản) và `addCatalogLabels(labels)` (xử lý nhãn danh mục nguyên tử) theo `contracts/web-teach-queue-contract.md`
- [X] T018 [US2] Cập nhật hàm `addCharGroupToQueue()` và Modal Bộ Ký Tự trong `webapp/js/teach.js`: gọi `addCatalogLabels(res.tokens)` để nạp danh mục mà không băm nhỏ nhãn dấu thanh
- [X] T019 [US2] Chạy kiểm thử xác nhận độc lập cho User Story 2 với `pytest tests/test_controller.py` và `npm run test:unit`

**Checkpoint**: User Stories 1 và 2 đều hoàn tất và hoạt động độc lập.

---

## Phase 5: User Story 3 - Củng Cố Kiểm Chứng Hình Học Chống Dính Nét & Chuẩn Hóa Giao Diện/Tài Liệu (Priority: P2)

**Goal**: Nâng cấp thuật toán `min_stroke_clearance` sang đo khoảng cách đoạn thẳng 2D kèm bounding box prune; sửa hướng dịch chuyển dấu nặng $cy += ...$ trong Writer; chuẩn hóa hiển thị thống kê Desktop GUI và khôi phục 100% CI xanh (pytest và Playwright).

**Independent Test**: Ghép các từ tiếng Việt phức tạp có dấu thanh và nét vươn dài, kiểm chứng khoảng cách giữa các đoạn nét liền kề luôn $\ge clearance\_floor$. Kiểm thử Desktop GUI và Playwright E2E vượt qua 100% không có lỗi.

### Tests cho User Story 3 🧪

- [X] T020 [P] [US3] Viết unit tests kiểm chứng `segment_distance` và `min_stroke_clearance` (đoạn cắt nhau, song song, điểm suy biến dot, bounding box prune) trong `tests/test_text_utils.py`
- [X] T021 [P] [US3] Viết unit tests kiểm chứng định dạng nhãn thống kê kho mẫu theo chuẩn char-first trong `tests/test_formatting.py`

### Implementation cho User Story 3

- [X] T022 [US3] Tích hợp thuật toán khoảng cách đoạn thẳng 2D vào `chuviettay/model/text_utils.py:min_stroke_clearance`: thay thế phép so sánh đỉnh rời rạc bằng so sánh đoạn thẳng kết hợp bounding box prune theo `contracts/stroke-clearance-geometry-contract.md`
- [X] T023 [US3] Sửa hướng dịch chuyển dấu nặng khi cưỡng chế sàn khe hở vật lý trong `chuviettay/model/writer.py:assemble_word`: khi $T == NANG$, dịch chuyển $cy += (clearance\_floor - dist\_mark)$ xuống dưới thay vì trừ $cy$
- [X] T024 [US3] Cập nhật hàm `format_stats_gui()` trong `chuviettay/formatting.py`: hiển thị dòng tiêu đề chính theo tổng số ký tự có mẫu và số mẫu nét, kèm phụ chú mẫu từ cũ nếu có
- [X] T025 [US3] Cập nhật `chuviettay/view/bank_tab.py`: làm mới nhãn thống kê và đồng bộ hóa thao tác xóa hàng loạt qua `selected_items()`
- [X] T026 [US3] Cập nhật các bài kiểm thử Desktop GUI trong `tests/test_gui.py`: sửa các assertion kỳ vọng cũ (`word_list.size()`, `stats_lbl`, `test_tim_kiem_loc_danh_sach`, `test_xoa_tu_dung_tu_duoc_chon_ke_ca_khi_dang_loc`)
- [X] T027 [US3] Cập nhật các kịch bản kiểm thử Playwright E2E trong `tests/e2e/bank.spec.ts` (tìm kiếm ký tự thay vì từ "xin") và `tests/e2e/teach.spec.ts` (kiểm tra hàng đợi ký tự)
- [X] T028 [US3] Chạy kiểm thử xác nhận độc lập cho User Story 3 với `pytest tests/test_text_utils.py tests/test_gui.py` và `npx playwright test`

**Checkpoint**: Toàn bộ 3 User Stories hoàn tất đầy đủ.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hoàn thiện tài liệu, rà soát mã nguồn và kiểm chứng toàn diện toàn bộ pipeline CI

- [X] T029 [P] Cập nhật tài liệu hướng dẫn trong `README.md` phản ánh mô hình học char-first, hướng dẫn dạy dấu thanh và cách kiểm tra kho mẫu
- [X] T030 [P] Chạy kiểm tra lint toàn diện với `ruff check .` và khắc phục triệt để các cảnh báo mã nguồn
- [X] T031 Chạy toàn bộ test suite CI (`pytest -vv --timeout=30 -m "not benchmark"`, `npm run test:unit`, `npm run test:browser`, `npx playwright test --workers=2`) theo `quickstart.md`, xác nhận đạt trạng thái 100% CI xanh (0 failures)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc - thực hiện ngay
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1 - CHẶN toàn bộ các User Story
- **User Story 1 (Phase 3 - MVP)**: Phụ thuộc vào Phase 2 - Không phụ thuộc vào Story khác
- **User Story 2 (Phase 4)**: Phụ thuộc vào Phase 2 và Phase 3 - Mở rộng quy trình dấu thanh dựa trên nền tảng char-first
- **User Story 3 (Phase 5)**: Phụ thuộc vào Phase 2, Phase 3, Phase 4 - Hoàn thiện hình học, giao diện và bộ test suite
- **Polish (Phase 6)**: Phụ thuộc vào việc hoàn tất toàn bộ 3 User Stories

### User Story Dependencies

- **US1 (P1)**: Xây dựng nền tảng hợp đồng `Bank.can()` char-first
- **US2 (P1)**: Dựa trên nền tảng char-first của US1 để hoàn thiện luồng dấu thanh trên Web Client, Controller và `.xopp`
- **US3 (P2)**: Cải tiến hình học `min_stroke_clearance` và cập nhật các bộ kiểm thử tự động phản ánh đúng hành vi của US1 và US2

### Parallel Opportunities

- Các task đánh dấu `[P]` có thể thực thi song song vì thao tác trên các tệp độc lập:
  - `T003`, `T004` trong Foundational phase
  - `T005`, `T006` trong User Story 1
  - `T011`, `T012`, `T013` trong User Story 2
  - `T020`, `T021` trong User Story 3
  - `T029`, `T030` trong Polish phase

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Hoàn thành Phase 1 (Setup) và Phase 2 (Foundational: `Bank.can()` contract & `segment_distance`)
2. Hoàn thành Phase 3 (User Story 1)
3. Chạy kiểm thử xác nhận `Bank.can()` char-first đạt 100% PASS

### Incremental Delivery

1. Setup + Foundational $\to$ Nền tảng hợp đồng vững chắc
2. Thêm User Story 1 $\to$ Đồng bộ `Bank.can()` & `Writer` (MVP đạt được)
3. Thêm User Story 2 $\to$ Dấu thanh Web Client, đa nét, và file `.xopp` chuẩn xác
4. Thêm User Story 3 $\to$ Nâng cấp hình học chống bết mực & khôi phục CI xanh 100%
5. Polish $\to$ Cập nhật `README.md`, chạy `ruff`, và kiểm tra toàn diện
