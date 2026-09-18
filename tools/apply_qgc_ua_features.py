#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


class FeaturePatchError(RuntimeError):
    pass


def locate_unique(root: Path, filename: str, markers: tuple[str, ...]) -> Path:
    matches: list[Path] = []
    for path in root.rglob(filename):
        if any(part in {".git", "build", "custom"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if all(marker in text for marker in markers):
            matches.append(path)
    if len(matches) != 1:
        raise FeaturePatchError(f"Expected one {filename}, found {len(matches)}")
    return matches[0]


def replace_once(text: str, old: str, new: str, description: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise FeaturePatchError(f"Could not apply {description}: source marker not found")
    return text.replace(old, new, 1)


def patch_status_utf8(root: Path) -> Path:
    path = root / "src" / "MAVLink" / "StatusTextHandler.cc"
    text = path.read_text(encoding="utf-8")

    if "#include <QtCore/QStringConverter>" not in text:
        text = replace_once(
            text,
            "#include <QtCore/QDateTime>\n",
            "#include <QtCore/QDateTime>\n#include <QtCore/QStringConverter>\n",
            "QStringConverter include",
        )

    old = '    const QString text = QString::fromLocal8Bit(b.constData(), std::strlen(b.constData()));\n'
    new = '''    const int payloadLength = static_cast<int>(std::strlen(b.constData()));
    const QByteArray payload(b.constData(), payloadLength);

    QStringDecoder utf8Decoder(QStringDecoder::Utf8);
    const QString utf8Text = utf8Decoder(payload);

    // PX4/ArduPilot status text is UTF-8 in this fork. Keep a local-8-bit
    // fallback for legacy devices which still send locale encoded text.
    const QString text = utf8Decoder.hasError() ? QString::fromLocal8Bit(payload) : utf8Text;
'''
    text = replace_once(text, old, new, "MAVLink STATUSTEXT UTF-8 decode")
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_play_font(root: Path) -> list[Path]:
    controller = root / "src" / "QmlControls" / "ScreenToolsController.cc"
    text = controller.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    return QStringLiteral("Open Sans");\n',
        '    return QStringLiteral("Play");\n',
        "global Play font family",
    )
    controller.write_text(text, encoding="utf-8", newline="\n")

    app = root / "src" / "QGCApplication.cc"
    text = app.read_text(encoding="utf-8")
    marker = '    // Although this should really be in _initForNormalAppBoot putting it here allowws us to create unit tests which pop up more easily\n'
    font_block = '''    // QGC PORTABLE: bundled Play font is the global UI family.
    if (QFontDatabase::addApplicationFont(":/fonts/play-regular") < 0) {
        qCWarning(QGCApplicationLog) << "Could not load /fonts/play-regular font";
    }
    if (QFontDatabase::addApplicationFont(":/fonts/play-bold") < 0) {
        qCWarning(QGCApplicationLog) << "Could not load /fonts/play-bold font";
    }

'''
    if font_block not in text:
        if marker not in text:
            raise FeaturePatchError("QGCApplication font marker not found")
        text = text.replace(marker, marker + font_block, 1)
    app.write_text(text, encoding="utf-8", newline="\n")
    return [controller, app]


def patch_vehicle_message_list(root: Path) -> Path:
    path = locate_unique(root, "VehicleMessageList.qml", ("property bool noMessages", "formatMessage"))
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "    Layout.preferredWidth:  ScreenTools.defaultFontPixelWidth * 50\n    height:                 contentHeight\n",
        "    Layout.preferredWidth:  messagePanelWidth\n"
        "    Layout.preferredHeight: Math.max(contentHeight, messagePanelMinHeight)\n"
        "    height:                 Math.max(contentHeight, messagePanelMinHeight)\n",
        "MAVLink Status panel sizing",
    )

    if "property real messagePanelWidth" not in text:
        marker = "    property bool noMessages: messageText.length === 0\n"
        replacement = (
            marker
            + "    property real messagePanelWidth: ScreenTools.defaultFontPixelWidth * 50\n"
            + "    property real messagePanelMinHeight: 0\n"
        )
        text = replace_once(text, marker, replacement, "MAVLink Status size properties")

    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_main_status(root: Path) -> Path:
    path = locate_unique(root, "MainStatusIndicator.qml", ("dropMainStatusIndicator", "VehicleMessageList"))
    text = path.read_text(encoding="utf-8")

    if "import QtCore" not in text:
        text = replace_once(
            text,
            "import QtQuick.Layouts\n",
            "import QtQuick.Layouts\nimport QtCore\n",
            "QtCore import for status settings",
        )

    layout_marker = '''        ColumnLayout {
            id:         mainLayout
            spacing:    _spacing
'''
    settings_block = '''        ColumnLayout {
            id:         mainLayout
            spacing:    _spacing

            Settings {
                id:         mavlinkStatusSettings
                category:   "MAVLinkStatus"

                property bool autoCloseEnabled: true
                property int autoCloseSeconds: 60
            }

            Timer {
                id:         mavlinkStatusCloseTimer
                interval:   Math.max(5, mavlinkStatusSettings.autoCloseSeconds) * 1000
                repeat:     false
                running:    mavlinkStatusSettings.autoCloseEnabled
                onTriggered: mainWindow.closeIndicatorDrawer()
            }
'''
    text = replace_once(text, layout_marker, settings_block, "MAVLink Status persisted timer")

    old_list = '''                VehicleMessageList { 
                    id: vehicleMessageList
                    messageFontPointSize: ScreenTools.defaultFontPointSize * 1.35
                }
'''
    new_list = '''                VehicleMessageList {
                    id:                     vehicleMessageList
                    messagePanelWidth:      ScreenTools.defaultFontPixelWidth * 72
                    messagePanelMinHeight:  ScreenTools.defaultFontPixelHeight * 20
                }

                RowLayout {
                    spacing: ScreenTools.defaultFontPixelWidth

                    QGCLabel {
                        text: "Автозакриття:"
                    }

                    QGCComboBox {
                        id: timeoutCombo
                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 15

                        property var timeoutValues: [0, 15, 30, 60, 120, 300, 600]

                        model: [
                            "Вимкнено",
                            "15 секунд",
                            "30 секунд",
                            "1 хвилина",
                            "2 хвилини",
                            "5 хвилин",
                            "10 хвилин"
                        ]

                        Component.onCompleted: {
                            if (!mavlinkStatusSettings.autoCloseEnabled) {
                                currentIndex = 0
                            } else {
                                const index = timeoutValues.indexOf(mavlinkStatusSettings.autoCloseSeconds)
                                currentIndex = index >= 0 ? index : 3
                            }
                        }

                        onActivated: (index) => {
                            const seconds = timeoutValues[index]
                            mavlinkStatusSettings.autoCloseEnabled = seconds > 0
                            if (seconds > 0) {
                                mavlinkStatusSettings.autoCloseSeconds = seconds
                                mavlinkStatusCloseTimer.restart()
                            } else {
                                mavlinkStatusCloseTimer.stop()
                            }
                        }
                    }
                }
'''
    text = replace_once(text, old_list, new_list, "MAVLink Status timer controls and expanded size")
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_centered_tool_menu(root: Path) -> Path:
    path = locate_unique(root, "MainWindow.qml", ("function showToolSelectDialog", "id: indicatorDrawer"))
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "            mainWindow.showIndicatorDrawer(toolSelectComponent, null)\n",
        "            mainWindow.showIndicatorDrawer(toolSelectComponent, null, false, true)\n",
        "center tool menu invocation",
    )

    text = replace_once(
        text,
        "function showIndicatorDrawer(drawerComponent, indicatorItem, keepOpen) {",
        "function showIndicatorDrawer(drawerComponent, indicatorItem, keepOpen, centerOnWindow) {",
        "drawer centering argument",
    )

    old_state = '''        indicatorDrawer.sourceComponent = drawerComponent
        indicatorDrawer.indicatorItem = indicatorItem
        indicatorDrawer.keepOpen = keepOpen === true
        indicatorDrawer.open()
'''
    new_state = '''        indicatorDrawer.sourceComponent = drawerComponent
        indicatorDrawer.indicatorItem = indicatorItem
        indicatorDrawer.keepOpen = keepOpen === true
        indicatorDrawer.centerOnWindow = centerOnWindow === true
        indicatorDrawer.open()
'''
    text = replace_once(text, old_state, new_state, "drawer center state")

    old_property = '''        property var sourceComponent
        property bool keepOpen: false
        property var indicatorItem
'''
    new_property = '''        property var sourceComponent
        property bool keepOpen: false
        property bool centerOnWindow: false
        property var indicatorItem
'''
    text = replace_once(text, old_property, new_property, "drawer center property")

    text = replace_once(
        text,
        "        y:              ScreenTools.toolbarHeight + _margins\n",
        "        y:              centerOnWindow\n"
        "                            ? Math.max(ScreenTools.toolbarHeight + _margins, Math.round((mainWindow.contentItem.height - height) / 2))\n"
        "                            : ScreenTools.toolbarHeight + _margins\n",
        "centered drawer y position",
    )

    old_calc = '''        function calcXPosition() {
            if (indicatorItem) {
'''
    new_calc = '''        function calcXPosition() {
            if (centerOnWindow) {
                const popupWidth = contentItem.implicitWidth + (indicatorDrawer.padding * 2)
                return Math.max(_margins, Math.round((mainWindow.contentItem.width - popupWidth) / 2))
            }
            if (indicatorItem) {
'''
    text = replace_once(text, old_calc, new_calc, "centered drawer x position")

    old_close = '''            _expanded                               = false
            indicatorItem                           = undefined
            indicatorDrawerLoader.sourceComponent   = undefined
'''
    new_close = '''            _expanded                               = false
            centerOnWindow                          = false
            indicatorItem                           = undefined
            indicatorDrawerLoader.sourceComponent   = undefined
'''
    text = replace_once(text, old_close, new_close, "drawer center reset")

    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_splash(root: Path) -> Path:
    path = root / "src" / "main.cc"
    text = path.read_text(encoding="utf-8")

    include_marker = "#include <QtWidgets/QApplication>\n"
    include_block = '''#include <QtWidgets/QApplication>
#include <QtWidgets/QSplashScreen>
#include <QtGui/QFontDatabase>
#include <QtGui/QPainter>
#include <QtCore/QElapsedTimer>
#include <QtCore/QEventLoop>
#include <QtCore/QThread>
'''
    text = replace_once(text, include_marker, include_block, "portable splash includes")

    app_marker = "    QGCApplication app(argc, argv, runUnitTests, simpleBootTest);\n"
    splash_block = '''    QGCApplication app(argc, argv, runUnitTests, simpleBootTest);

    QSplashScreen *portableSplash = nullptr;
    QElapsedTimer portableSplashTimer;
    if (!simpleBootTest && !runUnitTests) {
        (void) QFontDatabase::addApplicationFont(":/fonts/play-regular");
        (void) QFontDatabase::addApplicationFont(":/fonts/play-bold");

        QPixmap splashPixmap(720, 400);
        splashPixmap.fill(QColor("#101010"));

        QPainter painter(&splashPixmap);
        painter.setRenderHint(QPainter::Antialiasing, true);
        painter.setRenderHint(QPainter::TextAntialiasing, true);

        QFont titleFont(QStringLiteral("Play"), 34, QFont::Bold);
        painter.setFont(titleFont);
        painter.setPen(QColor("#FFD400"));
        painter.drawText(QRect(30, 115, 660, 90), Qt::AlignCenter, QStringLiteral("QGroundControl Portable"));

        QFont subtitleFont(QStringLiteral("Play"), 17, QFont::Normal);
        painter.setFont(subtitleFont);
        painter.setPen(QColor("#F5F5F5"));
        painter.drawText(QRect(30, 205, 660, 55), Qt::AlignCenter, QStringLiteral("made by Argone"));
        painter.end();

        portableSplash = new QSplashScreen(splashPixmap);
        portableSplash->setWindowFlag(Qt::WindowStaysOnTopHint, true);
        portableSplash->show();
        app.processEvents();
        portableSplashTimer.start();
    }
'''
    text = replace_once(text, app_marker, splash_block, "portable startup splash")

    init_marker = "    app.init();\n"
    close_block = '''    app.init();

    if (portableSplash) {
        while (portableSplashTimer.elapsed() < 1200) {
            app.processEvents(QEventLoop::AllEvents, 20);
            QThread::msleep(10);
        }
        portableSplash->close();
        delete portableSplash;
        portableSplash = nullptr;
        app.processEvents();
    }
'''
    text = replace_once(text, init_marker, close_block, "portable splash close")
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def verify_markers(paths: list[Path]) -> None:
    required = {
        "StatusTextHandler.cc": "QStringDecoder utf8Decoder(QStringDecoder::Utf8)",
        "ScreenToolsController.cc": 'QStringLiteral("Play")',
        "QGCApplication.cc": ':/fonts/play-regular',
        "VehicleMessageList.qml": "messagePanelMinHeight",
        "MainStatusIndicator.qml": "autoCloseSeconds: 60",
        "MainWindow.qml": "centerOnWindow",
        "main.cc": "QGroundControl Portable",
    }
    for path in paths:
        marker = required.get(path.name)
        if marker and marker not in path.read_text(encoding="utf-8"):
            raise FeaturePatchError(f"Verification marker missing from {path}: {marker}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()

    try:
        changed: list[Path] = []
        changed.append(patch_status_utf8(root))
        changed.extend(patch_play_font(root))
        changed.append(patch_vehicle_message_list(root))
        changed.append(patch_main_status(root))
        changed.append(patch_centered_tool_menu(root))
        changed.append(patch_splash(root))
        verify_markers(changed)
    except (FeaturePatchError, OSError) as exc:
        print(f"QGC UA feature patch failed: {exc}", file=sys.stderr)
        return 1

    for path in changed:
        print(f"ua-feature-patched {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
