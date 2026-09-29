"""Bank: nạp/lưu/tạo mới/thêm-xoá mẫu/chỉ mục tra cứu."""
import gzip
import json
import os

import pytest

from chuviettay.config import NANG, TONES
from chuviettay.model.bank import (
    Bank,
    BankCorruptedError,
    BankError,
    BankNotFoundError,
    BankValidationError,
    UnsupportedSchemaVersionError,
)


def test_nap_kho_nho(tiny_bank):
    assert set(tiny_bank.words) == {"xin", "ba", "chào"}
    assert tiny_bank.xh == 7.0
    assert set(tiny_bank.digits) == {"1", "2"}


def test_thieu_file_nem_BankNotFoundError_chu_khong_thoat_chuong_trinh(tmp_path):
    p = str(tmp_path / "khong_co.json.gz")
    with pytest.raises(BankNotFoundError) as ei:
        Bank(p)
    assert p in str(ei.value)
    assert isinstance(ei.value, FileNotFoundError)


def test_create_empty_va_load_or_create(tmp_path):
    p = str(tmp_path / "moi.json.gz")
    b = Bank.load_or_create(p)                                   # chưa có -> tạo
    assert b.words == {} and b.xh == 7.0
    b.add_sample("xin", [[0, 0, 3, -5]], 3.0)
    b.rebuild(); b.save()
    again = Bank.load_or_create(p)                               # đã có -> KHÔNG ghi đè
    assert "xin" in again.words


def test_rebuild_tao_chi_muc_than_chu_va_dau_thanh(tiny_bank):
    assert {k for k in tiny_bank.tl} == {"ba", "chao", "xin"}
    assert len(tiny_bank.tl["chao"]) == 2
    assert len(tiny_bank.marks["\u0300"]) == 2                   # 2 mẫu "chào" cho ra 2 nét dấu huyền rời
    assert all(len(tiny_bank.marks[t]) == 0 for t in TONES if t != "\u0300")


def test_marks_da_quy_ve_goc_toa_do(tiny_bank):
    for m in tiny_bank.marks["\u0300"]:
        xs, ys = m["s"][0][0::2], m["s"][0][1::2]
        assert sum(xs) / len(xs) == pytest.approx(0, abs=1e-9)
        assert sum(ys) / len(ys) == pytest.approx(0, abs=1e-9)


def test_can(tiny_bank):
    assert tiny_bank.can("ba")            # có thẳng
    assert tiny_bank.can("bà")            # ghép thân "ba" + dấu huyền rời
    assert not tiny_bank.can("bá")        # có thân nhưng chưa có nét dấu sắc để ghép
    assert tiny_bank.can("chao")          # không dấu: dùng thân của "chào"
    assert not tiny_bank.can("zzz")


def test_add_sample_tu_tim_net_dau_thanh(tiny_bank):
    body, tone = [0, 0, 5, -5, 10, 0], [4, -12, 6, -10]
    inst = tiny_bank.add_sample("bà", [body, tone], 10.004)
    assert inst["T"] == "\u0300" and inst["vi"] == 1 and inst["ti"] == 1
    assert inst["w"] == 10.0                                      # làm tròn 2 số lẻ
    assert tiny_bank.words["bà"] == [inst]


def test_add_sample_cum_nhieu_tu_khong_tim_dau_thanh(tiny_bank):
    # Cùng bộ nét, chỉ khác nhãn: từ đơn thì nhận ra nét dấu, cụm có khoảng trắng thì KHÔNG dò
    # (cặp đối chứng -- nếu bỏ điều kiện `" " not in label` thì cụm cũng ra ti=1 và test này vỡ).
    body, tone = [0, 0, 5, -5, 10, 0], [4, -12, 6, -10]
    single = tiny_bank.add_sample("bà", [body, tone], 10)
    phrase = tiny_bank.add_sample("bà ba", [body, tone], 20)
    assert single["ti"] == 1
    assert phrase["ti"] == -1


