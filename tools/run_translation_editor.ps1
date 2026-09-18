param(
    [string]$QgcRoot = "",
    [switch]$RefreshSource
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$editor = Join-Path $PSScriptRoot "qgc_translation_editor.py"
$overrides = Join-Path $repoRoot "translations\uk_manual_overrides.json"

if (-not $QgcRoot) {
    $QgcRoot = Join-Path $repoRoot ".translation-workspace"
    $translationDir = Join-Path $QgcRoot "translations"
    New-Item -ItemType Directory -Force -Path $translationDir | Out-Null

    $commit = "e0816c957602789200ae5ba0af45217f0f2f1db4"
    foreach ($name in @("qgc_source_uk_UA.ts", "qgc_json_uk_UA.ts")) {
        $target = Join-Path $translationDir $name
        if ($RefreshSource -or -not (Test-Path $target -PathType Leaf)) {
            $url = "https://raw.githubusercontent.com/mavlink/qgroundcontrol/$commit/translations/$name"
            Write-Host "Download $name..."
            Invoke-WebRequest -Uri $url -OutFile $target
        }
    }
}

& python $editor --source-root $QgcRoot --overrides $overrides
if ($LASTEXITCODE -ne 0) {
    throw "Translation editor failed with exit code $LASTEXITCODE"
}
