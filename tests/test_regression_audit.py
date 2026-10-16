"""test_regression_audit.py -- Bộ kiểm thử hồi quy chính thức cho các phát hiện rà soát (Spec 040).

Bao gồm:
- US1: Round-trip Markdown serialization (MathBlock, Heading, ký tự điều khiển Markdown, LineBreak trong ô bảng)
- US2: Căn lề đoạn văn Paragraph.align (left, center, right, justify)
- US4: Xử lý gạch ngang ~~text~~ và cảnh báo định dạng chữ giàu
- US5: Cơ chế missing_grid mặc định False và loại bỏ sinh lưới cũ hw2
"""
import gzip
import os
import re

import pytest
from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Heading, LineBreak, MathBlock, MathInline, Paragraph, Table, TableCell, TableRow, Text
from chuviettay.importer.markdown_importer import MarkdownImporter
from chuviettay.model import xopp
from chuviettay.model.bank import Bank


@pytest.fixture
def test_bank(tmp_path):
    from tests.conftest import tiny_bank_dict
    bank_path = tmp_path / "test_bank.json.gz"
    d = tiny_bank_dict()
    d["schema_version"] = 3
    d.setdefault("symbols", {})
    with gzip.open(bank_path, "wt", encoding="utf-8") as f:
        import json
        json.dump(d, f, ensure_ascii=False)
    return str(bank_path)


# ==============================================================================
# Phase 3 / US1 Tests: Round-trip Markdown Serialization
# ==============================================================================
def test_docx_markdown_roundtrip_math_and_escapes():
    """US1: Kiểm tra round-trip các ký tự đặc biệt Markdown, ListBlock và công thức toán qua bridge."""
    from chuviettay.browser.bridge import BrowserBridge
    from chuviettay.document.ir import ListBlock

    bridge = BrowserBridge()
    special_txt = r"Tính toán: 2*3*4 = 24 và #1 không phải thẻ tag; $5 và $10; ~~x~~; a_b_c; a|b; a\b."

    doc = Document(
        blocks=[
            Heading(level=2, inlines=[Text(text="Tiêu đề & Mục 1")]),
            Paragraph(inlines=[Text(text="Tính toán: 2*3*4 = 24 và #1 không phải thẻ tag; "), Text(text=r"$5 và $10; ~~x~~; a_b_c; a|b; a\b.")]),
            MathBlock(latex=r"E = mc^2"),
            ListBlock(
                ordered=True,
                start=1,
                items=[
                    [Paragraph(inlines=[Text(text="Bước 1: 2*3")])],
                    [Paragraph(inlines=[Text(text="Bước 2: #tag")])],
                ],
            ),
            Table(
                rows=[
                    TableRow(cells=[TableCell(blocks=[Paragraph(inlines=[Text(text="Công thức")])]), TableCell(blocks=[Paragraph(inlines=[Text(text="Giá trị")])])]),
                    TableRow(
                        cells=[
                            TableCell(blocks=[Paragraph(inlines=[MathInline(latex=r"|x| \le 1")]), MathBlock(latex=r"|y| = 2")]),
                            TableCell(blocks=[Paragraph(inlines=[Text(text="Dòng 1"), LineBreak(), Text(text="Dòng 2")]), Paragraph(inlines=[Text(text="Đoạn 2")])]),
                        ]
                    ),
                ],
                col_alignments=["left", "left"],
            ),
        ]
    )

    res = bridge._document_to_markdown_dict(doc)
    assert res["ok"] is True
    md_text = res["markdown_text"]

    # Kiểm tra MathBlock có mặt dạng $$...$$
    assert r"$$E = mc^2$$" in md_text
    # Kiểm tra Heading có ##
    assert "## Tiêu đề & Mục 1" in md_text
    # Kiểm tra ký tự toán trong bảng được escape để không vỡ cột
    assert r"\|x\|" in md_text
    assert r"\|y\|" in md_text

    # Re-import lại qua MarkdownImporter
    importer = MarkdownImporter()
    import_res = importer.import_text(md_text)
    re_doc = import_res.document

    # Xác nhận có đúng khối Heading, Paragraph, MathBlock, ListBlock, Table
    block_types = [type(b).__name__ for b in re_doc.blocks]
    assert block_types == ["Heading", "Paragraph", "MathBlock", "ListBlock", "Table"]

    # Xác nhận nội dung văn bản chứa các ký tự điều khiển được bảo toàn 100%
    re_para = re_doc.blocks[1]
    assert isinstance(re_para, Paragraph)
    assert "".join(getattr(i, "text", "") for i in re_para.inlines) == special_txt

    # Xác nhận công thức có | trong bảng và nhiều đoạn/dòng trong ô bảng được bảo toàn
    re_table = re_doc.blocks[4]
    assert isinstance(re_table, Table)
    cell_0_inlines = re_table.rows[1].cells[0].blocks[0].inlines
    math_inlines = [i for i in cell_0_inlines if isinstance(i, MathInline)]
    assert len(math_inlines) == 2
    assert math_inlines[0].latex == r"|x| \le 1"
    assert math_inlines[1].latex == r"|y| = 2"

    cell_1_text = "".join(getattr(i, "text", "") for i in re_table.rows[1].cells[1].blocks[0].inlines)
    assert cell_1_text == "Dòng 1 Dòng 2 Đoạn 2"


