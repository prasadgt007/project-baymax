# share.ps1 - Start ngrok tunnel for Project Baymax
# Reads NGROK_AUTHTOKEN from .env automatically. No manual setup needed.

$EnvFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Error ".env file not found at $EnvFile"
    exit 1
}

# Parse .env and extract NGROK_AUTHTOKEN
$token = $null
foreach ($line in Get-Content $EnvFile) {
    $line = $line.Trim()
    if ($line -match '^\s*NGROK_AUTHTOKEN\s*=\s*"?([^"#\s]+)"?') {
        $token = $matches[1]
        break
    }
}

if (-not $token -or $token -eq "your-ngrok-authtoken-here") {
    Write-Host ""
    Write-Host "  ERROR: NGROK_AUTHTOKEN not set in .env" -ForegroundColor Red
    Write-Host ""
    Write-Host "  1. Get your token at: https://dashboard.ngrok.com/get-started/your-authtoken" -ForegroundColor Yellow
    Write-Host "  2. Open .env and replace the placeholder:" -ForegroundColor Yellow
    Write-Host "       NGROK_AUTHTOKEN=`"paste-your-token-here`"" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "  Project Baymax - Sharing via ngrok" -ForegroundColor Cyan
Write-Host "  Configuring authtoken..." -ForegroundColor Gray

# Register the token (idempotent - safe to run every time)
npx ngrok config add-authtoken $token 2>&1 | Out-Null

Write-Host "  Starting tunnel on port 3000..." -ForegroundColor Gray
Write-Host "  (Vite dev server must already be running: npm run dev)" -ForegroundColor Gray
Write-Host ""

# Start the tunnel - Vite proxy will forward /api/ to FastAPI on port 8000
npx ngrok http 3000
