"""Fixture dùng chung cho toàn bộ bộ kiểm thử.

Nguyên tắc: test KHÔNG BAO GIỜ đụng vào kho mẫu thật của người dùng -- dùng bản chụp cố định
trong tests/data/, và luôn làm việc trên BẢN SAO trong thư mục tạm (real_bank_path). Với các test cần kết quả tất định, dùng kho
mẫu nhỏ tự dựng (tiny_bank_path) để tự tính tay được đáp án.
"""
import gzip
import json
import os
import shutil

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
# Fixture kho mẫu tổng hợp độc lập (sinh bởi scripts/gen_synthetic_bank.py), hoàn toàn
# không chứa dữ liệu cá nhân nhưng có đầy đủ dấu thanh, từ mốc, chữ số và dấu câu.
REAL_BANK = os.path.join(HERE, "data", "kho_mau_tong_hop.json.gz")


@pytest.fixture(autouse=True)
def _no_log_file(monkeypatch):
    """Không để test tạo file chuviettay.log trong thư mục dự án."""
    from chuviettay import logging_setup
    monkeypatch.setattr(logging_setup, "_configured", True)


@pytest.fixture
def real_bank_path(tmp_path):
    """Bản sao (trong thư mục tạm) của fixture kho mẫu tổng hợp."""
    dst = tmp_path / "bank.json.gz"
    shutil.copy(REAL_BANK, dst)
    return str(dst)


@pytest.fixture
def real_bank(real_bank_path):
    from chuviettay.model.bank import Bank
    return Bank(real_bank_path)


def _inst(w, strokes, T="", vi=-1, ti=-1):
    return {"w": w, "s": strokes, "T": T, "vi": vi, "ti": ti}


def tiny_bank_dict():
    """Kho mẫu nhỏ, tự dựng, đủ để chạm mọi nhánh chính của thuật toán:
    - "xin": 5 mẫu, độ rộng ổn định -> ứng viên từ mốc hiệu chỉnh cỡ tay
    - "ba": không dấu -> làm thân chữ khi ghép "bà"/"bá"...
    - "chào": có dấu huyền (nét dấu là nét số 1) -> cung cấp nét dấu thanh rời để ghép
    - chữ số 1, 2 và dấu , . cho nhánh số / dấu câu
    """
    xin = [_inst(w, [[0, 0, 3, -5, 6, 0, 9, -5]]) for w in (9.0, 9.2, 8.8, 9.1, 8.9)]
    return {
        "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0, "v": 1,
        "x0": 78.0, "width": 500.0, "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": {
            "xin": xin,
            "ba": [_inst(8.0, [[0, 0, 4, -5, 8, 0]]), _inst(8.4, [[0, 0, 4, -5.5, 8.4, 0]])],
            "chào": [
                _inst(14.0, [[0, 0, 5, -6, 10, 0, 14, -5], [7, -11, 9, -9]], T="\u0300", vi=2, ti=1),
                _inst(14.4, [[0, 0, 5, -6, 10, 0, 14.4, -5], [7.4, -11.5, 9.4, -9.5]], T="\u0300", vi=2, ti=1),
            ],
        },
        "digits": {"1": [_inst(3.0, [[0, 0, 1, -6]])], "2": [_inst(4.0, [[0, -6, 3, -6, 0, 0, 4, 0]])]},
        "punct": {",": [{"w": 1.0, "s": [[0, 0, 0.5, 1.5]]}], ".": [{"w": 1.0, "s": [[0, 0, 0.5, 0.5]]}]},
        "symbols": {},
        "letters": {
            "x": [_inst(2.5, [[0, 0, 2.5, -5]])],
            "i": [_inst(1.5, [[0, 0, 1.5, -5]])],
            "n": [_inst(3.0, [[0, 0, 3.0, -5]])],
            "b": [_inst(3.5, [[0, 0, 3.5, -7]])],
            "a": [_inst(3.0, [[0, 0, 3.0, -5]])],
            "c": [_inst(2.5, [[0, 0, 2.5, -5]])],
            "h": [_inst(3.5, [[0, 0, 3.5, -7]])],
            "o": [_inst(3.0, [[0, 0, 3.0, -5]])],
        },
        "marks": {},
    }


