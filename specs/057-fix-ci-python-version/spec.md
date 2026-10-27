# Feature Specification: Khắc Phục Lỗi Phân Giải Phiên Bản Python Trên CI (057-fix-ci-python-version)

**Feature Branch**: `057-fix-ci-python-version`  
**Created**: 2026-10-27  
**Status**: Draft  
**Input**: User description: "Run actions/setup-python@v5 Resolved .python-version as 3.13.5 Installed versions Version 3.13.5 was not found in the local cache (node:2329) [DEP0040] DeprecationWarning: The `punycode` module is deprecated. Please use a userland alternative instead. (Use `node --trace-deprecation ...` to show where the warning was created) Error: The version '3.13.5' with architecture 'x64' was not found for Ubuntu 26.04. The list of all available versions can be found here: https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json tôi gặp lỗi này"

---

## Bối cảnh và Mục tiêu (Context & Objectives)

Khi thực thi quy trình kiểm thử tự động (CI) trên GitHub Actions, các công việc sử dụng công cụ thiết lập môi trường Python (`actions/setup-python`) đọc thông tin từ tệp cấu hình phiên bản `.python-version`. Tệp này hiện đang ghim cứng bản vá cụ thể `3.13.5`.

Trên máy chủ thực thi (runner) của GitHub Actions (đặc biệt khi hệ thống nâng cấp môi trường thực thi như Ubuntu 26.04 hoặc khi sử dụng cache công cụ cục bộ), bản vá cụ thể `3.13.5` không có sẵn trong bộ nhớ đệm và không nằm trong danh mục phân phối nhị phân dựng sẵn (`versions-manifest.json`). Hậu quả là quy trình CI bị dừng đột ngột với thông báo lỗi:
`Error: The version '3.13.5' with architecture 'x64' was not found for Ubuntu 26.04.`

Mục tiêu của tính năng này là:
1. Chuẩn hóa định dạng khai báo phiên bản trong `.python-version` sang mức phiên bản thứ cấp (minor version `3.13`), cho phép công cụ tự động phân giải và sử dụng bản vá mới nhất có sẵn trên runner mà không bị lỗi thiếu gói nhị phân.
2. Bảo đảm tính tương thích và đồng bộ của quy trình CI (`.github/workflows/ci.yml`) và cấu hình triển khai tĩnh (`render.yaml`).
3. Bổ sung bài kiểm tra tính hợp lệ của định dạng phiên bản để ngăn ngừa lỗi ghim cứng bản vá vi mô không tồn tại trong tương lai.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tự động Phân giải Môi trường Python Hợp lệ trên CI (Priority: P1) 🎯 MVP

Là một nhà phát triển phần mềm hoặc kỹ sư CI/CD, tôi muốn quy trình CI tự động nhận diện và thiết lập môi trường Python một cách linh hoạt dựa trên dòng phiên bản hỗ trợ, để các bước kiểm tra mã nguồn (lint) và kiểm thử ứng dụng (tests, build web) luôn thực thi thành công mà không bị chặn bởi lỗi thiếu bản vá nhị phân cụ thể trên hệ điều hành của runner.

**Why this priority**: Lỗi môi trường CI là lỗi chặn toàn bộ (blocking failure), khiến các pull request và commit không thể xác minh chất lượng tự động.

**Independent Test**:
- Kích hoạt quy trình CI hoặc chạy thử nghiệm công cụ phân giải phiên bản với tệp cấu hình `.python-version`.
- Xác nhận bước thiết lập Python tìm thấy và sử dụng phiên bản Python 3.13 tương thích, trả về mã trạng thái thành công (exit code 0).

**Acceptance Scenarios**:
1. **Given** tệp `.python-version` khai báo dòng phiên bản `3.13`,  
   **When** công cụ `actions/setup-python` phân giải phiên bản trên máy chủ CI,  
   **Then** hệ thống tự động ánh xạ tới bản vá tương thích mới nhất sẵn có trên máy chủ và hoàn tất thiết lập môi trường mà không ném lỗi `version not found`.
2. **Given** các công việc CI như kiểm tra mã nguồn (`lint`) và kiểm thử ứng dụng web (`web-client`),  
   **When** quy trình kiểm thử tự động khởi chạy,  
   **Then** bước khởi tạo Python hoàn tất thành công và cho phép các bước kiểm thử kế tiếp thực thi bình thường.

---

### User Story 2 - Đồng bộ hóa Cấu hình Triển khai và Metadata Phiên bản (Priority: P2)

