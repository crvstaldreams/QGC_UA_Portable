#pragma once

#include <QtCore/QCoreApplication>
#include <QtCore/QDir>
#include <QtCore/QFileInfo>
#include <QtCore/QSettings>
#include <QtCore/QString>

#ifdef Q_OS_WIN
#include <QtCore/qt_windows.h>
#endif

namespace QGCPortablePaths
{

inline QString applicationDir()
{
#ifdef Q_OS_WIN
    static constexpr DWORD kBufferSize = 32768;
    wchar_t buffer[kBufferSize] = {};
    const DWORD length = GetModuleFileNameW(nullptr, buffer, kBufferSize);
    if ((length > 0) && (length < kBufferSize)) {
        return QFileInfo(QString::fromWCharArray(buffer, static_cast<int>(length))).absolutePath();
    }
#endif

    const QString appDir = QCoreApplication::applicationDirPath();
    return appDir.isEmpty() ? QDir::currentPath() : appDir;
}

inline QString ensureDir(const QString &path)
{
    QDir().mkpath(path);
    return QDir::cleanPath(path);
}

inline QString rootDir()
{
    return ensureDir(QDir(applicationDir()).filePath(QStringLiteral("PortableData")));
}

inline QString settingsDir()
{
    return ensureDir(QDir(rootDir()).filePath(QStringLiteral("Settings")));
}

inline QString filesDir()
{
    return ensureDir(QDir(rootDir()).filePath(QStringLiteral("Files")));
}

inline QString cacheDir()
{
    return ensureDir(QDir(rootDir()).filePath(QStringLiteral("Cache")));
}

inline QString tempDir()
{
    return ensureDir(QDir(rootDir()).filePath(QStringLiteral("Temp")));
}

inline QString configDir()
{
    return ensureDir(QDir(rootDir()).filePath(QStringLiteral("Config")));
}

inline void initialize()
{
    const QString settings = settingsDir();
    const QString temp = tempDir();

    (void) filesDir();
    (void) cacheDir();
    (void) configDir();

    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, settings);
    QSettings::setPath(QSettings::IniFormat, QSettings::SystemScope, settings);

    qputenv("TEMP", temp.toUtf8());
    qputenv("TMP", temp.toUtf8());

    qputenv("QGC_PORTABLE_ROOT", rootDir().toUtf8());
    qputenv("QGC_PORTABLE_SETTINGS_DIR", settings.toUtf8());
    qputenv("QGC_PORTABLE_FILES_DIR", filesDir().toUtf8());
    qputenv("QGC_PORTABLE_CACHE_DIR", cacheDir().toUtf8());
    qputenv("QGC_PORTABLE_TEMP_DIR", temp.toUtf8());
    qputenv("QGC_PORTABLE_CONFIG_DIR", configDir().toUtf8());
}

} // namespace QGCPortablePaths
