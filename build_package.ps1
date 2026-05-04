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

function Sync-RuntimeLayout {
    param(
        [string]$TargetDir
    )

    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TargetDir "bin") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TargetDir "poc_library/custom") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TargetDir "poc_library/cloud") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TargetDir "poc_library/user_generated") | Out-Null

    $NucleiBinary = Join-Path $Root "bin/nuclei.exe"
    if (Test-Path -LiteralPath $NucleiBinary) {
        Copy-Item -LiteralPath $NucleiBinary -Destination (Join-Path $TargetDir "bin/nuclei.exe") -Force
    }

    $PocSource = Join-Path $Root "poc_library"
    if (Test-Path -LiteralPath $PocSource) {
        Get-ChildItem -LiteralPath $PocSource -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $TargetDir "poc_library") -Recurse -Force
        }
    }
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

Copy-Item -LiteralPath $ExePath -Destination (Join-Path $PackageDir "Nuclei_GUI.exe") -Force

Sync-RuntimeLayout -TargetDir (Join-Path $Root "dist")
Sync-RuntimeLayout -TargetDir $PackageDir

Write-Host ""
Write-Host "Package ready:"
Write-Host "  $PackageDir"
Write-Host ""
Write-Host "External runtime layout:"
Write-Host "  Nuclei_GUI.exe"
Write-Host "  bin/nuclei.exe"
Write-Host "  poc_library/"
