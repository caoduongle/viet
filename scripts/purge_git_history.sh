#!/usr/bin/env bash
# scripts/purge_git_history.sh
# Script hỗ trợ rà soát và xóa vĩnh viễn blob dữ liệu cá nhân khỏi Git history bằng git-filter-repo trên Linux/macOS.
set -euo pipefail

CHECK_ONLY=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --check-only|-CheckOnly)
            CHECK_ONLY=true
            ;;
        --force|-Force)
            FORCE=true
            ;;
    esac
done

echo "=== Kiểm tra điều kiện tiên quyết xóa Git History ==="

# 1. Kiểm tra Git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Lỗi: Thư mục hiện tại không phải là một Git repository!" >&2
    exit 1
fi

# 2. Kiểm tra worktree sạch
STATUS=$(git status --porcelain)
if [ -n "$STATUS" ] && [ "$FORCE" = false ] && [ "$CHECK_ONLY" = false ]; then
    echo "Lỗi: Git working tree đang có file chưa commit. Vui lòng commit hoặc stash trước khi chạy purge!" >&2
    echo "$STATUS" >&2
    exit 1
fi

# 3. Kiểm tra sự tồn tại của file cá nhân trong lịch sử
echo "Đang quét các commit cũ tìm 'chu_cua_ban.json.gz' và 'kho_mau_chup_lai.json.gz'..."
FOUND=$(git log --all --name-only --oneline -- "chu_cua_ban.json.gz" "tests/data/kho_mau_chup_lai.json.gz" || true)
if [ -z "$FOUND" ]; then
    echo "✅ Không tìm thấy blob dữ liệu cá nhân nào trong toàn bộ lịch sử commit!"
    exit 0
else
    echo "⚠️ Phát hiện vết dữ liệu cá nhân trong các commit cũ:"
    echo "$FOUND" | head -n 10
fi

if [ "$CHECK_ONLY" = true ]; then
    echo ""
    echo "[CheckOnly] Dừng lại theo yêu cầu kiểm tra (không thực hiện viết lại commit)."
    exit 0
fi

# 4. Kiểm tra git-filter-repo
if ! command -v git-filter-repo > /dev/null 2>&1; then
    echo "Lỗi: Chưa cài đặt 'git-filter-repo'. Vui lòng cài bằng lệnh: pip install git-filter-repo" >&2
    exit 1
fi

# 5. Tạo branch backup an toàn
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_BRANCH="backup-pre-purge-${TIMESTAMP}"
echo "Đang tạo nhánh sao lưu dự phòng: ${BACKUP_BRANCH}..."
git branch "${BACKUP_BRANCH}"

# 6. Thực thi git filter-repo
echo "Bắt đầu viết lại lịch sử commit để loại bỏ hoàn toàn các file..."
git filter-repo --invert-paths --path "chu_cua_ban.json.gz" --path "tests/data/kho_mau_chup_lai.json.gz" --force

echo ""
echo "✅ Đã xóa hoàn toàn blob dữ liệu cá nhân khỏi lịch sử Git!"
echo "Nhánh sao lưu trước khi xóa: ${BACKUP_BRANCH}"
echo "LƯU Ý: Lịch sử commit đã thay đổi hash. Khi sẵn sàng cập nhật remote repo, chạy:"
echo "git push --force --all origin"
