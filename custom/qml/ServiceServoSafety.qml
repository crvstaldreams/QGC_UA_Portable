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

    function applyFmuPwmOutAuxProfile() {
        if (!safetyMaskFact) {
            return
        }

        // ArduPilot SRV_Channel function ids:
        // Motor1..Motor6 = 33..38, RCIN10 = 60.
        safetyMaskFact.rawValue = 255
        for (let output = 9; output <= 14; output++) {
            setServoFunction(output, 33 + (output - 9))
        }
        setServoFunction(15, 60)
    }

    function applyIoPwmOutMainProfile() {
        if (!safetyMaskFact) {
            return
        }

        safetyMaskFact.rawValue = 65280
        for (let output = 1; output <= 6; output++) {
            setServoFunction(output, 33 + (output - 1))
        }
        setServoFunction(7, 60)
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

    function runMotorTest(motorNumber) {
        if (!activeVehicle || !motorSafetyCheck.checked) {
            return
        }
        activeVehicle.motorTest(motorNumber, motorPercent.value, motorSeconds.value, true)
    }

    function stopMotorTests() {
        if (!activeVehicle) {
            return
        }
        for (let motor = 1; motor <= 16; motor++) {
            activeVehicle.motorTest(motor, 0, 1, false)
        }
    }

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
                    ToolTip.text: "BRD_SAFETY_MASK=255; SERVO9-14=Motor1-6; SERVO15=RCIN10"
                }

                QGCButton {
                    text: "I/O PWM OUT (MAIN)"
                    enabled: root.safetyMaskAvailable
                    onClicked: root.applyIoPwmOutMainProfile()
                    ToolTip.visible: hovered
                    ToolTip.text: "BRD_SAFETY_MASK=65280; SERVO1-6=Motor1-6; SERVO7=RCIN10"
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: "Зміна SERVOx_FUNCTION може потребувати перезавантаження польотника."
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
                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 15
                        text: "Параметр"
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
                                property Fact functionFact: visible
                                                            ? controller.getParameterFact(-1, parameterName, false)
                                                            : null

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: ScreenTools.defaultFontPixelWidth * 0.22
                                    spacing: ScreenTools.defaultFontPixelWidth * 0.42

                                    QGCLabel {
                                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 5.2
                                        text: "OUT " + (index + 1)
                                        font.bold: true
                                    }

                                    QGCLabel {
                                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 14
                                        text: parameterName
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
                        text: "УВАГА: тест запускає мотори фізично. Зніміть пропелери або надійно зафіксуйте борт."
                        color: qgcPal.warningText
                        wrapMode: Text.WordWrap
                        font.bold: true
                        font.pointSize: ScreenTools.smallFontPointSize
                    }

                    QGCCheckBox {
                        id: motorSafetyCheck
                        Layout.fillWidth: true
                        text: "Безпечну зону підтверджено — дозволити Motor Test"
                    }

                    RowLayout {
                        Layout.fillWidth: true

                        QGCLabel { text: "Потужність, %:" }

                        SpinBox {
                            id: motorPercent
                            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 7.5
                            from: 1
                            to: 30
                            value: 5
                            editable: true
                        }

                        QGCLabel { text: "Час, с:" }

                        SpinBox {
                            id: motorSeconds
                            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 7.5
                            from: 1
                            to: 10
                            value: 2
                            editable: true
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
                                enabled: !!root.activeVehicle && motorSafetyCheck.checked
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
