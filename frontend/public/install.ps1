# LightWeight Installer (Windows)
$ErrorActionPreference = 'Stop'
Write-Host "🚀 LightWeight is installing for Windows..." -ForegroundColor Cyan

$destDir = "$env:LOCALAPPDATA\LightWeight"
if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }

# GitHub Release manzili (lightweight-windows.exe)
$binaryUrl = "https://github.com/zecoryx/lightweight/releases/latest/download/lightweight-windows.exe"
$destPath = "$destDir\lightweight.exe"

Write-Host "📥 Downloading from GitHub..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $binaryUrl -OutFile $destPath

# PATH-ga qo'shish
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$destDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$destDir", "User")
    Write-Host "⚙️ Added to PATH" -ForegroundColor Gray
}

Write-Host "✅ Done! Restart your terminal and type 'lightweight chat'." -ForegroundColor Green
