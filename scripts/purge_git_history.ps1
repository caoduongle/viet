# scripts/purge_git_history.ps1
# Script hỗ trợ rà soát và xóa vĩnh viễn blob dữ liệu cá nhân khỏi Git history bằng git-filter-repo.
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "=== Kiểm tra điều kiện tiên quyết xóa Git History ===" -ForegroundColor Cyan

# 1. Kiểm tra Git repository
try {
    $null = git rev-parse --git-dir
} catch {
    Write-Error "Thư mục hiện tại không phải là một Git repository!"
    exit 1
}

# 2. Kiểm tra worktree sạch
$status = git status --porcelain
if ($status -and -not $Force -and -not $CheckOnly) {
    Write-Error "Git working tree đang có file chưa commit. Vui lòng commit hoặc stash trước khi chạy purge!`n$status"
    exit 1
}

# 3. Kiểm tra sự tồn tại của file cá nhân trong lịch sử
Write-Host "Đang quét các commit cũ tìm 'chu_cua_ban.json.gz' và 'kho_mau_chup_lai.json.gz'..."
$found = git log --all --name-only --oneline -- "chu_cua_ban.json.gz" "tests/data/kho_mau_chup_lai.json.gz"
if (-not $found) {
    Write-Host "✅ Không tìm thấy blob dữ liệu cá nhân nào trong toàn bộ lịch sử commit!" -ForegroundColor Green
    Write-Host "LƯU Ý VỀ MÁY CHỦ TỪ XA (GitHub): Dù lịch sử nhánh sạch hoàn toàn, các commit cũ vẫn có thể tồn tại trong bộ nhớ đệm máy chủ theo mã SHA cho đến khi GitHub chạy GC hoặc theo yêu cầu hỗ trợ." -ForegroundColor Gray
    exit 0
} else {
    Write-Host "⚠️ Phát hiện vết dữ liệu cá nhân trong các commit cũ:" -ForegroundColor Yellow
    $found | Select-Object -First 10 | ForEach-Object { Write-Host "   $_" }
}

if ($CheckOnly) {
    Write-Host "`n[CheckOnly] Dừng lại theo yêu cầu kiểm tra (không thực hiện viết lại commit)." -ForegroundColor Yellow
    exit 0
}

# 4. Kiểm tra git-filter-repo hoặc fallback git filter-branch
$useFilterRepo = $false
try {
    $repoVersion = & git filter-repo --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $repoVersion) {
        $useFilterRepo = $true
    }
} catch {}

if (-not $useFilterRepo) {
    try {
        $repoVersion = & py -3 -m git_filter_repo --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $repoVersion) {
            $useFilterRepo = $true
        }
    } catch {}
}

if (-not $useFilterRepo) {
    try {
        $repoVersion = & python -m git_filter_repo --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $repoVersion) {
            $useFilterRepo = $true
        }
    } catch {}
}

# 5. Tạo standalone bundle backup bên ngoài thư mục repo
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupBundle = "../repo-backup-before-purge-$timestamp.bundle"
Write-Host "Đang tạo git bundle sao lưu an toàn bên ngoài repo: $backupBundle..." -ForegroundColor Cyan
git bundle create $backupBundle --all
if ($LASTEXITCODE -ne 0) {
    Write-Error "Tạo git bundle sao lưu thất bại! Huỷ thao tác để bảo vệ lịch sử."
    exit 1
}
Write-Host "✅ Đã tạo bundle sao lưu thành công tại: $backupBundle" -ForegroundColor Green

# 6. Thực thi purge
if ($useFilterRepo) {
    Write-Host "Bắt đầu viết lại lịch sử commit bằng git-filter-repo..." -ForegroundColor Cyan
    git filter-repo --invert-paths --path "chu_cua_ban.json.gz" --path "tests/data/kho_mau_chup_lai.json.gz" --force
} else {
    Write-Host "Không tìm thấy git-filter-repo, chuyển sang fallback: git filter-branch..." -ForegroundColor Yellow
    $env:FILTER_BRANCH_SQUELCH_WARNING = "1"
    git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch chu_cua_ban.json.gz tests/data/kho_mau_chup_lai.json.gz' --prune-empty --tag-name-filter cat -- --all
    # Dọn dẹp refs/original/ tạo bởi filter-branch
    $origRefs = git for-each-ref --format="%(refname)" refs/original/
    if ($origRefs) {
        $origRefs | ForEach-Object { git update-ref -d $_ }
    }
    git reflog expire --expire=now --all
    git gc --prune=now
}

Write-Host "`n✅ Đã xóa hoàn toàn blob dữ liệu cá nhân khỏi lịch sử Git của nhánh!" -ForegroundColor Green
Write-Host "Tệp sao lưu độc lập trước khi xóa: $backupBundle" -ForegroundColor Gray
Write-Host "Để khôi phục nếu cần: git clone $backupBundle restored-repo" -ForegroundColor Gray
Write-Host "`nLƯU Ý QUAN TRỌNG VỀ ĐỒNG BỘ VÀ LƯU TRỮ TRÊN GITHUB:" -ForegroundColor Yellow
Write-Host "1. Cập nhật nhánh remote: chạy 'git push --force --mirror origin' để ghi đè mọi nhánh và thẻ." -ForegroundColor Yellow
Write-Host "2. Bộ nhớ đệm máy chủ GitHub (Loose Objects): Mặc dù lịch sử nhánh đã được làm sạch 100%," -ForegroundColor Gray
Write-Host "   GitHub vẫn có thể lưu tạm các commit object cũ qua mã SHA trực tiếp trong database máy chủ" -ForegroundColor Gray
Write-Host "   cho đến khi Garbage Collection định kỳ của GitHub chạy." -ForegroundColor Gray
Write-Host "3. Nếu cần xoá vĩnh viễn ngay lập tức khỏi bộ nhớ máy chủ GitHub:" -ForegroundColor Gray
Write-Host "   Liên hệ GitHub Support (https://support.github.com/contact) và yêu cầu chạy GC/purge cache" -ForegroundColor Gray
Write-Host "   cho repository caoduongle/viet để thu hồi các unreferenced commit objects." -ForegroundColor Gray
Write-Host "(Khuyến nghị: kiểm tra kỹ git log và remote refs trước khi push mirror để đảm bảo an toàn tuyệt đối)" -ForegroundColor Gray