def test_add_sample_khong_tu_rebuild(tiny_bank):
    tiny_bank.add_sample("bà", [[0, 0, 5, -5, 10, 0], [4, -12, 6, -10]], 10)
    assert "bà" not in [k for k, _ in sum(tiny_bank.tl.values(), [])]   # chỉ mục chưa cập nhật
    tiny_bank.rebuild()
    assert any(k == "bà" for k, _ in sum(tiny_bank.tl.values(), []))


def test_drop(tiny_bank):
    assert tiny_bank.drop("ba") == 2
    assert tiny_bank.drop("ba") == 0
    assert "ba" not in tiny_bank.words


def test_drop_non_existent_word_does_not_mutate_tombstones_or_generation(tiny_bank):
    gen_before = tiny_bank._generation
    tomb_count_before = len(tiny_bank._tombstones)
    assert "never_existed_xyz" not in tiny_bank.words
    assert tiny_bank.drop("never_existed_xyz") == 0
    assert tiny_bank._generation == gen_before
    assert len(tiny_bank._tombstones) == tomb_count_before
    assert "never_existed_xyz" not in tiny_bank._tombstones


def test_save_roi_nap_lai_giu_nguyen_tieng_viet(tiny_bank, tmp_path):
    tiny_bank.add_sample("bà", [[0, 0, 5, -5, 10, 0], [4, -12, 6, -10]], 10)
    tiny_bank.save()
    again = Bank(tiny_bank.path)
    assert "bà" in again.words and again.words["bà"][0]["ti"] == 1
    raw = gzip.decompress(open(tiny_bank.path, "rb").read()).decode("utf-8")
    assert "chào" in raw                                          # ensure_ascii=False: đọc được bằng mắt
    assert json.loads(raw)["xh"] == 7.0


def test_kho_that_nap_duoc_va_chi_muc_hop_ly(real_bank):
    assert len(real_bank.words) == 13
    assert sum(len(v) for v in real_bank.words.values()) == 99
    assert len(real_bank.marks[NANG]) > 0
    assert real_bank.can("số") and real_bank.can("sổ")            # "sổ" chưa dạy nhưng ghép được


# ------------------------------------------------------------ ghi an toàn
def test_save_bi_ngat_giua_chung_thi_kho_cu_con_nguyen_va_khong_de_lai_file_tam(tiny_bank, monkeypatch):
    """Mô phỏng mất điện/đầy đĩa GIỮA lúc ghi: file kho mẫu cũ phải còn đọc được như trước."""
    import json as _json
    before = open(tiny_bank.path, "rb").read()
    tiny_bank.add_sample("mới", [[0, 0, 4, -5]], 4.0)

    real_dump = _json.dump
    def dump_roi_ngat(obj, fp, **kw):
        fp.write("{\"xh\": 7.0, \"words\": {\"x\"")          # ghi dở dang rồi 'mất điện'
        raise OSError("đĩa đầy")
    monkeypatch.setattr("chuviettay.model.bank.json.dump", dump_roi_ngat)
    with pytest.raises(OSError, match="đĩa đầy"):
        tiny_bank.save()
    monkeypatch.setattr("chuviettay.model.bank.json.dump", real_dump)

    parent = os.path.dirname(tiny_bank.path)
    assert open(tiny_bank.path, "rb").read() == before                   # file thật không suy suyển một byte
    assert not any(f.endswith(".tmp") for f in os.listdir(parent))       # không để rác lại
    assert "mới" not in Bank(tiny_bank.path).words                        # vẫn nạp lại bình thường


def test_save_thanh_cong_khong_de_lai_file_tam(tiny_bank):
    tiny_bank.add_sample("mới", [[0, 0, 4, -5]], 4.0)
    tiny_bank.save()
    parent = os.path.dirname(tiny_bank.path)
    assert not any(f.endswith(".tmp") for f in os.listdir(parent))
    assert "mới" in Bank(tiny_bank.path).words


# ------------------------------------------------------------ kiểm tra dữ liệu hỏng & schema
def test_nap_file_rong_0_bytes_bao_loi(tmp_path):
    p = str(tmp_path / "empty.json.gz")
    open(p, "wb").close()
    with pytest.raises(BankCorruptedError, match="0 bytes"):
        Bank(p)


