import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import QGroundControl
import QGroundControl.Controls
import QGroundControl.Controllers
import QGroundControl.FactControls
import QGroundControl.FactSystem
import QGroundControl.Palette
import QGroundControl.ScreenTools

Item {
    id: root

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle
    property bool safetyMaskAvailable: controller.parameterExists(-1, "BRD_SAFETY_MASK")
    property Fact safetyMaskFact: safetyMaskAvailable
                                  ? controller.getParameterFact(-1, "BRD_SAFETY_MASK", false)
                                  : null
    property int presetRevision: 0
    property string activePreset: ""

    // ArduPilot reports hardware safety through SYS_STATUS motor outputs.
    // MAV_SYS_STATUS_SENSOR_MOTOR_OUTPUTS = 0x8000.
    readonly property int motorOutputsSensorBit: 32768
    // MAV_CMD_DO_SET_SAFETY_SWITCH_STATE = 5300.
    readonly property int setSafetyCommand: 5300
    readonly property bool safetyReleased: activeVehicle
                                           ? ((Number(activeVehicle.sensorsEnabledBits) & motorOutputsSensorBit) !== 0)
                                           : false
    property bool safetyCommandPending: false
    property string safetyCommandMessage: ""
    property int motorPercentValue: 5
    property int motorSecondsValue: 2


    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    FactPanelController {
        id: controller
    }

    function servoParamName(outputIndex) {
        return "SERVO" + outputIndex + "_FUNCTION"
    }

    function servoParamExists(outputIndex) {
        return controller.parameterExists(-1, servoParamName(outputIndex))
    }

    function setServoFunction(outputIndex, functionValue) {
        if (!servoParamExists(outputIndex)) {
            return false
        }
        const fact = controller.getParameterFact(-1, servoParamName(outputIndex), false)
        if (!fact) {
            return false
        }
        fact.rawValue = functionValue
        return true
    }

    function applyServoProfile(maskValue, assignments, presetName) {
        if (!safetyMaskFact) {
            return
        }

        safetyMaskFact.rawValue = maskValue

        // A preset is authoritative: every available channel not explicitly
        // listed below becomes Disabled.
        for (let output = 1; output <= 16; output++) {
            setServoFunction(output, 0)
        }
        for (const output in assignments) {
            setServoFunction(Number(output), assignments[output])
        }

        activePreset = presetName
        presetRevision++
        Qt.callLater(function() { root.presetRevision++ })
    }

    function applyFmuPwmOutAuxProfile() {
        applyServoProfile(
            255,
            { "9": 33, "10": 34, "11": 35, "12": 36, "13": 37, "14": 38, "15": 60 },
            "FMU PWM OUT (AUX)")
    }

    function applyIoPwmOutMainProfile() {
        applyServoProfile(
            65280,
            { "1": 33, "2": 34, "3": 35, "4": 36, "5": 37, "6": 38, "7": 60 },
            "I/O PWM OUT (MAIN)")
    }

    function maskBitEnabled(outputIndex) {
        if (!safetyMaskFact) {
            return false
        }
        const raw = Math.max(0, Math.floor(Number(safetyMaskFact.rawValue)))
        const bit = Math.pow(2, outputIndex - 1)
        return Math.floor(raw / bit) % 2 === 1
    }

    function setMaskBit(outputIndex, enabled) {
        if (!safetyMaskFact) {
            return
        }
        const raw = Math.max(0, Math.floor(Number(safetyMaskFact.rawValue)))
        const bit = Math.pow(2, outputIndex - 1)
        const currentlyEnabled = Math.floor(raw / bit) % 2 === 1
        if (enabled && !currentlyEnabled) {
            safetyMaskFact.rawValue = raw + bit
        } else if (!enabled && currentlyEnabled) {
            safetyMaskFact.rawValue = raw - bit
        }
    }

    function syncSafetySlider() {
        if (!safetyTrack || !safetyHandle) {
            return
        }
        const maxX = Math.max(0, safetyTrack.width - safetyHandle.width)
        safetyHandle.x = safetyReleased ? maxX : 0
    }

    function setHardwareSafetyReleased(released) {
        if (!activeVehicle || !activeVehicle.apmFirmware || safetyCommandPending) {
            syncSafetySlider()
            return
        }
        if (!released) {
            stopMotorTests()
        }
        safetyCommandPending = true
        safetyCommandMessage = released ? "Знімаємо запобіжник…" : "Вмикаємо запобіжник…"
        // Target the autopilot component directly. ArduPilot supports command 5300:
        // param1 0 = SAFE (engaged), 1 = DANGEROUS (released).
        activeVehicle.sendCommand(1, setSafetyCommand, true, released ? 1 : 0)
        safetyCommandTimeout.restart()
    }

    function runMotorTest(motorNumber) {
        if (!activeVehicle || !safetyReleased || !motorSafetyCheck.checked) {
            return
        }
        activeVehicle.motorTest(motorNumber, motorPercentValue, motorSecondsValue, true)
    }

    function stopMotorTests() {
        if (!activeVehicle) {
            return
        }
        for (let motor = 1; motor <= 16; motor++) {
            activeVehicle.motorTest(motor, 0, 1, false)
        }
    }

    Timer {
        id: safetyCommandTimeout
        interval: 3000
        repeat: false
        onTriggered: {
            root.safetyCommandPending = false
            root.safetyCommandMessage = ""
            root.syncSafetySlider()
        }
    }

    Timer {
        id: safetyStatusSync
        interval: 350
        repeat: false
        onTriggered: root.syncSafetySlider()
    }

    Connections {
        target: root.activeVehicle
        ignoreUnknownSignals: true

        function onSensorsEnabledBitsChanged() {
            safetyStatusSync.restart()
        }

        function onMavCommandResult(vehicleId, targetComponent, command, ackResult, failureCode) {
            if (command !== root.setSafetyCommand) {
                return
            }
            root.safetyCommandPending = false
            root.safetyCommandMessage = ackResult === 0 ? "" : "Команду запобіжника відхилено"
            safetyCommandTimeout.stop()
            safetyStatusSync.restart()
        }
    }

    Component.onCompleted: Qt.callLater(root.syncSafetySlider)
    onSafetyReleasedChanged: safetyStatusSync.restart()

    ColumnLayout {
        anchors.fill: parent
        spacing: ScreenTools.defaultFontPixelHeight * 0.35

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: profileRow.implicitHeight + ScreenTools.defaultFontPixelHeight * 0.65
            radius: ScreenTools.defaultFontPixelWidth / 3
            color: qgcPal.window

            RowLayout {
                id: profileRow
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth * 0.45
                spacing: ScreenTools.defaultFontPixelWidth * 0.6

                QGCLabel {
                    text: "Швидкі профілі:"
                    font.bold: true
                }

                QGCButton {
                    text: "FMU PWM OUT (AUX)"
                    enabled: root.safetyMaskAvailable
                    onClicked: root.applyFmuPwmOutAuxProfile()
                    ToolTip.visible: hovered
                    ToolTip.text: "BRD_SAFETY_MASK=255; OUT9-14=Motor1-6; OUT15=RCIN10; інші OUT=Disabled"
                }

                QGCButton {
                    text: "I/O PWM OUT (MAIN)"
                    enabled: root.safetyMaskAvailable
                    onClicked: root.applyIoPwmOutMainProfile()
                    ToolTip.visible: hovered
                    ToolTip.text: "BRD_SAFETY_MASK=65280; OUT1-6=Motor1-6; OUT7=RCIN10; інші OUT=Disabled"
                }

                QGCLabel {
                    visible: root.activePreset.length > 0
                    text: "Застосовано: " + root.activePreset
                    color: qgcPal.buttonHighlight
                    font.bold: true
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: "Зміна призначення виходів може потребувати перезавантаження польотника."
                    color: qgcPal.warningText
                    font.pointSize: ScreenTools.smallFontPointSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScreenTools.defaultFontPixelWidth

        Rectangle {
            Layout.preferredWidth: parent.width * 0.52
            Layout.fillHeight: true
            radius: ScreenTools.defaultFontPixelWidth / 3
            color: qgcPal.window

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth * 0.7
                spacing: ScreenTools.defaultFontPixelHeight * 0.28

                QGCLabel {
                    Layout.fillWidth: true
                    text: "Servo / призначення виходів"
                    font.bold: true
                    font.pointSize: ScreenTools.defaultFontPointSize
                }

                RowLayout {
                    Layout.fillWidth: true

                    QGCLabel {
                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 6
                        text: "Вихід"
                        font.bold: true
                    }

                    QGCLabel {
                        Layout.fillWidth: true
                        text: "Функція"
                        font.bold: true
                    }
                }

                QGCFlickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentHeight: servoColumn.height
                    flickableDirection: Flickable.VerticalFlick
                    clip: true

                    ColumnLayout {
                        id: servoColumn
                        width: parent.width
                        spacing: 1

                        Repeater {
                            model: 16

                            Rectangle {
                                required property int index

                                Layout.fillWidth: true
                                Layout.preferredHeight: visible ? ScreenTools.defaultFontPixelHeight * 1.95 : 0
                                visible: root.servoParamExists(index + 1)
                                color: index % 2 ? qgcPal.windowShade : qgcPal.window
                                radius: ScreenTools.defaultFontPixelWidth / 5

                                property string parameterName: root.servoParamName(index + 1)
                                property Fact functionFact: {
                                    const revision = root.presetRevision
                                    return visible
                                           ? controller.getParameterFact(-1, parameterName, false)
                                           : null
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: ScreenTools.defaultFontPixelWidth * 0.22
                                    spacing: ScreenTools.defaultFontPixelWidth * 0.42

                                    QGCLabel {
                                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 5.2
                                        text: "OUT " + (index + 1)
                                        font.bold: true
                                    }

                                    FactComboBox {
                                        Layout.fillWidth: true
                                        fact: functionFact
                                        indexModel: false
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScreenTools.defaultFontPixelHeight * 0.55

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: safetyColumn.implicitHeight + ScreenTools.defaultFontPixelHeight
                radius: ScreenTools.defaultFontPixelWidth / 3
                color: qgcPal.window

                ColumnLayout {
                    id: safetyColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: ScreenTools.defaultFontPixelWidth * 0.65
                    spacing: ScreenTools.defaultFontPixelHeight * 0.25

                    QGCLabel {
                        Layout.fillWidth: true
                        text: "BRD_SAFETY_MASK"
                        font.bold: true
                        font.pointSize: ScreenTools.defaultFontPointSize
                    }

                    QGCLabel {
                        Layout.fillWidth: true
                        visible: !root.safetyMaskAvailable
                        text: "Параметр BRD_SAFETY_MASK відсутній на цьому борту."
                        color: qgcPal.warningText
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.safetyMaskAvailable

                        QGCLabel {
                            text: "Значення:"
                            font.bold: true
                        }

                        FactTextField {
                            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 11
                            fact: root.safetyMaskFact
                            showUnits: false
                        }

                        QGCLabel {
                            Layout.fillWidth: true
                            text: root.safetyMaskFact ? "raw = " + root.safetyMaskFact.rawValue : ""
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.safetyMaskAvailable
                        columns: 4
                        columnSpacing: ScreenTools.defaultFontPixelWidth * 0.45
                        rowSpacing: 0

                        Repeater {
                            model: 16

                            QGCCheckBox {
                                required property int index
                                text: "OUT " + (index + 1)
                                checked: root.maskBitEnabled(index + 1)
                                onClicked: root.setMaskBit(index + 1, checked)
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: ScreenTools.defaultFontPixelWidth / 3
                color: qgcPal.window

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScreenTools.defaultFontPixelWidth * 0.65
                    spacing: ScreenTools.defaultFontPixelHeight * 0.28

                    QGCLabel {
                        Layout.fillWidth: true
                        text: "Тест моторів"
                        font.bold: true
                        font.pointSize: ScreenTools.defaultFontPointSize
                    }

                    QGCLabel {
                        Layout.fillWidth: true
                        text: "УВАГА: зніміть пропелери або надійно зафіксуйте борт."
                        color: qgcPal.warningText
                        wrapMode: Text.WordWrap
                        font.bold: true
                        font.pointSize: ScreenTools.smallFontPointSize
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScreenTools.defaultFontPixelWidth * 0.55

                        Rectangle {
                            id: safetyTrack
                            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 16
                            Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 1.65
                            radius: height / 2
                            color: qgcPal.windowShadeDark
                            border.color: root.safetyReleased ? qgcPal.warningText : qgcPal.colorGreen
                            border.width: 2
                            enabled: !!root.activeVehicle && root.activeVehicle.apmFirmware && !root.safetyCommandPending
                            opacity: enabled ? 1.0 : 0.55
                            clip: true

                            onWidthChanged: Qt.callLater(root.syncSafetySlider)

                            QGCLabel {
                                anchors.centerIn: parent
                                text: root.safetyCommandPending
                                      ? "..."
                                      : (root.safetyReleased ? "← Увімкнути" : "Зняти →")
                                color: qgcPal.text
                                font.pointSize: ScreenTools.smallFontPointSize
                                font.bold: true
                            }

                            Rectangle {
                                id: safetyHandle
                                width: ScreenTools.defaultFontPixelWidth * 3.1
                                height: parent.height - 6
                                y: 3
                                x: 0
                                radius: height / 2
                                color: root.safetyReleased ? qgcPal.warningText : qgcPal.colorGreen
                                border.color: qgcPal.text
                                border.width: 1

                                QGCLabel {
                                    anchors.centerIn: parent
                                    text: root.safetyReleased ? "◀" : "▶"
                                    color: qgcPal.window
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                enabled: safetyTrack.enabled
                                cursorShape: Qt.OpenHandCursor
                                drag.target: safetyHandle
                                drag.axis: Drag.XAxis
                                drag.minimumX: 0
                                drag.maximumX: Math.max(0, safetyTrack.width - safetyHandle.width)

                                onPressed: cursorShape = Qt.ClosedHandCursor
                                onReleased: {
                                    cursorShape = Qt.OpenHandCursor
                                    const maxX = Math.max(0, safetyTrack.width - safetyHandle.width)
                                    const desiredReleased = maxX > 0 && safetyHandle.x >= maxX * 0.5
                                    if (desiredReleased !== root.safetyReleased) {
                                        root.setHardwareSafetyReleased(desiredReleased)
                                    } else {
                                        root.syncSafetySlider()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 15
                            Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 1.65
                            radius: ScreenTools.defaultBorderRadius
                            // Engaged safety is the safe state (green); released safety is dangerous (red).
                            color: root.safetyReleased ? qgcPal.warningText : qgcPal.colorGreen

                            QGCLabel {
                                anchors.centerIn: parent
                                text: root.safetyReleased ? "ЗАПОБІЖНИК ЗНЯТО" : "ЗАПОБІЖНИК УВІМКНЕНО"
                                color: qgcPal.window
                                font.bold: true
                                font.pointSize: ScreenTools.smallFontPointSize
                            }
                        }

                        QGCLabel {
                            Layout.fillWidth: true
                            visible: root.safetyCommandMessage.length > 0
                            text: root.safetyCommandMessage
                            color: qgcPal.warningText
                            elide: Text.ElideRight
                            font.pointSize: ScreenTools.smallFontPointSize
                        }
                    }

                    QGCCheckBox {
                        id: motorSafetyCheck
                        Layout.fillWidth: true
                        text: "Безпечну зону підтверджено"
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: ScreenTools.defaultFontPixelWidth * 0.45

                        QGCLabel { text: "Потужність, %:"; font.pointSize: ScreenTools.smallFontPointSize }

                        Rectangle {
                            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 7
                            Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 1.45
                            radius: ScreenTools.defaultBorderRadius
                            color: qgcPal.windowShadeDark
                            border.color: qgcPal.buttonBorder
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                spacing: 0

                                Rectangle {
                                    Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 1.8
                                    Layout.fillHeight: true
                                    color: percentMinus.containsMouse ? qgcPal.buttonHighlight : qgcPal.button
                                    QGCLabel { anchors.centerIn: parent; text: "−"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                                    MouseArea {
                                        id: percentMinus
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.motorPercentValue = Math.max(1, root.motorPercentValue - 1)
                                    }
                                }

                                QGCLabel {
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    text: root.motorPercentValue
                                    font.bold: true
                                    font.pointSize: ScreenTools.smallFontPointSize
                                }

                                Rectangle {
                                    Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 1.8
                                    Layout.fillHeight: true
                                    color: percentPlus.containsMouse ? qgcPal.buttonHighlight : qgcPal.button
                                    QGCLabel { anchors.centerIn: parent; text: "+"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                                    MouseArea {
                                        id: percentPlus
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.motorPercentValue = Math.min(30, root.motorPercentValue + 1)
                                    }
                                }
                            }
                        }

                        QGCLabel { text: "Час, с:"; font.pointSize: ScreenTools.smallFontPointSize }

                        Rectangle {
                            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 7
                            Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 1.45
                            radius: ScreenTools.defaultBorderRadius
                            color: qgcPal.windowShadeDark
                            border.color: qgcPal.buttonBorder
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                spacing: 0

                                Rectangle {
                                    Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 1.8
                                    Layout.fillHeight: true
                                    color: secondsMinus.containsMouse ? qgcPal.buttonHighlight : qgcPal.button
                                    QGCLabel { anchors.centerIn: parent; text: "−"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                                    MouseArea {
                                        id: secondsMinus
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.motorSecondsValue = Math.max(1, root.motorSecondsValue - 1)
                                    }
                                }

                                QGCLabel {
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    text: root.motorSecondsValue
                                    font.bold: true
                                    font.pointSize: ScreenTools.smallFontPointSize
                                }

                                Rectangle {
                                    Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 1.8
                                    Layout.fillHeight: true
                                    color: secondsPlus.containsMouse ? qgcPal.buttonHighlight : qgcPal.button
                                    QGCLabel { anchors.centerIn: parent; text: "+"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                                    MouseArea {
                                        id: secondsPlus
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.motorSecondsValue = Math.min(10, root.motorSecondsValue + 1)
                                    }
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }

                        QGCButton {
                            text: "СТОП"
                            enabled: !!root.activeVehicle
                            onClicked: root.stopMotorTests()
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 4
                        columnSpacing: ScreenTools.defaultFontPixelWidth * 0.32
                        rowSpacing: ScreenTools.defaultFontPixelHeight * 0.2

                        Repeater {
                            model: 16

                            QGCButton {
                                required property int index

                                Layout.fillWidth: true
                                text: "Motor " + (index + 1)
                                enabled: !!root.activeVehicle && root.safetyReleased && motorSafetyCheck.checked
                                onClicked: root.runMotorTest(index + 1)
                            }
                        }
                    }

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }
        }
        }
    }
}
