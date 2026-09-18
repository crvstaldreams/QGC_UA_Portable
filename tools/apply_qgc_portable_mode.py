#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


class PortableModeError(RuntimeError):
    pass


PATH_REPLACEMENTS = {
    "QStandardPaths::writableLocation(QStandardPaths::TempLocation)": "QGCPortablePaths::tempDir()",
    "QStandardPaths::writableLocation(QStandardPaths::CacheLocation)": "QGCPortablePaths::cacheDir()",
    "QStandardPaths::writableLocation(QStandardPaths::GenericCacheLocation)": "QGCPortablePaths::cacheDir()",
    "QStandardPaths::writableLocation(QStandardPaths::AppConfigLocation)": "QGCPortablePaths::configDir()",
    "QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)": "QGCPortablePaths::rootDir()",
    "QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation)": "QGCPortablePaths::filesDir()",
    "QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation)": "QGCPortablePaths::filesDir()",
    "QStandardPaths::writableLocation(QStandardPaths::DownloadLocation)": "QGCPortablePaths::filesDir()",
    'QDir::homePath() + QStringLiteral("/.qgcmapscache/")':
        'QDir(QGCPortablePaths::cacheDir()).filePath(QStringLiteral("QGCMapsFallback"))',
    "QDir::tempPath()": "QGCPortablePaths::tempDir()",
}


def _insert_include(text: str) -> str:
    if '#include "PortablePaths.h"' in text:
        return text
    match = re.search(r"^#include\s", text, flags=re.MULTILINE)
    if not match:
        raise PortableModeError("Could not locate include block")
    return text[: match.start()] + '#include "PortablePaths.h"\n' + text[match.start() :]


def _replace_standard_paths(source_root: Path) -> list[Path]:
    changed: list[Path] = []
    src_root = source_root / "src"
    for path in sorted(src_root.rglob("*")):
        if path.suffix.lower() not in {".cc", ".cpp", ".cxx"}:
            continue

        text = path.read_text(encoding="utf-8")
        updated = text
        replacements = 0
        for old, new in PATH_REPLACEMENTS.items():
            count = updated.count(old)
            if count:
                updated = updated.replace(old, new)
                replacements += count

        if replacements:
            updated = _insert_include(updated)
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append(path)

    if not changed:
        raise PortableModeError("No QStandardPaths writable locations were patched")

    portable_header = source_root / "custom" / "src" / "PortablePaths.h"
    if not portable_header.is_file():
        raise PortableModeError(f"PortablePaths.h missing: {portable_header}")

    for source_file in changed:
        local_header = source_file.parent / "PortablePaths.h"
        shutil.copy2(portable_header, local_header)

    return changed


def _patch_application_boot(source_root: Path) -> Path:
    path = source_root / "src" / "QGCApplication.cc"
    text = path.read_text(encoding="utf-8")
    marker = "{\n    _msecsElapsedTime.start();"
    replacement = "{\n    QGCPortablePaths::initialize();\n\n    _msecsElapsedTime.start();"
    if "QGCPortablePaths::initialize();" not in text:
        if marker not in text:
            raise PortableModeError("QGCApplication constructor marker not found")
        text = text.replace(marker, replacement, 1)
        path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _force_portable_save_path(source_root: Path) -> Path:
    path = source_root / "src" / "Settings" / "AppSettings.cc"
    text = path.read_text(encoding="utf-8")

    if "QGC PORTABLE: force all user files beside the executable" in text:
        return path

    start = "    SettingsFact* savePathFact = qobject_cast<SettingsFact*>(savePath());\n    QString appName = QCoreApplication::applicationName();"
    replacement = """    SettingsFact* savePathFact = qobject_cast<SettingsFact*>(savePath());
#ifdef QGC_PORTABLE_BUILD
    // QGC PORTABLE: force all user files beside the executable.
    savePathFact->setRawValue(QGCPortablePaths::filesDir());
    savePathFact->setVisible(false);
#else
    QString appName = QCoreApplication::applicationName();"""

    if start not in text:
        raise PortableModeError("AppSettings savePath start marker not found")
    text = text.replace(start, replacement, 1)

    end = "    connect(savePathFact, &Fact::rawValueChanged, this, &AppSettings::savePathsChanged);"
    if end not in text:
        raise PortableModeError("AppSettings savePath end marker not found")
    text = text.replace(end, "#endif // QGC_PORTABLE_BUILD\n\n" + end, 1)

    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _patch_installer(source_root: Path) -> Path:
    path = source_root / "deploy" / "windows" / "nullsoft_installer.nsi"
    text = path.read_text(encoding="utf-8")

    replacements = {
        'InstallDir "$PROGRAMFILES64\\${APPNAME}"': 'InstallDir "$LOCALAPPDATA\\Programs\\${APPNAME}"',
        'ReadRegStr $R0 HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "UninstallString"':
            'ReadRegStr $R0 HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "UninstallString"',
        'WriteRegStr HKLM "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"':
            'WriteRegStr HKCU "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"',
        'WriteRegDWORD HKLM "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe"':
            'WriteRegDWORD HKCU "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe"',
        'WriteRegExpandStr HKLM "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe"':
            'WriteRegExpandStr HKCU "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe"',
        'DeleteRegKey HKLM "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"':
            'DeleteRegKey HKCU "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"',
        'DeleteRegKey HKLM "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe"':
            'DeleteRegKey HKCU "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe"',
    }

    applied = 0
    for old, new in replacements.items():
        if old in text:
            count = text.count(old)
            text = text.replace(old, new)
            applied += count

    text = text.replace("SetShellVarContext all", "SetShellVarContext current")

    # Keep Windows Error Reporting dumps inside the portable application tree.
    text = text.replace(
        'WriteRegExpandStr HKCU "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe" "DumpFolder" "%LOCALAPPDATA%\\QGCCrashDumps"',
        'WriteRegExpandStr HKCU "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting\\LocalDumps\\${EXENAME}.exe" "DumpFolder" "$INSTDIR\\bin\\PortableData\\Files\\CrashLogs"'
    )
    text = text.replace(
        "  SetOutPath $INSTDIR\n  File /r",
        "  SetOutPath $INSTDIR\n  CreateDirectory \"$INSTDIR\\bin\\PortableData\\Files\\CrashLogs\"\n  File /r",
        1,
    )

    # Portable builds never use the legacy AppData tree, so uninstall must not touch it.
    text = text.replace(
        '  ${If} $R1 != 1\n    RMDir /r /REBOOTOK "$APPDATA\\${ORGNAME}\\"\n  ${Endif}\n',
        '',
        1,
    )

    if "%LOCALAPPDATA%\\QGCCrashDumps" in text:
        raise PortableModeError("Legacy external crash-dump path is still present")
    if "$APPDATA\\${ORGNAME}" in text:
        raise PortableModeError("Legacy AppData uninstall path is still present")

    if applied < 7:
        raise PortableModeError(f"Installer portable patch incomplete; replacements={applied}")

    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def apply_portable_mode(source_root: Path) -> list[Path]:
    changed = _replace_standard_paths(source_root)
    changed.append(_patch_application_boot(source_root))
    changed.append(_force_portable_save_path(source_root))
    changed.append(_patch_installer(source_root))
    return list(dict.fromkeys(changed))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()

    try:
        changed = apply_portable_mode(args.source_root.resolve())
    except (PortableModeError, OSError, UnicodeError) as exc:
        print(f"QGC portable customization failed: {exc}", file=sys.stderr)
        return 1

    for path in changed:
        print("portable-patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