def test_nap_file_gzip_hong_bao_loi(tmp_path):
    p = str(tmp_path / "bad.json.gz")
    with open(p, "wb") as f:
        f.write(b"day khong phai file gzip")
    with pytest.raises(BankCorruptedError, match="gzip"):
        Bank(p)


def test_nap_file_json_hong_bao_loi(tmp_path):
    p = str(tmp_path / "bad_json.json.gz")
    with gzip.open(p, "wb") as f:
        f.write(b"{khong phai json hop le:")
    with pytest.raises(BankCorruptedError, match="JSON"):
        Bank(p)


def test_nap_file_thieu_truong_words_bao_loi(tmp_path):
    p = str(tmp_path / "missing_words.json.gz")
    d = {"xh": 7.0, "digits": {}, "punct": {}, "pen": {"tool": "pen", "color": "#000", "width": "1"}}
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    with pytest.raises(BankValidationError, match="words"):
        Bank(p)


def test_nap_file_xh_am_bao_loi(tmp_path):
    p = str(tmp_path / "bad_xh.json.gz")
    d = {"xh": -2.0, "words": {}, "digits": {}, "punct": {}, "pen": {"tool": "pen", "color": "#000", "width": "1"}}
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    with pytest.raises(BankValidationError, match="xh"):
        Bank(p)


def test_nap_file_schema_version_moi_hon_bao_loi(tmp_path):
    p = str(tmp_path / "future_version.json.gz")
    d = Bank.empty_dict()
    d["schema_version"] = 999
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    with pytest.raises(UnsupportedSchemaVersionError, match="schema_version=999"):
        Bank(p)


def test_nap_file_stroke_so_luong_toa_do_le_bao_loi(tmp_path):
    p = str(tmp_path / "odd_stroke.json.gz")
    d = Bank.empty_dict()
    d["words"]["test"] = [{"w": 5.0, "s": [[0, 0, 5]], "T": "", "vi": -1, "ti": -1}]
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    with pytest.raises(BankValidationError, match="chẵn"):
        Bank(p)


def test_nap_file_stroke_toa_do_nan_inf_bao_loi(tmp_path):
    p = str(tmp_path / "nan_stroke.json.gz")
    d = Bank.empty_dict()
    d["words"]["test"] = [{"w": 5.0, "s": [[0, 0, float("nan"), 0]], "T": "", "vi": -1, "ti": -1}]
    # Cho phép nan qua allow_nan=True để kiểm tra validator bắt được
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f, allow_nan=True)
    with pytest.raises(BankValidationError, match="hữu hạn"):
        Bank(p)


def test_nap_file_stroke_rong_bao_loi(tmp_path):
    p = str(tmp_path / "empty_stroke.json.gz")
    d = Bank.empty_dict()
    d["words"]["test"] = [{"w": 5.0, "s": [], "T": "", "vi": -1, "ti": -1}]
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    with pytest.raises(BankValidationError, match="không rỗng"):
        Bank(p)


def test_nap_file_thieu_metadata_line_bao_loi(tmp_path):
    p = str(tmp_path / "missing_line.json.gz")
    d = Bank.empty_dict()
    del d["line"]
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    with pytest.raises(BankValidationError, match="line"):
        Bank(p)


def test_di_tru_kho_v1_thieu_metadata_tu_dong_dien_defaults(tmp_path):
    p = str(tmp_path / "legacy_missing_metrics.json.gz")
    d = {
        "xh": 7.0,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.2", "capStyle": "round"},
        "words": {"a": [{"w": 5.0, "s": [[0, 0, 5, 0]], "T": "", "vi": -1, "ti": -1}]},
        "digits": {}, "punct": {},
    }
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)
    b = Bank(p)
    assert b.d["schema_version"] == 3
    assert b.d["line"] == 24.0
    assert b.d["width"] == 500.0
    assert b.d["x0"] == 78.0
    assert b.d["wgaps"] == [11.0]


