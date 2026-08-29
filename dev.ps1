# dev.ps1 - Launch Suitest local dev services on Windows PowerShell
$env:SUITEST_MODE="local"
$env:SUITEST_LOCAL_AUTH_BYPASS="true"
$env:SUITEST_DATABASE_URL="sqlite+aiosqlite:///.suitest/suitest.db"

Write-Host "==========================================" -ForegroundColor Green
Write-Host " Starting Suitest Local Dev Environment   " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Web UI:     http://localhost:3000" -ForegroundColor Cyan
Write-Host "API Server: http://localhost:4000" -ForegroundColor Cyan
Write-Host "API Docs:   http://localhost:4000/docs" -ForegroundColor Cyan
Write-Host "Local auth: bypass enabled (seeded OWNER/ADMIN session)" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Green

# 1. Start Backend API
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:SUITEST_MODE='local'; `$env:SUITEST_LOCAL_AUTH_BYPASS='true'; `$env:SUITEST_DATABASE_URL='sqlite+aiosqlite:///.suitest/suitest.db'; .venv\Scripts\uvicorn.exe --factory suitest_api.main:create_app --host 0.0.0.0 --port 4000 --reload"

# 2. Start Frontend Web UI
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd apps/web; pnpm dev"

# 3. Start Test Runner Worker
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:SUITEST_MODE='local'; `$env:SUITEST_DATABASE_URL='sqlite+aiosqlite:///.suitest/suitest.db'; .venv\Scripts\python.exe -m suitest_runner"
