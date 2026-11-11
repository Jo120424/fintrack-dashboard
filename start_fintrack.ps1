# FINTRACK – Local Development Launcher (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Test-Path "C:\Program Files\nodejs") {
    $env:PATH = "C:\Program Files\nodejs;$env:PATH"
}

$PythonExe = Join-Path $Root "backend\.venv\Scripts\python.exe"
$BackendApp = Join-Path $Root "backend\app.py"
$FrontendDir = Join-Path $Root "frontend"

Write-Host "Starting FINTRACK Backend API on http://127.0.0.1:5000 ..." -ForegroundColor Cyan
$backend = Start-Process -FilePath $PythonExe -ArgumentList $BackendApp -WorkingDirectory $Root -PassThru

Write-Host "Starting FINTRACK Vite Frontend on http://localhost:5173 ..." -ForegroundColor Cyan
$frontend = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm.cmd run dev" -WorkingDirectory $FrontendDir -PassThru

Write-Host "Both servers launched. Press Ctrl+C or close windows to stop." -ForegroundColor Green
Write-Host "Open http://localhost:5173 in your browser." -ForegroundColor Yellow

try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    if (!$backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if (!$frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
}
