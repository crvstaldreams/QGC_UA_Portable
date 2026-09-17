param(
    [Parameter(Mandatory=$true)][string]$QgcRoot,
    [Parameter(Mandatory=$true)][string]$OverlayRoot,
    [string]$ExpectedCommit = "e0816c957602789200ae5ba0af45217f0f2f1db4"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$QgcRoot = (Resolve-Path $QgcRoot).Path
$OverlayRoot = (Resolve-Path $OverlayRoot).Path

Write-Host "=== Verify pinned QGC source ==="
Push-Location $QgcRoot
try {
    $head = (git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "git rev-parse failed" }
    if ($head -ne $ExpectedCommit) {
        throw "Unexpected QGC commit: $head (expected $ExpectedCommit)"
    }
    Write-Host "QGC commit verified: $head"

    Write-Host "=== Apply STREAM-TECHNO custom overlay ==="
    $customDestination = Join-Path $QgcRoot "custom"
    if (Test-Path $customDestination) { Remove-Item $customDestination -Recurse -Force }
    Copy-Item (Join-Path $OverlayRoot "custom") $customDestination -Recurse -Force

    $patches = @(
        (Join-Path $OverlayRoot "patches\0001-mavlink-console-utf8.patch"),
        (Join-Path $OverlayRoot "patches\0002-ukrainian-default.patch"),
        (Join-Path $OverlayRoot "patches\0003-pin-px4-gpsdrivers.patch")
    )
    foreach ($patch in $patches) {
        Write-Host "Checking patch: $(Split-Path $patch -Leaf)"
        & git apply --check --whitespace=error-all $patch
        if ($LASTEXITCODE -ne 0) { throw "git apply --check failed for $patch" }
        & git apply --whitespace=error-all $patch
        if ($LASTEXITCODE -ne 0) { throw "git apply failed for $patch" }
    }

    Write-Host "=== Verify pinned external dependencies ==="
    $dependencyVerifier = Join-Path $OverlayRoot "tools\verify_qgc_dependency_pins.py"
    & python $dependencyVerifier --source-root $QgcRoot
    if ($LASTEXITCODE -ne 0) { throw "verify_qgc_dependency_pins.py failed" }

    Write-Host "=== Apply scoped MAVLink Status UI customization ==="
    $customizer = Join-Path $OverlayRoot "tools\apply_qgc_ui_customizations.py"
    & python $customizer --source-root $QgcRoot
    if ($LASTEXITCODE -ne 0) { throw "apply_qgc_ui_customizations.py failed" }

    Write-Host "=== Verify customization markers ==="
    $allQml = Get-ChildItem -Path $QgcRoot -Filter *.qml -Recurse -File
    $mainWindow = $allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'keepOpen \? Popup.CloseOnEscape' -Quiet } | Select-Object -First 1
    $status = $allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'messageFontPointSize: ScreenTools.defaultFontPointSize \* 1.35' -Quiet } | Select-Object -First 1
    if (-not $mainWindow) { throw "Persistent MAVLink Status close-policy marker not found" }
    if (-not $status) { throw "Scoped MAVLink Status messageFontPointSize marker not found" }

    $overrides = Join-Path $customDestination "cmake\CustomOverrides.cmake"
    if (-not (Select-String -Path $overrides -Pattern 'QGroundControl-UA' -Quiet)) {
        throw "QGroundControl-UA custom application identity missing"
    }

    Write-Host "Prepared QGC source successfully."
    git status --short
}
finally {
    Pop-Location
}
