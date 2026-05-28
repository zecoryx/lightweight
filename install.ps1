# LightWeight One-liner Installer for Windows (PowerShell)
# Usage: irm https://lightweight.zecoryx.uz/install.ps1 | iex

$ErrorActionPreference = 'Stop'

Write-Host "LightWeight Windows uchun o'rnatilmoqda..." -ForegroundColor Cyan

$destDir = "$env:LOCALAPPDATA\LightWeight"
if (!(Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
}

$rawArch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
switch ($rawArch) {
    "AMD64" { $arch = "x86_64" }
    "ARM64" { $arch = "arm64" }
    default { $arch = $rawArch.ToLowerInvariant() }
}

if ($arch -ne "x86_64") {
    throw "LightWeight currently provides a Windows x86_64 binary only. Your system architecture is '$arch'."
}

$binaryUrl = "https://lightweight.zecoryx.uz/dist/lightweight-windows-$arch.exe"
$checksumUrl = "$binaryUrl.sha256"
$destPath = "$destDir\lightweight.exe"
$tmpPath = Join-Path $env:TEMP "lightweight.exe"
$checksumPath = Join-Path $env:TEMP "lightweight.exe.sha256"

Write-Host "Dastur yuklab olinmoqda..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $binaryUrl -OutFile $tmpPath -UseBasicParsing
} catch {
    $status = $null
    if ($_.Exception.Response) {
        $status = [int]$_.Exception.Response.StatusCode
    }
    if ($status -eq 404) {
        throw "Binary topilmadi (404): $binaryUrl. Deploy paytida frontend/public/dist/lightweight-windows-$arch.exe fayli serverga chiqqanini tekshiring."
    }
    throw "LightWeight binary yuklab olinmadi: $($_.Exception.Message)"
}

if (!(Test-Path $tmpPath) -or ((Get-Item $tmpPath).Length -eq 0)) {
    throw "Yuklab olingan fayl bo'sh. O'rnatish to'xtatildi."
}

try {
    Invoke-WebRequest -Uri $checksumUrl -OutFile $checksumPath -UseBasicParsing
    $expected = (Get-Content $checksumPath -Raw).Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)[0].Trim().ToLowerInvariant()
    $actual = (Get-FileHash -Path $tmpPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($expected -ne $actual) {
        throw "Checksum mos kelmadi. O'rnatish to'xtatildi."
    }
} catch {
    if ($_.Exception.Message -like "*Checksum mos kelmadi*") {
        throw
    }
    Write-Host "Ogohlantirish: checksum fayli topilmadi, tekshiruv o'tkazilmadi." -ForegroundColor Yellow
}

Move-Item -Force $tmpPath $destPath

# PATH-ga qo'shish
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$userPath = if ($null -eq $userPath) { "" } else { $userPath }
if ($userPath.Split(";") -notcontains $destDir) {
    Write-Host "Tizim yo'llariga (PATH) qo'shilmoqda..." -ForegroundColor Gray
    $newPath = if ($userPath.Length -gt 0) { "$userPath;$destDir" } else { $destDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

if ($env:Path.Split(";") -notcontains $destDir) {
    $env:Path = "$env:Path;$destDir"
}

Write-Host "LightWeight muvaffaqiyatli o'rnatildi!" -ForegroundColor Green
Write-Host "Tekshirish uchun ishga tushiring: lightweight --help" -ForegroundColor Cyan
Write-Host "Keyin sinab ko'ring: lightweight doctor" -ForegroundColor Cyan
Write-Host "Modeldan oldin reja ko'ring: lightweight check qwen:32b --mode fit" -ForegroundColor Cyan
