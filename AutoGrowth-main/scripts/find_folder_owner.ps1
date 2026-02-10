# ============================================================================
# 识别 Google Drive 文件夹所有者
# ============================================================================
# 用途：生成 Google Drive 链接，帮助识别文件夹所有者
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "识别 Google Drive 文件夹所有者" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 获取当前配置
Write-Host "📋 获取当前配置..." -ForegroundColor Yellow
Write-Host ""

$envVars = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="get(spec.template.spec.containers[0].env)" 2>&1

$gdriveRoots = $envVars | Select-String "PIPELINE_GDRIVE_ROOTS"

if (-not $gdriveRoots) {
    Write-Host "❌ 未找到 PIPELINE_GDRIVE_ROOTS 配置" -ForegroundColor Red
    exit 1
}

Write-Host "当前配置：" -ForegroundColor White
Write-Host "$gdriveRoots" -ForegroundColor Gray
Write-Host ""

# 解析文件夹 ID
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "文件夹信息" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 提取配置值
$configValue = $gdriveRoots -replace ".*'value':\s*'([^']+)'.*", '$1'

# 解析每个文件夹
$folders = $configValue -split ','

foreach ($folder in $folders) {
    if ($folder -match '(.+?):(.+)') {
        $name = $matches[1].Trim()
        $id = $matches[2].Trim()
        
        Write-Host "📁 $name" -ForegroundColor Yellow
        Write-Host "   文件夹 ID: $id" -ForegroundColor White
        
        # 判断文件夹类型
        if ($id -match '^0A') {
            Write-Host "   类型: 共享云端硬盘 (Shared Drive)" -ForegroundColor Cyan
            Write-Host "   访问链接: https://drive.google.com/drive/folders/$id" -ForegroundColor Green
        } elseif ($id -match '^1') {
            Write-Host "   类型: 普通文件夹 (Regular Folder)" -ForegroundColor Cyan
            Write-Host "   访问链接: https://drive.google.com/drive/folders/$id" -ForegroundColor Green
        } else {
            Write-Host "   类型: 未知" -ForegroundColor Yellow
            Write-Host "   访问链接: https://drive.google.com/drive/folders/$id" -ForegroundColor Green
        }
        
        Write-Host ""
    }
}

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "如何查看文件夹所有者" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📝 操作步骤：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 复制上面的访问链接" -ForegroundColor White
Write-Host "2. 在浏览器中打开链接" -ForegroundColor White
Write-Host "3. 如果能访问：" -ForegroundColor White
Write-Host "   - 右键点击文件夹 → '查看详细信息'" -ForegroundColor Gray
Write-Host "   - 或点击文件夹右上角的 'i' 图标" -ForegroundColor Gray
Write-Host "   - 查看'所有者'信息" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 如果无法访问（显示'需要权限'）：" -ForegroundColor White
Write-Host "   - 点击'请求访问权限'" -ForegroundColor Gray
Write-Host "   - 或联系你的团队管理员" -ForegroundColor Gray
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "可能的文件夹所有者" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "根据项目配置，可能的所有者包括：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 项目管理员" -ForegroundColor White
Write-Host "   - 项目 ID: $PROJECT_ID" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 服务账号" -ForegroundColor White

# 获取服务账号信息
$serviceAccount = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="value(spec.template.spec.serviceAccountName)" 2>&1

if ($serviceAccount) {
    Write-Host "   - 服务账号: $serviceAccount" -ForegroundColor Gray
} else {
    Write-Host "   - 使用默认服务账号" -ForegroundColor Gray
}

Write-Host ""
Write-Host "3. 团队成员" -ForegroundColor White
Write-Host "   - 查看 Google Drive 共享设置" -ForegroundColor Gray
Write-Host "   - 查看项目 IAM 成员列表" -ForegroundColor Gray
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "下一步操作建议" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "选项 1：联系文件夹所有者" -ForegroundColor Yellow
Write-Host "   - 请求访问权限" -ForegroundColor White
Write-Host "   - 或请求提供新的文件夹 ID" -ForegroundColor White
Write-Host ""

Write-Host "选项 2：创建你自己的文件夹" -ForegroundColor Yellow
Write-Host "   - 运行: .\scripts\configure_my_folders.ps1" -ForegroundColor White
Write-Host "   - 使用你有权限的文件夹" -ForegroundColor White
Write-Host ""

Write-Host "选项 3：查看项目成员" -ForegroundColor Yellow
Write-Host "   - 运行: gcloud projects get-iam-policy $PROJECT_ID" -ForegroundColor White
Write-Host "   - 联系项目管理员" -ForegroundColor White
Write-Host ""

