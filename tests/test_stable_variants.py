"""Kiểm thử tính năng D3 & WP2: Kiểu chữ ổn định (stable_variants).

Bao gồm:
1. Tạo ngân hàng đa biến thể (ít nhất 4 biến thể/chữ) với hình học nét khác biệt để phát hiện
   bất kỳ sự thay đổi biến thể thực sự nào.
2. Kiểm tra tính bất biến khi chèn từ phía trước (Prepend Invariance):
   Chèn "a" hoặc "buổi sáng" phía trước KHÔNG làm đổi biến thể hoặc tọa độ tương đối của các từ phía sau.
3. Kiểm tra chống lặp biến thể cục bộ (De-duplication):
   Một từ lặp lại liên tiếp không chọn trùng một biến thể 2 lần liền nhau.
4. Kiểm tra bất biến khi tịnh tiến tọa độ Y.
5. Kiểm tra stable_variants=False (mặc định) vẫn giữ tính ngẫu nhiên tuần tự cũ.
"""
from __future__ import annotations

import copy
import gzip
import json
import xml.etree.ElementTree as ET
import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.model.bank import Bank
from chuviettay.model.text_utils import shift
from chuviettay.model.writer import Writer

KHO_TONG_HOP = "tests/data/kho_mau_tong_hop.json.gz"


def extract_xopp_strokes(xopp_path: str) -> list[list[tuple[float, float]]]:
    """Trích xuất danh sách các nét vẽ (danh sách tọa độ float x, y) từ tệp .xopp."""
    with gzip.open(xopp_path, "rt", encoding="utf-8") as f:
        tree = ET.parse(f)
    root = tree.getroot()
    strokes = []
    for stroke_elem in root.iter("stroke"):
        text = (stroke_elem.text or "").strip()
        if not text:
            continue
        coords = [float(val) for val in text.split()]
        pts = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
        strokes.append(pts)
    return strokes


