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


    Write-Host "=== Download bundled Play font ==="
    $fontDir = Join-Path $customDestination "resources"
    New-Item -ItemType Directory -Force -Path $fontDir | Out-Null
    $playRegular = Join-Path $fontDir "Play-Regular.ttf"
    $playBold = Join-Path $fontDir "Play-Bold.ttf"
    $playLicense = Join-Path $customDestination "licenses\third-party\Play-OFL.txt"
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/google/fonts/main/ofl/play/Play-Regular.ttf" -OutFile $playRegular
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/google/fonts/main/ofl/play/Play-Bold.ttf" -OutFile $playBold
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/google/fonts/main/ofl/play/OFL.txt" -OutFile $playLicense
    foreach ($fontFile in @($playRegular, $playBold)) {
        if (-not (Test-Path $fontFile -PathType Leaf)) { throw "Play font missing: $fontFile" }
        if ((Get-Item $fontFile).Length -lt 10000) { throw "Play font download looks invalid: $fontFile" }
    }

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

    Write-Host "=== Generate complete Ukrainian translations ==="
    $translationGenerator = Join-Path $OverlayRoot "tools\generate_ukrainian_translations.py"
    $translationCache = Join-Path $OverlayRoot "translation-cache\en_uk.json"
    $translationOverrides = Join-Path $OverlayRoot "translations\uk_manual_overrides.json"
    & python $translationGenerator --source-root $QgcRoot --cache $translationCache --overrides $translationOverrides
    if ($LASTEXITCODE -ne 0) { throw "generate_ukrainian_translations.py failed" }

    Write-Host "=== Apply scoped MAVLink Status UI customization ==="
    $customizer = Join-Path $OverlayRoot "tools\apply_qgc_ui_customizations.py"
    & python $customizer --source-root $QgcRoot
    if ($LASTEXITCODE -ne 0) { throw "apply_qgc_ui_customizations.py failed" }


    Write-Host "=== Apply Ukrainian UI, UTF-8, Play font and splash features ==="
    $uaFeaturePatcher = Join-Path $OverlayRoot "tools\apply_qgc_ua_features.py"
    & python $uaFeaturePatcher --source-root $QgcRoot
    if ($LASTEXITCODE -ne 0) { throw "apply_qgc_ua_features.py failed" }

    Write-Host "=== Apply portable QGC data layout ==="
    $portableCustomizer = Join-Path $OverlayRoot "tools\apply_qgc_portable_mode.py"
    & python $portableCustomizer --source-root $QgcRoot
    if ($LASTEXITCODE -ne 0) { throw "apply_qgc_portable_mode.py failed" }

    Write-Host "=== Verify portable mode markers ==="
    $qgcApplication = Join-Path $QgcRoot "src\QGCApplication.cc"
    $appSettings = Join-Path $QgcRoot "src\Settings\AppSettings.cc"
    $installerScript = Join-Path $QgcRoot "deploy\windows\nullsoft_installer.nsi"
    if (-not (Select-String -Path $qgcApplication -Pattern 'QGCPortablePaths::initialize\(\)' -Quiet)) {
        throw "Portable QSettings/cache initialization marker not found"
    }
    if (-not (Select-String -Path $qgcApplication -Pattern '#include "PortablePaths\.h"' -Quiet)) {
        throw "PortablePaths.h include missing from QGCApplication.cc"
    }
    $portableHeader = Join-Path $QgcRoot "src\PortablePaths.h"
    if (-not (Test-Path $portableHeader -PathType Leaf)) {
        throw "PortablePaths.h was not copied next to QGCApplication.cc"
    }
    if (-not (Select-String -Path $appSettings -Pattern 'QGC PORTABLE: force all user files beside the executable' -Quiet)) {
        throw "Portable AppSettings save path marker not found"
    }
    if (-not (Select-String -Path $installerScript -Pattern '\$LOCALAPPDATA\\Programs\\\$\{APPNAME\}' -Quiet)) {
        throw "Portable per-user installer path marker not found"
    }

    Write-Host "=== Verify customization markers ==="
    $allQml = Get-ChildItem -Path $QgcRoot -Filter *.qml -Recurse -File
    $mainWindow = $allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'keepOpen \? Popup.CloseOnEscape' -Quiet } | Select-Object -First 1
    $status = $allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'messageFontPointSize:\s*ScreenTools.defaultFontPointSize\s*\*\s*1\.60' -Quiet } | Select-Object -First 1
    if (-not $mainWindow) { throw "Persistent MAVLink Status close-policy marker not found" }
    if (-not $status) { throw "Scoped MAVLink Status messageFontPointSize marker not found" }

    $statusHandler = Join-Path $QgcRoot "src\MAVLink\StatusTextHandler.cc"
    $screenToolsController = Join-Path $QgcRoot "src\QmlControls\ScreenToolsController.cc"
    $mainSource = Join-Path $QgcRoot "src\main.cc"
    $ukSource = Join-Path $QgcRoot "translations\qgc_source_uk_UA.ts"
    $ukJson = Join-Path $QgcRoot "translations\qgc_json_uk_UA.ts"

    if (-not (Select-String -Path $statusHandler -Pattern 'QStringDecoder utf8Decoder' -Quiet)) {
        throw "MAVLink STATUSTEXT UTF-8 marker not found"
    }
    if (-not (Select-String -Path $screenToolsController -Pattern 'QStringLiteral\("Play"\)' -Quiet)) {
        throw "Global Play font marker not found"
    }
    if (-not (Select-String -Path $mainSource -Pattern 'QGroundControl Portable' -Quiet)) {
        throw "Portable splash screen marker not found"
    }
    if (-not ($allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'autoCloseSeconds:\s*60' -Quiet } | Select-Object -First 1)) {
        throw "MAVLink Status 60-second auto-close marker not found"
    }
    if (-not ($allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'interval:\s*5000' -Quiet } | Select-Object -First 1)) {
        throw "MAVLink Status 5-second refresh marker not found"
    }
    if (-not ($allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'width:\s*mainWindow\.contentItem\.width\s*\*\s*0\.65' -Quiet } | Select-Object -First 1)) {
        throw "MAVLink Status 65-percent width marker not found"
    }
    if (-not ($allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'text:\s*"Закрити"' -Quiet } | Select-Object -First 1)) {
        throw "MAVLink Status close button marker not found"
    }
    $contrastTextField = Join-Path $QgcRoot "src\QmlControls\QGCTextField.qml"
    if (-not (Select-String -Path $contrastTextField -Pattern 'control\.activeFocus \? 3 : 2' -Quiet)) {
        throw "High contrast search/text field marker not found"
    }
    if (-not ($allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'QGC UA contrast progress style' -Quiet } | Select-Object -First 1)) {
        throw "High contrast progress bar marker not found"
    }
    if (-not ($allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'centerOnWindow' -Quiet } | Select-Object -First 1)) {
        throw "Centered tool menu marker not found"
    }
    foreach ($translationFile in @($ukSource, $ukJson)) {
        if (Select-String -Path $translationFile -Pattern 'type="unfinished"' -Quiet) {
            throw "Unfinished Ukrainian translations remain in $translationFile"
        }
    }
    $serviceModeQml = Join-Path $QgcRoot "custom\qml\ServiceMode.qml"
    $serviceParamsQml = Join-Path $QgcRoot "custom\qml\ServiceParameterEditor.qml"
    $serviceServoQml = Join-Path $QgcRoot "custom\qml\ServiceServoSafety.qml"
    $serviceMavlinkQml = Join-Path $QgcRoot "custom\qml\ServiceMavlinkStatus.qml"
    if (-not (Select-String -Path $mainWindow.FullName -Pattern 'Спрощ\. режим для сервісу' -Quiet)) {
        throw "Service mode menu button marker not found"
    }
    if (-not (Test-Path $serviceModeQml -PathType Leaf)) {
        throw "ServiceMode.qml missing from custom overlay"
    }
    foreach ($serviceMarker in @(
        'text:\s*"Огляд"',
        'text:\s*"Прошивка"',
        'text:\s*"Параметри"',
        'text:\s*"Датчики"',
        'text:\s*"Servo/Saf.Mask"',
        'text:\s*"MAVLink Status"',
        'text:\s*"Реконнект"',
        'activeVehicle\.rebootVehicle\(\)',
        'QGCAttitudeWidget',
        'FlightMap',
        'activeVehicle\.gps\.count\.valueString',
        'activeVehicle\.gps\.lock\.enumStringValue',
        'QGCCompassWidget'
    )) {
        if (-not (Select-String -Path $serviceModeQml -Pattern $serviceMarker -Quiet)) {
            throw "Service mode marker not found: $serviceMarker"
        }
    }
    if (-not (Test-Path $serviceParamsQml -PathType Leaf)) {
        throw "ServiceParameterEditor.qml missing from custom overlay"
    }
    foreach ($paramMarker in @('serviceTreeModel', 'controller\.parameters', 'BRD_', 'SERVO')) {
        if (-not (Select-String -Path $serviceParamsQml -Pattern $paramMarker -Quiet)) {
            throw "Service parameter editor marker not found: $paramMarker"
        }
    }

    if (-not (Test-Path $serviceMavlinkQml -PathType Leaf)) {
        throw "ServiceMavlinkStatus.qml missing from custom overlay"
    }
    foreach ($mavMarker in @('interval:\s*5000', 'messageFontPointSize:.*1\.60', 'refreshMessages\(\)')) {
        if (-not (Select-String -Path $serviceMavlinkQml -Pattern $mavMarker -Quiet)) {
            throw "Service MAVLink Status marker not found: $mavMarker"
        }
    }

    if (-not (Test-Path $serviceServoQml -PathType Leaf)) {
        throw "ServiceServoSafety.qml missing from custom overlay"
    }
    foreach ($servoMarker in @('SERVO', 'BRD_SAFETY_MASK', 'motorTest\(')) {
        if (-not (Select-String -Path $serviceServoQml -Pattern $servoMarker -Quiet)) {
            throw "Servo/Safety service marker not found: $servoMarker"
        }
    }

    if (-not (Test-Path $playRegular -PathType Leaf) -or -not (Test-Path $playBold -PathType Leaf)) {
        throw "Bundled Play fonts are missing"
    }

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