Là một kỹ sư vận hành và duy trì hệ thống, tôi muốn tệp cấu hình triển khai (`render.yaml`) và các bài kiểm tra metadata trong dự án đồng bộ nhất quán về cách chỉ định phiên bản Python, bảo đảm quy trình build tự động trên nền tảng đám mây hoạt động ổn định.

**Why this priority**: Tránh sự phân mảnh giữa cấu hình CI cục bộ/GitHub và cấu hình môi trường triển khai thực tế.

**Independent Test**:
- Kiểm tra nội dung tệp `render.yaml` và chạy bài kiểm tra metadata `tests/test_version_metadata.py`.
- Xác nhận giá trị biến môi trường `PYTHON_VERSION` tuân thủ dòng phiên bản chuẩn và bài kiểm thử vượt qua 100%.

**Acceptance Scenarios**:
1. **Given** tệp cấu hình `render.yaml`,  
   **When** hệ thống triển khai đọc thông tin môi trường,  
   **Then** biến `PYTHON_VERSION` được đặt là `3.13` tương thích với quy chuẩn dự án.
2. **Given** bộ kiểm tra metadata phiên bản của dự án,  
   **When** chạy `pytest tests/test_version_metadata.py`,  
   **Then** bài kiểm tra xác nhận tệp `.python-version` tồn tại và chứa định dạng phiên bản hợp lệ.

---

## Edge Cases

- **Runner cập nhật phiên bản hệ điều hành mới**: Khi GitHub Actions nâng cấp phiên bản hệ điều hành nền tảng (ví dụ Ubuntu 24.04 lên Ubuntu 26.04), việc chỉ định `3.13` bảo đảm runner luôn chọn bản nhị phân dựng sẵn phù hợp cho kiến trúc hệ điều hành đó.
- **Công cụ quản lý môi trường cục bộ (pyenv, uv, mise)**: Các công cụ này đều hỗ trợ định dạng `3.13` trong `.python-version` và tự động chọn bản vá cục bộ cao nhất.
- **Tương thích đa phiên bản trong ma trận kiểm thử**: Ma trận kiểm thử `test-core` hiện đang dùng `['3.12', '3.13']`; việc thống nhất `3.13` không gây xung đột với ma trận kiểm thử.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tệp `.python-version` PHẢI chỉ định dòng phiên bản thứ cấp `3.13` (minor version) thay vì ghim cứng bản vá vi mô không khả dụng `3.13.5`.
- **FR-002**: Tệp cấu hình workflow `.github/workflows/ci.yml` PHẢI thiết lập môi trường Python thành công cho toàn bộ các công việc CI (`lint`, `test-core`, `web-client`, `test-python-314`).
- **FR-003**: Tệp cấu hình triển khai `render.yaml` PHẢI đồng bộ giá trị biến môi trường `PYTHON_VERSION` thành `3.13`.
- **FR-004**: Bộ kiểm thử metadata của dự án PHẢI có bài kiểm tra xác nhận tính hợp lệ của định dạng phiên bản trong `.python-version` (định dạng `^\d+\.\d+$`).

### Key Entities

- **Python Version Configuration (`.python-version`)**: Tệp văn bản chuẩn quy định phiên bản Python mục tiêu của dự án cho các công cụ CI và quản lý môi trường.
- **CI Workflow Configuration (`ci.yml`)**: Tệp định nghĩa quy trình tích hợp liên tục tự động trên GitHub Actions.
- **Deployment Blueprint (`render.yaml`)**: Tệp đặc tả cấu hình môi trường triển khai cho nền tảng đám mây.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 lỗi `version not found` phát sinh tại bước `Set up Python` trên toàn bộ các công việc của quy trình CI.
- **SC-002**: 100% các công việc CI phân giải và tải thành công runtime Python tương ứng trên runner Ubuntu.
- **SC-003**: 100% bài kiểm thử trong test suite (bao gồm bài kiểm thử metadata phiên bản mới) vượt qua thành công.

---

## Assumptions

- Phiên bản Python 3.13 là phiên bản chính thức được khuyến nghị cho môi trường CI của dự án, đồng thời mã nguồn hoàn toàn tương thích với Python 3.10 đến 3.14 như quy định trong `pyproject.toml`.
- Các công cụ CI hiện đại (như `actions/setup-python@v5`) ưu tiên phân giải phiên bản theo mẫu minor (`3.13`) để tự động áp dụng các bản vá bảo mật và tương thích hạ tầng runner.
