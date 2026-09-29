"""Quản lý các thư viện phụ thuộc tuỳ chọn (optional dependencies) cho các bộ nạp tài liệu."""
from __future__ import annotations

import importlib
from typing import Any


class OptionalDependencyError(RuntimeError):
    """Ném ra khi người dùng gọi tính năng yêu cầu thư viện mở rộng chưa được cài đặt."""

    def __init__(self, message: str, package_name: str, extra: str = "docs"):
        super().__init__(message)
        self.package_name = package_name
        self.extra = extra


def check_dependency(module_name: str) -> bool:
    """Kiểm tra xem một module có sẵn trong môi trường hay không mà không gây lỗi."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def require_dependency(module_name: str, feature_desc: str = "tính năng này", extra: str = "docs") -> Any:
    """Nạp một module tuỳ chọn. Nếu chưa cài đặt, ném OptionalDependencyError kèm hướng dẫn cụ thể."""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise OptionalDependencyError(
            f"Để mở {feature_desc}, bạn cần cài đặt thêm thư viện '{module_name}'. "
            f'Hãy chạy lệnh: pip install ".[{extra}]" hoặc tải bản đóng gói đầy đủ.',
            package_name=module_name,
            extra=extra,
        ) from exc
