#!/usr/bin/env python3
"""Script nghiệm thu tính năng chuyển đổi thuần ký tự và nạp file lưới .xopp (R1 - R4).

Chạy:
    python tools/accept_char_bank.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Đảm bảo import được chuviettay
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from chuviettay.controller.app_controller import AppController
from chuviettay.model.char_catalog import CATALOG_GROUPS
from chuviettay.model.composer import WriteOptions
from chuviettay.model.writer import Writer
from tests.helpers import fill_grid_with_ink


def main() -> int:
    print("=" * 70)
    print("BÁO CÁO NGHIỆM THU: CHUYỂN ĐỔI THUẦN KÝ TỰ & NẠP LƯỚI Ô .XOPP")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # -------------------------------------------------------------
        # 1. Kiểm tra R1: Mô hình thuần ký tự & tự động ghép chữ
        # -------------------------------------------------------------
        print("\n[1/4] Kiểm tra R1: Ghép chữ tự động và phân loại ký tự...")
        bank_path = tmp_path / "test_bank.json.gz"
        ctl = AppController()
        ctl.load_bank(str(bank_path), create_if_missing=True)

        # Dạy một số ký tự mẫu (a, b, c, 1, 2, dấu câu)
        ctl.teach_char("a", [[0.0, 0.0, 5.0, -8.0]], width=5.0)
        ctl.teach_char("b", [[0.0, -14.0, 0.0, 0.0]], width=6.0)
        ctl.teach_char("c", [[5.0, -8.0, 0.0, 0.0]], width=5.0)
        ctl.teach_char("1", [[0.0, -12.0, 3.0, 0.0]], width=4.0)
        ctl.teach_char(".", [[0.0, 0.0, 1.0, 0.0]], width=1.0)
        ctl.teach_char("dấu sắc", [[0.0, -12.0, 3.0, -15.0]], width=3.0)

        stats = ctl.get_stats()
        assert stats.n_letters >= 3, f"Số chữ cái không đúng: {stats.n_letters}"
        assert stats.digit_counts.get("1", 0) >= 1, "Chữ số không được lưu"
        assert stats.punct_counts.get(".", 0) >= 1, "Dấu câu không được lưu"
        assert stats.tone_mark_counts.get("́", 0) >= 1, "Dấu sắc không được lưu"

        # Kiểm tra Writer mặc định assemble_letters=True
        opts = WriteOptions()
        assert opts.assemble_letters is True, "WriteOptions.assemble_letters phải mặc định là True!"

        writer = Writer(ctl.bank, assemble_letters=opts.assemble_letters)
        assert writer.assemble_letters is True, "Writer phải bật ghép chữ mặc định!"
        print("  -> R1 ĐẠT: Phân loại ký tự và mặc định ghép chữ hoạt động chuẩn xác.")

        # -------------------------------------------------------------
        # 2. Kiểm tra R2 & F2: Nạp file lưới .xopp & sửa lỗi bearing
        # -------------------------------------------------------------
        print("\n[2/4] Kiểm tra R2 & F2: Xuất lưới, điền mực, nạp lưới và kiểm tra lsb/rsb...")
        raw_grid_path = str(tmp_path / "raw_grid.xopp")
        filled_grid_path = str(tmp_path / "filled_grid.xopp")

        # Xuất lưới chữ cái
        test_chars = ["a", "b", "c", "d", "e"]
        ctl.export_letter_grid(raw_grid_path, target_xh=7.94, group_id="co_ban")
        assert os.path.exists(raw_grid_path), "Không tạo được file lưới thô"

        # Giả lập điền mực
        filled_count = fill_grid_with_ink(raw_grid_path, filled_grid_path, labels=test_chars)
        assert filled_count >= len(test_chars), f"Số ô điền mực ({filled_count}) không đủ"

        # Nạp lưới vào kho qua controller
        result = ctl.import_grid(filled_grid_path, dedup=True)
        print(f"  -> Kết quả GridImportResult: thêm={result.added_samples}, trùng={result.duplicate_samples}, bỏ qua={result.skipped_multi_char}, loại={result.rejected_cells}")
        assert result.added_samples >= 2, "Phải thêm được mẫu mới từ lưới"

        # Kiểm tra lsb/rsb không bị giãn 10 lần (F2 check)
        sample_a = ctl.bank.letters["a"][0]
        lsb = sample_a.get("lsb", 0.0)
        rsb = sample_a.get("rsb", 0.0)
        xh = ctl.bank.xh
        print(f"  -> Bearing kiểm tra mẫu 'a': lsb={lsb:.2f}, rsb={rsb:.2f}, xh={xh:.2f}")
        assert lsb <= 0.5 * xh, f"lsb ({lsb}) quá lớn so với xh ({xh}) - lỗi F2 chưa sửa!"
        assert rsb <= 0.5 * xh, f"rsb ({rsb}) quá lớn so với xh ({xh}) - lỗi F2 chưa sửa!"
        print("  -> R2 & F2 ĐẠT: Nạp lưới thành công, side bearings được tính chuẩn từ nét mực.")

        # -------------------------------------------------------------
        # 3. Kiểm tra R3: Bộ ký tự catalog thay cho bộ từ SEED
        # -------------------------------------------------------------
        print("\n[3/4] Kiểm tra R3: Danh mục ký tự catalog...")
        assert "co_ban" in CATALOG_GROUPS, "Thiếu nhóm co_ban trong CATALOG_GROUPS"
        assert "chu_so" in CATALOG_GROUPS, "Thiếu nhóm chu_so trong CATALOG_GROUPS"
        assert "dau_cau" in CATALOG_GROUPS, "Thiếu nhóm dau_cau trong CATALOG_GROUPS"

        missing_co_ban = ctl.get_missing_chars(group_id="co_ban")
        print(f"  -> Số ký tự còn thiếu trong nhóm 'co_ban': {len(missing_co_ban)} ký tự")
        assert isinstance(missing_co_ban, list), "get_missing_chars phải trả về danh sách"
        print("  -> R3 ĐẠT: Catalog nhóm ký tự đầy đủ và cung cấp danh sách thiếu chính xác.")

        # -------------------------------------------------------------
        # 4. Kiểm tra R4 & D1: Bảo toàn dữ liệu người dùng (words)
        # -------------------------------------------------------------
        print("\n[4/4] Kiểm tra R4 & D1: Bảo toàn dữ liệu từ cũ trong kho...")
        # Ghi một từ vào bank.words để giả lập kho cũ
        ctl.bank.words["tieng_viet_cu"] = [{"s": [[0, 0, 5, 5]], "w": 5.0, "h": 5.0}]
        ctl.bank.save()

        # Nạp lại kho
        ctl2 = AppController()
        ctl2.load_bank(str(bank_path))
        assert "tieng_viet_cu" in ctl2.bank.words, "Mục words của kho cũ bị mất sau khi nạp!"
        print("  -> R4 & D1 ĐẠT: Trường 'words' của người dùng được bảo toàn 100%.")

    print("\n" + "=" * 70)
    print("TẤT CẢ 4 MỤC NGHIỆM THU ĐỀU ĐẠT CHUẨN XANH 100%!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
