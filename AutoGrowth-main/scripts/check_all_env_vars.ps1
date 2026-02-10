# ============================================================================
# 检查所有环境变量
# ============================================================================
# 用途：检查 autogrowth-backend 的所有环境变量配置
# 作者：AutoGrowth Team
# 日期：2026-01-29
# ============================================================================

$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "检查所有环境变量" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 获取当前环境变量配置..." -ForegroundColor Yellow
Write-Host ""

# 获取所有环境变量
$envOutput = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="get(spec.template.spec.containers[0].env)" 2>&1

Write-Host "当前环境变量列表：" -ForegroundColor White
Write-Host "============================================================================" -ForegroundColor Gray

# 解析并显示每个环境变量
$envOutput -split ';' | ForEach-Object {
    if ($_ -match "{'name':\s*'([^']+)',\s*'value':\s*'([^']+)'}") {
        $name = $matches[1]
        $value = $matches[2]
        
        # 高亮显示重要的环境变量
        if ($name -eq "PIPELINE_GDRIVE_ROOTS") {
            Write-Host "✅ $name = $value" -ForegroundColor Green
        } elseif ($name -match "DATABASE|FIRESTORE|GCP|FIREBASE") {
            Write-Host "   $name = $value" -ForegroundColor Cyan
        } else {
            Write-Host "   $name = $value" -ForegroundColor Gray
        }
    } elseif ($_ -match "{'name':\s*'([^']+)',\s*'valueFrom'") {
        $name = $matches[1]
        Write-Host "   $name = [从 Secret 读取]" -ForegroundColor Yellow
    }
}

Write-Host "============================================================================" -ForegroundColor Gray
Write-Host ""

# 检查关键环境变量
Write-Host "📋 检查关键环境变量..." -ForegroundColor Yellow
Write-Host ""

$criticalVars = @(
    "PIPELINE_GDRIVE_ROOTS",
    "FIRESTORE_PROJECT_ID",
    "FIRESTORE_NAMESPACE",
    "GCP_PROJECT_ID",
    "DATABASE_NAME",
    "DATABASE_USER",
    "FRONTEND_ORIGINS"
)

$missingVars = @()

foreach ($varName in $criticalVars) {
    if ($envOutput -match $varName) {
        Write-Host "   ✅ $varName 已配置" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $varName 缺失！" -ForegroundColor Red
        $missingVars += $varName
    }
}

Write-Host ""

if ($missingVars.Count -gt 0) {
    Write-Host "⚠️  发现缺失的环境变量：" -ForegroundColor Red
    $missingVars | ForEach-Object {
        Write-Host "   - $_" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "💡 解决方案：运行完整配置脚本" -ForegroundColor Yellow
    Write-Host "   .\scripts\restore_all_env_vars.ps1" -ForegroundColor White
} else {
    Write-Host "✅ 所有关键环境变量都已配置" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "检查完成" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

