#pragma once

#include <QtCore/QCoreApplication>
#include <QtCore/QDir>
#include <QtCore/QSettings>
#include <QtCore/QString>

namespace QGCPortablePaths
{

inline QString applicationDir()
{
    // QGCApplication derives from QApplication, so by the time portable
    // initialization runs Qt already knows the executable directory.
    // Deliberately avoid including Windows headers here: rpcndr.h defines
    // 'interface' as a macro, which collides with upstream QGC identifiers.
    const QString appDir = QCoreApplication::applicationDirPath();
    return appDir.isEmpty() ? QDir::currentPath() : QDir::cleanPath(appDir);
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
