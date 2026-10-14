# BookMyCare one-time setup for Windows PowerShell.
# Run from the project root:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "== Backend ==" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) {
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    $secret = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
    (Get-Content .env) -replace "^JWT_SECRET=.*", "JWT_SECRET=$secret" | Set-Content .env
    Write-Host "Created backend\.env (add AI keys there if you have them)."
}
& .\.venv\Scripts\python.exe -m alembic upgrade head
& .\.venv\Scripts\python.exe -m scripts.seed_demo

Write-Host "== Frontend ==" -ForegroundColor Cyan
Set-Location "$root\frontend"
npm ci
Write-Host "Setup complete. Start with scripts\run-backend.ps1 and scripts\run-frontend.ps1" -ForegroundColor Green