# ==============================================================================
# Phase 4 / US2 Tests: Paragraph Alignment in Core Engine & IR
# ==============================================================================
def test_paragraph_alignment(test_bank, tmp_path):
    """US2: Kiểm tra căn lề left, center, right, justify và TokenBox trong DocumentLayoutEngine (F1)."""
    ctl = AppController(test_bank)
    ctl.load_bank()

    xs = {}
    boxes_by_align = {}
    for al in ("left", "center", "right"):
        out = str(tmp_path / f"align_{al}.xopp")
        boxes = []
        ctl.write_document(
            Document(blocks=[Paragraph(inlines=[Text(text="xin zzz")], align=al)]),
            WriteOptions(seed=3, jitter=0.0, background="plain"),
            out,
            token_layout_callback=lambda b, acc=boxes: acc.append(b),
        )
        xml = gzip.decompress(open(out, "rb").read()).decode("utf-8")
        x_coords = [float(m.group(1)) for m in re.finditer(r"<stroke[^>]*>(-?[0-9.]+) ", xml)]
        assert x_coords, f"Không tìm thấy nét vẽ trong file {out}"
        xs[al] = min(x_coords)
        boxes_by_align[al] = [b for b in boxes if b.token == "zzz"]
        assert len(boxes_by_align[al]) == 1

    # Căn trái < Căn giữa < Căn phải cho cả nét vẽ và TokenBox
    assert xs["left"] < xs["center"] < xs["right"], f"Tọa độ x không phân biệt theo căn lề: {xs}"
    assert boxes_by_align["left"][0].x < boxes_by_align["center"][0].x < boxes_by_align["right"][0].x
    # Kiểm tra đối xứng hình học: center nằm chính giữa left và right (sai số < 0.1 pt theo SC-002)
    assert xs["center"] == pytest.approx((xs["left"] + xs["right"]) / 2.0, abs=0.05)
    assert boxes_by_align["center"][0].x == pytest.approx(
        (boxes_by_align["left"][0].x + boxes_by_align["right"][0].x) / 2.0, abs=0.05
    )

    # Kiểm tra justify: dòng tràn kéo giãn chạm lề phải, dòng cuối và dòng kết thúc bởi LineBreak giữ căn trái
    just_boxes_left = []
    just_boxes_full = []
    text_multi = " ".join(["xin", "ba", "chào", "zzz"] * 8)
    ctl.write_document(
        Document(blocks=[Paragraph(inlines=[Text(text=text_multi)], align="left")]),
        WriteOptions(seed=3, jitter=0.0, width=180.0, background="plain"),
        str(tmp_path / "just_left.xopp"),
        token_layout_callback=lambda b: just_boxes_left.append(b),
    )
    ctl.write_document(
        Document(blocks=[Paragraph(inlines=[Text(text=text_multi)], align="justify")]),
        WriteOptions(seed=3, jitter=0.0, width=180.0, background="plain"),
        str(tmp_path / "just_full.xopp"),
        token_layout_callback=lambda b: just_boxes_full.append(b),
    )
    # Dòng đầu tiên (dòng tràn): từ cuối dòng của justify phải dời sang phải so với căn trái và chạm sát lề phải
    first_line_y = just_boxes_left[0].y
    line1_left_max_r = max(b.x + b.width for b in just_boxes_left if b.y == first_line_y)
    line1_just_max_r = max(b.x + b.width for b in just_boxes_full if b.y == first_line_y)
    assert line1_just_max_r > line1_left_max_r
    assert line1_just_max_r == pytest.approx(36.0 + 180.0, abs=0.1)

    # Dòng cuối cùng của đoạn: justify không kéo giãn, khớp với căn trái
    last_line_y = just_boxes_left[-1].y
    line_last_left = [b.x for b in just_boxes_left if b.y == last_line_y]
    line_last_just = [b.x for b in just_boxes_full if b.y == last_line_y]
    assert line_last_just == pytest.approx(line_last_left, abs=0.05)


