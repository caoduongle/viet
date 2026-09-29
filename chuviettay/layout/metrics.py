"""Đặc tả hình học và chỉ số typographic cho động cơ bố cục nét chữ."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Size:
    """Kích thước hình học và các mốc căn lề theo chuẩn in ấn (typographic metrics).

    - width: Bề rộng bao ngoài (pt).
    - height: Chiều cao bao ngoài (pt).
    - ascent: Khoảng cách từ đường cơ sở (baseline) lên đỉnh cao nhất của ký tự (pt).
    - descent: Khoảng cách từ đường cơ sở (baseline) xuống đáy sâu nhất của ký tự (pt).
    - baseline: Toạ độ tương đối từ đỉnh trên xuống đường cơ sở (baseline = ascent).
    """
    width: float
    height: float
    ascent: float = 0.0
    descent: float = 0.0
    baseline: float = 0.0

    @classmethod
    def from_box(cls, width: float, height: float, baseline_ratio: float = 0.8) -> Size:
        """Tạo Size đơn giản từ rộng và cao, tự suy ra baseline."""
        ascent = round(height * baseline_ratio, 2)
        descent = round(height - ascent, 2)
        return cls(width=width, height=height, ascent=ascent, descent=descent, baseline=ascent)


TypographicMetrics = Size


@dataclass
class PositionedGlyph:
    """Một mẫu nét chữ hoặc ký hiệu đặt tại toạ độ tuyệt đối trên trang giấy."""
    strokes: list[list[float]]
    x: float
    y: float
    scale: float = 1.0


@dataclass
class PositionedStroke:
    """Nét vẽ vector hình học (đường viền bảng, gạch ngang phân số, nét căn thức)."""
    points: list[tuple[float, float]]
    width: float = 1.41
    color: str | None = None
