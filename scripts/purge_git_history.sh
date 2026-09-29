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
    echo "LƯU Ý VỀ MÁY CHỦ TỪ XA (GitHub): Dù lịch sử nhánh sạch hoàn toàn, các commit cũ vẫn có thể tồn tại trong bộ nhớ đệm máy chủ theo mã SHA cho đến khi GitHub chạy GC hoặc theo yêu cầu hỗ trợ."
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

# 4. Kiểm tra git-filter-repo hoặc fallback git filter-branch
USE_FILTER_REPO=false
if command -v git-filter-repo > /dev/null 2>&1 && git filter-repo --version > /dev/null 2>&1; then
    USE_FILTER_REPO=true
elif python3 -m git_filter_repo --version > /dev/null 2>&1; then
    USE_FILTER_REPO=true
fi

# 5. Tạo standalone bundle backup bên ngoài thư mục repo
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_BUNDLE="../repo-backup-before-purge-${TIMESTAMP}.bundle"
echo "Đang tạo git bundle sao lưu an toàn bên ngoài repo: ${BACKUP_BUNDLE}..."
git bundle create "${BACKUP_BUNDLE}" --all
echo "✅ Đã tạo bundle sao lưu thành công tại: ${BACKUP_BUNDLE}"

# 6. Thực thi purge
if [ "$USE_FILTER_REPO" = true ]; then
    echo "Bắt đầu viết lại lịch sử commit bằng git-filter-repo..."
    git filter-repo --invert-paths --path "chu_cua_ban.json.gz" --path "tests/data/kho_mau_chup_lai.json.gz" --force
else
    echo "Không tìm thấy git-filter-repo, chuyển sang fallback: git filter-branch..."
    export FILTER_BRANCH_SQUELCH_WARNING=1
    git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch chu_cua_ban.json.gz tests/data/kho_mau_chup_lai.json.gz' --prune-empty --tag-name-filter cat -- --all
    # Dọn dẹp refs/original/ tạo bởi filter-branch
    git for-each-ref --format="%(refname)" refs/original/ | while read -r ref; do
        git update-ref -d "$ref"
    done
    git reflog expire --expire=now --all
    git gc --prune=now
fi

echo ""
echo "✅ Đã xóa hoàn toàn blob dữ liệu cá nhân khỏi lịch sử Git của nhánh!"
echo "Tệp sao lưu độc lập trước khi xóa: ${BACKUP_BUNDLE}"
echo "Để khôi phục nếu cần: git clone ${BACKUP_BUNDLE} restored-repo"
echo ""
echo "LƯU Ý QUAN TRỌNG VỀ ĐỒNG BỘ VÀ LƯU TRỮ TRÊN GITHUB:"
echo "1. Cập nhật nhánh remote: chạy 'git push --force --mirror origin' để ghi đè mọi nhánh và thẻ."
echo "2. Bộ nhớ đệm máy chủ GitHub (Loose Objects): Mặc dù lịch sử nhánh đã được làm sạch 100%,"
echo "   GitHub vẫn có thể lưu tạm các commit object cũ qua mã SHA trực tiếp trong database máy chủ"
echo "   cho đến khi Garbage Collection định kỳ của GitHub chạy."
echo "3. Nếu cần xoá vĩnh viễn ngay lập tức khỏi bộ nhớ máy chủ GitHub:"
echo "   Liên hệ GitHub Support (https://support.github.com/contact) và yêu cầu chạy GC/purge cache"
echo "   cho repository caoduongle/viet để thu hồi các unreferenced commit objects."
echo "(Khuyến nghị: kiểm tra kỹ git log và remote refs trước khi push mirror để đảm bảo an toàn tuyệt đối)"