# ==============================================================================
# Phase 6 / US4 Tests: Strikethrough & Rich Text Warnings
# ==============================================================================
def test_markdown_strikethrough():
    """US4: Kiểm tra gạch ngang ~~text~~ và cảnh báo kiểu chữ giàu (nguồn gốc F2)."""
    importer = MarkdownImporter()
    res = importer.import_text("Chữ **đậm** và *nghiêng* và ~~gạch~~ và `code` và [liên kết](http://x.y).\n\n- Mục ~~danh sách~~")

    # Thu thập toàn bộ text từ các block inlines
    all_text = "".join(getattr(i, "text", "") for b in res.document.blocks for i in getattr(b, "inlines", []))

    # Cặp dấu ~~ phải được loại bỏ, không in thô ra chữ viết tay
    assert "~~" not in all_text, f"Dấu ~~ chưa được loại bỏ trong text: {all_text}"
    assert "gạch" in all_text

    # Phải có cảnh báo về việc làm phẳng định dạng kiểu chữ giàu
    assert len(res.warnings) > 0, "Không có cảnh báo khi tài liệu chứa định dạng kiểu chữ giàu"
    assert any("kiểu chữ" in w.lower() or "định dạng" in w.lower() for w in res.warnings)


# ==============================================================================
# Phase 7 / US5 Tests: Desktop Legacy Removal & missing_grid=False
# ==============================================================================
def test_desktop_legacy(test_bank, tmp_path):
    """US5: Kiểm tra missing_grid mặc định False, loại bỏ nhánh sinh lưới hw2 và cập nhật tiêu đề Web UI."""
    opts = WriteOptions()
    assert opts.missing_grid is False, "Giá trị mặc định của WriteOptions.missing_grid phải là False"

    ctl = AppController(test_bank)
    ctl.load_bank()

    out = str(tmp_path / "out_semantic.xopp")
    # Viết từ thiếu mẫu ("quokka" chưa có trong test_bank)
    res = ctl.write_text("quokka", opts, out)

    # Xác nhận không có file _thieu.xopp nào được tạo khi dùng tùy chọn mặc định
    thieu_file = str(tmp_path / "out_semantic_thieu.xopp")
    assert not os.path.exists(thieu_file), "File _thieu.xopp không được phép sinh khi missing_grid=False"
    assert res.missing_grid_path is None

    # Khi bật tường minh missing_grid=True, thông điệp hướng dẫn trên lưới phải theo chuẩn Web UI (không còn hw_note.py)
    out_with_grid = str(tmp_path / "out_grid.xopp")
    res_grid = ctl.write_text("quokka", WriteOptions(missing_grid=True), out_with_grid)
    assert res_grid.missing_grid_path and os.path.exists(res_grid.missing_grid_path)
    grid_texts = [(t.text or "").strip() for t in xopp.read_xopp(res_grid.missing_grid_path).iter("text")]
    joined_grid_texts = " ".join(grid_texts)
    assert "hw_note.py" not in joined_grid_texts
    assert "Dạy chữ -> Nạp file lưới" in joined_grid_texts

    # Kiểm tra make_grid luôn sinh chuẩn hw3 kể cả khi truyền grid_version="hw2"
    grid_out = str(tmp_path / "grid_hw3.xopp")
    xopp.make_grid(grid_out, ["xin"], ctl.bank, "Header test", grid_version="hw2")
    assert os.path.exists(grid_out)
    hw_tags = [(t.text or "").strip() for t in xopp.read_xopp(grid_out).iter("text")]
    assert "hw3c" in hw_tags and "hw2c" not in hw_tags

