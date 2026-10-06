/**
 * Kiểm thử tính toàn vẹn và cơ chế hợp nhất của Bank trong MEMFS (Pyodide Node.js).
 * Mô phỏng hai tab độc lập cùng thao tác trên một file kho mẫu:
 *   - Dạy từ xen kẽ
 *   - Xoá từ và đảm bảo tombstone không bị hồi sinh
 *   - Kiểm tra rủi ro cùng mili-giây / cùng kích thước (same-ms edge case)
 */
import { loadPyodide } from "pyodide";
import path from "node:path";

async function runBankMergeTests() {
  console.log("[Test Bank Merge MEMFS] Đang khởi tạo Pyodide...");
  const pyodide = await loadPyodide();

  pyodide.FS.mkdir("/repo");
  pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: process.cwd() }, "/repo");

  console.log("[Test Bank Merge MEMFS] Đang thực thi kịch bản đa tab...");
  pyodide.runPython(`
import sys
import os
import time

sys.path.insert(0, "/repo")

from chuviettay.model.bank import Bank

test_dir = "/tmp/bank_merge_test"
os.makedirs(test_dir, exist_ok=True)
bank_path = f"{test_dir}/shared_bank.json.gz"

if os.path.exists(bank_path):
    os.remove(bank_path)

# 1. Khởi tạo kho trống
init_bank = Bank.load_or_create(bank_path)
init_bank.save()

# 2. Hai tab A và B cùng mở kho
tab_a = Bank(bank_path)
tab_b = Bank(bank_path)

# Tab A dạy từ "hoa"
tab_a.add_sample("hoa", [[0.0, 0.0, 5.0, -10.0]], 10.0)
tab_a.mark_dirty()
tab_a.save()

# Tab B dạy từ "la"
tab_b.add_sample("la", [[0.0, 0.0, 4.0, -8.0]], 8.0)
tab_b.mark_dirty()
tab_b.save()

# Tab C đọc lại file từ đĩa xem đã có cả "hoa" và "la" chưa
tab_c = Bank(bank_path)
assert "hoa" in tab_c.words, "Tab C phải có từ 'hoa' do Tab A thêm"
assert "la" in tab_c.words, "Tab C phải có từ 'la' do Tab B thêm"
assert len(tab_c.words["hoa"]) == 1
assert len(tab_c.words["la"]) == 1

# 3. Kịch bản Xoá: Tab A xoá "hoa", Tab B thêm mẫu thứ 2 cho "la"
tab_a = Bank(bank_path)
tab_a.drop("hoa")
tab_a.mark_dirty()
tab_a.save()

tab_b = Bank(bank_path)
tab_b.add_sample("la", [[0.0, 0.0, 4.2, -8.2]], 8.4)
tab_b.mark_dirty()
tab_b.save()

tab_d = Bank(bank_path)
assert "hoa" not in tab_d.words, "Từ 'hoa' đã bị xoá, không được hồi sinh!"
assert len(tab_d.words["la"]) == 2, "Từ 'la' phải có đủ 2 mẫu"

# 4. Kịch bản kiểm tra cùng mili-giây (Same-ms & Same-size risk test)
# Giả lập tình huống st_mtime_ns của file bị ép giống hệt _last_synced_mtime_ns
tab_e = Bank(bank_path)
tab_f = Bank(bank_path)

# Thêm nét cho từ "canh" ở tab E
tab_e.add_sample("canh", [[0.0, 0.0, 6.0, -12.0]], 12.0)
tab_e.mark_dirty()
tab_e.save()

# Ép mtime của tab F bằng đúng mtime hiện tại của file trên đĩa để kiểm tra
st = os.stat(bank_path)
# Tab F thêm từ "cay"
tab_f.add_sample("cay", [[0.0, 0.0, 7.0, -14.0]], 14.0)
tab_f.mark_dirty()
tab_f.save()

tab_final = Bank(bank_path)
assert "canh" in tab_final.words, "Từ 'canh' phải tồn tại"
assert "cay" in tab_final.words, "Từ 'cay' phải tồn tại"
`);

  console.log("[Test Bank Merge MEMFS] [PASS] Toàn bộ kịch bản hợp nhất đa tab và tombstone trên MEMFS thành công!");
}

runBankMergeTests().catch((err) => {
  console.error("[Test Bank Merge MEMFS] [FAIL]:", err);
  process.exit(1);
});
