#pragma once

#include "QGCCorePlugin.h"

class CustomPlugin final : public QGCCorePlugin
{
    Q_OBJECT

public:
    explicit CustomPlugin(QObject *parent = nullptr);
    ~CustomPlugin() final = default;

    static QGCCorePlugin *instance();

    void paletteOverride(const QString &colorName, QGCPalette::PaletteColorInfo_t &colorInfo) final;
};