def generate_large_synthetic_bank_dict(n_samples: int = 5000) -> dict:
    """Tạo nhanh kho mẫu tổng hợp có số lượng mẫu lớn (mặc định 5,000) phục vụ benchmark.
    Bao gồm các từ có dấu thanh để kiểm thử chỉ mục _raw_marks và lọc phân vị."""
    tones_list = ["", "\u0300", "\u0301", "\u0303", "\u0309", "\u0323"]
    words_dict = {}
    samples_per_word = 10
    num_words = max(1, n_samples // samples_per_word)

    for w_idx in range(num_words):
        t = tones_list[w_idx % len(tones_list)]
        word_label = f"word_{w_idx}" if not t else f"word_{w_idx}{t}"
        samples = []
        for s_idx in range(samples_per_word):
            ti = 1 if t else -1
            vi = 2 if t else -1
            strokes = [[0.0, 0.0, 5.0, -5.0, 10.0, 0.0]]
            if t:
                strokes.append([5.0, -10.0 + s_idx * 0.05, 7.0, -8.0 + s_idx * 0.05])
            samples.append({"w": 12.0 + (s_idx * 0.1), "s": strokes, "T": t, "vi": vi, "ti": ti})
        words_dict[word_label] = samples

    return {
        "schema_version": 2,
        "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0, "v": 1,
        "x0": 78.0, "width": 500.0, "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": words_dict,
        "digits": {"1": [{"w": 3.0, "s": [[0, 0, 1, -6]]}]},
        "punct": {".": [{"w": 1.0, "s": [[0, 0, 0.5, 0.5]]}]},
        "tombstones": {},
        "generation": 1,
    }


@pytest.fixture
def tiny_bank_path(tmp_path):
    p = tmp_path / "tiny.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(tiny_bank_dict(), f, ensure_ascii=False)
    return str(p)


@pytest.fixture
def tiny_bank(tiny_bank_path):
    from chuviettay.model.bank import Bank
    return Bank(tiny_bank_path)


def make_corrupt_bank(path: str, mode: str = "bad_gzip") -> str:
    """Tạo file kho mẫu bị hỏng ở path:
    - 'bad_gzip': header/payload gzip không hợp lệ
    - 'bad_json': gzip hợp lệ nhưng bên trong là JSON sai cú pháp
    - 'empty': file 0 bytes
    """
    if mode == "empty":
        with open(path, "wb"):
            pass
    elif mode == "bad_gzip":
        with open(path, "wb") as f:
            f.write(b"not-a-gzip-stream-at-all\x00\x01\x02\x03")
    elif mode == "bad_json":
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write("{invalid-json-content: 123,")
    return path


@pytest.fixture
def legacy_words_only_bank_path(tmp_path):
    """Kho mẫu chỉ chứa từ nguyên khối cũ (words) và hoàn toàn không có letters."""
    p = tmp_path / "legacy_bank.json.gz"
    d = {
        "schema_version": 1,
        "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0, "v": 1,
        "x0": 78.0, "width": 500.0, "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": {
            "xin": [{"w": 9.0, "s": [[0, 0, 3, -5, 6, 0, 9, -5]]}],
            "chào": [{"w": 14.0, "s": [[0, 0, 5, -6, 10, 0, 14, -5], [7, -11, 9, -9]], "T": "\u0300", "vi": 2, "ti": 1}],
        },
        "digits": {}, "punct": {}, "symbols": {}, "letters": {}, "marks": {},
    }
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    return str(p)


@pytest.fixture
def legacy_words_only_bank(legacy_words_only_bank_path):
    from chuviettay.model.bank import Bank
    return Bank(legacy_words_only_bank_path)


def extract_rendered_line_labels_from_tokens(tokens: list[str], prefix: str = "LINE_") -> list[str]:
    """Lọc danh sách các nhãn dòng theo tiền tố prefix từ danh sách token đã kết xuất."""
    return [t for t in tokens if t.startswith(prefix)]


