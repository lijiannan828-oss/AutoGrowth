# ============================================================================
# 诊断前端显示为空的问题
# ============================================================================
# 用途：全面诊断为什么前端显示为空
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"
$BACKEND_URL = "https://autogrowth-backend-969916464848-us-central1.run.app"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "诊断前端显示为空的问题" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 步骤 1：验证后端环境变量配置
# ============================================================================
Write-Host "📋 步骤 1：验证后端环境变量配置..." -ForegroundColor Yellow
Write-Host ""

$envVars = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="get(spec.template.spec.containers[0].env)" 2>&1

$gdriveRoots = $envVars | Select-String "PIPELINE_GDRIVE_ROOTS"

if ($gdriveRoots) {
    Write-Host "✅ PIPELINE_GDRIVE_ROOTS 已配置" -ForegroundColor Green
    Write-Host "   值：$gdriveRoots" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "❌ PIPELINE_GDRIVE_ROOTS 未配置！" -ForegroundColor Red
    Write-Host "   请运行：.\scripts\configure_gdrive_roots.ps1" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# 步骤 2：检查后端服务状态
# ============================================================================
Write-Host "📋 步骤 2：检查后端服务状态..." -ForegroundColor Yellow
Write-Host ""

$serviceStatus = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="value(status.conditions[0].status)" 2>&1

if ($serviceStatus -eq "True") {
    Write-Host "✅ 后端服务运行正常" -ForegroundColor Green
} else {
    Write-Host "❌ 后端服务状态异常：$serviceStatus" -ForegroundColor Red
}
Write-Host ""

# ============================================================================
# 步骤 3：测试后端 API 端点
# ============================================================================
Write-Host "📋 步骤 3：测试后端 API 端点..." -ForegroundColor Yellow
Write-Host ""

Write-Host "   测试健康检查端点..." -ForegroundColor Cyan
try {
    $healthResponse = Invoke-WebRequest -Uri "$BACKEND_URL/health" -Method GET -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ 健康检查通过：$($healthResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ 健康检查失败：$($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "   测试 API 根路径..." -ForegroundColor Cyan
try {
    $apiResponse = Invoke-WebRequest -Uri "$BACKEND_URL/api/v1" -Method GET -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ API 根路径可访问：$($apiResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  API 根路径：$($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ""

# ============================================================================
# 步骤 4：检查后端日志
# ============================================================================
Write-Host "📋 步骤 4：检查后端日志（最近 20 条）..." -ForegroundColor Yellow
Write-Host ""

$logs = gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$BACKEND_SERVICE AND severity>=WARNING" `
    --limit=20 `
    --project=$PROJECT_ID `
    --format="table(timestamp,severity,textPayload)" 2>&1

if ($logs) {
    Write-Host $logs -ForegroundColor Gray
} else {
    Write-Host "   ✅ 没有警告或错误日志" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# 步骤 5：检查前端配置
# ============================================================================
Write-Host "📋 步骤 5：检查前端配置..." -ForegroundColor Yellow
Write-Host ""

Write-Host "   前端应该调用的 API 端点：" -ForegroundColor Cyan
Write-Host "   - $BACKEND_URL/api/v1/pipeline/gdrive-roots" -ForegroundColor White
Write-Host "   - $BACKEND_URL/api/v1/pipeline/folders" -ForegroundColor White
Write-Host ""

# ============================================================================
# 步骤 6：提供解决方案
# ============================================================================
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "诊断结果与解决方案" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🔍 可能的原因：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 浏览器缓存问题（最常见）" -ForegroundColor White
Write-Host "   解决方案：" -ForegroundColor Cyan
Write-Host "   - 按 Ctrl + Shift + Delete 清除缓存" -ForegroundColor Gray
Write-Host "   - 按 Ctrl + F5 硬刷新页面" -ForegroundColor Gray
Write-Host "   - 使用无痕模式测试（Ctrl + Shift + N）" -ForegroundColor Gray
Write-Host ""

Write-Host "2. 前端 API 调用错误" -ForegroundColor White
Write-Host "   解决方案：" -ForegroundColor Cyan
Write-Host "   - 打开浏览器开发者工具（F12）" -ForegroundColor Gray
Write-Host "   - 查看 Network 标签页" -ForegroundColor Gray
Write-Host "   - 刷新页面，查看 API 请求是否成功" -ForegroundColor Gray
Write-Host "   - 检查是否有 401/403/500 错误" -ForegroundColor Gray
Write-Host ""

Write-Host "3. 前端代码未正确解析数据" -ForegroundColor White
Write-Host "   解决方案：" -ForegroundColor Cyan
Write-Host "   - 打开浏览器开发者工具（F12）" -ForegroundColor Gray
Write-Host "   - 查看 Console 标签页" -ForegroundColor Gray
Write-Host "   - 查看是否有 JavaScript 错误" -ForegroundColor Gray
Write-Host ""

Write-Host "4. 需要重新登录" -ForegroundColor White
Write-Host "   解决方案：" -ForegroundColor Cyan
Write-Host "   - 退出登录" -ForegroundColor Gray
Write-Host "   - 清除浏览器缓存" -ForegroundColor Gray
Write-Host "   - 重新登录" -ForegroundColor Gray
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "📝 下一步操作建议" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 清除浏览器缓存并硬刷新（Ctrl + Shift + Delete，然后 Ctrl + F5）" -ForegroundColor White
Write-Host "2. 打开浏览器开发者工具（F12），查看 Network 和 Console" -ForegroundColor White
Write-Host "3. 刷新页面，观察 API 请求" -ForegroundColor White
Write-Host "4. 截图发给我，我会帮你分析" -ForegroundColor White
Write-Host ""