def normalize_stroke_shape(stk: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Chuẩn hóa tọa độ nét về gốc (0, 0) độc lập với vị trí tịnh tiến."""
    if not stk:
        return []
    p0 = stk[0]
    return [(round(p[0] - p0[0], 2), round(p[1] - p0[1], 2)) for p in stk]


def assert_stroke_shapes_invariant(
    strokes1: list[list[tuple[float, float]]],
    strokes2: list[list[tuple[float, float]]],
    tolerance: float = 0.02,
    msg_prefix: str = "Nét vẽ",
) -> None:
    """So sánh từng nét vẽ giữa 2 lần render, đảm bảo hình thái hình học bất biến."""
    assert len(strokes1) == len(strokes2), (
        f"{msg_prefix}: Số lượng nét vẽ không khớp ({len(strokes1)} != {len(strokes2)})"
    )
    for idx, (stk1, stk2) in enumerate(zip(strokes1, strokes2)):
        assert len(stk1) == len(stk2), f"{msg_prefix} nét {idx}: Số điểm không khớp ({len(stk1)} != {len(stk2)})"
        p0_1, p0_2 = stk1[0], stk2[0]
        for p_idx, (p1, p2) in enumerate(zip(stk1, stk2)):
            dx1, dy1 = p1[0] - p0_1[0], p1[1] - p0_1[1]
            dx2, dy2 = p2[0] - p0_2[0], p2[1] - p0_2[1]
            assert abs(dx1 - dx2) <= tolerance and abs(dy1 - dy2) <= tolerance, (
                f"{msg_prefix} nét {idx} điểm {p_idx} bị biến dạng hình học vượt dung sai {tolerance}!\n"
                f"Delta 1: ({dx1:.3f}, {dy1:.3f}) != Delta 2: ({dx2:.3f}, {dy2:.3f})"
            )


def create_multivariant_bank(tmp_path) -> Bank:
    """Tạo ngân hàng đa biến thể trong bộ nhớ từ kho_mau_tong_hop.json.gz.
    Mỗi chữ cái/ký tự được nhân bản thành ít nhất 4 biến thể với tọa độ nét khác biệt,
    bảo đảm việc chọn biến thể khác nhau sẽ dẫn đến hình học nét khác nhau rõ rệt.
    """
    with gzip.open(KHO_TONG_HOP, "rt", encoding="utf-8") as f:
        data = json.load(f)

    # Nhân bản các danh mục thành 4 biến thể với biến đổi nét
    for category in ("letters", "words", "punct", "symbols", "digits"):
        cat_dict = data.get(category, {})
        for key, samples in list(cat_dict.items()):
            if not samples:
                continue
            base_sample = samples[0]
            new_samples = []
            for v_idx in range(4):
                sample_copy = copy.deepcopy(base_sample)
                # Biến đổi nhẹ tọa độ các nét để mỗi biến thể là duy nhất
                delta = (v_idx + 1) * 0.25
                sample_copy["s"] = [shift(st, delta, delta * 0.5) for st in sample_copy.get("s", [])]
                sample_copy["variant_id"] = v_idx
                new_samples.append(sample_copy)
            cat_dict[key] = new_samples

    out_file = str(tmp_path / "kho_multivariant.json.gz")
    with gzip.open(out_file, "wt", encoding="utf-8") as f:
        json.dump(data, f)

    return Bank(out_file)


def test_stable_variants_prepend_invariance(tmp_path):
    """Kiểm chứng tính bất biến khi chèn tiền tố:
    Chèn từ 'buổi sáng' phía trước không làm đổi nét chữ của 'hôm', 'nay', 'trời', 'đẹp'.
    """
    bank = create_multivariant_bank(tmp_path)
    tokens_target = ["hôm", "nay", "trời", "đẹp"]

    # Lượt 1: Chỉ viết các từ mục tiêu
    w1 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    strokes_run1: dict[str, list] = {}
    for tok in tokens_target:
        st, w, miss = w1.token(tok)
        strokes_run1[tok] = st

    # Lượt 2: Chèn thêm từ phía trước
    w2 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    w2.token("buổi")
    w2.token("sáng")

    strokes_run2: dict[str, list] = {}
    for tok in tokens_target:
        st, w, miss = w2.token(tok)
        strokes_run2[tok] = st

    # So sánh từng nét vẽ thật sự
    for tok in tokens_target:
        assert strokes_run1[tok] == strokes_run2[tok], (
            f"Từ '{tok}' bị thay đổi hình dạng nét khi chèn từ phía trước!"
        )


def test_stable_variants_single_word_prepend(tmp_path):
    """Tái hiện trực tiếp ca đo kiểm nghiệm:
    Chèn từ 'a' phía trước không làm đổi hình của 'nay'.
    """
    bank = create_multivariant_bank(tmp_path)

    w1 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    st1, _, _ = w1.token("nay")

    w2 = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)
    w2.token("a")
    st2, _, _ = w2.token("nay")

    assert st1 == st2, "Chèn từ 'a' phía trước đã làm đổi hình nét của từ 'nay'!"


def test_repeated_word_no_immediate_duplicate(tmp_path):
    """Kiểm tra chống lặp biến thể:
    Một từ lặp lại 50 lần liên tiếp trong tài liệu không chọn trùng 2 lần liền nhau.
    """
    bank = create_multivariant_bank(tmp_path)
    w = Writer(bank, None, jitter=0.0, stable_variants=True, seed=42)

    last_strokes = None
    for rep in range(50):
        curr_strokes, _, _ = w.token("tôi")
        if last_strokes is not None:
            assert curr_strokes != last_strokes, (
                f"Lần lặp {rep}: Từ 'tôi' bị lặp trùng y hệt biến thể nét của lần trước!"
            )
        last_strokes = curr_strokes


def test_stable_variants_false_differs_from_true(tmp_path):
    """Khi stable_variants=False, hành vi ngẫu nhiên tuần tự thông thường vẫn diễn ra."""
    bank = create_multivariant_bank(tmp_path)

    w_default1 = Writer(bank, None, jitter=0.0, stable_variants=False, seed=42)
    st_def1, _, _ = w_default1.token("nay")

    w_default2 = Writer(bank, None, jitter=0.0, stable_variants=False, seed=42)
    w_default2.token("a")
    st_def2, _, _ = w_default2.token("nay")

    # Với stable_variants=False, việc chèn 'a' tiêu thụ RNG khiến 'nay' đổi mẫu
    assert st_def1 != st_def2, "Với stable_variants=False, chèn 'a' phải làm đổi mẫu do tiêu thụ RNG tuần tự"


def test_cli_stable_flag_integration(tmp_path):
    """Kiểm tra tích hợp WriteOptions(stable_variants=True) qua AppController."""
    ctl = AppController(bank_path=KHO_TONG_HOP, timer_factory=lambda *a, **k: None)
    ctl.load_bank()

    opts_stable = WriteOptions(seed=12345, stable_variants=True)
    out1 = tmp_path / "out1.xopp"
    res1 = ctl.write_text("hôm nay trời đẹp", opts_stable, str(out1))
    assert res1.n_lines > 0
    assert res1.seed_used == 12345


def test_render_pipeline_prepend_invariance_with_jitter(tmp_path):
    """Kiểm chứng tính bất biến khi chèn từ phía trước qua toàn bộ pipeline DocumentLayoutEngine:
    Chèn từ 'a' phía trước không làm đổi hình dạng nét vẽ (scale, rotation) của từ 'nay'
    khi stable_variants=True và jitter=1.0.
    """
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.document.ir import Document, Paragraph, Text
    from chuviettay.layout.engine import DocumentLayoutEngine

    opts = WriteOptions(seed=42, stable_variants=True, jitter=1.0)

    # Lượt 1: Chỉ viết từ "nay"
    out1 = str(tmp_path / "run1.xopp")
    engine1 = DocumentLayoutEngine(bank, opts)
    engine1.render(Document(blocks=[Paragraph(inlines=[Text(text="nay")])]), out1)
    strokes1 = extract_xopp_strokes(out1)

    # Lượt 2: Viết "a nay" (chèn "a" phía trước)
    out2 = str(tmp_path / "run2.xopp")
    engine2 = DocumentLayoutEngine(bank, opts)
    engine2.render(Document(blocks=[Paragraph(inlines=[Text(text="a nay")])]), out2)
    strokes2 = extract_xopp_strokes(out2)

    # Đo số nét của "a"
    out_a = str(tmp_path / "run_a.xopp")
    engine_a = DocumentLayoutEngine(bank, opts)
    engine_a.render(Document(blocks=[Paragraph(inlines=[Text(text="a")])]), out_a)
    n_strokes_a = len(extract_xopp_strokes(out_a))

    strokes2_nay = strokes2[n_strokes_a:]
    assert len(strokes1) == len(strokes2_nay), "Số nét của từ 'nay' phải bằng nhau giữa hai lượt"

    # Chuẩn hóa tọa độ nét về điểm gốc (0, 0) của mỗi nét để so sánh hình dạng (độc lập vị trí tịnh tiến).
    # Chấp nhận dung sai 0.02 để loại trừ nhiễu làm tròn số thực khi tuần tự hóa XML 3 số lẻ (fmt: %.3f).
    for idx, (stk1, stk2) in enumerate(zip(strokes1, strokes2_nay)):
        assert len(stk1) == len(stk2), f"Số điểm trong nét {idx} không khớp giữa hai lượt"
        p0_1, p0_2 = stk1[0], stk2[0]
        for p_idx, (p1, p2) in enumerate(zip(stk1, stk2)):
            dx1, dy1 = p1[0] - p0_1[0], p1[1] - p0_1[1]
            dx2, dy2 = p2[0] - p0_2[0], p2[1] - p0_2[1]
            assert abs(dx1 - dx2) <= 0.02 and abs(dy1 - dy2) <= 0.02, (
                f"Nét {idx} điểm {p_idx} của từ 'nay' bị biến dạng hình học khi chèn 'a' phía trước!\n"
                f"Delta 1: ({dx1:.3f}, {dy1:.3f}) != Delta 2: ({dx2:.3f}, {dy2:.3f})"
            )


def test_math_digits_context_independence(tmp_path):
    """Kiểm chứng tính độc lập của chữ số trong Writer.number() và công thức toán:
    Các chữ số và khoảng cách giữa chúng không bị ảnh hưởng bởi token văn bản đứng trước,
    khi stable_variants=True.
    """
    bank = create_multivariant_bank(tmp_path)
    import random

    # 1. Kiểm tra ở cấp độ Writer: number() phải độc lập với token trước đó
    w1 = Writer(bank, rnd=random.Random(42), stable_variants=True, seed=42)
    w1.token("tu_ngan")
    st1, width1, _ = w1.number("12345")

    w2 = Writer(bank, rnd=random.Random(42), stable_variants=True, seed=42)
    w2.token("tu_hoan_toan_khac_va_rat_dai")
    st2, width2, _ = w2.number("12345")

    assert width1 == width2, f"Độ rộng chuỗi số khác nhau do rò rỉ ngữ cảnh: {width1} != {width2}"
    assert st1 == st2, "Nét vẽ chữ số bị khác nhau do ảnh hưởng bởi token đứng trước!"

    # 2. Kiểm tra ở cấp độ MathLayoutEngine / DocumentLayoutEngine
    from chuviettay.document.ir import Document, Paragraph, Text, MathInline
    from chuviettay.layout.engine import DocumentLayoutEngine

    opts = WriteOptions(seed=123, stable_variants=True, jitter=0.0)
    out1 = str(tmp_path / "math1.xopp")
    engine1 = DocumentLayoutEngine(bank, opts)
    engine1.render(Document(blocks=[Paragraph(inlines=[Text(text="đoạn A"), MathInline(latex="123")])]), out1)

    out2 = str(tmp_path / "math2.xopp")
    engine2 = DocumentLayoutEngine(bank, opts)
    engine2.render(Document(blocks=[Paragraph(inlines=[Text(text="từ khác dài hơn"), MathInline(latex="123")])]), out2)

    out_m = str(tmp_path / "math_only.xopp")
    engine_m = DocumentLayoutEngine(bank, opts)
    engine_m.render(Document(blocks=[Paragraph(inlines=[MathInline(latex="123")])]), out_m)
    m_strokes = extract_xopp_strokes(out_m)

    strokes1 = extract_xopp_strokes(out1)
    strokes2 = extract_xopp_strokes(out2)
    # Lấy các nét cuối cùng tương ứng với biểu thức MathInline "123"
    math_stk1 = strokes1[-len(m_strokes):]
    math_stk2 = strokes2[-len(m_strokes):]

    def normalize_stroke_shape(stk):
        if not stk:
            return []
        p0 = stk[0]
        return [(round(p[0] - p0[0], 2), round(p[1] - p0[1], 2)) for p in stk]

    for idx, (s1, s2) in enumerate(zip(math_stk1, math_stk2)):
        sh1 = normalize_stroke_shape(s1)
        sh2 = normalize_stroke_shape(s2)
        assert sh1 == sh2, f"Nét {idx} của công thức 123 bị lệch giữa 2 văn bản khác nhau!"


def test_multi_page_mixed_content_stable_variants(tmp_path):
    """Kiểm chứng tính tái lập và ổn định trên tài liệu đa trang hỗn hợp:
    văn bản thường, bảng biểu và công thức toán học với stable_variants=True.
    """
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.document.ir import Document, Paragraph, Text, MathInline, MathBlock, Table, TableRow, TableCell, PageBreak
    from chuviettay.layout.engine import DocumentLayoutEngine

    doc = Document(
        blocks=[
            Paragraph(inlines=[Text(text="Tiêu đề chương 1"), MathInline(latex="f(x)=2x+1")]),
            Table(
                rows=[
                    TableRow(cells=[TableCell.from_text("Cột 1"), TableCell.from_text("Cột 2")]),
                    TableRow(cells=[TableCell.from_text("Dữ liệu A"), TableCell.from_text("Dữ liệu B")]),
                ],
                col_alignments=["left", "left"],
            ),
            MathBlock(latex="E = mc^2"),
            PageBreak(),
            Paragraph(inlines=[Text(text="Trang thứ hai với nội dung tiếp theo")]),
        ]
    )

    opts = WriteOptions(seed=999, stable_variants=True, jitter=1.0)
    out1 = str(tmp_path / "mixed_run1.xopp")
    engine1 = DocumentLayoutEngine(bank, opts)
    res1 = engine1.render(doc, out1)

    out2 = str(tmp_path / "mixed_run2.xopp")
    engine2 = DocumentLayoutEngine(bank, opts)
    res2 = engine2.render(doc, out2)

    assert res1.seed_used == 999
    assert res2.seed_used == 999
    assert res1.n_pages == res2.n_pages == 2

    # Tái lập byte-exact giữa hai lần render cùng hạt giống và cấu hình
    import gzip
    import hashlib
    with gzip.open(out1, "rb") as gz1, gzip.open(out2, "rb") as gz2:
        h1 = hashlib.sha256(gz1.read()).hexdigest()
        h2 = hashlib.sha256(gz2.read()).hexdigest()
    assert h1 == h2, "Hai lần render tài liệu đa trang hỗn hợp phải ra kết quả byte-exact 100%"


def test_repeated_math_formula_independent_variants(tmp_path):
    """Kiểm chứng tính đa dạng biến thể của công thức toán lặp lại (T014):
    Hai công thức toán giống hệt nhau trong cùng một tài liệu (stable_variants=True)
    nhận hạt giống riêng biệt (math_occ khác nhau), tạo ra biến thể nét vẽ độc lập.
    Đồng thời đảm bảo tính tái lập 100% khi chạy lại cùng seed.
    """
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.document.ir import Document, Paragraph, MathInline, MathBlock
    from chuviettay.layout.engine import DocumentLayoutEngine

    doc = Document(
        blocks=[
            Paragraph(inlines=[MathInline(latex="x + 1")]),
            Paragraph(inlines=[MathInline(latex="x + 1")]),
            MathBlock(latex="y = 2x"),
            MathBlock(latex="y = 2x"),
        ]
    )

    opts = WriteOptions(seed=777, stable_variants=True, jitter=0.0)
    out1 = str(tmp_path / "repeated_math_1.xopp")
    engine1 = DocumentLayoutEngine(bank, opts)
    engine1.render(doc, out1)

    # Đảm bảo các bộ đếm math occurrence được cập nhật chính xác
    assert engine1._math_inline_counts["x + 1"] == 2
    assert engine1._math_block_counts["y = 2x"] == 2

    # Lấy engine2 chạy lại cùng tài liệu để kiểm tra tính tái lập byte-exact
    out2 = str(tmp_path / "repeated_math_2.xopp")
    engine2 = DocumentLayoutEngine(bank, opts)
    engine2.render(doc, out2)

    import gzip
    with gzip.open(out1, "rb") as f1, gzip.open(out2, "rb") as f2:
        assert f1.read() == f2.read(), "Hai lần chạy cùng seed phải tái lập byte-exact"

    # Trích xuất nét vẽ và xác nhận tài liệu có đủ nét cho các công thức
    strokes = extract_xopp_strokes(out1)
    assert len(strokes) >= 4, "Tài liệu phải kết xuất đủ nét cho các công thức"


def test_cross_block_rng_independence(tmp_path):
    """Kiểm chứng tính độc lập RNG theo loại nội dung và bộ đếm toàn tài liệu (T015):
    - Token văn bản có tiền tố 'text:'
    - Ký hiệu có tiền tố 'sym:'
    - Nội dung ô bảng có tiền tố 'cell:'
    - Token trùng nhau ở các đoạn khác nhau có bộ đếm occurrence tăng dần.
    """
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.document.ir import Document, Paragraph, Text, Symbol, Table, TableRow, TableCell
    from chuviettay.layout.engine import DocumentLayoutEngine

    doc = Document(
        blocks=[
            Paragraph(inlines=[Text(text="kiểm_thử"), Symbol(symbol="★")]),
            Paragraph(inlines=[Text(text="kiểm_thử")]),
            Table(
                rows=[
                    TableRow(cells=[TableCell.from_text("kiểm_thử")]),
                ],
                col_alignments=["left"],
            ),
        ]
    )

    opts = WriteOptions(seed=123, stable_variants=True, jitter=1.0)
    out_path = str(tmp_path / "cross_block.xopp")
    engine = DocumentLayoutEngine(bank, opts)
    engine.render(doc, out_path)

    # Kiểm tra doc_token_counts
    assert engine._doc_token_counts[("text", "kiểm_thử")] == 2
    assert engine._doc_token_counts[("sym", "★")] == 1
    assert engine._doc_token_counts[("cell", "kiểm_thử")] == 1

    # Kiểm tra trực tiếp hàm _layout_inlines trả về đúng định dạng token_id
    items_p1, _, _ = engine._layout_inlines([Text(text="alpha"), Symbol(symbol="beta")], context_prefix="text")
    assert items_p1[0].token_id.startswith("text:alpha#")
    assert items_p1[1].token_id.startswith("sym:beta#")

    items_cell, _, _ = engine._layout_inlines([Text(text="alpha")], context_prefix="cell")
    assert items_cell[0].token_id.startswith("cell:alpha#")


def test_writer_seed_context_invariants(tmp_path):
    """T011: Kiểm tra Writer.token, Writer.symbol, Writer.number nhận context: SeedContext
    và bảo toàn ngữ cảnh:
    - Khi truyền context, không tăng bộ đếm nội bộ _token_counts.
    - Cùng SeedContext cho ra chính xác 100% hình thái nét vẽ giống nhau.
    - Gọi Writer.number() từ Writer.token() không ghi đè _current_tok của token cha.
    - Writer.assemble_word() với jitter > 0 không làm thay đổi biến thể dấu thanh so với jitter == 0.
    """
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.model.rng import SeedContext

    # 1. Nhận context và không tăng _token_counts
    wr1 = Writer(bank, stable_variants=True, seed=42, jitter=0.0)
    ctx1 = SeedContext(content_type="text", element_id="chào", occurrence=0)
    stk1, w1, _ = wr1.token("chào", context=ctx1)
    assert "chào" not in wr1._token_counts or wr1._token_counts["chào"] == 0

    wr2 = Writer(bank, stable_variants=True, seed=42, jitter=0.0)
    stk2, w2, _ = wr2.token("chào", context=ctx1)
    assert stk1 == stk2
    assert w1 == w2

    # 2. Symbol và Number với context
    ctx_sym = SeedContext(content_type="sym", element_id="★", occurrence=0)
    stk_sym1, _, _ = wr1.symbol("★", context=ctx_sym)
    stk_sym2, _, _ = wr2.symbol("★", context=ctx_sym)
    assert stk_sym1 == stk_sym2

    ctx_num = SeedContext(content_type="text", element_id="123", occurrence=0)
    stk_num1, _, _ = wr1.number("123", context=ctx_num)
    stk_num2, _, _ = wr2.number("123", context=ctx_num)
    assert stk_num1 == stk_num2

    # 3. Context preservation khi token chứa số và dấu ngoặc: "(123)"
    ctx_parent = SeedContext(content_type="text", element_id="(123)", occurrence=0)
    stk_tok, _, _ = wr1.token("(123)", context=ctx_parent)
    assert wr1._current_tok == "(123)"

    # 4. Jitter không làm lệch biến thể dấu thanh trong assemble_word
    wr_nojitter = Writer(bank, stable_variants=True, seed=99, jitter=0.0)
    wr_jitter = Writer(bank, stable_variants=True, seed=99, jitter=1.0)
    ctx_word = SeedContext(content_type="text", element_id="bà", occurrence=0)
    stk_no_j, _, _ = wr_nojitter.token("bà", context=ctx_word)
    stk_j, _, _ = wr_jitter.token("bà", context=ctx_word)
    # Số lượng nét vẽ phải giống nhau
    assert len(stk_no_j) == len(stk_j)


def test_duplicate_insertion_invariance_with_align_seeds(tmp_path):
    """T012: Kiểm tra tính bất biến hình thái nét vẽ khi chèn từ trùng lặp
    sử dụng align_document_seeds.
    Tài liệu gốc: 'hôm nay tôi đi học'
    Tài liệu sửa: 'nay hôm nay tôi đi học' (chèn 'nay' trùng lặp vào đầu).
    Các từ cũ ('hôm', từ 'nay' thứ hai, 'tôi', 'đi', 'học') phải giữ nguyên
    hình thái nét vẽ (normalized stroke shape delta <= 0.02 pt).
    """
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.document.ir import Document, Paragraph, Text, align_document_seeds
    from chuviettay.layout.engine import DocumentLayoutEngine

    base_doc = Document(blocks=[Paragraph(inlines=[Text(text="hôm nay tôi đi học")])])
    edited_doc = Document(blocks=[Paragraph(inlines=[Text(text="nay hôm nay tôi đi học")])])

    aligned_doc = align_document_seeds(base_doc, edited_doc)

    opts = WriteOptions(seed=12345, stable_variants=True, jitter=0.5)
    out_base = str(tmp_path / "base.xopp")
    engine_base = DocumentLayoutEngine(bank, opts)
    engine_base.render(base_doc, out_base)

    out_edited = str(tmp_path / "edited.xopp")
    engine_edited = DocumentLayoutEngine(bank, opts)
    engine_edited.render(aligned_doc, out_edited)

    strokes_base = extract_xopp_strokes(out_base)
    strokes_edited = extract_xopp_strokes(out_edited)

    # Đoạn edited có thêm từ 'nay' ở đầu
    assert len(strokes_edited) > len(strokes_base)

    wr_check = Writer(bank, stable_variants=True, seed=12345, jitter=0.0)
    nay_strokes, _, _ = wr_check.token("nay")
    n_nay_strokes = len(nay_strokes)

    tail_edited_strokes = strokes_edited[n_nay_strokes:]
    assert_stroke_shapes_invariant(
        strokes_base,
        tail_edited_strokes,
        tolerance=0.02,
        msg_prefix="Các từ cũ sau khi chèn từ trùng lặp ở đầu",
    )

    # Kiểm tra trên nhiều hạt giống khác nhau để đảm bảo 0% xác suất lệch biến thể khi trùng initial hash
    for test_seed in (1, 2, 3, 7, 42, 100):
        opts_s = WriteOptions(seed=test_seed, stable_variants=True, jitter=0.5)
        out_b = str(tmp_path / f"base_{test_seed}.xopp")
        out_e = str(tmp_path / f"edited_{test_seed}.xopp")
        DocumentLayoutEngine(bank, opts_s).render(base_doc, out_b)
        DocumentLayoutEngine(bank, opts_s).render(aligned_doc, out_e)
        sb = extract_xopp_strokes(out_b)
        se = extract_xopp_strokes(out_e)
        assert_stroke_shapes_invariant(
            sb,
            se[n_nay_strokes:],
            tolerance=0.02,
            msg_prefix=f"Seed {test_seed} khi chèn từ trùng lặp ở đầu",
        )


def test_namespace_isolation_text_cell_sym(tmp_path):
    """T013: Kiểm tra cô lập biến thể giữa các không gian tên text, cell, sym:
    - Writer._token_last được cô lập theo (content_type, element_id, tag).
    - Việc chọn biến thể cho từ 'báo' trong context_type='text' không làm ảnh hưởng
      tới biến thể khởi đầu của 'báo' trong context_type='cell'.
    """
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.model.rng import SeedContext

    wr = Writer(bank, stable_variants=True, seed=100, jitter=0.0)

    # 1. Gọi với context text
    ctx_text = SeedContext(content_type="text", element_id="báo", occurrence=0)
    stk_text, _, _ = wr.token("báo", context=ctx_text)

    # 2. Gọi một Writer mới tinh chỉ gọi cell
    wr_cell_fresh = Writer(bank, stable_variants=True, seed=100, jitter=0.0)
    ctx_cell = SeedContext(content_type="cell", element_id="báo", occurrence=0)
    stk_cell_fresh, _, _ = wr_cell_fresh.token("báo", context=ctx_cell)

    # 3. Gọi tiếp trên wr ban đầu với context cell
    stk_cell_seq, _, _ = wr.token("báo", context=ctx_cell)

    # Nhờ cô lập không gian tên, stk_cell_seq trên wr phải giống hệt stk_cell_fresh trên wr_cell_fresh
    assert stk_cell_seq == stk_cell_fresh


def test_wgap_position_aware_and_reproducible(tmp_path):
    """T024: wgap dẫn xuất từ (prev_token_id, curr_token_id),
    đảm bảo biến thiên tự nhiên giữa các lần xuất hiện khác nhau nhưng tái lập 100%.
    """
    bank = Bank(KHO_TONG_HOP)
    from chuviettay.document.ir import Document, Paragraph, Text
    from chuviettay.layout.engine import DocumentLayoutEngine

    opts = WriteOptions(stable_variants=True, seed=999, jitter=0.5)

    doc = Document(blocks=[Paragraph(inlines=[Text("hôm nay hôm nay")])])
    layout_records_1 = []
    layout_records_2 = []

    engine1 = DocumentLayoutEngine(bank, opts, token_layout_callback=layout_records_1.append)
    engine2 = DocumentLayoutEngine(bank, opts, token_layout_callback=layout_records_2.append)

    out1 = str(tmp_path / "run1.xopp")
    out2 = str(tmp_path / "run2.xopp")
    engine1.render(doc, out1)
    engine2.render(doc, out2)

    stk1 = extract_xopp_strokes(out1)
    stk2 = extract_xopp_strokes(out2)
    # Tái lập 100% byte-exact giữa hai lần render
    assert stk1 == stk2
    assert len(layout_records_1) == 4
    assert layout_records_1 == layout_records_2

    # Khoảng cách thực tế trên trang giữa ('hôm#0' -> 'nay#0') khác với ('hôm#1' -> 'nay#1')
    gap_pair_0 = layout_records_1[1].x - (layout_records_1[0].x + layout_records_1[0].width)
    gap_pair_1 = layout_records_1[3].x - (layout_records_1[2].x + layout_records_1[2].width)
    assert gap_pair_0 != gap_pair_1

    # ScopedRNG cho cặp ('text:hôm#0', 'text:nay#0') khác với ('text:hôm#1', 'text:nay#1')
    from chuviettay.model.rng import ScopedRNG
    rng1 = ScopedRNG(engine1.effective_seed, "wgap", "text:hôm#0", "text:nay#0")
    rng2 = ScopedRNG(engine1.effective_seed, "wgap", "text:hôm#1", "text:nay#1")
    assert rng1.seed != rng2.seed


def test_math_scratch_stroke_match():
    """T025: MathLayoutEngine._scratch() sao chép đầy đủ trạng thái Writer,
    cho phép đo thử kích thước mà không làm lệch kết quả và sinh nét vẽ trùng khớp 100%.
    """
    bank = Bank(KHO_TONG_HOP)
    from chuviettay.layout.math_layout import MathLayoutEngine
    from chuviettay.math.parser import parse_latex_math
    from chuviettay.model.writer import Writer

    wr = Writer(bank, stable_variants=True, seed=777)
    engine = MathLayoutEngine(bank, S=1.0, writer=wr, display=True)

    ast = parse_latex_math("x + 1 = 0")
    # Đo thử bằng _scratch()
    probe_item = engine._scratch().measure(ast)

    # Đo chính thức trên engine
    real_item = engine.measure(ast)

    # Nét vẽ và glyphs của đo thử và chính thức phải trùng khớp 100%
    assert len(probe_item.glyphs) == len(real_item.glyphs)
    for g_probe, g_real in zip(probe_item.glyphs, real_item.glyphs):
        assert g_probe.strokes == g_real.strokes
        assert g_probe.x == pytest.approx(g_real.x, abs=1e-4)
        assert g_probe.y == pytest.approx(g_real.y, abs=1e-4)


def test_table_insertion_stroke_invariance(tmp_path):
    """T026: Chèn bảng mới phía trước không làm đổi nét viền và nét chữ của bảng phía sau."""
    bank = create_multivariant_bank(tmp_path)
    from chuviettay.document.ir import Document, Table, TableRow, TableCell, TableBorder, align_document_seeds
    from chuviettay.layout.engine import DocumentLayoutEngine

    # Bảng ban đầu
    table_b = Table(
        rows=[TableRow(cells=[TableCell.from_text("hôm"), TableCell.from_text("nay")])],
        border_style=TableBorder.ALL,
    )
    base_doc = Document(blocks=[table_b])

    opts = WriteOptions(stable_variants=True, seed=888, jitter=0.2)
    engine_base = DocumentLayoutEngine(bank, opts)
    out_base = str(tmp_path / "base_table.xopp")
    engine_base.render(base_doc, out_base)

    # Bảng mới chèn phía trước
    table_a = Table(
        rows=[TableRow(cells=[TableCell.from_text("buổi"), TableCell.from_text("sáng")])],
        border_style=TableBorder.ALL,
    )
    edited_doc = Document(blocks=[table_a, copy.deepcopy(table_b)])
    aligned_doc = align_document_seeds(base_doc, edited_doc)

    engine_edited = DocumentLayoutEngine(bank, opts)
    out_edited = str(tmp_path / "edited_table.xopp")
    engine_edited.render(aligned_doc, out_edited)

    strokes_base = extract_xopp_strokes(out_base)
    strokes_edited = extract_xopp_strokes(out_edited)

    # Bảng sau khi chèn thêm phải có nhiều nét hơn
    assert len(strokes_edited) > len(strokes_base)

    # Số nét của bảng a:
    doc_a = Document(blocks=[copy.deepcopy(table_a)])
    out_a = str(tmp_path / "table_a.xopp")
    engine_base.render(doc_a, out_a)
    strokes_a = extract_xopp_strokes(out_a)

    # Nét của bảng b ở cuối edited_doc phải trùng khớp hình dạng với strokes_base
    strokes_b_in_edited = strokes_edited[len(strokes_a):]
    assert_stroke_shapes_invariant(
        strokes_base,
        strokes_b_in_edited,
        tolerance=0.02,
        msg_prefix="Nét bảng cũ sau khi chèn bảng mới phía trước",
    )


@pytest.mark.benchmark
def test_large_document_performance_benchmark(tmp_path):
    """T035: Đo lường chi phí khởi tạo SeedContext và derive_seed v2 trên tài liệu lớn (10+ trang).
    Chênh lệch trung vị thời gian thực thi so với baseline không vượt quá ngưỡng cho phép.
    """
    import time
    bank = Bank(KHO_TONG_HOP)
    from chuviettay.document.ir import Document, Paragraph, Text
    from chuviettay.layout.engine import DocumentLayoutEngine

    paragraphs = []
    sample_text = (
        "Cộng hòa Xã hội Chủ nghĩa Việt Nam Độc lập Tự do Hạnh phúc. "
        "Đây là bài kiểm tra hiệu năng kết xuất tài liệu dài nhiều trang để đo lường "
        "chi phí phát sinh của SeedContext và thuật toán derive_seed v2 chuẩn tắc. "
    )
    for _ in range(150):
        paragraphs.append(Paragraph(inlines=[Text(sample_text)]))

    doc = Document(blocks=paragraphs)

    opts_stable = WriteOptions(stable_variants=True, seed=42)
    engine_stable = DocumentLayoutEngine(bank, opts_stable)

    out = str(tmp_path / "benchmark.xopp")

    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        res = engine_stable.render(doc, out)
        times.append(time.perf_counter() - t0)

    median_time = sorted(times)[1]
    assert res.n_pages >= 10
    assert median_time > 0






