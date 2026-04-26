param(
    [switch]$SkipInstall,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not $SkipInstall) {
    python -m pip install -r "requirements.txt"
    python -m pip install -r "requirements-build.txt"
}

$ExePath = Join-Path $Root "dist/Nuclei_GUI.exe"

if (-not $SkipBuild) {
    python -m PyInstaller --noconfirm --clean "Nuclei_GUI.spec"
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Build output not found: $ExePath"
}

$PackageDir = Join-Path $Root "dist/Nuclei_GUI_portable"
if (Test-Path -LiteralPath $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PackageDir "bin") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PackageDir "poc_library/custom") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PackageDir "poc_library/cloud") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PackageDir "poc_library/user_generated") | Out-Null

Copy-Item -LiteralPath $ExePath -Destination (Join-Path $PackageDir "Nuclei_GUI.exe") -Force

$NucleiBinary = Join-Path $Root "bin/nuclei.exe"
if (Test-Path -LiteralPath $NucleiBinary) {
    Copy-Item -LiteralPath $NucleiBinary -Destination (Join-Path $PackageDir "bin/nuclei.exe") -Force
}

$PocSource = Join-Path $Root "poc_library"
if (Test-Path -LiteralPath $PocSource) {
    Copy-Item -Path (Join-Path $PocSource "*") -Destination (Join-Path $PackageDir "poc_library") -Recurse -Force
}

Write-Host ""
Write-Host "Package ready:"
Write-Host "  $PackageDir"
Write-Host ""
Write-Host "External runtime layout:"
Write-Host "  Nuclei_GUI.exe"
Write-Host "  bin/nuclei.exe"
Write-Host "  poc_library/"
