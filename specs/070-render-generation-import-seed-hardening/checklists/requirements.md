# Specification Quality Checklist: Feature 070 - Render Generation, Import Generation, Export Stale Guard & Test Hardening

**Purpose**: Validate specification completeness and quality before proceeding to planning  
**Created**: 2026-11-01  
**Updated**: 2026-11-01 (Bổ sung kiểm chứng `renderedGeneration` & `renderedSnapshot` đầy đủ trong `canExport()`, bộ đếm `importGeneration` chống ghi đè khi mở nhiều tệp liên tiếp, kiểm thử Stage 2 giải nén XOPP có kiểm soát, xác định hóa E2E race condition và ổn định hóa bài kiểm thử XSS kho mẫu trên CI)  
**Feature**: [spec.md](../spec.md)  

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Đặc tả đã bao phủ trọn vẹn toàn bộ 5 nhóm cải tiến từ báo cáo rà soát commit `53258d2`:
  1. **P1 – Khóa xuất tệp theo `renderedGeneration` và `renderedSnapshot` (gồm cả `writeOptions` và `format`)**: Ngăn xuất nhầm tài liệu cũ khi người dùng đổi tùy chọn viết chữ hoặc khi lần kết xuất mới bị lỗi.
  2. **P2 – Kiểm thử trực tiếp Stage 2 Stale Guard (giải nén XOPP bị trì hoãn)**: Chứng minh kết quả giải nén muộn bị loại bỏ trước khi cam kết.
  3. **P2 – Kiểm soát thế hệ nhập tệp (`currentImportGeneration`)**: Ngăn chặn kết quả đọc/chuyển đổi tệp cũ (.docx vs .txt/.md) hoàn tất muộn ghi đè lên tệp được chọn sau cùng.
  4. **P2 – Xác định hóa hoàn toàn bài kiểm thử E2E Race Condition**: Điều khiển thời điểm phản hồi của tiến trình nền thay vì chờ thời gian cố định.
  5. **P3 – Dọn dẹp `debounceTimer` và ổn định hóa bài kiểm thử XSS trên CI (`bank.spec.ts:137`)**: Loại bỏ tranh chấp thời điểm với `refreshBankView()` khi chạy đa luồng `--workers=2`.
- Toàn bộ 16/16 tiêu chí kiểm định chất lượng đều ĐẠT (PASS). Đã sẵn sàng cho giai đoạn lập kế hoạch chi tiết (`/speckit-plan`).
