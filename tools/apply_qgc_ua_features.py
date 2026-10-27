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

    if "QGC UA standard indicator scrollbar" not in text:
        scroll_marker = "            contentHeight:  indicatorDrawerLoader.height\n"
        scroll_replacement = (
            scroll_marker
            + "            // QGC UA standard indicator scrollbar\n"
            + "            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }\n"
        )
        text = replace_once(text, scroll_marker, scroll_replacement, "standard indicator scrollbar")

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
        criticalVehicleMessagePopup.close()
        criticalVehicleMessagePopup.additionalCriticalMessagesReceived = false
        showTool(qsTr("ARGN Service Mode"), "qrc:/qml/QGroundControl/Custom/ServiceMode.qml", "/qmlimages/Gears.svg")
    }
'''
    text = replace_once(text, vehicle_function, vehicle_with_service, "service mode show function")

    critical_message_function = '''    function showCriticalVehicleMessage(message) {
        closeIndicatorDrawer()
'''
    critical_message_with_service_guard = '''    function serviceModeVisible() {
        return toolDrawer.visible &&
               toolDrawer.toolSource.toString() === "qrc:/qml/QGroundControl/Custom/ServiceMode.qml"
    }

    function showCriticalVehicleMessage(message) {
        if (serviceModeVisible()) {
            criticalVehicleMessagePopup.close()
            criticalVehicleMessagePopup.additionalCriticalMessagesReceived = false
            return
        }
        closeIndicatorDrawer()
'''
    text = replace_once(
        text,
        critical_message_function,
        critical_message_with_service_guard,
        "suppress critical vehicle popup in service mode",
    )

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
                            text:               qsTr("ARGN Service Mode")
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


def patch_quick_vehicle_toolbar(root: Path) -> list[Path]:
    main_window = root / "src" / "UI" / "MainWindow.qml"
    setup_view = root / "src" / "Vehicle" / "VehicleSetup" / "SetupView.qml"
    toolbar = root / "src" / "QmlControls" / "FlyViewToolBar.qml"

    # MainWindow helpers for direct setup navigation and a real link reconnect.
    text = main_window.read_text(encoding="utf-8")
    parameter_helper = '''    function showVehicleConfigParametersPage() {
        showVehicleConfig()
        toolDrawerLoader.item.showParametersPanel()
    }
'''
    helper_block = parameter_helper + '''
    function showVehicleConfigSummaryPage() {
        showVehicleConfig()
        toolDrawerLoader.item.showSummaryPanel()
    }

    function showVehicleConfigFirmwarePage() {
        showVehicleConfig()
        toolDrawerLoader.item.showFirmwarePanel()
    }

    function showVehicleComponentConfigPage(vehicleComponent) {
        showVehicleConfig()
        toolDrawerLoader.item.showVehicleComponentPanel(vehicleComponent)
    }

    function rebootConnectedVehicle() {
        const vehicle = QGroundControl.multiVehicleManager.activeVehicle
        if (vehicle && !vehicle.armed) {
            vehicle.rebootVehicle()
        }
    }

    function restartGroundControlApplication() {
        QGroundControl.restartApplication()
    }
'''
    text = replace_once(text, parameter_helper, helper_block, "vehicle setup quick-navigation helpers")
    main_window.write_text(text, encoding="utf-8", newline="\n")

    # Expose Firmware as a normal callable page, matching the existing Parameters helper.
    text = setup_view.read_text(encoding="utf-8")
    parameters_fn = '''    function showParametersPanel() {
        if (mainWindow.allowViewSwitch()) {
            parametersButton.checked = true
            panelLoader.setSource("qrc:/qml/QGroundControl/VehicleSetup/SetupParameterEditor.qml")
        }
    }
'''
    firmware_fn = parameters_fn + '''
    function showFirmwarePanel() {
        if (mainWindow.allowViewSwitch()) {
            firmwareButton.checked = true
            panelLoader.setSource("qrc:/qml/QGroundControl/VehicleSetup/FirmwareUpgrade.qml")
        }
    }
'''
    text = replace_once(text, parameters_fn, firmware_fn, "Vehicle Setup firmware helper")
    setup_view.write_text(text, encoding="utf-8", newline="\n")

    # Put Vehicle Setup shortcuts ahead of the normal flight indicators. The
    # existing QGCFlickable handles narrow windows automatically.
    text = toolbar.read_text(encoding="utf-8")
    stock_indicators = "        FlyViewToolBarIndicators { id: toolIndicators }\n"
    quick_indicators = '''        Row {
            id: quickVehicleSetupRow
            height: toolsFlickable.height
            spacing: ScreenTools.defaultFontPixelWidth * 0.25

            property var setupComponents: _activeVehicle && _activeVehicle.autopilotPlugin
                                                ? _activeVehicle.autopilotPlugin.vehicleComponents
                                                : []

            QGCToolBarButton {
                height: parent.height
                visible: !!_activeVehicle
                icon.source: "/qmlimages/VehicleSummaryIcon.png"
                onClicked: mainWindow.showVehicleConfigSummaryPage()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Summary")
            }

            Repeater {
                model: quickVehicleSetupRow.setupComponents
                QGCToolBarButton {
                    height: quickVehicleSetupRow.height
                    visible: modelData && modelData.setupSource.toString() !== ""
                    icon.source: modelData ? modelData.iconResource : ""
                    onClicked: mainWindow.showVehicleComponentConfigPage(modelData)
                    ToolTip.visible: hovered
                    ToolTip.text: modelData ? modelData.name : ""
                }
            }

            QGCToolBarButton {
                height: parent.height
                icon.source: "/qmlimages/Gears.svg"
                onClicked: mainWindow.showServiceMode()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("ARGN Service Mode")
            }

            QGCToolBarButton {
                height: parent.height
                visible: QGroundControl.multiVehicleManager.parameterReadyVehicleAvailable &&
                         QGroundControl.corePlugin.showAdvancedUI
                icon.source: "/qmlimages/subMenuButtonImage.png"
                onClicked: mainWindow.showVehicleConfigParametersPage()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Parameters")
            }

            QGCToolBarButton {
                height: parent.height
                visible: !ScreenTools.isMobile && QGroundControl.corePlugin.options.showFirmwareUpgrade
                icon.source: "/qmlimages/FirmwareUpgradeIcon.png"
                onClicked: mainWindow.showVehicleConfigFirmwarePage()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Firmware")
            }

            QGCToolBarButton {
                height: parent.height
                enabled: !!_activeVehicle
                icon.source: "/InstrumentValueIcons/reload.svg"
                onClicked: mainWindow.rebootConnectedVehicle()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Reboot Vehicle")
            }

            QGCToolBarButton {
                height: parent.height
                icon.source: "/qmlimages/Gears.svg"
                onClicked: mainWindow.restartGroundControlApplication()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Restart QGroundControl")
            }

            FlyViewToolBarIndicators {
                height: quickVehicleSetupRow.height
            }
        }
'''
    text = replace_once(text, stock_indicators, quick_indicators, "Vehicle Setup quick toolbar")
    # Keep the existing contentWidth binding valid.
    text = text.replace("contentWidth:           toolIndicators.width", "contentWidth:           quickVehicleSetupRow.width")
    toolbar.write_text(text, encoding="utf-8", newline="\n")

    return [main_window, setup_view, toolbar]



def patch_service_entry_tune(root: Path) -> list[Path]:
    """One short MAVLink PLAY_TUNE message when entering service mode."""
    header = root / "src" / "Vehicle" / "Vehicle.h"
    source = root / "src" / "Vehicle" / "Vehicle.cc"
    h = header.read_text(encoding="utf-8")
    h = replace_once(h, "    Q_INVOKABLE void rebootVehicle();",
                     "    Q_INVOKABLE void rebootVehicle();\n    Q_INVOKABLE void playServiceEntryTune();",
                     "service entry tune API")
    header.write_text(h, encoding="utf-8", newline="\n")
    s = source.read_text(encoding="utf-8")
    marker = "void Vehicle::rebootVehicle()\n{"
    method = """void Vehicle::playServiceEntryTune()
{
    // MAVLink PLAY_TUNE uses the on-board buzzer; unsupported boards ignore it.
    const SharedLinkInterfacePtr link = vehicleLinkManager()->primaryLink().lock();
    if (!link || armed()) {
        return;
    }
    mavlink_message_t message{};
    // First 10 notes of supplied MIDI, preserving 230 BPM and dotted note length.
    const char tune[] = "MFT230O4L8DD>D4<A4.G#4G4F4DFG";
    mavlink_msg_play_tune_pack(
        static_cast<uint8_t>(MAVLinkProtocol::instance()->getSystemId()),
        static_cast<uint8_t>(MAVLinkProtocol::getComponentId()),
        &message,
        static_cast<uint8_t>(_id),
        static_cast<uint8_t>(_defaultComponentId),
        tune, "");
    sendMessageOnLinkThreadSafe(link.get(), message);
}

"""
    s = replace_once(s, marker, method + marker, "vehicle MAVLink play tune")
    source.write_text(s, encoding="utf-8", newline="\n")
    return [header, source]


def patch_buzzer_speech(root: Path) -> list[Path]:
    """Play short text-derived note patterns via the existing MAVLink buzzer link."""
    header = root / "src" / "Vehicle" / "Vehicle.h"
    source = root / "src" / "Vehicle" / "Vehicle.cc"
    h = header.read_text(encoding="utf-8")
    h = replace_once(h,
        "    Q_INVOKABLE void playServiceEntryTune();",
        """    Q_INVOKABLE void playServiceEntryTune();
    Q_INVOKABLE void playBuzzerSpeech(const QString &text, int speed, int pitch);
    Q_INVOKABLE void stopBuzzerSpeech();""", "buzzer speech API")
    h = replace_once(h, "private:\n",
        """private:
    QTimer* _buzzerSpeechTimer = nullptr;
    QString _buzzerSpeechText;
    int _buzzerSpeechIndex = 0;
    int _buzzerSpeechSpeed = 5;
    int _buzzerSpeechPitch = 4;
""", "buzzer speech state")
    header.write_text(h, encoding="utf-8", newline="\n")
    s = source.read_text(encoding="utf-8")
    anchor = "void Vehicle::playServiceEntryTune()\n{"
    impl = """void Vehicle::stopBuzzerSpeech()
{
    if (_buzzerSpeechTimer) _buzzerSpeechTimer->stop();
    _buzzerSpeechText.clear();
    _buzzerSpeechIndex = 0;
    const auto link = vehicleLinkManager()->primaryLink().lock();
    if (!link) return;
    mavlink_message_t message{};
    mavlink_msg_play_tune_pack(
        static_cast<uint8_t>(MAVLinkProtocol::instance()->getSystemId()),
        static_cast<uint8_t>(MAVLinkProtocol::getComponentId()),
        &message, static_cast<uint8_t>(_id),
        static_cast<uint8_t>(_defaultComponentId), "", "");
    sendMessageOnLinkThreadSafe(link.get(), message);
}

void Vehicle::playBuzzerSpeech(const QString &text, int speed, int pitch)
{
    stopBuzzerSpeech();
    if (armed() || !vehicleLinkManager()->primaryLink().lock()) return;
    _buzzerSpeechText = text.left(240);
    _buzzerSpeechSpeed = qBound(1, speed, 10);
    _buzzerSpeechPitch = qBound(2, pitch, 6);
    if (_buzzerSpeechText.trimmed().isEmpty()) return;
    if (!_buzzerSpeechTimer) {
        _buzzerSpeechTimer = new QTimer(this);
        connect(_buzzerSpeechTimer, &QTimer::timeout, this, [this]() {
            if (armed() || !vehicleLinkManager()->primaryLink().lock() ||
                _buzzerSpeechIndex >= _buzzerSpeechText.size()) {
                stopBuzzerSpeech();
                return;
            }
            const QChar ch = _buzzerSpeechText.at(_buzzerSpeechIndex++).toLower();
            // Deterministic phoneme-like tones, not speech samples.
            if (ch.isSpace()) return;
            const QString scale = QStringLiteral("CDEFGAB");
            const uint code = ch.unicode();
            const QChar note = scale.at(code % scale.size());
            const int octave = qBound(2, _buzzerSpeechPitch + int((code / 7) % 3) - 1, 7);
            const int length = QStringLiteral("аеєиіїоуюяaeiouy").contains(ch) ? 8 : 16;
            const QByteArray tune = QStringLiteral("MFT240O%1L%2%3")
                .arg(octave).arg(length).arg(note).toLatin1();
            mavlink_message_t message{};
            mavlink_msg_play_tune_pack(
                static_cast<uint8_t>(MAVLinkProtocol::instance()->getSystemId()),
                static_cast<uint8_t>(MAVLinkProtocol::getComponentId()),
                &message, static_cast<uint8_t>(_id),
                static_cast<uint8_t>(_defaultComponentId), tune.constData(), "");
            const auto link = vehicleLinkManager()->primaryLink().lock();
            if (link) sendMessageOnLinkThreadSafe(link.get(), message);
        });
    }
    _buzzerSpeechIndex = 0;
    _buzzerSpeechTimer->start(260 - _buzzerSpeechSpeed * 20);
}

"""
    s = replace_once(s, anchor, impl + anchor, "buzzer speech implementation")
    source.write_text(s, encoding="utf-8", newline="\n")
    return [header, source]


def patch_service_midi_player(root: Path) -> list[Path]:
    """MIDI-derived buzzer playback: seek, pause, resume and stop."""
    header = root / "src" / "Vehicle" / "Vehicle.h"
    source = root / "src" / "Vehicle" / "Vehicle.cc"
    h = header.read_text(encoding="utf-8")
    h = replace_once(h, "    Q_INVOKABLE void playServiceEntryTune();",
        """    Q_INVOKABLE void playServiceEntryTune();
    Q_INVOKABLE void playServiceMidi(double seconds = 0);
    Q_INVOKABLE void seekServiceMidi(double seconds);
    Q_INVOKABLE void pauseServiceMidi();
    Q_INVOKABLE void stopServiceMidi();
    Q_INVOKABLE double serviceMidiPositionSeconds() const;
    Q_INVOKABLE bool loadServiceMidi(const QUrl &path);
    Q_INVOKABLE double serviceMidiDurationSeconds() const;""",
        "service MIDI API")
    anchor = "    Q_INVOKABLE void playServiceEntryTune();"
    # Keep state attached to the vehicle, so a disconnected/removed vehicle
    # destroys its playback timer automatically.
    state_anchor = "    Q_INVOKABLE void playServiceEntryTune();"
    # Inject private state immediately after the existing class-private marker,
    # not after public methods; QTimer objects should never be copied.
    private_marker = "private:\n"
    h = replace_once(h, private_marker,
        """private:
    QTimer* _serviceMidiTimer = nullptr;
    QElapsedTimer _serviceMidiClock;
    qint64 _serviceMidiStartMs = 0;
    qint64 _serviceMidiPausedMs = 0;
    int _serviceMidiNextIndex = 0;
    bool _serviceMidiPlaying = false;
    QByteArray _serviceMidiCustomScore;
    double _serviceMidiDurationMs = 158608.7;
""", "service MIDI fields")
    header.write_text(h, encoding="utf-8", newline="\n")

    s = source.read_text(encoding="utf-8")
    s = replace_once(s, '#include "Vehicle.h"', '#include "Vehicle.h"\n#include "ServiceMidiParser.h"', "MIDI parser include")
    anchor = "void Vehicle::playServiceEntryTune()\n{"
    implementation = """namespace {
struct ServiceMidiNote { quint16 tick; quint16 duration; quint8 pitch; };
const QByteArray &serviceMidiScore() {
    static const QByteArray score = qUncompress(QByteArray::fromBase64(
        QByteArrayLiteral("__SCORE__")));
    return score;
}
constexpr double serviceMidiMsPerTick = 260870.0 / 96000.0; // 230 BPM, 96 PPQN
constexpr double serviceMidiTotalMs = 158608.7;
static bool sendServiceMidiTune(Vehicle *vehicle, const QString &tune) {
    const auto link = vehicle->vehicleLinkManager()->primaryLink().lock();
    if (!link) return false;
    mavlink_message_t message{};
    const QByteArray bytes = tune.toLatin1();
    mavlink_msg_play_tune_pack(
        static_cast<uint8_t>(MAVLinkProtocol::instance()->getSystemId()),
        static_cast<uint8_t>(MAVLinkProtocol::getComponentId()),
        &message,
        static_cast<uint8_t>(vehicle->id()),
        static_cast<uint8_t>(vehicle->defaultComponentId()),
        bytes.constData(), "");
    return vehicle->sendMessageOnLinkThreadSafe(link.get(), message);
}
}

double Vehicle::serviceMidiDurationSeconds() const
{
    return _serviceMidiDurationMs / 1000.0;
}

bool Vehicle::loadServiceMidi(const QUrl &path)
{
    QByteArray loaded;
    double length = 0.0;
    if (!ServiceMidiParser::parse(path, loaded, length)) return false;
    stopServiceMidi();
    _serviceMidiCustomScore = loaded;
    _serviceMidiDurationMs = length * 1000.0;
    return true;
}

double Vehicle::serviceMidiPositionSeconds() const
{
    qint64 ms = _serviceMidiPausedMs;
    if (_serviceMidiPlaying) ms = _serviceMidiStartMs + _serviceMidiClock.elapsed();
    return qBound(0.0, ms / 1000.0, _serviceMidiDurationMs / 1000.0);
}

void Vehicle::seekServiceMidi(double seconds)
{
    pauseServiceMidi();
    _serviceMidiPausedMs = qBound(qint64(0), qint64(seconds * 1000.0), qint64(_serviceMidiDurationMs));
}

void Vehicle::pauseServiceMidi()
{
    if (_serviceMidiPlaying) {
        _serviceMidiPausedMs = qint64(serviceMidiPositionSeconds() * 1000.0);
        _serviceMidiPlaying = false;
        if (_serviceMidiTimer) _serviceMidiTimer->stop();
        sendServiceMidiTune(this, QString()); // stop current buzzer sound
    }
}

void Vehicle::stopServiceMidi()
{
    pauseServiceMidi();
    _serviceMidiPausedMs = 0;
    _serviceMidiNextIndex = 0;
}

void Vehicle::playServiceMidi(double seconds)
{
    if (armed() || !vehicleLinkManager()->primaryLink().lock()) return;
    pauseServiceMidi();
    _serviceMidiStartMs = qBound(qint64(0), qint64(seconds * 1000.0), qint64(_serviceMidiDurationMs));
    _serviceMidiPausedMs = _serviceMidiStartMs;
    _serviceMidiClock.restart();
    _serviceMidiNextIndex = 0;
    const auto &score = _serviceMidiCustomScore.isEmpty() ? serviceMidiScore() : _serviceMidiCustomScore;
    const auto *raw = reinterpret_cast<const unsigned char *>(score.constData());
    const int count = score.size() / 5;
    while (_serviceMidiNextIndex < count) {
        const int off = _serviceMidiNextIndex * 5;
        const int tick = int(raw[off]) | (int(raw[off+1]) << 8);
        if (tick * serviceMidiMsPerTick >= _serviceMidiStartMs) break;
        ++_serviceMidiNextIndex;
    }
    if (!_serviceMidiTimer) {
        _serviceMidiTimer = new QTimer(this);
        _serviceMidiTimer->setInterval(15);
        connect(_serviceMidiTimer, &QTimer::timeout, this, [this]() {
            if (armed() || !vehicleLinkManager()->primaryLink().lock()) {
                stopServiceMidi();
                return;
            }
            const auto &score = _serviceMidiCustomScore.isEmpty() ? serviceMidiScore() : _serviceMidiCustomScore;
            const auto *raw = reinterpret_cast<const unsigned char *>(score.constData());
            const int count = score.size() / 5;
            const qint64 elapsed = _serviceMidiStartMs + _serviceMidiClock.elapsed();
            while (_serviceMidiNextIndex < count) {
                const int off = _serviceMidiNextIndex * 5;
                const int tick = int(raw[off]) | (int(raw[off+1]) << 8);
                if (tick * serviceMidiMsPerTick > elapsed) break;
                const int duration = int(raw[off+2]) | (int(raw[off+3]) << 8);
                const int midiNote = raw[off+4];
                const QStringList names = { "C", "C#", "D", "D#", "E", "F",
                                            "F#", "G", "G#", "A", "A#", "B" };
                const int octave = midiNote / 12 - 1;
                const int durationBase = duration >= 120 ? 4 : duration >= 70 ? 4 : duration >= 35 ? 8 : 16;
                const QString dot = duration >= 120 ? "." : "";
                const QString tune = QStringLiteral("MFT230O%1L%2%3%4")
                    .arg(octave).arg(durationBase).arg(names[midiNote % 12]).arg(dot);
                sendServiceMidiTune(this, tune);
                ++_serviceMidiNextIndex;
            }
            if (elapsed >= _serviceMidiDurationMs || _serviceMidiNextIndex >= count) {
                _serviceMidiPlaying = false;
                _serviceMidiPausedMs = qint64(_serviceMidiDurationMs);
                _serviceMidiTimer->stop();
            }
        });
    }
    _serviceMidiPlaying = true;
    _serviceMidiTimer->start();
}

"""
    implementation = implementation.replace("__SCORE__", "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")
    s = replace_once(s, anchor, implementation + anchor, "MIDI sequencer implementation")
    source.write_text(s, encoding="utf-8", newline="\n")
    return [header, source]


def patch_libevents_compat(root: Path) -> Path:
    """Pin libevents to a version compatible with QGC v5.0.8 MAVLink headers."""
    path = root / "src" / "MAVLink" / "LibEvents" / "CMakeLists.txt"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "    GIT_TAG main",
        "    GIT_TAG 9ef591c447fe0386d698bf6fb9a6d27e43988ee4",
        "libevents compatible pinned revision",
    )
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_application_restart(root: Path) -> list[Path]:
    """Expose native relaunch through the existing QGroundControl QML singleton."""
    header = root / "src" / "QmlControls" / "QGroundControlQmlGlobal.h"
    source = root / "src" / "QmlControls" / "QGroundControlQmlGlobal.cc"
    h = header.read_text(encoding="utf-8")
    h = replace_once(
        h,
        "    Q_INVOKABLE void    saveGlobalSetting       (const QString& key, const QString& value);",
        "    Q_INVOKABLE bool restartApplication();\n    Q_INVOKABLE void    saveGlobalSetting       (const QString& key, const QString& value);",
        "QML restart API",
    )
    header.write_text(h, encoding="utf-8", newline="\n")

    s = source.read_text(encoding="utf-8")
    s = replace_once(
        s, '#include "QGCApplication.h"',
        '#include <QtCore/QCoreApplication>\n#include <QtCore/QProcess>\n#include <QtCore/QTimer>\n#include "QGCApplication.h"',
        "restart Qt includes",
    )
    anchor = "void QGroundControlQmlGlobal::saveGlobalSetting (const QString& key, const QString& value)"
    implementation = """bool QGroundControlQmlGlobal::restartApplication()
{
    const QString executable = QCoreApplication::applicationFilePath();
    const QStringList arguments = QCoreApplication::arguments().mid(1);
#ifdef Q_OS_WIN
    // Wait for the previous process to release RunGuard before relaunching.
    // An independent PowerShell helper survives the QGC process shutdown.
    const auto psQuote = [](QString value) {
        value.replace(QChar(0x27), QStringLiteral("''"));
        return QStringLiteral("'") + value + QStringLiteral("'");
    };
    QStringList quotedArguments;
    for (const QString &argument : arguments) {
        quotedArguments << psQuote(argument);
    }
    const QString script = QStringLiteral(
        "Wait-Process -Id %1 -ErrorAction SilentlyContinue; "
        "Start-Sleep -Milliseconds 800; "
        "Start-Process -FilePath %2 -WorkingDirectory %3%4")
        .arg(QCoreApplication::applicationPid())
        .arg(psQuote(executable))
        .arg(psQuote(QCoreApplication::applicationDirPath()))
        .arg(quotedArguments.isEmpty()
             ? QString()
             : QStringLiteral(" -ArgumentList @(") + quotedArguments.join(QStringLiteral(",")) + QStringLiteral(")"));
    const QByteArray scriptUtf16(reinterpret_cast<const char *>(script.utf16()),
                                   static_cast<qsizetype>(script.size()) * sizeof(char16_t));
    const QString encoded = QString::fromLatin1(scriptUtf16.toBase64());
    if (!QProcess::startDetached(QStringLiteral("powershell.exe"),
                                 {QStringLiteral("-NoProfile"), QStringLiteral("-NonInteractive"),
                                  QStringLiteral("-WindowStyle"), QStringLiteral("Hidden"),
                                  QStringLiteral("-EncodedCommand"), encoded},
                                 QCoreApplication::applicationDirPath())) {
        qgcApp()->showAppMessage(tr("Unable to restart QGroundControl."));
        return false;
    }
#else
    if (!QProcess::startDetached(executable, arguments, QCoreApplication::applicationDirPath())) {
        qgcApp()->showAppMessage(tr("Unable to restart QGroundControl."));
        return false;
    }
#endif
    QTimer::singleShot(0, qgcApp(), []() { qgcApp()->quit(); });
    return true;
}

"""
    s = replace_once(s, anchor, implementation + anchor, "native application relaunch")
    source.write_text(s, encoding="utf-8", newline="\n")
    return [header, source]


def patch_service_firmware_page(root: Path) -> Path:
    path = root / "src" / "Vehicle" / "VehicleSetup" / "FirmwareUpgrade.qml"
    text = path.read_text(encoding="utf-8")

    old = '''SetupPage {
    id:             firmwarePage
    pageComponent:  firmwarePageComponent
    pageName:       qsTr("Firmware")
    showAdvanced:   globals.activeVehicle && globals.activeVehicle.apmFirmware
'''
    new = '''SetupPage {
    id:             firmwarePage
    pageComponent:  firmwarePageComponent
    pageName:       qsTr("Firmware")

    // Service Mode already exposes the required maintenance actions directly.
    // Keep the standard Firmware page unchanged elsewhere, but suppress the
    // Advanced options control/popup when the page is embedded there.
    property bool serviceModeEmbedded: false
    showAdvanced:   !serviceModeEmbedded && globals.activeVehicle && globals.activeVehicle.apmFirmware
'''
    text = replace_once(text, old, new, "service-mode Firmware advanced-options suppression")
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def patch_splash(root: Path) -> Path:
    path = root / "src" / "main.cc"
    text = path.read_text(encoding="utf-8")

    include_marker = "#include <QtWidgets/QApplication>\n"
    include_block = '''#include <QtWidgets/QApplication>
#include <QtWidgets/QSplashScreen>
#include <QtGui/QFont>
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
        "VehicleMessageList.qml": "function refreshMessages()",
        "QGCTextField.qml": "control.activeFocus ? 3 : 2",
        "MainWindow.qml": "QGC UA standard indicator scrollbar",
        "FlyViewToolBar.qml": "quickVehicleSetupRow",
        "FirmwareUpgradeController.cc": "Ignoring duplicate flashable USB interface",
        "FirmwareUpgrade.qml": "serviceModeEmbedded",
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
        patch_steps = [
            ("status_utf8", patch_status_utf8),
            ("firmware_upgrade_dedupe", patch_firmware_upgrade_dedupe),
            ("play_font", patch_play_font),
            ("vehicle_message_list", patch_vehicle_message_list),
            ("contrast_controls", patch_contrast_controls),
            ("centered_tool_menu", patch_centered_tool_menu),
            ("service_mode_menu", patch_service_mode_menu),
            ("quick_vehicle_toolbar", patch_quick_vehicle_toolbar),
            ("application_restart", patch_application_restart),
            ("libevents_compat", patch_libevents_compat),
            ("service_entry_tune", patch_service_entry_tune),
            ("service_midi_player", patch_service_midi_player),
            ("buzzer_speech", patch_buzzer_speech),
            ("service_firmware_page", patch_service_firmware_page),
            ("splash", patch_splash),
        ]
        for step_name, step_fn in patch_steps:
            print(f"UA_PATCH_STEP_BEGIN: {step_name}", flush=True)
            result = step_fn(root)
            if isinstance(result, list):
                changed.extend(result)
            else:
                changed.append(result)
            print(f"UA_PATCH_STEP_OK: {step_name}", flush=True)
        print("UA_PATCH_STEP_BEGIN: verify_markers", flush=True)
        verify_markers(changed)
        print("UA_PATCH_STEP_OK: verify_markers", flush=True)
    except (FeaturePatchError, OSError) as exc:
        print(f"QGC UA feature patch failed: {exc}", file=sys.stderr)
        return 1

    for path in changed:
        print(f"ua-feature-patched {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
