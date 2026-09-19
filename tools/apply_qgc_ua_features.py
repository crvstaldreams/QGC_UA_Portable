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


def patch_firmware_upgrade_dedupe(root: Path) -> Path:
    path = root / "src" / "Vehicle" / "VehicleSetup" / "FirmwareUpgradeController.cc"
    text = path.read_text(encoding="utf-8")

    if "#include <QtCore/QSet>" not in text:
        text = replace_once(
            text,
            "#include <QtCore/QJsonArray>\n",
            "#include <QtCore/QJsonArray>\n#include <QtCore/QSet>\n",
            "QSet include for firmware device dedupe",
        )

    old = '''QStringList FirmwareUpgradeController::availableBoardsName(void)
{
    QGCSerialPortInfo::BoardType_t boardType;
    QString boardName;
    QStringList names;

    auto ports = QGCSerialPortInfo::availablePorts();
    for (const auto& info : ports) {
        if(info.canFlash()) {
            info.getBoardInfo(boardType, boardName);
            names.append(boardName);
        }
    }

    return names;
}
'''
    new = '''QStringList FirmwareUpgradeController::availableBoardsName(void)
{
    QGCSerialPortInfo::BoardType_t boardType;
    QString boardName;
    QStringList names;
    QSet<QString> seenPhysicalDevices;

    const auto ports = QGCSerialPortInfo::availablePorts();
    for (const auto& info : ports) {
        if (!info.canFlash()) {
            continue;
        }

        info.getBoardInfo(boardType, boardName);

        // Windows can expose a Pixhawk 6C/Holybro composite USB device as
        // multiple COM interfaces. When those interfaces share a real USB
        // serial number they are one physical flight controller, not two.
        // Never deduplicate ports with an empty serial number: two separate
        // boards may legitimately have the same VID/PID and display name.
        const QString usbSerial = info.serialNumber().trimmed();
        if (!usbSerial.isEmpty()) {
            const QString physicalDeviceKey = QStringLiteral("%1:%2:%3")
                                                  .arg(info.vendorIdentifier())
                                                  .arg(info.productIdentifier())
                                                  .arg(usbSerial);
            if (seenPhysicalDevices.contains(physicalDeviceKey)) {
                qCDebug(FirmwareUpgradeLog)
                    << "Ignoring duplicate flashable USB interface"
                    << "port" << info.portName()
                    << "systemLocation" << info.systemLocation()
                    << "serialNumber" << usbSerial
                    << "boardName" << boardName;
                continue;
            }
            seenPhysicalDevices.insert(physicalDeviceKey);
        }

        qCDebug(FirmwareUpgradeLog)
            << "Detected flashable physical device"
            << "port" << info.portName()
            << "systemLocation" << info.systemLocation()
            << "serialNumber" << usbSerial
            << "boardName" << boardName;

        names.append(boardName);
    }

    return names;
}
'''
    text = replace_once(text, old, new, "Pixhawk composite USB firmware dedupe")
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
            + "    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle\n"
            + "    property real messagePanelWidth: ScreenTools.defaultFontPixelWidth * 50\n"
            + "    property real messagePanelMinHeight: 0\n"
        )
        text = replace_once(text, marker, replacement, "MAVLink Status reusable properties")

    # The stock component depends on an outer _activeVehicle property. Make it
    # self-contained so it can be reused from the service-mode MAVLink page.
    text = text.replace("_activeVehicle", "activeVehicle")

    old_completed = '''    Component.onCompleted: {
        messageText.text = formatMessage(activeVehicle.formattedMessages)
        if (activeVehicle) {
            activeVehicle.resetAllMessages()
        }
    }
'''
    new_completed = '''    function refreshMessages() {
        messageText.text = activeVehicle ? formatMessage(activeVehicle.formattedMessages) : ""
    }

    Component.onCompleted: {
        refreshMessages()
        if (activeVehicle) {
            activeVehicle.resetAllMessages()
        }
    }
'''
    text = replace_once(text, old_completed, new_completed, "MAVLink Status refresh API")

    # Guard clear action when no vehicle is present.
    text = text.replace(
        "                activeVehicle.clearMessages()\n                mainWindow.closeIndicatorDrawer()\n",
        "                if (activeVehicle) {\n                    activeVehicle.clearMessages()\n                    refreshMessages()\n                }\n                mainWindow.closeIndicatorDrawer()\n",
    )

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

    # Open the status as a dedicated centered modal rather than attached to the
    # toolbar indicator. keepOpen=true, centerOnWindow=true.
    text = replace_once(
        text,
        "        mainWindow.showIndicatorDrawer(overallStatusComponent, control, true)\n",
        "        mainWindow.showIndicatorDrawer(overallStatusComponent, null, true, true)\n",
        "centered MAVLink Status invocation",
    )

    old_component = '''    Component {
        id: overallStatusIndicatorPage

        ToolIndicatorPage {
            showExpand:         _activeVehicle.mainStatusIndicatorContentItem ? true : false
            waitForParameters:  _activeVehicle.mainStatusIndicatorContentItem ? true : false
            contentComponent:   mainStatusContentComponent
            expandedComponent:  mainStatusExpandedComponent
        }
    }
'''
    new_component = '''    Component {
        id: overallStatusIndicatorPage

        Rectangle {
            width:  mainWindow.contentItem.width * 0.65
            height: mainWindow.contentItem.height * 0.65
            color:  mavStatusPal.window
            radius: ScreenTools.defaultBorderRadius
            border.width: 2
            border.color: mavStatusPal.buttonBorder

            property bool _showExpand: false

            QGCPalette {
                id: mavStatusPal
                colorGroupEnabled: true
            }

            Component.onCompleted:   mainWindow.suppressCriticalVehicleMessages = true
            Component.onDestruction: mainWindow.suppressCriticalVehicleMessages = false

            Settings {
                id: mavlinkStatusSettings
                category: "MAVLinkStatus"

                property bool autoCloseEnabled: true
                property int autoCloseSeconds: 60
            }

            Timer {
                id: mavlinkStatusCloseTimer
                interval: Math.max(5, mavlinkStatusSettings.autoCloseSeconds) * 1000
                repeat: false
                running: mavlinkStatusSettings.autoCloseEnabled
                onTriggered: mainWindow.closeIndicatorDrawer()
            }

            Timer {
                interval: 5000
                repeat: true
                running: true
                onTriggered: vehicleMessageList.refreshMessages()
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth
                spacing: ScreenTools.defaultFontPixelHeight * 0.5

                RowLayout {
                    Layout.fillWidth: true
                    spacing: ScreenTools.defaultFontPixelWidth

                    QGCLabel {
                        text: "MAVLink Status"
                        font.bold: true
                        font.pointSize: ScreenTools.largeFontPointSize
                    }

                    Item { Layout.fillWidth: true }

                    QGCLabel {
                        text: "Оновлення кожні 5 с"
                    }

                    QGCComboBox {
                        id: timeoutCombo
                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 14
                        property var timeoutValues: [0, 15, 30, 60, 120, 300, 600]
                        model: [
                            "Автозакриття вимкн.",
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

                    QGCButton {
                        text: "Закрити"
                        onClicked: mainWindow.closeIndicatorDrawer()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: mavStatusPal.windowShadeDark
                    radius: ScreenTools.defaultBorderRadius
                    border.width: 2
                    border.color: mavStatusPal.buttonBorder
                    clip: true

                    ScrollView {
                        id: mavlinkStatusScroll
                        anchors.fill: parent
                        anchors.margins: ScreenTools.defaultFontPixelWidth * 0.6
                        clip: true
                        ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        VehicleMessageList {
                            id: vehicleMessageList
                            width: mavlinkStatusScroll.availableWidth
                            activeVehicle: control._activeVehicle
                            messageFontPointSize: ScreenTools.defaultFontPointSize * 1.60
                            messagePanelWidth: mavlinkStatusScroll.availableWidth
                            messagePanelMinHeight: mavlinkStatusScroll.availableHeight
                        }
                    }
                }
            }
        }
    }
'''
    text = replace_once(text, old_component, new_component, "dedicated centered MAVLink Status panel")

    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_contrast_controls(root: Path) -> list[Path]:
    changed: list[Path] = []

    # Search/text fields: always-visible yellow border, thicker active-focus
    # border, and darker fill for stronger separation from the background.
    text_field = root / "src" / "QmlControls" / "QGCTextField.qml"
    text = text_field.read_text(encoding="utf-8")
    old_text_field = (
        "        border.width:   control.validationError ? 2 : (qgcPal.globalTheme === QGCPalette.Light ? 1 : 0)\n"
        "        border.color:   control.validationError ? qgcPal.colorRed : qgcPal.buttonBorder\n"
    )
    if old_text_field not in text:
        raise FeaturePatchError("Could not apply high contrast QGCTextField: border anchors missing")
    text = text.replace(
        old_text_field,
        "        border.width:   control.validationError ? 3 : (control.activeFocus ? 3 : 2)\n"
        "        border.color:   control.validationError ? qgcPal.colorRed : (control.activeFocus ? qgcPal.buttonHighlight : qgcPal.buttonBorder)\n",
        1,
    )
    text = text.replace(
        "        color:          qgcPal.textField\n",
        "        color:          control.activeFocus ? qgcPal.windowShadeDark : qgcPal.textField\n",
        1,
    )
    text_field.write_text(text, encoding="utf-8", newline="\n")
    changed.append(text_field)

    # Apply a consistent dark/yellow high-contrast style to native Qt
    # ProgressBar controls which do not already define their own background.
    progress_index = 0
    for path in root.rglob("*.qml"):
        if any(part in {".git", "build", "custom"} for part in path.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if "ProgressBar {" not in source:
            continue

        offset = 0
        updated = source
        touched = False
        while True:
            pos = updated.find("ProgressBar {", offset)
            if pos < 0:
                break
            open_brace = updated.find("{", pos)
            depth = 1
            i = open_brace + 1
            in_string = False
            quote = ""
            escape = False
            while i < len(updated) and depth:
                ch = updated[i]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == quote:
                        in_string = False
                else:
                    if ch in {'"', "'"}:
                        in_string = True
                        quote = ch
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                i += 1
            if depth != 0:
                raise FeaturePatchError(f"Unbalanced ProgressBar block in {path}")

            block_end = i
            block = updated[pos:block_end]
            if "QGC UA contrast progress style" in block or "background:" in block or "contentItem:" in block:
                offset = block_end
                continue

            id_match = re.search(r"\bid\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", block)
            if id_match:
                control_id = id_match.group(1)
                id_line = ""
            else:
                progress_index += 1
                control_id = f"qgcContrastProgressBar{progress_index}"
                id_line = f"\n        id: {control_id}"

            style = f'''{id_line}
        // QGC UA contrast progress style
        background: Rectangle {{
            implicitWidth: 200
            implicitHeight: 14
            radius: 7
            color: "#101010"
            border.color: "#FFD400"
            border.width: 2
        }}
        contentItem: Item {{
            implicitWidth: 200
            implicitHeight: 14
            Rectangle {{
                width: {control_id}.visualPosition * parent.width
                height: parent.height
                radius: 7
                color: {control_id}.enabled ? "#FFD400" : "#6B5E00"
            }}
        }}
'''
            insert_at = open_brace + 1
            updated = updated[:insert_at] + style + updated[insert_at:]
            touched = True
            offset = block_end + len(style)

        if touched:
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append(path)

    return changed


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


def patch_service_mode_menu(root: Path) -> Path:
    # The build is pinned to QGC v5.0.8, where MainWindow lives at this exact
    # path. Do not locate it using spacing-sensitive QML id text such as
    # "id: setupButton": upstream aligns ids with variable whitespace.
    path = root / "src" / "UI" / "MainWindow.qml"
    if not path.is_file():
        raise FeaturePatchError(f"MainWindow.qml not found at pinned path: {path}")

    text = path.read_text(encoding="utf-8")
    for marker in ("function showVehicleConfig()", "setupButton", "settingsButton"):
        if marker not in text:
            raise FeaturePatchError(
                f"MainWindow.qml service-mode anchor missing: {marker}"
            )

    vehicle_function = '''    function showVehicleConfig() {
        showTool(qsTr("Vehicle Configuration"), "qrc:/qml/QGroundControl/VehicleSetup/SetupView.qml", "/qmlimages/Gears.svg")
    }
'''
    vehicle_with_service = vehicle_function + '''
    function showServiceMode() {
        showTool(qsTr("Спрощ. режим для сервісу"), "qrc:/qml/QGroundControl/Custom/ServiceMode.qml", "/qmlimages/Gears.svg")
    }
'''
    text = replace_once(text, vehicle_function, vehicle_with_service, "service mode show function")

    setup_block = '''                        SubMenuButton {
                            id:                 setupButton
                            height:             toolSelectDialog._toolButtonHeight
                            Layout.fillWidth:   true
                            text:               qsTr("Vehicle Configuration")
                            imageResource:      "/qmlimages/Gears.svg"
                            onClicked: {
                                if (mainWindow.allowViewSwitch()) {
                                    mainWindow.closeIndicatorDrawer()
                                    mainWindow.showVehicleConfig()
                                }
                            }
                        }
'''
    service_button = setup_block + '''
                        SubMenuButton {
                            id:                 serviceModeButton
                            height:             toolSelectDialog._toolButtonHeight
                            Layout.fillWidth:   true
                            text:               qsTr("Спрощ. режим для сервісу")
                            imageResource:      "/qmlimages/Gears.svg"
                            onClicked: {
                                if (mainWindow.allowViewSwitch()) {
                                    mainWindow.closeIndicatorDrawer()
                                    mainWindow.showServiceMode()
                                }
                            }
                        }
'''
    text = replace_once(text, setup_block, service_button, "service mode menu button")
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_splash(root: Path) -> Path:
    path = root / "src" / "main.cc"
    text = path.read_text(encoding="utf-8")

    ui_boot_var_marker = "    bool simpleBootTest = false;\n"
    ui_boot_var_replacement = """    bool simpleBootTest = false;
    bool uiBootTest = false;
"""
    text = replace_once(text, ui_boot_var_marker, ui_boot_var_replacement, "full UI boot test flag")

    ui_boot_option_marker = '        { "--simple-boot-test",     &simpleBootTest,        nullptr },\n'
    ui_boot_option_replacement = '''        { "--simple-boot-test",     &simpleBootTest,        nullptr },
        { "--ui-boot-test",         &uiBootTest,            nullptr },
'''
    text = replace_once(text, ui_boot_option_marker, ui_boot_option_replacement, "full UI boot test option")

    include_marker = "#include <QtWidgets/QApplication>\n"
    include_block = '''#include <QtWidgets/QApplication>
#include <QtWidgets/QSplashScreen>
#include <QtGui/QFont>
#include <QtGui/QFontDatabase>
#include <QtGui/QPainter>
#include <QtGui/QScreen>
#include <QtCore/QElapsedTimer>
#include <QtCore/QEventLoop>
#include <QtCore/QThread>
#include <QtQuick/QQuickWindow>
'''
    text = replace_once(text, include_marker, include_block, "portable splash includes")

    app_marker = "    QGCApplication app(argc, argv, runUnitTests, simpleBootTest);\n"
    splash_block = '''    QGCApplication app(argc, argv, runUnitTests, simpleBootTest);

    QSplashScreen *portableSplash = nullptr;
    QElapsedTimer portableSplashTimer;
    if (!simpleBootTest && !runUnitTests) {
        (void) QFontDatabase::addApplicationFont(":/fonts/play-regular");
        (void) QFontDatabase::addApplicationFont(":/fonts/play-bold");
        QApplication::setFont(QFont(QStringLiteral("Play")));

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

    // QGC_STARTUP_WINDOW_RECOVERY
    // Portable builds can inherit stale/off-screen window geometry across revisions.
    // Make sure the main QML window is visible and intersects at least one screen.
    if (!runUnitTests && !simpleBootTest) {
        if (QQuickWindow *mainWindow = app.mainRootWindow()) {
            bool intersectsAvailableScreen = false;
            const QRect windowRect(mainWindow->x(), mainWindow->y(), mainWindow->width(), mainWindow->height());
            for (QScreen *screen : QGuiApplication::screens()) {
                if (screen && screen->availableGeometry().intersects(windowRect)) {
                    intersectsAvailableScreen = true;
                    break;
                }
            }

            if (!intersectsAvailableScreen) {
                if (QScreen *screen = QGuiApplication::primaryScreen()) {
                    const QRect available = screen->availableGeometry();
                    const int safeWidth = qMin(qMax(mainWindow->width(), 960), available.width());
                    const int safeHeight = qMin(qMax(mainWindow->height(), 640), available.height());
                    mainWindow->resize(safeWidth, safeHeight);
                    mainWindow->setPosition(
                        available.x() + (available.width() - safeWidth) / 2,
                        available.y() + (available.height() - safeHeight) / 2);
                }
            }

            if (!mainWindow->isVisible()) {
                mainWindow->show();
            }
            if (mainWindow->visibility() == QWindow::Minimized) {
                mainWindow->showNormal();
            }
            mainWindow->raise();
            mainWindow->requestActivate();
            app.processEvents(QEventLoop::AllEvents, 50);
            qInfo() << "QGC_STARTUP_WINDOW_RECOVERY"
                    << "visible=" << mainWindow->isVisible()
                    << "geometry=" << mainWindow->geometry();
        } else {
            qCritical() << "QGC_STARTUP_WINDOW_RECOVERY: mainRootWindow is null";
        }
    }

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

    if (uiBootTest) {
        QQuickWindow *window = app.mainRootWindow();
        if (!window) {
            qCritical() << "QGC_UI_BOOT_FAIL: mainRootWindow is null";
            app.shutdown();
            return 91;
        }

        QElapsedTimer uiBootTimer;
        uiBootTimer.start();
        while (uiBootTimer.elapsed() < 1500) {
            app.processEvents(QEventLoop::AllEvents, 20);
            QThread::msleep(10);
        }

        if (!window->isVisible()) {
            qCritical() << "QGC_UI_BOOT_FAIL: main window exists but is not visible";
            app.shutdown();
            return 92;
        }

        qInfo() << "QGC_UI_BOOT_OK";
        app.shutdown();
        return 0;
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
        "VehicleMessageList.qml": "function refreshMessages()",
        "MainStatusIndicator.qml": "messageFontPointSize: ScreenTools.defaultFontPointSize * 1.60",
        "QGCTextField.qml": "control.activeFocus ? 3 : 2",
        "MainWindow.qml": "centerOnWindow",
        "FirmwareUpgradeController.cc": "Ignoring duplicate flashable USB interface",
        "main.cc": "QGC_STARTUP_WINDOW_RECOVERY",
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
        changed.append(patch_firmware_upgrade_dedupe(root))
        changed.extend(patch_play_font(root))
        changed.append(patch_vehicle_message_list(root))
        changed.append(patch_main_status(root))
        changed.extend(patch_contrast_controls(root))
        changed.append(patch_centered_tool_menu(root))
        changed.append(patch_service_mode_menu(root))
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