def test_di_tru_kho_v1_legacy_sang_v2_trong_bo_nho(tmp_path):
    p = str(tmp_path / "legacy_v1.json.gz")
    d = {
        "xh": 7.0, "wgaps": [11.0], "dgaps": [3.5], "line": 24.0, "v": 1,
        "x0": 78.0, "width": 500.0, "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": {"ba": [{"w": 8.0, "s": [[0, 0, 4, -5, 8, 0]], "T": "", "vi": -1, "ti": -1}]},
        "digits": {}, "punct": {},
    }
    # File gốc trên đĩa hoàn toàn không có trường schema_version
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f)

    b = Bank(p)
    # Trong bộ nhớ đã được nâng cấp lên schema_version = 3
    assert b.d["schema_version"] == 3
    assert "ba" in b.words

    # Nhưng trên đĩa vẫn giữ nguyên bản gốc (chưa ghi đè vì chỉ đọc)
    disk_raw = gzip.decompress(open(p, "rb").read()).decode("utf-8")
    assert "schema_version" not in disk_raw

    # Khi có thao tác save() mới ghi phiên bản 3 xuống đĩa
    b.save()
    disk_after = gzip.decompress(open(p, "rb").read()).decode("utf-8")
    assert '"schema_version":3' in disk_after


def test_concurrent_save_an_toan_khong_lam_hong_kho(tmp_path):
    """Mô phỏng nhiều luồng/tiến trình cùng gọi save(): file kho không bị hỏng VÀ không mất dữ liệu (no lost updates)."""
    import concurrent.futures

    p = str(tmp_path / "concurrent_bank.json.gz")
    b_init = Bank.create_empty(p)
    b_init.add_sample("goc", [[0, 0, 5, 0]], 5.0)
    b_init.save()

    def do_save(thread_idx: int) -> None:
        bank = Bank(p)
        w_val = float(thread_idx + 1)
        bank.add_sample(f"tu_{thread_idx}", [[0, 0, w_val, 0]], w_val)
        bank.save()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(do_save, i) for i in range(8)]
        for f in concurrent.futures.as_completed(futures):
            f.result()  # Đảm bảo không ném ngoại lệ

    # File cuối cùng phải nguyên vẹn và nạp lại bình thường
    final_bank = Bank(p)
    assert final_bank.d["schema_version"] == 3
    assert "goc" in final_bank.words
    assert not any(f.endswith(".tmp") for f in os.listdir(tmp_path))

    # TẤT CẢ các từ được ghi đồng thời đều phải còn nguyên (không bị lost update)
    for i in range(8):
        assert f"tu_{i}" in final_bank.words, f"tu_{i} bị mất sau concurrent save!"


def test_merge_bank_dicts_deduplicates_and_respects_deleted_words():
    """Kiểm tra merge_bank_dicts khử trùng mẫu và không hồi sinh từ đã xóa."""
    from chuviettay.model.bank import merge_bank_dicts

    base = {
        "words": {
            "xin": [{"w": 8.0, "s": [[0, 0, 5, 5]], "T": "", "vi": -1, "ti": -1}],
            "chao": [{"w": 9.0, "s": [[0, 0, 6, 6]], "T": "", "vi": -1, "ti": -1}],
        },
        "digits": {},
        "punct": {},
    }

    disk = {
        "words": {
            # "xin" có 1 mẫu trùng toạ độ (sẽ bỏ qua) và 1 mẫu mới (sẽ thêm vào)
            "xin": [
                {"w": 8.0, "s": [[0.0, 0.0, 5.0, 5.0]], "T": "", "vi": -1, "ti": -1},
                {"w": 8.5, "s": [[0, 0, 7, 7]], "T": "", "vi": -1, "ti": -1},
            ],
            # "ban" là từ mới trên đĩa -> thêm vào base
            "ban": [{"w": 7.0, "s": [[0, 0, 4, 4]], "T": "", "vi": -1, "ti": -1}],
            # "chao" đã bị xóa khỏi base -> không được hồi sinh
            "chao": [{"w": 9.0, "s": [[0, 0, 6, 6]], "T": "", "vi": -1, "ti": -1}],
        },
        "digits": {"1": [{"w": 4.0, "s": [[0, 0, 0, 10]], "T": "", "vi": -1, "ti": -1}]},
        "punct": {},
    }

    deleted_words = {"chao"}
    merged = merge_bank_dicts(base, disk, deleted_words=deleted_words)

    # 1. "xin" phải có đúng 2 mẫu (1 gốc + 1 mới, không bị trùng mẫu [[0,0,5,5]])
    assert len(merged["words"]["xin"]) == 2
    # 2. "ban" được gộp vào
    assert "ban" in merged["words"]
    # 3. "chao" nằm trong deleted_words nên không được có trong merged
    assert "chao" not in merged["words"]
    # 4. "digits" được gộp đúng
    assert "1" in merged["digits"]


