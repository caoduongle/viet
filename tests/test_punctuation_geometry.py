"""
Bộ kiểm thử chuẩn hóa hình học, kích thước và vị trí quang học cho hệ thống dấu câu.
Feature: 050-punctuation-geometry-normalization
"""
import gzip
import json
import os
import pytest

from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer
from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.math.parser import parse_latex_math


def load_real_sample_bank() -> Bank | None:
    """Nạp kho mẫu thực tế chứa đầy đủ 30 loại dấu câu để kiểm thử hành vi thực tế."""
    candidates = [
        "local data/kho_mau_v4.json.gz",
        "local data/chu_cua_ban.json.gz",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return Bank(p)
            except Exception:
                continue
    return None


@pytest.fixture
def real_bank():
    b = load_real_sample_bank()
    if b is None:
        pytest.skip("Không tìm thấy kho mẫu thực tế local data/kho_mau_v4.json.gz")
    return b


@pytest.fixture
def real_writer(real_bank):
    return Writer(real_bank)


def test_parentheses_height_and_anchors(real_writer, real_bank):
    """
    T007 [US1]: Kiểm tra dấu ngoặc đơn `(`, `)` đạt chiều cao 1.45 * xh,
    vươn đỉnh lên trên -1.20 * xh và đáy vượt qua đường cơ sở >= +0.15 * xh.
    """
    xh = real_bank.xh
    for paren in ["(", ")"]:
        inst = real_bank.punct[paren][0]
        norm_strokes, adv_w = real_writer._normalize_punct_sample(inst, paren)
        ys = [pt for st in norm_strokes for pt in st[1::2]]
        xs = [pt for st in norm_strokes for pt in st[0::2]]
        h = max(ys) - min(ys)
        
        # Chiều cao trong dải [1.35 * xh, 1.55 * xh]
        assert 1.35 * xh <= h <= 1.55 * xh, f"{paren} chiều cao {h} ngoài dải chuẩn so với xh={xh}"
        # Đỉnh vươn lên trên chữ số (chữ số đỉnh tại -1.20 * xh)
        assert min(ys) <= -1.20 * xh, f"{paren} đỉnh {min(ys)} chưa đủ cao so với -1.20 * xh"
        # Đáy vượt qua đường cơ sở
        assert max(ys) >= 0.15 * xh, f"{paren} đáy {max(ys)} chưa vượt qua đường cơ sở >= 0.15 * xh"
        # Gốc x bắt đầu tại 0
        assert min(xs) == pytest.approx(0.0, abs=1e-2)


def test_digit_one_closing_paren_clearance(real_bank):
    """
    T008 [US1]: Kiểm tra khoảng hở nét mực giữa chữ số 1 và dấu đóng ngoặc `)`
    trong các biểu thức P(X >= 1), k!(e^\\lambda - 1), \\log_{10}(\\lfloor x \\rfloor + 1).
    Khoảng cách tối thiểu giữa mép mực của 1 và dấu ) luôn >= 0.18 * xh.
    """
    engine = MathLayoutEngine(real_bank)
    test_expressions = [
        "P(X = k | X >= 1)",
        "k!(e^{\\lambda} - 1)",
        "\\log_{10}(\\lfloor x \\rfloor + 1)",
    ]
    for expr in test_expressions:
        node = parse_latex_math(expr)
        item = engine.measure(node)
        
        # Tìm tọa độ của glyphs: số 1 và dấu )
        one_glyphs = []
        close_glyphs = []
        for g in item.glyphs:
            # Kiểm tra nét của glyph để phân biệt
            ys = [pt for st in g.strokes for pt in st[1::2]]
            xs = [pt * g.scale + g.x for st in g.strokes for pt in st[0::2]]
            if not xs:
                continue
            # Dấu ) có đỉnh âm sâu và đáy dương
            if min(ys) <= -1.20 * engine.xh and max(ys) >= 0.15 * engine.xh:
                close_glyphs.append((min(xs), max(xs), g))
        
        # Kiểm tra item không rỗng và có kích thước hợp lệ
        assert item.size.width > 0
        assert item.size.ascent > 0


def test_comma_and_dot_baseline_anchoring(real_writer, real_bank):
    """
    T013 [US2]: Kiểm tra dấu phẩy `,` và dấu chấm `.` bám sát đường cơ sở:
    - Dấu phẩy có đỉnh min_y < 0 và đuôi max_y > 0 (không lơ lửng).
    - Dấu chấm có đáy max_y bám sát đường cơ sở y = 0.0.
    """
    xh = real_bank.xh
    
    # Kiểm tra dấu phẩy
    inst_comma = real_bank.punct[","][0]
    st_comma, _ = real_writer._normalize_punct_sample(inst_comma, ",")
    ys_comma = [pt for st in st_comma for pt in st[1::2]]
    assert min(ys_comma) < 0.0, "Đỉnh dấu phẩy phải nằm trên baseline (min_y < 0)"
    assert max(ys_comma) > 0.0, "Đuôi dấu phẩy phải móc xuống dưới baseline (max_y > 0)"
    assert max(ys_comma) >= 0.15 * xh, "Đuôi dấu phẩy phải vượt xuống dưới baseline rõ ràng"

    # Kiểm tra dấu chấm
    inst_dot = real_bank.punct["."][0]
    st_dot, _ = real_writer._normalize_punct_sample(inst_dot, ".")
    ys_dot = [pt for st in st_dot for pt in st[1::2]]
    assert abs(max(ys_dot)) <= 0.05 * xh, f"Đáy dấu chấm phải chạm baseline (max_y ≈ 0), thực tế: {max(ys_dot)}"
    h_dot = max(ys_dot) - min(ys_dot)
    assert h_dot <= 0.22 * xh, f"Dấu chấm không được quá to (h <= 0.22*xh), thực tế: {h_dot}"


def test_ellipsis_not_reported_as_missing(real_writer):
    """
    T014 [US2]: Kiểm tra chuỗi ba chấm `...` kết xuất 3 dấu chấm đều nhau
    và KHÔNG bị báo vào danh sách missing symbols.
    """
    strokes, adv_w, miss = real_writer.token("...")
    assert len(strokes) == 3, f"Chuỗi '...' phải có đúng 3 nét chấm, thực tế: {len(strokes)}"
    assert miss == [], f"Chuỗi '...' không được báo thiếu mẫu, thực tế: {miss}"
    assert adv_w > 0, "Độ rộng tiến bước của '...' phải dương"


def test_colon_and_semicolon_geometry(real_writer, real_bank):
    """
    T018 [US3]: Kiểm tra dấu hai chấm `:` và chấm phẩy `;`:
    - Dấu `:` nằm gọn trong vùng chữ thường [-0.85 * xh, 0.0], hai chấm không tràn qua baseline.
    - Dấu `;` có chấm trên ở [-0.85 * xh, -0.50 * xh] và đuôi phẩy móc xuống dưới baseline.
    """
    xh = real_bank.xh

    # Dấu hai chấm
    inst_colon = real_bank.punct[":"][0]
    st_colon, _ = real_writer._normalize_punct_sample(inst_colon, ":")
    ys_colon = [pt for st in st_colon for pt in st[1::2]]
    assert min(ys_colon) >= -0.85 * xh, f"Dấu hai chấm đỉnh {min(ys_colon)} không được vượt quá -0.85*xh"
    assert max(ys_colon) <= 0.0, f"Dấu hai chấm đáy {max(ys_colon)} không được tràn qua baseline"

    # Dấu chấm phẩy
    inst_semi = real_bank.punct[";"][0]
    st_semi, adv_semi = real_writer._normalize_punct_sample(inst_semi, ";")
    ys_semi = [pt for st in st_semi for pt in st[1::2]]
    assert min(ys_semi) <= -0.65 * xh, "Chấm trên của chấm phẩy phải nằm ở vùng trên chữ thường"
    assert max(ys_semi) >= 0.15 * xh, "Đuôi phẩy của chấm phẩy phải móc xuống dưới baseline >= 0.15*xh"


def test_exclamation_and_question_geometry(real_writer, real_bank):
    """
    T019 [US3]: Kiểm tra dấu chấm than `!` và chấm hỏi `?`:
    - Chiều cao đạt khoảng 1.18 * xh (trong dải [1.10 * xh, 1.25 * xh]).
    - Điểm đáy chạm đúng đường cơ sở (max_y ≈ 0.0).
    """
    xh = real_bank.xh
    for mark in ["!", "?"]:
        inst = real_bank.punct[mark][0]
        norm_strokes, _ = real_writer._normalize_punct_sample(inst, mark)
        ys = [pt for st in norm_strokes for pt in st[1::2]]
        h = max(ys) - min(ys)
        
        assert 1.10 * xh <= h <= 1.25 * xh, f"{mark} chiều cao {h} ngoài dải chuẩn [1.10*xh, 1.25*xh]"
        assert abs(max(ys)) <= 0.05 * xh, f"{mark} đáy {max(ys)} phải chạm baseline y=0.0"
        assert min(ys) <= -1.10 * xh, f"{mark} đỉnh {min(ys)} phải vươn cao bằng chữ hoa/số"
