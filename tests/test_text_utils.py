"""Hàm thuần xử lý chữ/hình học -- nhóm dễ test nhất, đáp án tự tính tay được."""
from chuviettay.config import NANG
from chuviettay.model import text_utils as tu


def test_fmt_bo_so_0_thua():
    assert tu.fmt(1.0) == "1"
    assert tu.fmt(1.5) == "1.5"
    assert tu.fmt(0) == "0"
    assert tu.fmt(3.14159) == "3.142"


def test_clamp():
    assert tu.clamp(5, 0, 3) == 3
    assert tu.clamp(-1, 0, 3) == 0
    assert tu.clamp(2, 0, 3) == 2


def test_weight_theo_loai_ky_tu():
    assert tu.weight("i") == 0.55           # chữ hẹp
    assert tu.weight("m") == 1.5            # chữ rộng
    assert tu.weight("A") == 1.25           # chữ hoa
    assert tu.weight("a") == 1.0
    assert tu.weight("im") == 0.55 + 1.5
    assert tu.weight("-") == 0.8            # ký tự khác


def test_tone_info():
    assert tu.tone_info("ba") == ("", -1, 0, ["b", "a"])
    tone, vi, hats, letters = tu.tone_info("bà")
    assert (tone, vi, hats, letters) == ("\u0300", 1, 0, ["b", "a"])
    tone, vi, hats, letters = tu.tone_info("tôi")           # dấu mũ đếm riêng, không phải dấu thanh
    assert (tone, vi, hats, letters) == ("", -1, 1, ["t", "o", "i"])
    tone, vi, _, _ = tu.tone_info("hỏi")
    assert (tone, vi) == ("\u0309", 1)
    assert tu.tone_info("bạ")[0] == NANG


def test_strip_tone_chi_bo_dau_thanh():
    assert tu.strip_tone("bà") == "ba"
    assert tu.strip_tone("số") == tu.strip_tone("sổ") == "sô"   # giữ dấu mũ
    assert tu.strip_tone("ba") == "ba"


def test_vowel_x_ty_le_theo_do_rong_chu_cai():
    # 2 chữ cái cùng độ rộng, nguyên âm là chữ thứ 2 -> tâm của nửa sau = 3/4 bề rộng
    assert tu.vowel_x(["b", "a"], 1, 10) == 7.5


def test_near_extreme_va_du_phong():
    strokes = [[0, 1, 1, 5, 10, 9]]
    assert tu.near_extreme(strokes, 0.5, max) == 5        # chỉ xét điểm có |x-0.5| <= 5
    assert tu.near_extreme(strokes, 0.5, min) == 1
    assert tu.near_extreme(strokes, 100, max) == 9        # không điểm nào gần -> xét tất cả
    assert tu.near_extreme([], 0, max) == 0.0


def test_shift_bbox():
    assert tu.shift([1, 2, 3, 4], 1, 10) == [2, 12, 4, 14]
    assert tu.bbox([1, 5, 4, 2, 3, 9]) == (1, 2, 4, 9)


def test_find_tone_dau_huyen_sac_hoi_nga():
    xh = 7.0
    body = [0, 0, 5, -5, 10, 0]
    tone_stroke = [4, -12, 6, -10]                          # nằm cao hơn cỡ chữ thường, ngắn
    assert tu.find_tone([body, tone_stroke], "bà", xh) == 1
    assert tu.find_tone([body], "ba", xh) == -1              # từ không dấu
    assert tu.find_tone([body], "bà", xh) == -1              # có dấu mà không thấy nét dấu nào


def test_find_tone_dau_nang_nam_duoi_dong_ke():
    xh = 7.0
    body = [0, 0, 10, -5]
    dot_below = [5, 3, 5.5, 3.5]
    assert tu.find_tone([body, dot_below], "bạ", xh) == 1


def test_find_tone_dau_thanh_tren_chu_i_thi_khong_con_cham_i():
    # "bì": dấu huyền nằm ngay trên chữ i nên chữ i không còn chấm -> chỉ cần 1 nét "nằm cao"
    xh = 7.0
    body = [0, 0, 5, -5, 10, 0]
    tone_stroke = [4, -12, 6, -10]
    assert tu.find_tone([body, tone_stroke], "bì", xh) == 1


