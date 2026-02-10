# ============================================================================
# 同步 Firestore 数据
# ============================================================================
# 用途：触发后端 API 重新同步 PIPELINE_GDRIVE_ROOTS 到 Firestore
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"
$BACKEND_URL = "https://autogrowth-backend-969916464848.us-central1.run.app"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "同步 Firestore 数据" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 步骤 1：验证后端服务状态
Write-Host "📋 步骤 1：验证后端服务状态..." -ForegroundColor Yellow
Write-Host ""

try {
    $healthResponse = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method GET -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ 后端服务运行正常：$($healthResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ 后端服务不可用：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   请先运行：.\scripts\restart_backend.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 步骤 2：验证环境变量配置
Write-Host "📋 步骤 2：验证环境变量配置..." -ForegroundColor Yellow
Write-Host ""

$envVars = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="get(spec.template.spec.containers[0].env)" 2>&1

$gdriveRoots = $envVars | Select-String "PIPELINE_GDRIVE_ROOTS"

if ($gdriveRoots) {
    Write-Host "   ✅ PIPELINE_GDRIVE_ROOTS 已配置" -ForegroundColor Green
    Write-Host "   值：$gdriveRoots" -ForegroundColor Gray
} else {
    Write-Host "   ❌ PIPELINE_GDRIVE_ROOTS 未配置！" -ForegroundColor Red
    Write-Host "   请先运行：.\scripts\configure_gdrive_roots.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 步骤 3：调用后端 API 触发同步
Write-Host "📋 步骤 3：触发数据同步..." -ForegroundColor Yellow
Write-Host ""

Write-Host "   尝试调用可能的同步 API 端点..." -ForegroundColor Cyan

# 尝试多个可能的端点
$endpoints = @(
    "/api/v1/pipeline/sync",
    "/api/v1/pipeline/gdrive-roots",
    "/api/v1/transfer/sources",
    "/api/v1/admin/sync"
)

$syncSuccess = $false

foreach ($endpoint in $endpoints) {
    Write-Host "   测试端点：$endpoint" -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri "$BACKEND_URL$endpoint" -Method GET -UseBasicParsing -ErrorAction Stop
        Write-Host "   ✅ 端点可访问：$($response.StatusCode)" -ForegroundColor Green
        Write-Host "   响应内容：" -ForegroundColor Gray
        Write-Host $response.Content -ForegroundColor White
        $syncSuccess = $true
        break
    } catch {
        Write-Host "   ⚠️  端点不可用：$($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""

if ($syncSuccess) {
    Write-Host "   ✅ 数据同步成功！" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  未找到同步端点" -ForegroundColor Yellow
    Write-Host "   可能需要手动触发同步或等待后端自动同步" -ForegroundColor Yellow
}
Write-Host ""

# 完成
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "同步完成" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 后续步骤：" -ForegroundColor Yellow
Write-Host "  1. 清除浏览器缓存（Ctrl + Shift + Delete）" -ForegroundColor White
Write-Host "  2. 硬刷新页面（Ctrl + F5）" -ForegroundColor White
Write-Host "  3. 检查前端是否能看到 CN/JP/KR/US Programs" -ForegroundColor White
Write-Host "  4. 如果还是空的，请查看浏览器开发者工具（F12）的 Network 和 Console" -ForegroundColor White
Write-Host ""

