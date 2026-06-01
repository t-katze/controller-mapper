param(
    [switch]$InstallDeps,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }
$Spec = Join-Path $Root "packaging\controller-mapper.spec"

Push-Location $Root
try {
    if ($InstallDeps) {
        & $Python -m pip install -e ".[build]"
        if ($LASTEXITCODE -ne 0) {
            throw "Build dependencies installation failed."
        }
    }

    & $Python -m PyInstaller --version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller が見つかりません。依存を入れるには -InstallDeps を付けて実行してください。"
    }

    $PyInstallerArgs = @("--noconfirm")
    if ($Clean) {
        $PyInstallerArgs += "--clean"
    }
    $PyInstallerArgs += $Spec

    & $Python -m PyInstaller @PyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    Write-Host "Built: dist\controller-mapper\controller-mapper.exe"
}
finally {
    Pop-Location
}
