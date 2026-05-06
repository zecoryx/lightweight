# LightWeight Installer (Windows)
$ErrorActionPreference = 'Stop'
Write-Host "LightWeight is installing for Windows..." -ForegroundColor Cyan

$destDir = "$env:LOCALAPPDATA\LightWeight"
if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }

# Hosted binary path
$binaryUrl = "https://lightweight.zecoryx.uz/dist/lightweight-windows-x86_64.exe"
$destPath = "$destDir\lightweight.exe"

Write-Host "Downloading LightWeight..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $binaryUrl -OutFile $destPath

# Add to PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$destDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$destDir", "User")
    Write-Host "Added to PATH" -ForegroundColor Gray
}

if ($env:Path -notlike "*$destDir*") {
    $env:Path = "$env:Path;$destDir"
}

Write-Host "Done! Verify the install with: lightweight --help" -ForegroundColor Green
Write-Host "Then try: lightweight pull qwen:32b" -ForegroundColor Cyan
