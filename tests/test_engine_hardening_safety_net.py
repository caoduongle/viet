"""Kiểm thử chốt an toàn (Safety Net Tests) tái hiện các lỗi L1–L14 và nghi vấn kiến trúc R7.

Các kiểm thử này được thiết kế để xác định chính xác các điểm lỗi đã được rà soát trước khi triển khai sửa đổi.
"""
import ast
import tempfile
import pytest

from chuviettay.document.ir import Text
from chuviettay.importer.markdown_importer import MarkdownImporter
from chuviettay.model.bank import Bank


def test_l1_digits_and_punct_learning(tmp_path):
    """L1: Kho tạo mới phải học và lưu được chữ số (0-9) và dấu câu vào bank.digits và bank.punct."""
    bank_path = str(tmp_path / "bank_l1.json.gz")
    bank = Bank.create_empty(bank_path)

    stroke = [10.0, 10.0, 20.0, 20.0]
    # Dạy chữ số '2' và dấu phẩy ','
    bank.add_sample("2", [stroke], 15.0)
    bank.add_sample(",", [stroke], 10.0)

    # Sau khi phân loại đúng, '2' phải vào bank.digits và ',' phải vào bank.punct
    assert "2" in bank.digits, "Chữ số '2' phải được phân loại và lưu trong bank.digits"
    assert "," in bank.punct, "Dấu phẩy ',' phải được phân loại và lưu trong bank.punct"


def test_l2_missing_token_count_not_negative(tmp_path):
    """L2: Tỷ lệ thiếu mẫu không được ra số âm (ví dụ -2/1) khi gặp token có nhiều dấu ngoặc/dấu câu."""
    from chuviettay.controller.results import WriteOptions
    from chuviettay.document.ir import Document, Paragraph
    from chuviettay.layout.engine import DocumentLayoutEngine

    bank_path = str(tmp_path / "empty_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    engine = DocumentLayoutEngine(bank, WriteOptions())

    doc = Document(blocks=[Paragraph(inlines=[Text(text="(Xin,")])])
    out_xopp = str(tmp_path / "out_l2.xopp")
    res = engine.render(doc, out_xopp)

    # n_tokens phải luôn >= n_missing_tokens, không được để n_tokens - n_missing < 0
    assert res.n_tokens >= res.n_missing_tokens, (
        f"n_tokens ({res.n_tokens}) phải >= n_missing_tokens ({res.n_missing_tokens})"
    )


def test_l3_n_pages_reported_from_page_buffer(tmp_path):
    """L3: WriteResult.n_pages phải phản ánh đúng số trang thực tế trong PageBuffer (không cố định là 1)."""
    from chuviettay.controller.results import WriteOptions
    from chuviettay.document.ir import Document, PageBreak, Paragraph
    from chuviettay.layout.engine import DocumentLayoutEngine

    bank_path = str(tmp_path / "empty_bank.json.gz")
    bank = Bank.create_empty(bank_path)
    engine = DocumentLayoutEngine(bank, WriteOptions())

    # Tạo tài liệu có 3 trang bằng PageBreak
    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Trang 1")]),
        PageBreak(),
        Paragraph(inlines=[Text(text="Trang 2")]),
        PageBreak(),
        Paragraph(inlines=[Text(text="Trang 3")]),
    ])
    out_xopp = str(tmp_path / "out_l3.xopp")
    res = engine.render(doc, out_xopp)

    assert res.n_pages == 3, f"Kỳ vọng 3 trang nhưng kết quả báo {res.n_pages} trang"


def test_l7_html_sanitizer_preserves_inequalities():
    """L7: Markdown importer không được nuốt nội dung chứa dấu so sánh < và >."""
    importer = MarkdownImporter()
    res = importer.import_text("1 < 2 và 3 > 2")
    p = res.document.blocks[0]
    full_text = "".join(getattr(inl, "text", "") for inl in p.inlines)
    assert "<" in full_text and ">" in full_text, f"Toán tử so sánh bị mất: {full_text}"


def test_l11_sample_deduplication(tmp_path):
    """L11: Học cùng một mẫu nét 2 lần không được làm tăng số mẫu (phải khử trùng)."""
    bank_path = str(tmp_path / "bank_l11.json.gz")
    bank = Bank.create_empty(bank_path)

    stroke = [10.0, 10.0, 20.0, 20.0]
    bank.add_sample("test", [stroke], 15.0)
    bank.add_sample("test", [stroke], 15.0)

    assert len(bank.words["test"]) == 1, "Mẫu nét trùng lặp phải được khử trùng, không tăng lên 2"


def test_l12_drop_symbol_records_tombstone(tmp_path):
    """L12: drop_symbol phải ghi nhận tombstone để tránh hồi sinh khi hợp nhất kho."""
    bank_path = str(tmp_path / "bank_l12.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.add_symbol_sample("+", [[10.0, 10.0, 20.0, 20.0]], 15.0)

    bank.drop_symbol("+")
    tombstones = bank.d.get("tombstones", {})
    # tombstone phải ghi nhận symbol '+' đã bị xoá
    symbol_tombs = tombstones.get("symbols", []) if isinstance(tombstones, dict) else []
    assert "+" in tombstones or "+" in symbol_tombs, "Ký hiệu bị xoá phải có tombstone ghi nhận"


def test_l13_symmetric_tone_mark_quartile_trimming(tmp_path):
    """L13: Cắt phân vị dấu thanh phải đối xứng cho cả đầu trên và đầu dưới khi n=11."""
    bank_path = str(tmp_path / "bank_l13.json.gz")
    bank = Bank.create_empty(bank_path)

    # 11 mẫu dấu sắc với giá trị dy tăng dần từ 1 đến 11
    bank._raw_marks["sắc"] = [
        {"s": [[0.0, 0.0, 1.0, 1.0]], "dx": 5.0, "dy": float(i), "_src": "a"}
        for i in range(1, 12)
    ]
    bank._refresh_tone_marks("sắc")
    trimmed_dys = [m["dy"] for m in bank.marks["sắc"]]

    # Với n=11, cắt 10% (1 mẫu mỗi đầu) -> phải giữ 9 mẫu (từ 2 đến 10)
    assert len(trimmed_dys) == 9, f"Cắt đối xứng phải giữ 9 mẫu, thực tế giữ {len(trimmed_dys)}"
    assert 2.0 in trimmed_dys and 10.0 in trimmed_dys
    assert 1.0 not in trimmed_dys and 11.0 not in trimmed_dys


def test_r7_layout_does_not_import_controller():
    """R7: layout/engine.py không được import controller."""
    with open("chuviettay/layout/engine.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="engine.py")

    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if "controller" in node.module:
                imported.append(f"from {node.module} import ... (line {node.lineno})")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "controller" in alias.name:
                    imported.append(f"import {alias.name} (line {node.lineno})")

    assert not imported, f"layout/engine.py vi phạm kiến trúc khi import controller: {imported}"
