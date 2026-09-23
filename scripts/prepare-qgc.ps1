param(
    [Parameter(Mandatory=$true)][string]$QgcRoot,
    [Parameter(Mandatory=$true)][string]$OverlayRoot,
    [string]$ExpectedCommit = "e0816c957602789200ae5ba0af45217f0f2f1db4",
    [string]$TranslationRef = "master"
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
        (Join-Path $OverlayRoot "patches\0003-pin-px4-gpsdrivers.patch"),
        (Join-Path $OverlayRoot "patches\0004-px4-compass-info.patch")
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

    Write-Host "=== Use official upstream Ukrainian translations ==="
    $translationDir = Join-Path $QgcRoot "translations"
    $ukSource = Join-Path $translationDir "qgc_source_uk_UA.ts"
    $ukJson = Join-Path $translationDir "qgc_json_uk_UA.ts"
    $upstreamTranslationBase = "https://raw.githubusercontent.com/mavlink/qgroundcontrol/$TranslationRef/translations"

    Invoke-WebRequest -Uri "$upstreamTranslationBase/qgc_source_uk_UA.ts" -OutFile $ukSource
    Invoke-WebRequest -Uri "$upstreamTranslationBase/qgc_json_uk_UA.ts" -OutFile $ukJson

    foreach ($translationFile in @($ukSource, $ukJson)) {
        if (-not (Test-Path $translationFile -PathType Leaf)) {
            throw "Official Ukrainian translation missing: $translationFile"
        }
        if ((Get-Item $translationFile).Length -lt 1000) {
            throw "Official Ukrainian translation download looks invalid: $translationFile"
        }
        if (-not (Select-String -Path $translationFile -Pattern '<TS version="2\.1" language="uk"' -Quiet)) {
            throw "Unexpected Ukrainian translation format: $translationFile"
        }
    }
    Write-Host "Using mavlink/qgroundcontrol@$TranslationRef Ukrainian translations."

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
    if (-not $mainWindow) { throw "Indicator drawer close-policy marker not found" }

    $statusHandler = Join-Path $QgcRoot "src\MAVLink\StatusTextHandler.cc"
    $screenToolsController = Join-Path $QgcRoot "src\QmlControls\ScreenToolsController.cc"
    $mainSource = Join-Path $QgcRoot "src\main.cc"
    if (-not (Select-String -Path $statusHandler -Pattern 'QStringDecoder utf8Decoder' -Quiet)) {
        throw "MAVLink STATUSTEXT UTF-8 marker not found"
    }
    if (-not (Select-String -Path $screenToolsController -Pattern 'QStringLiteral\("Play"\)' -Quiet)) {
        throw "Global Play font marker not found"
    }
    if (-not (Select-String -Path $mainSource -Pattern 'QGroundControl Portable' -Quiet)) {
        throw "Portable splash screen marker not found"
    }
    if (-not ($allQml | Where-Object { Select-String -Path $_.FullName -Pattern 'interval:\s*5000' -Quiet } | Select-Object -First 1)) {
        throw "MAVLink Status 5-second refresh marker not found"
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
        if (-not (Select-String -Path $translationFile -Pattern '<TS version="2\.1" language="uk"' -Quiet)) {
            throw "Official Ukrainian localization marker missing from $translationFile"
        }
    }
    $serviceModeQml = Join-Path $QgcRoot "custom\qml\ServiceMode.qml"
    $serviceParamsQml = Join-Path $QgcRoot "custom\qml\ServiceParameterEditor.qml"
    $serviceServoQml = Join-Path $QgcRoot "custom\qml\ServiceServoSafety.qml"
    $serviceMavlinkQml = Join-Path $QgcRoot "custom\qml\ServiceMavlinkStatus.qml"
    $serviceMPParamsQml = Join-Path $QgcRoot "custom\qml\ServiceMPParams.qml"
    $serviceMapQml = Join-Path $QgcRoot "custom\qml\ServiceMap.qml"
    $mpParamsController = Join-Path $QgcRoot "custom\src\MPParamsController.cc"
    if (-not (Select-String -Path $mainWindow.FullName -Pattern 'Спрощ\. режим для сервісу' -Quiet)) {
        throw "Service mode menu button marker not found"
    }
    if (-not (Test-Path $serviceModeQml -PathType Leaf)) {
        throw "ServiceMode.qml missing from custom overlay"
    }
    foreach ($serviceMarker in @(
        'text:\s*"Огляд"',
        'text:\s*"Карта"',
        'text:\s*"Прошивка"',
        'text:\s*"Параметри"',
        'text:\s*"Датчики"',
        'text:\s*"Servo/Saf.Mask"',
        'text:\s*"MAVLink Status"',
        'text:\s*"MP Params"',
        'text:\s*"Реконнект"',
        'mainWindow\.restartActiveConnections\(\)',
        'QGCAttitudeWidget',
        'activeVehicle\.gps\.count\.valueString',
        'activeVehicle\.gps\.lock\.enumStringValue',
        'QGCCompassWidget'
    )) {
        if (-not (Select-String -Path $serviceModeQml -Pattern $serviceMarker -Quiet)) {
            throw "Service mode marker not found: $serviceMarker"
        }
    }
    if (-not (Test-Path $serviceMapQml -PathType Leaf)) {
        throw "ServiceMap.qml missing from custom overlay"
    }
    foreach ($mapMarker in @('FlightMap\s*\{', 'VehicleMapItem', 'allowVehicleLocationCenter:\s*true', 'mapName:\s*"ServiceMap"')) {
        if (-not (Select-String -Path $serviceMapQml -Pattern $mapMarker -Quiet)) {
            throw "Service map marker not found: $mapMarker"
        }
    }

    $flyToolbarQml = Join-Path $QgcRoot "src\QmlControls\FlyViewToolBar.qml"
    if (-not (Select-String -Path $flyToolbarQml -Pattern 'quickVehicleSetupRow' -Quiet)) {
        throw "Vehicle Setup quick toolbar marker not found"
    }
    if (-not (Select-String -Path $mainWindow.FullName -Pattern 'restartActiveConnections' -Quiet)) {
        throw "Permanent reconnect helper marker not found"
    }

    if (-not (Test-Path $serviceParamsQml -PathType Leaf)) {
        throw "ServiceParameterEditor.qml missing from custom overlay"
    }
    foreach ($paramMarker in @('serviceTreeModel', 'controller\.parameters', 'BRD_', 'SERVO')) {
        if (-not (Select-String -Path $serviceParamsQml -Pattern $paramMarker -Quiet)) {
            throw "Service parameter editor marker not found: $paramMarker"
        }
    }

    if (-not (Test-Path $serviceMPParamsQml -PathType Leaf)) {
        throw "ServiceMPParams.qml missing from custom overlay"
    }
    foreach ($mpMarker in @('Read Params', 'Write Params', 'Mission Planner Params', 'LinkConfiguration\.TypeSerial', 'controller\.compareModel', 'uiScale:\s*0\.82', 'columnFractions')) {
        if (-not (Select-String -Path $serviceMPParamsQml -Pattern $mpMarker -Quiet)) {
            throw "MP Params service marker not found: $mpMarker"
        }
    }
    if (Select-String -Path $serviceMPParamsQml -Pattern 'MP Parameter Tree|TreeView\s*\{' -Quiet) {
        throw "MP Params tree UI must be removed"
    }
    if (-not (Test-Path $mpParamsController -PathType Leaf)) {
        throw "MPParamsController.cc missing from custom overlay"
    }
    foreach ($mpControllerMarker in @('_parseMpFile', 'separator\(QStringLiteral', 'writePending', '_rebuildTree', 'stream << name <<')) {
        if (-not (Select-String -Path $mpParamsController -Pattern $mpControllerMarker -Quiet)) {
            throw "MP Params controller marker not found: $mpControllerMarker"
        }
    }

    if (-not (Test-Path $serviceMavlinkQml -PathType Leaf)) {
        throw "ServiceMavlinkStatus.qml missing from custom overlay"
    }
    foreach ($mavMarker in @('interval:\s*5000', 'messageFontPointSize:\s*ScreenTools\.defaultFontPointSize', 'refreshMessages\(\)', 'ScrollBar\.vertical\.policy:\s*ScrollBar\.AlwaysOn')) {
        if (-not (Select-String -Path $serviceMavlinkQml -Pattern $mavMarker -Quiet)) {
            throw "Service MAVLink Status marker not found: $mavMarker"
        }
    }

    if (-not (Test-Path $serviceServoQml -PathType Leaf)) {
        throw "ServiceServoSafety.qml missing from custom overlay"
    }
    foreach ($servoMarker in @('SERVO', 'BRD_SAFETY_MASK', 'motorTest\(', 'FMU PWM OUT \(AUX\)', 'I/O PWM OUT \(MAIN\)', 'applyServoProfile', 'setServoFunction\(output, 0\)', 'setSafetyCommand:\s*5300', 'activeVehicle\.sendCommand\(1, setSafetyCommand', 'activeVehicle\.sensorsEnabledBits', 'drag\.target:\s*safetyHandle', '255,', '65280,')) {
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