def test_create_empty_atomic_pipeline(tmp_path):
    """Kiểm tra Bank.create_empty() tạo file hợp lệ, nguyên tử và không để lại file rác."""
    p = str(tmp_path / "new_empty_bank.json.gz")
    b = Bank.create_empty(p)
    assert os.path.exists(p)
    assert b.d["schema_version"] == 3
    assert b.words == {}
    assert not any(f.endswith(".tmp") for f in os.listdir(tmp_path))
    # Mở lại kiểm tra tính toàn vẹn
    reloaded = Bank(p)
    assert reloaded.d["schema_version"] == 3


def test_incremental_teach_performance_and_correctness(tmp_path):
    """Kiểm tra add_sample_incremental hoạt động chính xác và đạt hiệu năng cao."""
    import time

    p = str(tmp_path / "incremental_bank.json.gz")
    b = Bank.create_empty(p)

    start = time.perf_counter()
    for i in range(50):
        w = f"word_{i}"
        b.add_sample_incremental(w, [[0.0, 0.0, 5.0, 0.0]], 5.0)
    b.save()
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"Thêm 50 từ tăng dần mất {elapsed:.2f}s (quá ngưỡng 1.0s)"
    assert len(b.words) == 50
    for i in range(50):
        assert b.can(f"word_{i}")
        assert f"word_{i}" in b.tl


def test_sequential_teach_benchmark_with_tones(tmp_path):
    """Kiểm tra hiệu năng lưu tuần tự khi dạy 20 từ liên tiếp có dấu thanh.
    Nhờ fast-path cache validation (bỏ qua đọc lại đĩa và rebuild) và compresslevel=6,
    tổng thời gian 20 lần dạy liên tiếp phải < 1.0s (trung bình < 50ms/từ)."""
    import time

    p = str(tmp_path / "bench_bank.json.gz")
    b = Bank.create_empty(p)

    # 1. Khởi tạo kho có sẵn 100 từ
    for i in range(100):
        b.add_sample(f"word_{i}", [[0.0, 0.0, 5.0, 0.0]], 5.0)
    b.rebuild()
    b.save()

    # 2. Dạy 20 từ tuần tự có dấu thanh (mỗi từ add_sample_incremental + save)
    words_to_teach = [
        ("bà", [[0.0, 0.0, 5.0, -5.0, 10.0, 0.0], [4.0, -12.0, 6.0, -10.0]], 10.0),
        ("bá", [[0.0, 0.0, 5.0, -5.0, 10.0, 0.0], [6.0, -12.0, 4.0, -10.0]], 10.0),
        ("bả", [[0.0, 0.0, 5.0, -5.0, 10.0, 0.0], [4.0, -12.0, 5.0, -14.0, 6.0, -12.0]], 10.0),
        ("bã", [[0.0, 0.0, 5.0, -5.0, 10.0, 0.0], [4.0, -12.0, 5.0, -10.0, 6.0, -12.0]], 10.0),
        ("bạ", [[0.0, 0.0, 5.0, -5.0, 10.0, 0.0], [5.0, 3.0, 5.0, 3.5]], 10.0),
    ] * 4  # 20 words

    start = time.perf_counter()
    for w, strokes, width in words_to_teach:
        b.add_sample_incremental(w, strokes, width)
        b.save()
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"Dạy 20 từ tuần tự mất {elapsed:.3f}s (quá ngưỡng 1.0s, trung bình {elapsed/20*1000:.1f}ms/từ)"
    assert len(b.words) >= 105
    for w, _, _ in words_to_teach:
        assert b.can(w)


