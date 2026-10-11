"""Kiểm thử bảo toàn cấu trúc bảng khi nạp DOCX qua bridge và trích xuất Markdown."""
import pytest
from chuviettay.browser.bridge import BrowserBridge


def test_import_docx_preserves_table_structure_and_cells():
    """Kiểm tra file sample_table.docx sau khi nạp qua bridge phải giữ nguyên các ô và giá trị trong bảng."""
    bridge = BrowserBridge()
    with open("tests/fixtures/sample_table.docx", "rb") as f:
        docx_bytes = f.read()

    res = bridge.import_docx(docx_bytes)
    assert res["ok"] is True
    md_text = res.get("markdown_text", "")

    # Phải có các đoạn văn trước và sau bảng
    assert "Đoạn văn mở đầu trước bảng." in md_text
    assert "Đoạn văn kết thúc sau bảng." in md_text

    # Bảng phải được biểu diễn bằng Markdown pipe table
    assert "|" in md_text, "Markdown phải chứa cú pháp bảng '|'"
    assert "Mã số" in md_text
    assert "Họ và tên" in md_text
    assert "Điểm số" in md_text
    assert "SV01" in md_text
    assert "Nguyễn Văn A" in md_text
    assert "8.5" in md_text
    assert "SV02" in md_text


def test_import_docx_pipe_escaping_and_multiline_cells():
    """Kiểm tra ô có ký tự '|' phải được escape và không làm vỡ cấu trúc hàng."""
    import docx
    import io

    doc = docx.Document()
    tbl = doc.add_table(rows=2, cols=2)
    tbl.rows[0].cells[0].text = "Cột A"
    tbl.rows[0].cells[1].text = "Cột B"
    tbl.rows[1].cells[0].text = "Giá trị a | b"
    tbl.rows[1].cells[1].text = "Dòng 1\nDòng 2"

    bio = io.BytesIO()
    doc.save(bio)

    bridge = BrowserBridge()
    res = bridge.import_docx(bio.getvalue())
    assert res["ok"] is True
    md = res["markdown_text"]

    # Ký tự pipe trong text ô phải được escape thành \|
    assert r"a \| b" in md or r"a &vert; b" in md or r"a \| b" in md
    # Ký tự xuống dòng không được tạo hàng trần
    lines = [line.strip() for line in md.splitlines() if line.strip()]
    assert any(line.startswith("|") and line.endswith("|") for line in lines)


def test_import_docx_nested_tables_extraction():
    """Kiểm tra trích xuất bảng lồng nhau (nested table) không bị mất nội dung và có cảnh báo."""
    bridge = BrowserBridge()
    with open("tests/fixtures/sample_nested_table.docx", "rb") as f:
        docx_bytes = f.read()

    res = bridge.import_docx(docx_bytes)
    assert res["ok"] is True
    md = res.get("markdown_text", "")
    unsupported = res.get("unsupported", [])

    # 1. Toàn bộ nội dung của bảng lồng nhau phải có mặt trong Markdown
    assert "Con 1" in md
    assert "Con 2" in md
    assert "Con 3" in md
    assert "Con 4" in md
    assert "Ô bên phải" in md

    # 2. Phải có thông báo chẩn đoán về bảng lồng nhau
    assert any("Bảng lồng nhau" in u or "nested table" in u for u in unsupported)


def test_import_docx_column_alignments_preserved():
    """Kiểm tra căn lề các cột từ DOCX được bảo toàn và chuyển đổi thành delimiter Markdown (:---, :---:, ---:)."""
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import io

    doc = docx.Document()
    tbl = doc.add_table(rows=2, cols=3)
    p0 = tbl.rows[0].cells[0].paragraphs[0]
    p0.text = "Trái"
    p0.alignment = WD_ALIGN_PARAGRAPH.LEFT

    p1 = tbl.rows[0].cells[1].paragraphs[0]
    p1.text = "Giữa"
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p2 = tbl.rows[0].cells[2].paragraphs[0]
    p2.text = "Phải"
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    tbl.rows[1].cells[0].text = "1"
    tbl.rows[1].cells[1].text = "2"
    tbl.rows[1].cells[2].text = "3"

    bio = io.BytesIO()
    doc.save(bio)

    bridge = BrowserBridge()
    res = bridge.import_docx(bio.getvalue())
    assert res["ok"] is True
    md = res.get("markdown_text", "")

    # Phải có hàng phân cách với định dạng căn lề tương ứng
    lines = [l.strip() for l in md.splitlines() if l.strip()]
    delimiter_line = next((l for l in lines if ":---" in l or "---:" in l), None)
    assert delimiter_line is not None, f"Không tìm thấy hàng delimiter trong markdown:\n{md}"
    parts = [p.strip() for p in delimiter_line.strip("|").split("|")]
    assert len(parts) == 3
    assert parts[0] == ":---"
    assert parts[1] == ":---:"
    assert parts[2] == "---:"
