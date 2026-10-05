"""Kiểm thử tính toàn vẹn dữ liệu kho mẫu, khử trùng và kiến trúc sạch (User Story 4 - L11, L12, L13, R7, R10)."""
import os
import pytest
from chuviettay.model import xopp
from chuviettay.model.bank import Bank, merge_bank_dicts
from chuviettay.model.text_utils import sample_signature


def test_sample_deduplication(tmp_path):
    """Thêm mẫu nét giống hệt nhau không làm tăng số lượng mẫu (L11)."""
    bank_path = str(tmp_path / "dedup_bank.json.gz")
    bank = Bank.create_empty(bank_path)

    stroke = [10.0, 10.0, 20.0, 20.0]
    bank.add_sample("chào", [stroke], 25.0)
    assert len(bank.words["chào"]) == 1

    # Thêm cùng nét vẽ một lần nữa
    bank.add_sample("chào", [stroke], 25.0)
    assert len(bank.words["chào"]) == 1, "Mẫu nét trùng lặp phải bị khử trùng"

    # Thêm mẫu ký hiệu trùng lặp (D3)
    bank.add_symbol_sample("π", [stroke], 15.0)
    assert len(bank.symbols["π"]) == 1
    bank.add_symbol_sample("π", [stroke], 15.0)
    assert len(bank.symbols["π"]) == 1, "Mẫu ký hiệu trùng lặp phải bị khử trùng khi dedup=True"
    bank.add_symbol_sample("π", [stroke], 15.0, dedup=False)
    assert len(bank.symbols["π"]) == 2, "Mẫu ký hiệu không bị khử trùng khi dedup=False"



def test_tombstone_across_all_categories(tmp_path):
    """drop và drop_symbol ghi nhận tombstone và loại bỏ phần tử khi hợp nhất (L12)."""
    bank_path = str(tmp_path / "tomb_bank.json.gz")
    bank = Bank.create_empty(bank_path)

    stroke = [10.0, 10.0, 20.0, 20.0]
    bank.add_sample("1", [stroke], 15.0)
    bank.add_sample(",", [stroke], 10.0)
    bank.add_symbol_sample("+", [stroke], 15.0)

    # Xoá symbol, digit, punct
    bank.drop_symbol("+")
    bank.drop("1")
    bank.drop(",")

    # Kiểm tra tombstone được ghi nhận
    assert "+" in bank._tombstones
    assert "1" in bank._tombstones
    assert "," in bank._tombstones

    # Giả lập đĩa có chứa các mẫu đó, kiểm tra merge_bank_dicts không làm hồi sinh chúng
    disk_data = {
        "generation": 0,
        "words": {},
        "digits": {"1": [{"w": 15.0, "s": [stroke]}]},
        "punct": {",": [{"w": 10.0, "s": [stroke]}]},
        "symbols": {"+": [{"w": 15.0, "s": [stroke]}]},
        "tombstones": {},
    }
    merge_bank_dicts(bank.d, disk_data, bank._deleted_words, bank._readded_words)

    assert "+" not in bank.symbols
    assert "1" not in bank.digits
    assert "," not in bank.punct


def test_symmetric_tone_mark_trimming(tmp_path):
    """Lọc phân vị dấu thanh đối xứng cả đầu trên và đầu dưới (L13)."""
    bank = Bank.create_empty(str(tmp_path / "trim_bank.json.gz"))

    # 11 mẫu dy tăng từ 1 đến 11
    bank._raw_marks["hỏi"] = [
        {"s": [[0.0, 0.0, 1.0, 1.0]], "dx": 5.0, "dy": float(i), "_src": "a"}
        for i in range(1, 12)
    ]
    bank._refresh_tone_marks("hỏi")
    trimmed = bank.marks["hỏi"]

    # Cắt 10% (1 mẫu mỗi đầu): giữ 9 mẫu (từ 2 đến 10)
    assert len(trimmed) == 9
    dys = [m["dy"] for m in trimmed]
    assert 1.0 not in dys
    assert 11.0 not in dys
    assert min(dys) == 2.0
    assert max(dys) == 10.0


def test_xopp_read_and_stroke_xml_security(tmp_path):
    """read_xopp đóng tệp đúng cách và stroke_xml escape các thuộc tính XML (R10)."""
    file_path = str(tmp_path / "sample.xopp")
    xopp.save_xopp(file_path, [xopp.HEAD, xopp.PAGE_OPEN % (595.0, 842.0), xopp.PAGE_CLOSE, "</xournal>"])

    # Đọc xopp nhiều lần không bị rò rỉ file descriptor
    for _ in range(5):
        root = xopp.read_xopp(file_path)
        assert root is not None

    # Kiểm tra stroke_xml escape các ký tự đặc biệt trong thuộc tính
    pen = {"tool": "pen", "color": '#000000" onmouseover="alert(1)'}
    xml_str = xopp.stroke_xml([(10.0, 10.0), (20.0, 20.0)], pen)
    assert 'onmouseover="alert(1)' not in xml_str
    assert '&quot;' in xml_str or '&#34;' in xml_str or 'onmouseover=&quot;' in xml_str


def test_learn_same_file_twice_does_not_double(tmp_path):
    """Học cùng một file .xopp hai lần không làm nhân đôi số lượng mẫu (L11)."""
    from chuviettay.model.learning import learn_from_files

    bank = Bank.create_empty(str(tmp_path / "bank.json.gz"))
    p = str(tmp_path / "sheet.xopp")
    xopp.make_grid(p, ["ba"], bank, "h", {"ba": [[0, 0, 4.5, -5.5, 8.5, 0]]}, calib=False)

    r1 = learn_from_files(bank, [p])
    assert r1.n_added == 1
    assert len(bank.words["ba"]) == 1

    r2 = learn_from_files(bank, [p])
    assert r2.n_added == 0
    assert len(bank.words["ba"]) == 1, "Học lại cùng file không được nhân đôi mẫu"
