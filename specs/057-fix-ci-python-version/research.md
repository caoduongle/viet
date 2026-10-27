# Phase 0 Research: Chuẩn Hóa Phân Giải Phiên Bản Python Trên CI & Render

**Feature**: `057-fix-ci-python-version`  
**Date**: 2026-10-27  
**Status**: Completed  

---

## 1. Nghiên cứu Kỹ thuật & Quyết định

### Nghiên cứu 1: Cơ chế tìm kiếm phiên bản của `actions/setup-python@v5`

- **Vấn đề thực tế**:
  - Khi `actions/setup-python@v5` được cấu hình với `python-version-file: '.python-version'`, nó đọc chuỗi bên trong tệp này.
  - Nếu tệp ghi `3.13.5`: action coi đây là yêu cầu phiên bản tuyệt đối (exact micro/patch version). Nó sẽ kiểm tra thư mục công cụ cục bộ `/opt/hostedtoolcache/Python/3.13.5/x64`. Nếu không có, nó tải `versions-manifest.json` từ kho lưu trữ `actions/python-versions`.
  - Trên các bản phát hành Ubuntu của GitHub Actions (ví dụ `ubuntu-latest`, hiện tại là Ubuntu 24.04 hoặc bản thử nghiệm 26.04), các bản vá cụ thể chưa được build sẵn hoặc chưa được phát hành (như `3.13.5`) sẽ không có mặt trong manifest. Action sẽ ném lỗi:
    `Error: The version '3.13.5' with architecture 'x64' was not found for Ubuntu 26.04.`
- **Quyết định thiết kế**:
  - Chuyển giá trị trong `.python-version` từ `3.13.5` thành `3.13`.
  - Với giá trị `3.13`, `setup-python` sẽ tự động tìm kiếm phiên bản `3.13.x` cao nhất hiện có trong local tool cache hoặc trong manifest dựng sẵn cho hệ điều hành đó. Điều này bảo đảm CI luôn tìm thấy phiên bản tương thích và không bao giờ bị lỗi thiếu gói nhị phân.
- **Lựa chọn thay thế đã xem xét**:
  - *Hardcode phiên bản cụ thể khác như 3.13.0*: Bị từ chối vì khi GitHub cập nhật tool cache lên bản vá cao hơn (ví dụ 3.13.1, 3.13.2), việc ghim cứng 3.13.0 lại tiếp tục có nguy cơ bị lỗi hoặc buộc phải tải lại từ mạng thay vì dùng cache. Khai báo `3.13` là chuẩn khuyến nghị chính thức của GitHub Actions.
  - *Sử dụng `3.13.x`*: Chuẩn pyenv và nhiều tool runner khuyến nghị `3.13` ngắn gọn, cả pyenv và GitHub setup-python đều hiểu `3.13` là `3.13.*`.

---

### Nghiên cứu 2: Đồng bộ hóa cấu hình `render.yaml`

- **Vấn đề thực tế**:
  - `render.yaml` hiện đang khai báo biến môi trường:
    ```yaml
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.5
    ```
  - Trên hạ tầng Render Static Sites, Render sử dụng biến này để cài đặt Python. Ghim cứng `3.13.5` tiềm ẩn rủi ro khi phiên bản runtime của Render chưa cập nhật tới bản vá này.
- **Quyết định thiết kế**:
  - Đồng bộ `PYTHON_VERSION` trong `render.yaml` thành `3.13`.
- **Lựa chọn thay thế đã xem xét**:
  - Giữ nguyên `render.yaml`: Bị từ chối vì không bảo đảm tính nhất quán trong toàn bộ dự án.

---

### Nghiên cứu 3: Kiểm thử tự động tính hợp lệ của metadata phiên bản

- **Vấn đề thực tế**:
  - Hiện tại, file `tests/test_version_metadata.py` kiểm tra `pyproject.toml`, `package.json`, `CHANGELOG.md` và `version.json`, nhưng chưa kiểm tra `.python-version`.
- **Quyết định thiết kế**:
  - Bổ sung hàm kiểm thử `test_python_version_file_format()` trong `tests/test_version_metadata.py`:
    - Xác nhận tệp `.python-version` tồn tại.
    - Xác nhận nội dung chỉ định dòng minor hợp lệ (mẫu regex `^\d+\.\d+$`, ví dụ `3.13`), không ghim bản vá vi mô dư thừa.
- **Lựa chọn thay thế đã xem xét**:
  - Không thêm test: Bị từ chối vì vi phạm nguyên tắc III của Constitution (Comprehensive Automated Testing).

---

## 2. Kết luận Nghiên cứu

Tất cả các câu hỏi kỹ thuật đã được làm rõ hoàn toàn (`NEEDS CLARIFICATION: 0`). Đủ điều kiện chuyển sang Phase 1.