def test_merge_bank_dicts_preserves_samples_with_same_strokes_different_metadata():
    """Kiểm tra merge_bank_dicts phân biệt mẫu dựa trên cả toạ độ nét và siêu dữ liệu (w, T, vi, ti).
    Hai mẫu có nét trùng nhau nhưng độ rộng hoặc dấu khác nhau phải được giữ lại cả hai."""
    from chuviettay.model.bank import merge_bank_dicts

    base = {
        "words": {
            "test": [
                {"w": 10.0, "s": [[0.0, 0.0, 5.0, 0.0]], "T": "", "vi": -1, "ti": -1},
            ]
        },
        "digits": {},
        "punct": {},
    }

    disk = {
        "words": {
            "test": [
                # Mẫu trùng toạ độ nét nhưng độ rộng khác (w=12.0 thay vì 10.0)
                {"w": 12.0, "s": [[0.0, 0.0, 5.0, 0.0]], "T": "", "vi": -1, "ti": -1},
                # Mẫu trùng hoàn toàn cả nét và w=10.0
                {"w": 10.0, "s": [[0.0, 0.0, 5.0, 0.0]], "T": "", "vi": -1, "ti": -1},
                # Mẫu trùng toạ độ nét nhưng có dấu thanh (T, vi, ti)
                {"w": 10.0, "s": [[0.0, 0.0, 5.0, 0.0]], "T": "\u0300", "vi": 1, "ti": 0},
            ]
        },
        "digits": {},
        "punct": {},
    }

    merged = merge_bank_dicts(base, disk)
    samples = merged["words"]["test"]
    # Phải có đúng 3 mẫu phân biệt: (w=10, T=""), (w=12, T=""), (w=10, T=huyền)
    # Mẫu trùng hoàn toàn (w=10, T="") bị khử trùng.
    assert len(samples) == 3
    widths = [s["w"] for s in samples]
    assert widths.count(10.0) == 2
    assert widths.count(12.0) == 1


# ------------------------------------------------------------------ US1 tests: Safe persistence abort
def test_save_aborts_and_does_not_overwrite_when_disk_corrupted(tmp_path):
    """Khi file trên đĩa bị corrupt hoặc không thể load_and_validate, Bank.save()
    bắt buộc phải raise BankError, dọn sạch file tạm, và KHÔNG được ghi đè file trên đĩa."""
    from tests.conftest import make_corrupt_bank
    p = str(tmp_path / "bank.json.gz")
    b = Bank.create_empty(p)
    b.add_sample("xin", [[0, 0, 5, 0]], 5.0)
    b.save()

    # Làm hỏng file trên đĩa từ một nguồn bên ngoài
    make_corrupt_bank(p, mode="bad_gzip")
    with open(p, "rb") as f:
        corrupted_bytes = f.read()

    # Thay đổi trong bộ nhớ và lưu lại -> phải raise BankCorruptedError hoặc BankError
    b.add_sample("chao", [[0, 0, 6, 0]], 6.0)
    with pytest.raises(BankError):
        b.save()

    # File trên đĩa phải còn nguyên vẹn byte-identical với trạng thái corrupt
    with open(p, "rb") as f:
        assert f.read() == corrupted_bytes

    # Thư mục cha không còn sót file .tmp
    parent = tmp_path
    tmp_files = list(parent.glob("*.tmp")) + list(parent.glob(".bank_*.tmp"))
    assert len(tmp_files) == 0


def test_save_force_overwrite_replaces_corrupt_disk(tmp_path):
    """Khi người dùng chỉ định rõ force_overwrite=True, Bank.save() bỏ qua merge
    và ghi đè thành công lên file hỏng trên đĩa."""
    from tests.conftest import make_corrupt_bank
    p = str(tmp_path / "bank.json.gz")
    b = Bank.create_empty(p)
    b.add_sample("xin", [[0, 0, 5, 0]], 5.0)
    b.save()

    # Làm hỏng file trên đĩa
    make_corrupt_bank(p, mode="bad_json")

    # Lưu với force_overwrite=True
    b.add_sample("chao", [[0, 0, 6, 0]], 6.0)
    b.save(force_overwrite=True)

    # Nạp lại file từ đĩa phải thành công và có đủ 'xin', 'chao'
    reloaded = Bank(p)
    assert "xin" in reloaded.words
    assert "chao" in reloaded.words


