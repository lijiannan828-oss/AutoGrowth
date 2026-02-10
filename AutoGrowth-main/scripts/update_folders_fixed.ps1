$PROJECT_ID = "fleet-blend-469520-n7"
$REGION = "us-central1"
$BACKEND_SERVICE = "autogrowth-backend"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Update Google Drive Folders (Fixed)" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

$CN_FOLDER_ID = "15dWvRCO6KuDdQEjlbJJW1JKIc-fC8ghA"
$JP_FOLDER_ID = "1FyX0Mea2cCtIxCRfbOkXBt-dKUG9356k"
$KR_FOLDER_ID = "1-80H6V-22Q6FboWSXhqvmYpR3vWMbbl1"
$US_FOLDER_ID = "1Sodv8GBUp-8cZeOjoAxqWwP_GeBcCA1D"

$GDRIVE_ROOTS = "CN Programs:$CN_FOLDER_ID,JP Programs:$JP_FOLDER_ID,KR Programs:$KR_FOLDER_ID,US Programs:$US_FOLDER_ID"

Write-Host "New Configuration:" -ForegroundColor Yellow
Write-Host "  CN Programs: $CN_FOLDER_ID" -ForegroundColor Green
Write-Host "  JP Programs: $JP_FOLDER_ID" -ForegroundColor Green
Write-Host "  KR Programs: $KR_FOLDER_ID" -ForegroundColor Green
Write-Host "  US Programs: $US_FOLDER_ID" -ForegroundColor Green
Write-Host ""
Write-Host "Full Config Value:" -ForegroundColor Yellow
Write-Host "  $GDRIVE_ROOTS" -ForegroundColor Cyan
Write-Host ""

Write-Host "Updating environment variables..." -ForegroundColor Yellow
Write-Host ""

# Method 1: Try with proper escaping
Write-Host "  Attempting update with escaped value..." -ForegroundColor Cyan

$escapedValue = $GDRIVE_ROOTS -replace ' ', '\ '
$updateResult = gcloud run services update $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --update-env-vars="PIPELINE_GDRIVE_ROOTS=$escapedValue" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Update successful!" -ForegroundColor Green
} else {
    Write-Host "  Method 1 failed, trying alternative method..." -ForegroundColor Yellow
    
    # Method 2: Use gcloud command with proper quoting
    $cmd = "gcloud run services update $BACKEND_SERVICE --region=$REGION --project=$PROJECT_ID --update-env-vars=`"PIPELINE_GDRIVE_ROOTS=$GDRIVE_ROOTS`""
    
    Write-Host "  Executing: $cmd" -ForegroundColor Gray
    
    $updateResult = Invoke-Expression $cmd 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Update successful!" -ForegroundColor Green
    } else {
        Write-Host "  Update failed!" -ForegroundColor Red
        Write-Host $updateResult -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

Write-Host "Verifying configuration..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$verifyResult = gcloud run services describe $BACKEND_SERVICE `
    --region=$REGION `
    --project=$PROJECT_ID `
    --format="get(spec.template.spec.containers[0].env)" | Select-String "PIPELINE_GDRIVE_ROOTS"

if ($verifyResult) {
    Write-Host "Configuration verified!" -ForegroundColor Green
    Write-Host "Current config:" -ForegroundColor White
    Write-Host $verifyResult -ForegroundColor Gray
} else {
    Write-Host "Cannot verify configuration" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Configuration update complete!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Wait 2-3 minutes for service to redeploy" -ForegroundColor White
Write-Host "  2. Run: .\scripts\restart_backend.ps1" -ForegroundColor White
Write-Host "  3. Clear browser cache (Ctrl + Shift + Delete)" -ForegroundColor White
Write-Host "  4. Hard refresh page (Ctrl + F5)" -ForegroundColor White
Write-Host "  5. Check if frontend shows data" -ForegroundColor White
Write-Host ""

