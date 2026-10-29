# Windows PowerShell setup for the Wells Fargo Statement Converter.
# Run once:   powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Checking Python..." -ForegroundColor Cyan
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Host "Python not found. Install it from https://www.python.org/downloads/ (tick 'Add to PATH'), then re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "==> Creating virtual environment..." -ForegroundColor Cyan
if ($python.Source -like "*py.exe") { py -m venv .venv } else { python -m venv .venv }

Write-Host "==> Installing dependencies..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .\.venv\Scripts\python.exe -m pip install --quiet pdfplumber pandas openpyxl flask reportlab

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "  Web UI (drag & drop):  .\start-web.ps1   then open http://localhost:8080"
Write-Host "  Command line:          .\.venv\Scripts\python.exe converter.py statement.pdf"