# ------------------------------------------------------------------ US4 benchmark: 5,000 samples
def test_large_bank_persistence_benchmark_5000_samples(tmp_path):
    """Benchmark độ trễ ghi kho mẫu với 5,000 mẫu:
    1. Tạo file kho mẫu với 5,000 mẫu thực tế có đủ dấu thanh.
    2. Nạp kho mẫu lên bộ nhớ và đo thời gian thực hiện 20 lần dạy từ liên tiếp (add_sample_incremental + save).
    3. Kiểm tra độ trễ trung bình mỗi lần lưu < 1.0 giây (bảo đảm đường dẫn nhanh fast-path hoạt động hiệu quả)."""
    import time
    from tests.conftest import generate_large_synthetic_bank_dict

    p = tmp_path / "large_5000.json.gz"
    large_d = generate_large_synthetic_bank_dict(n_samples=5000)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(large_d, f, ensure_ascii=False)

    bank = Bank(str(p))
    total_samples = sum(len(s_list) for s_list in bank.words.values())
    assert total_samples >= 5000

    num_incremental = 50
    latencies = []
    t_start_batch = time.perf_counter()

    for i in range(num_incremental):
        t0 = time.perf_counter()
        bank.add_sample_incremental(
            "chào",
            [[0.0, 0.0, 5.0, -6.0, 10.0, 0.0, 14.0, -5.0], [7.0, -11.0 + i * 0.05, 9.0, -9.0 + i * 0.05]],
            14.0,
        )
        bank.save()
        latencies.append(time.perf_counter() - t0)

    t_total = time.perf_counter() - t_start_batch
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    print(f"\n[BENCHMARK] 50 saves: avg={avg_latency:.4f}s, max={max_latency:.4f}s, total={t_total:.4f}s")
    print(f"[BENCHMARK] First 5 latencies: {[round(x, 4) for x in latencies[:5]]}")
    print(f"[BENCHMARK] Last 5 latencies: {[round(x, 4) for x in latencies[-5:]]}")

    # Đảm bảo độ trễ mỗi lần lưu dưới 1.0s và tổng 50 lần dưới 30.0s (SC-004)
    assert avg_latency < 1.0, f"Độ trễ trung bình quá lớn: {avg_latency:.3f}s (> 1.0s)"
    assert max_latency < 2.0, f"Độ trễ lớn nhất vượt ngưỡng: {max_latency:.3f}s (> 2.0s)"
    assert t_total < 30.0, f"Tổng thời gian batch 50 lần vượt ngưỡng: {t_total:.3f}s (> 30.0s)"

    # Nạp lại kiểm tra tính toàn vẹn
    reloaded = Bank(str(p))
    assert len(reloaded.words["chào"]) >= num_incremental


# ------------------------------------------------------------------ US5 tests: In-memory consistency on drop
def test_drop_prunes_tl_raw_marks_and_updates_can_immediately(tiny_bank):
    """Khi drop(word), các chỉ mục tra cứu trong bộ nhớ (tl, _raw_marks, marks)
    phải được dọn dẹp ngay lập tức và can(word) trả về False mà không cần gọi rebuild()."""
    # tiny_bank có 'chào' (dấu huyền)
    assert tiny_bank.can("chào")
    assert "chao" in tiny_bank.tl
    assert len(tiny_bank.marks["\u0300"]) > 0
    assert len(tiny_bank._raw_marks["\u0300"]) > 0

    # Xoá 'chào'
    removed = tiny_bank.drop("chào")
    assert removed == 2
    assert "chào" not in tiny_bank.words

    # can("chào") phải False ngay lập tức vì không còn thân 'chào' và không còn dấu huyền
    assert not tiny_bank.can("chào")
    assert "chao" not in tiny_bank.tl

    # Dấu huyền trong _raw_marks và marks xuất phát từ 'chào' phải bị loại bỏ
    assert len(tiny_bank._raw_marks["\u0300"]) == 0
    assert len(tiny_bank.marks["\u0300"]) == 0

