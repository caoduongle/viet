"""Golden-master: đầu ra thuật toán phải GIỐNG HỆT bản gốc (trước khi tái cấu trúc sang MVC).

Các mã SHA-256 dưới đây được sinh bằng cách chạy CHÍNH bản hw_note.py gốc (một file) trên kho mẫu
nhỏ trong conftest.py với cùng văn bản/tuỳ chọn/seed -- không phải chạy lại từ bản mới, nên đây là
bằng chứng độc lập chứ không phải tự so với chính mình.

Khi nào test này đỏ?
  * Bạn vừa sửa thuật toán (writer.py / composer.py / xopp.py / text_utils.py ...) làm đổi nét vẽ
    ra. Nếu là CỐ Ý: kiểm tra kết quả bằng mắt trong Xournal++, rồi cập nhật hằng số GOLDEN bên dưới
    (thông báo lỗi in sẵn mã băm mới). Nếu KHÔNG cố ý: bạn vừa làm hỏng hành vi cũ -- hoàn tác đi.
  * Hiếm: phiên bản Python khác đổi cách sinh số ngẫu nhiên (random.gauss/randrange). Các mã này đã
    kiểm với Python 3.12; nếu chỉ lệch trên máy khác mà không sửa gì, so sánh với 3.12 trước.
"""
import gzip
import hashlib

import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions

GOLDEN = {
    "co_ban": {
        "xopp": "74d594d85731358506dd3fd935504570640da12eae6ddbab5fa2e66eb95af2d3",
        "thieu": "4e88b973407a89a6e1fcf78041ae02622bfdd03718b3cce988ac77a38679941d",
    },
    "tuy_chon": {"xopp": "b375acd8be97d4634e1e5747ad959fb9b36e5e389544a7210e44221a0eca7e29"},
    "nhieu_trang": {"xopp": "993a1d12a66338137a57e3fa76696085896e4845d1161c296f36fd93bdec637d"},
    "strict_case": {
        "xopp": "9010c33617ff2caea0d58915f02f35e9f655c1a5f8a4cb4fe0e1142ef72226c7",
        "thieu": "1dac4d3e0fdcc956b9335238e103c87b8c26f23646941c110485e076e643eb1a",
    },
}

CASES = {
    "co_ban": ("xin ba bà chào Xin 12 1,2 xin. (xin) zzz bá", WriteOptions(seed=7)),
    "tuy_chon": ("xin ba bà chào\n\nxin xin xin ba ba 12 1,2 xin",
                 WriteOptions(width=60, scale=1.3, space=1.2, jitter=0.5, seed=21, color="#1a237e", wscale=1.4)),
    "nhieu_trang": ("\n".join(["xin ba bà"] * 7), WriteOptions(line=1000, seed=3)),
    "strict_case": ("Xin Ba xin", WriteOptions(strict_case=True, seed=1)),
}


def sha(path):
    return hashlib.sha256(gzip.decompress(open(path, "rb").read())).hexdigest()


@pytest.mark.parametrize("name", sorted(CASES))
def test_dau_ra_giong_het_ban_goc(name, tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    text, opts = CASES[name]
    out = str(tmp_path / (name + ".xopp"))
    result = ctl.write_text(text, opts, out)

    assert sha(out) == GOLDEN[name]["xopp"], (
        "%s: file .xopp khác bản gốc. Mã băm mới: %s" % (name, sha(out)))
    if "thieu" in GOLDEN[name]:
        assert result.missing_grid_path, "%s: bản gốc có tạo file _thieu.xopp mà bản mới không" % name
        assert sha(result.missing_grid_path) == GOLDEN[name]["thieu"], (
            "%s: file _thieu.xopp khác bản gốc. Mã băm mới: %s" % (name, sha(result.missing_grid_path)))
    else:
        assert result.missing_grid_path is None, "%s: bản gốc không tạo file _thieu.xopp" % name
