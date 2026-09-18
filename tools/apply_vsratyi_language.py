#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

VSRATYI_LANGUAGE_ID = 10001


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"{label}: anchor not found")
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {text.count(old)}")
    return text.replace(old, new, 1)


def patch_app_settings_h(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "kVsratyiLanguageId"
    if marker in text:
        return

    old = """    static QLocale::Language _qLocaleLanguageEarlyAccess(void);

    static QList<QLocale::Language> _rgReleaseLanguages;
"""
    new = f"""    static QLocale::Language _qLocaleLanguageEarlyAccess(void);
    static bool _vsratyiLanguageEarlyAccess(void);
    static constexpr int kVsratyiLanguageId = {VSRATYI_LANGUAGE_ID};

    static QList<QLocale::Language> _rgReleaseLanguages;
"""
    text = replace_once(text, old, new, "AppSettings.h Vsratyi declarations")
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_app_settings_cc(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if 'QStringLiteral("Всратий")' not in text:
        old = """        for (const auto& languageInfo: _rgLanguageInfo) {
            if (_rgPartialLanguages.contains(languageInfo.languageId)) {
                rgEnumStrings.append(QString(languageInfo.languageName) + AppSettings::tr(" (Partial)"));
                rgEnumValues.append(languageInfo.languageId);
            }
        }
#ifdef QGC_DAILY_BUILD
"""
        new = """        for (const auto& languageInfo: _rgLanguageInfo) {
            if (_rgPartialLanguages.contains(languageInfo.languageId)) {
                rgEnumStrings.append(QString(languageInfo.languageName) + AppSettings::tr(" (Partial)"));
                rgEnumValues.append(languageInfo.languageId);
            }
        }

        // STREAM-TECHNO: humorous Ukrainian pseudo-locale. It intentionally
        // uses its own settings id while QGCApplication applies QLocale::Ukrainian.
        rgEnumStrings.append(QStringLiteral("Всратий"));
        rgEnumValues.append(kVsratyiLanguageId);

#ifdef QGC_DAILY_BUILD
"""
        text = replace_once(text, old, new, "AppSettings.cc language list")

    if "rawLanguage == kVsratyiLanguageId" not in text:
        old = """    // Note that the AppSettings group has no group name
    QLocale::Language localeLanguage = static_cast<QLocale::Language>(settings.value(qLocaleLanguageName).toInt());
"""
        new = """    // Note that the AppSettings group has no group name
    const int rawLanguage = settings.value(qLocaleLanguageName).toInt();
    if (rawLanguage == kVsratyiLanguageId) {
        return QLocale::Ukrainian;
    }

    QLocale::Language localeLanguage = static_cast<QLocale::Language>(rawLanguage);
"""
        text = replace_once(text, old, new, "AppSettings.cc pseudo-locale early access")

    if "bool AppSettings::_vsratyiLanguageEarlyAccess(void)" not in text:
        anchor = """    return localeLanguage;
}
"""
        idx = text.rfind(anchor)
        if idx < 0:
            raise RuntimeError("AppSettings.cc helper insertion anchor not found")
        insert_at = idx + len(anchor)
        helper = f"""

bool AppSettings::_vsratyiLanguageEarlyAccess(void)
{{
    QSettings settings;
    return settings.value(qLocaleLanguageName, QLocale::English).toInt() == kVsratyiLanguageId;
}}
"""
        text = text[:insert_at] + helper + text[insert_at:]

    path.write_text(text, encoding="utf-8", newline="\n")


def patch_qgc_application(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if "const bool vsratyiLanguage" not in text:
        old = """    QLocale::Language possibleLocale = AppSettings::_qLocaleLanguageEarlyAccess();
"""
        new = """    const bool vsratyiLanguage = AppSettings::_vsratyiLanguageEarlyAccess();
    QLocale::Language possibleLocale = AppSettings::_qLocaleLanguageEarlyAccess();
"""
        text = replace_once(text, old, new, "QGCApplication Vsratyi flag")

    old_source = """        if (_qgcTranslatorSourceCode.load(_locale, QLatin1String("qgc_source_"), "", ":/i18n")) {
            installTranslator(&_qgcTranslatorSourceCode);
        } else {
            qCWarning(QGCApplicationLog) << "Error loading source localization for" << _locale.name();
        }
        if (JsonHelper::translator()->load(_locale, QLatin1String("qgc_json_"), "", ":/i18n")) {
            installTranslator(JsonHelper::translator());
        } else {
            qCWarning(QGCApplicationLog) << "Error loading json localization for" << _locale.name();
        }
"""
    if "qgc_source_vsratyi" not in text:
        new_source = """        if (vsratyiLanguage) {
            qCDebug(QGCApplicationLog) << "Loading humorous Ukrainian localization: Всратий";
            if (_qgcTranslatorSourceCode.load(QStringLiteral("qgc_source_vsratyi"), QStringLiteral(":/i18n"))) {
                installTranslator(&_qgcTranslatorSourceCode);
            } else {
                qCWarning(QGCApplicationLog) << "Error loading Всратий source localization";
            }
            if (JsonHelper::translator()->load(QStringLiteral("qgc_json_vsratyi"), QStringLiteral(":/i18n"))) {
                installTranslator(JsonHelper::translator());
            } else {
                qCWarning(QGCApplicationLog) << "Error loading Всратий json localization";
            }
        } else {
            if (_qgcTranslatorSourceCode.load(_locale, QLatin1String("qgc_source_"), "", ":/i18n")) {
                installTranslator(&_qgcTranslatorSourceCode);
            } else {
                qCWarning(QGCApplicationLog) << "Error loading source localization for" << _locale.name();
            }
            if (JsonHelper::translator()->load(_locale, QLatin1String("qgc_json_"), "", ":/i18n")) {
                installTranslator(JsonHelper::translator());
            } else {
                qCWarning(QGCApplicationLog) << "Error loading json localization for" << _locale.name();
            }
        }
"""
        text = replace_once(text, old_source, new_source, "QGCApplication translator selection")

    path.write_text(text, encoding="utf-8", newline="\n")


def verify(root: Path) -> None:
    app_h = (root / "src/Settings/AppSettings.h").read_text(encoding="utf-8")
    app_cc = (root / "src/Settings/AppSettings.cc").read_text(encoding="utf-8")
    qgc = (root / "src/QGCApplication.cc").read_text(encoding="utf-8")

    required = {
        "AppSettings.h": ["kVsratyiLanguageId = 10001", "_vsratyiLanguageEarlyAccess"],
        "AppSettings.cc": ['QStringLiteral("Всратий")', "rawLanguage == kVsratyiLanguageId"],
        "QGCApplication.cc": ["qgc_source_vsratyi", "qgc_json_vsratyi", "QLocale::Ukrainian"],
    }
    for label, markers in required.items():
        body = app_h if label.endswith(".h") else app_cc if label == "AppSettings.cc" else qgc
        for marker in markers:
            if marker not in body:
                raise RuntimeError(f"{label}: missing marker {marker!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()

    patch_app_settings_h(root / "src/Settings/AppSettings.h")
    patch_app_settings_cc(root / "src/Settings/AppSettings.cc")
    patch_qgc_application(root / "src/QGCApplication.cc")
    verify(root)

    print("Vsratyi language mode patched successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
