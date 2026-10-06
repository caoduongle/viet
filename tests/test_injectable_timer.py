"""Kiểm thử tiêm bộ hẹn giờ vào AppController (thay đổi lõi 3.1).
Cho phép môi trường đơn luồng (như Pyodide) hoặc test cô lập thay thế threading.Timer.
"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from chuviettay.controller.app_controller import AppController


class FakeTimer:
    """Mock timer không tạo luồng OS."""

    def __init__(self, interval: float, function, args=None, kwargs=None):
        self.interval = interval
        self.function = function
        self.args = args or []
        self.kwargs = kwargs or {}
        self.daemon = False
        self.started = False
        self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def trigger(self):
        self.function(*self.args, **self.kwargs)


def test_default_timer_is_threading_timer(tmp_path):
    """Mặc định controller vẫn dùng threading.Timer (không phá vỡ CPython/GUI)."""
    bank_path = str(tmp_path / "test.json.gz")
    ctl = AppController(bank_path)
    assert getattr(ctl, "timer_factory", threading.Timer) is threading.Timer


def test_injectable_timer_used_in_schedule_save(tmp_path):
    """Khi tiêm timer_factory, schedule_save gọi factory đó thay vì threading.Timer."""
    bank_path = str(tmp_path / "test.json.gz")
    created_timers: list[FakeTimer] = []

    def mock_factory(interval, func, args=None, kwargs=None):
        timer = FakeTimer(interval, func, args, kwargs)
        created_timers.append(timer)
        return timer

    ctl = AppController(bank_path, timer_factory=mock_factory)
    ctl.load_bank(bank_path, create_if_missing=True)

    ctl.schedule_save()
    assert len(created_timers) == 1
    t = created_timers[0]
    assert t.started is True
    assert t.cancelled is False
    assert t.interval == 2.0

    # Lên lịch lần 2 -> huỷ timer cũ, tạo timer mới
    ctl.schedule_save()
    assert len(created_timers) == 2
    assert t.cancelled is True
    assert created_timers[1].started is True

    # flush_save huỷ timer đang chờ
    ctl.flush_save()
    assert created_timers[1].cancelled is True
