# LightWeight One-liner Installer for Windows (PowerShell)
# Usage: irm https://lightweight.zecoryx.uz/install.ps1 | iex

$ErrorActionPreference = 'Stop'

Write-Host "LightWeight Windows uchun o'rnatilmoqda..." -ForegroundColor Cyan

$destDir = "$env:LOCALAPPDATA\LightWeight"
if (!(Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
}

$binaryUrl = "https://lightweight.zecoryx.uz/dist/lightweight-windows-x86_64.exe"
$destPath = "$destDir\lightweight.exe"

Write-Host "Dastur yuklab olinmoqda..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $binaryUrl -OutFile $destPath

# PATH-ga qo'shish
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$destDir*") {
    Write-Host "Tizim yo'llariga (PATH) qo'shilmoqda..." -ForegroundColor Gray
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$destDir", "User")
}

if ($env:Path -notlike "*$destDir*") {
    $env:Path = "$env:Path;$destDir"
}

Write-Host "LightWeight muvaffaqiyatli o'rnatildi!" -ForegroundColor Green
Write-Host "Tekshirish uchun ishga tushiring: lightweight --help" -ForegroundColor Cyan
Write-Host "Keyin sinab ko'ring: lightweight pull qwen:32b" -ForegroundColor Cyan
