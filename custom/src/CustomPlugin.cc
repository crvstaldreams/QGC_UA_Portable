#include "CustomPlugin.h"
#include "MPParamsController.h"
#include "CompassTelemetryController.h"

#include <QtQml/qqml.h>

#include <QtCore/QApplicationStatic>

Q_APPLICATION_STATIC(CustomPlugin, s_customPluginInstance);

CustomPlugin::CustomPlugin(QObject *parent)
    : QGCCorePlugin(parent)
{
    qmlRegisterType<MPParamsController>("QGroundControl.Custom", 1, 0, "MPParamsController");
    qmlRegisterType<CompassTelemetryController>("QGroundControl.Custom", 1, 0, "CompassTelemetryController");
}

QGCCorePlugin *CustomPlugin::instance()
{
    return s_customPluginInstance();
}

void CustomPlugin::paletteOverride(const QString &colorName, QGCPalette::PaletteColorInfo_t &colorInfo)
{
    const auto setPalette = [&colorInfo](const QColor &enabled, const QColor &disabled) {
        colorInfo[QGCPalette::Dark][QGCPalette::ColorGroupEnabled] = enabled;
        colorInfo[QGCPalette::Dark][QGCPalette::ColorGroupDisabled] = disabled;
        colorInfo[QGCPalette::Light][QGCPalette::ColorGroupEnabled] = enabled;
        colorInfo[QGCPalette::Light][QGCPalette::ColorGroupDisabled] = disabled;
    };

    if (colorName == QStringLiteral("window")) {
        setPalette(QColor("#101010"), QColor("#101010"));
    } else if (colorName == QStringLiteral("windowShadeLight")) {
        setPalette(QColor("#2A2A2A"), QColor("#202020"));
    } else if (colorName == QStringLiteral("windowShade")) {
        setPalette(QColor("#1B1B1B"), QColor("#181818"));
    } else if (colorName == QStringLiteral("windowShadeDark")) {
        setPalette(QColor("#080808"), QColor("#080808"));
    } else if (colorName == QStringLiteral("text")) {
        setPalette(QColor("#F5F5F5"), QColor("#8A8A8A"));
    } else if (colorName == QStringLiteral("warningText")) {
        setPalette(QColor("#FF5252"), QColor("#B33A3A"));
    } else if (colorName == QStringLiteral("button")) {
        setPalette(QColor("#242424"), QColor("#181818"));
    } else if (colorName == QStringLiteral("buttonBorder")) {
        setPalette(QColor("#FFD400"), QColor("#5C5200"));
    } else if (colorName == QStringLiteral("buttonText")) {
        setPalette(QColor("#FFFFFF"), QColor("#777777"));
    } else if (colorName == QStringLiteral("buttonHighlight") ||
               colorName == QStringLiteral("primaryButton") ||
               colorName == QStringLiteral("mapButtonHighlight") ||
               colorName == QStringLiteral("mapIndicator")) {
        setPalette(QColor("#FFD400"), QColor("#6B5E00"));
    } else if (colorName == QStringLiteral("buttonHighlightText") ||
               colorName == QStringLiteral("primaryButtonText")) {
        setPalette(QColor("#101010"), QColor("#282828"));
    } else if (colorName == QStringLiteral("textField")) {
        setPalette(QColor("#181818"), QColor("#111111"));
    } else if (colorName == QStringLiteral("textFieldText")) {
        setPalette(QColor("#FFFFFF"), QColor("#777777"));
    } else if (colorName == QStringLiteral("mapButton")) {
        setPalette(QColor("#111111"), QColor("#080808"));
    } else if (colorName == QStringLiteral("mapIndicatorChild")) {
        setPalette(QColor("#8A7400"), QColor("#514500"));
    } else if (colorName == QStringLiteral("alertBackground")) {
        setPalette(QColor("#FFD400"), QColor("#8A7400"));
    } else if (colorName == QStringLiteral("alertBorder")) {
        setPalette(QColor("#101010"), QColor("#101010"));
    } else if (colorName == QStringLiteral("alertText")) {
        setPalette(QColor("#101010"), QColor("#202020"));
    } else if (colorName == QStringLiteral("missionItemEditor")) {
        setPalette(QColor("#202020"), QColor("#151515"));
    } else if (colorName == QStringLiteral("toolStripHoverColor") ||
               colorName == QStringLiteral("hoverColor")) {
        setPalette(QColor("#4A4000"), QColor("#2C2600"));
    } else if (colorName == QStringLiteral("toolbarBackground")) {
        setPalette(QColor("#0B0B0B"), QColor("#0B0B0B"));
    } else if (colorName == QStringLiteral("groupBorder")) {
        setPalette(QColor("#5C5200"), QColor("#302B00"));
    } else if (colorName == QStringLiteral("brandingPurple") ||
               colorName == QStringLiteral("brandingBlue")) {
        setPalette(QColor("#FFD400"), QColor("#8A7400"));
    }
}
