$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Force Restart Backend Service" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Service Info:" -ForegroundColor Yellow
Write-Host "  Project ID: $PROJECT_ID" -ForegroundColor White
Write-Host "  Region: $REGION" -ForegroundColor White
Write-Host "  Service Name: $BACKEND_SERVICE" -ForegroundColor White
Write-Host ""

Write-Host "Step 1: Get current service status..." -ForegroundColor Yellow
Write-Host ""

$serviceUrl = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="value(status.url)" 2>&1

Write-Host "  Service URL: $serviceUrl" -ForegroundColor Gray
Write-Host ""

Write-Host "Step 2: Force redeploy service..." -ForegroundColor Yellow
Write-Host ""

Write-Host "  Updating service (adding timestamp label to trigger redeploy)..." -ForegroundColor Cyan
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

$updateResult = gcloud run services update $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --update-labels="last-restart=$timestamp" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Service restart successful!" -ForegroundColor Green
} else {
    Write-Host "  Service restart failed!" -ForegroundColor Red
    Write-Host $updateResult -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Step 3: Wait for service to be ready..." -ForegroundColor Yellow
Write-Host ""

Write-Host "  Waiting 10 seconds..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host "Step 4: Verify service status..." -ForegroundColor Yellow
Write-Host ""

$serviceStatus = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="value(status.conditions[0].status)" 2>&1

if ($serviceStatus -eq "True") {
    Write-Host "  Service running normally" -ForegroundColor Green
} else {
    Write-Host "  Service status: $serviceStatus" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "Step 5: Test health check..." -ForegroundColor Yellow
Write-Host ""

try {
    $healthResponse = Invoke-WebRequest -Uri "$serviceUrl/health" -Method GET -UseBasicParsing -ErrorAction Stop
    Write-Host "  Health check passed: $($healthResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Service restart complete!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Clear browser cache (Ctrl + Shift + Delete)" -ForegroundColor White
Write-Host "  2. Hard refresh page (Ctrl + F5)" -ForegroundColor White
Write-Host "  3. Check if frontend shows data" -ForegroundColor White
Write-Host "  4. If still empty, may need to resync Firestore data" -ForegroundColor White
Write-Host ""

