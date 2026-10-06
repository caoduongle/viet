"""Kiểm thử tính năng D2: Callback toạ độ token và thu thập vị trí từ thiếu mẫu.

Đảm bảo:
  1. Khi token_layout_callback=None (mặc định), DocumentLayoutEngine hoạt động bình thường.
  2. Khi truyền callback, DocumentLayoutEngine gửi thông tin TokenBox cho từng từ,
     bao gồm vị trí x, y, width, height, trang, và danh sách missing (nếu có).
"""
from __future__ import annotations

from chuviettay.document.ir import Document, Paragraph, Text
from chuviettay.layout.engine import DocumentLayoutEngine, TokenBox
from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteOptions

KHO_TONG_HOP = "tests/data/kho_mau_tong_hop.json.gz"


def test_token_layout_callback():
    bank = Bank(KHO_TONG_HOP)
    opts = WriteOptions(seed=42)

    boxes: list[TokenBox] = []

    def on_token(box: TokenBox):
        boxes.append(box)

    engine = DocumentLayoutEngine(bank, opts, token_layout_callback=on_token)
    doc = Document(blocks=[Paragraph(inlines=[Text(text="hôm nay xyz123 trời đẹp")])])

    xopp_str, res = engine.layout(doc)

    assert len(boxes) > 0
    tokens = [b.token for b in boxes]
    assert "hôm" in tokens
    assert "nay" in tokens
    assert "xyz123" in tokens

    # Kiểm tra token thiếu mẫu "xyz123" có thông tin missing
    missing_box = next((b for b in boxes if b.token == "xyz123"), None)
    assert missing_box is not None
    assert len(missing_box.missing) > 0
    assert missing_box.page == 0
    assert missing_box.width > 0
    assert missing_box.height > 0
