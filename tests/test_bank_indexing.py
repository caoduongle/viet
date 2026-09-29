"""Kiểm thử tính tương đương giữa add_sample_incremental() và rebuild(),
và bảo toàn dấu thanh thô (_raw_marks) khi phân vị thay đổi."""
from chuviettay.config import TONES
from chuviettay.model.bank import Bank


def test_incremental_indexing_matches_rebuild_exactly(tmp_path):
    """Thêm 30 mẫu có dấu và không dấu lần lượt qua add_sample_incremental(),
    sau mỗi lần thêm hoặc khi kết thúc, `marks` và `tl` phải khớp 100% với `rebuild()`."""
    p = str(tmp_path / "test_inc.json.gz")
    b = Bank.create_empty(p)

    # Tập mẫu thử với dấu huyền (\u0300) và sắc (\u0301)
    samples = [
        ("chào", [[0, 0, 5, -6, 10, 0, 14, -5], [7, -11 + i * 0.1, 9, -9 + i * 0.1]], 14.0)
        for i in range(15)
    ] + [
        ("má", [[0, 0, 4, -5, 8, 0, 12, -5], [6, -10 + i * 0.2, 8, -12 + i * 0.2]], 12.0)
        for i in range(15)
    ]

    for label, strokes, width in samples:
        b.add_sample_incremental(label, strokes, width)

    # Lưu lại trạng thái tạo bởi incremental
    inc_marks = {t: list(b.marks[t]) for t in TONES}
    inc_tl = {k: list(v) for k, v in b.tl.items()}

    # Chạy rebuild() từ đầu từ self.words
    b.rebuild()
    rebuilt_marks = {t: list(b.marks[t]) for t in TONES}
    rebuilt_tl = {k: list(v) for k, v in b.tl.items()}

    # So sánh khớp tuyệt đối
    assert inc_tl == rebuilt_tl, "Chỉ mục tl bị lệch giữa incremental và rebuild!"
    assert inc_marks == rebuilt_marks, "Chỉ mục marks bị lệch giữa incremental và rebuild!"


def test_raw_marks_retains_filtered_outliers(tmp_path):
    """Dấu thô (_raw_marks) phải lưu đầy đủ mọi dấu thanh gặt được;
    khi len >= 10, marks sẽ lọc phân vị nhưng _raw_marks không được xoá bỏ các dấu đó."""
    p = str(tmp_path / "test_raw.json.gz")
    b = Bank.create_empty(p)

    # Thêm 12 mẫu dấu huyền (\u0300), trong đó có mẫu biên trên/dưới
    for i in range(12):
        dy_offset = -8.0 if i == 0 else (-7.0 if i == 1 else (i - 6) * 0.1)
        b.add_sample_incremental(
            "chào",
            [[0, 0, 5, -6, 10, 0, 14, -5], [7, -11 + dy_offset, 9, -9 + dy_offset]],
            14.0
        )

    assert hasattr(b, "_raw_marks"), "Bank phải có thuộc tính _raw_marks"
    assert len(b._raw_marks["\u0300"]) == 12, "Toàn bộ 12 dấu phải còn nguyên trong _raw_marks"
    # marks áp dụng lọc phân vị 10-90% khi có >= 10 mẫu -> loại bỏ biên (còn 9 mẫu)
    assert len(b.marks["\u0300"]) == 9, "marks phải lọc phân vị khi có 12 mẫu (còn 9 mẫu)"


def test_tone_marks_parity_across_different_counts(tmp_path):
    """Kiểm tra tính tương đương tuyệt đối giữa incremental và rebuild
    ở các mốc số lượng dấu: < 10 (chưa lọc), == 10 (bắt đầu lọc), và > 10."""
    p = str(tmp_path / "parity_counts.json.gz")
    b = Bank.create_empty(p)

    for i in range(25):
        dy_off = (i - 12) * 0.15
        dx_off = (i % 5 - 2) * 0.1
        b.add_sample_incremental(
            "chào",
            [[0, 0, 5, -6, 10, 0, 14, -5], [7 + dx_off, -11 + dy_off, 9 + dx_off, -9 + dy_off]],
            14.0,
        )
        if i in (5, 9, 10, 15, 24):
            inc_marks = {t: list(b.marks[t]) for t in TONES}
            b_rebuilt = Bank.create_empty(str(tmp_path / f"rebuilt_{i}.json.gz"))
            b_rebuilt.words = {k: list(v) for k, v in b.words.items()}
            b_rebuilt.rebuild()
            rebuilt_marks = {t: list(b_rebuilt.marks[t]) for t in TONES}
            assert inc_marks == rebuilt_marks, f"Marks không khớp ở mốc {i+1} mẫu!"