def test_find_tone_dem_du_so_net_nam_cao_moi_dam_ket_luan():
    # "tiền" = dấu huyền + dấu mũ (ê) + chấm của chữ i -> phải thấy ĐÚNG 3 nét nằm cao
    xh = 7.0
    body = [0, 0, 5, -5, 10, 0]
    high = [[2, -12, 3, -11], [5, -12, 6, -11], [8, -12, 9, -11]]
    assert tu.find_tone([body, *high], "tiền", xh) == 3          # đủ 3 -> trả về nét cao cuối cùng
    assert tu.find_tone([body, high[0]], "tiền", xh) == -1       # thiếu -> không dám kết luận
    assert tu.find_tone([body, *high, [11, -12, 12, -11]], "tiền", xh) == -1   # thừa -> cũng không


def test_normalize_text():
    src = "\u201cXin\u201d \u2018chào\u2019 \u2013 a\u2014b\u00a0c\td\r\ne\u200dx"
    out = tu.normalize_text(src)
    assert out == '"Xin" \'chào\' - a-b c    d\nex'
    assert tu.normalize_text("a\u0301") == "\u00e1"          # chuẩn hoá về NFC


def test_place_tinh_tien_ti_le_khong_xoay():
    got = tu.place([[1, 2, 3, 4]], 10, 20, 2, 0)
    assert got == [[(12.0, 24.0), (16.0, 28.0)]]


def test_segment_distance_intersecting():
    """T020: Hai đoạn thẳng cắt nhau phải có khoảng cách bằng 0.0."""
    p1, p2 = (0.0, 0.0), (10.0, 10.0)
    q1, q2 = (0.0, 10.0), (10.0, 0.0)
    assert tu.segment_distance(p1, p2, q1, q2) == 0.0


def test_segment_distance_parallel_and_endpoints():
    """T020: Hai đoạn thẳng song song hoặc lệch nhau có khoảng cách chính xác."""
    # Song song cách nhau 2.5 đơn vị
    p1, p2 = (0.0, 0.0), (10.0, 0.0)
    q1, q2 = (2.0, 2.5), (8.0, 2.5)
    assert tu.segment_distance(p1, p2, q1, q2) == 2.5

    # Lệch nhau ngoài đầu mút
    p1, p2 = (0.0, 0.0), (2.0, 0.0)
    q1, q2 = (5.0, 4.0), (5.0, 6.0)
    # Đầu mút gần nhất là (2, 0) và (5, 4) -> khoảng cách hypot(3, 4) = 5.0
    assert tu.segment_distance(p1, p2, q1, q2) == 5.0


def test_segment_distance_degenerate_dots():
    """T020: Xử lý an toàn các đoạn suy biến (điểm đơn / dot) không bị ZeroDivisionError."""
    # Điểm và đoạn thẳng
    dot = (0.0, 0.0)
    p1, p2 = (0.0, 3.0), (4.0, 3.0)
    assert tu.segment_distance(dot, dot, p1, p2) == 3.0

    # Cả hai đều là điểm suy biến
    dot1 = (1.0, 1.0)
    dot2 = (4.0, 5.0)
    assert tu.segment_distance(dot1, dot1, dot2, dot2) == 5.0


def test_min_stroke_clearance_geometric_accuracy():
    """T020: min_stroke_clearance sử dụng khoảng cách đoạn thẳng 2D kèm bounding box prune."""
    # Hai nét thẳng đứng cách nhau 1.2
    stroke_a = [0.0, 0.0, 0.0, 10.0]
    stroke_b = [1.2, 0.0, 1.2, 10.0]
    assert tu.min_stroke_clearance([stroke_a], [stroke_b]) == 1.2

    # Hai nét cắt nhau
    stroke_cross_1 = [0.0, 0.0, 5.0, 5.0]
    stroke_cross_2 = [0.0, 5.0, 5.0, 0.0]
    assert tu.min_stroke_clearance([stroke_cross_1], [stroke_cross_2]) == 0.0

    # Một nét rỗng
    assert tu.min_stroke_clearance([], [stroke_a]) == 999.0
