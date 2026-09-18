import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import QGroundControl
import QGroundControl.Controls
import QGroundControl.Palette
import QGroundControl.ScreenTools
import QGroundControl.FlightMap

Rectangle {
    id: root
    color: qgcPal.window

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle
    property string currentPage: "parameters"
    property bool parametersReady: QGroundControl.multiVehicleManager.parameterReadyVehicleAvailable &&
                                   activeVehicle &&
                                   !activeVehicle.parameterManager.missingParameters

    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    function showFirmware() {
        currentPage = "firmware"
    }

    function showParameters() {
        currentPage = "parameters"
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: ScreenTools.defaultFontPixelWidth
        spacing: ScreenTools.defaultFontPixelWidth

        Rectangle {
            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 19
            Layout.fillHeight: true
            radius: ScreenTools.defaultFontPixelWidth / 2
            color: qgcPal.windowShade

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth
                spacing: ScreenTools.defaultFontPixelHeight / 2

                QGCLabel {
                    Layout.fillWidth: true
                    text: qsTr("Спрощ. режим для сервісу")
                    font.pointSize: ScreenTools.mediumFontPointSize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: activeVehicle ? qsTr("Борт підключено") : qsTr("Борт не підключено")
                    color: activeVehicle ? qgcPal.text : qgcPal.warningText
                    wrapMode: Text.WordWrap
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: qsTr("Firmware")
                    checked: root.currentPage === "firmware"
                    onClicked: root.showFirmware()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: qsTr("Параметри")
                    checked: root.currentPage === "parameters"
                    enabled: root.parametersReady
                    onClicked: root.showParameters()
                }

                Item {
                    Layout.fillHeight: true
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: qsTr("У сервісному режимі залишені тільки прошивка, параметри та контроль орієнтації борту.")
                    wrapMode: Text.WordWrap
                    font.pointSize: ScreenTools.smallFontPointSize
                    color: qgcPal.text
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: ScreenTools.defaultFontPixelWidth / 2
            color: qgcPal.windowShade

            Loader {
                id: serviceLoader
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth
                source: root.currentPage === "firmware"
                        ? "qrc:/qml/QGroundControl/VehicleSetup/FirmwareUpgrade.qml"
                        : (root.parametersReady
                           ? "qrc:/qml/QGroundControl/Custom/ServiceParameterEditor.qml"
                           : "")
            }

            QGCLabel {
                anchors.centerIn: parent
                width: parent.width * 0.8
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                visible: root.currentPage === "parameters" && !root.parametersReady
                text: qsTr("Підключіть борт і дочекайтеся повного завантаження параметрів.")
                font.pointSize: ScreenTools.mediumFontPointSize
            }
        }

        Rectangle {
            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 24
            Layout.fillHeight: true
            radius: ScreenTools.defaultFontPixelWidth / 2
            color: qgcPal.windowShade

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth
                spacing: ScreenTools.defaultFontPixelHeight

                QGCLabel {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Положення польотника")
                    font.pointSize: ScreenTools.mediumFontPointSize
                    font.bold: true
                }

                QGCAttitudeWidget {
                    Layout.alignment: Qt.AlignHCenter
                    size: Math.min(root.height * 0.27, ScreenTools.defaultFontPixelHeight * 14)
                    vehicle: root.activeVehicle
                    showPitch: true
                    showHeading: true
                }

                RowLayout {
                    Layout.fillWidth: true

                    QGCLabel {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("Крен\n%1°").arg(root.activeVehicle ? root.activeVehicle.roll.rawValue.toFixed(1) : "—")
                    }

                    QGCLabel {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("Тангаж\n%1°").arg(root.activeVehicle ? root.activeVehicle.pitch.rawValue.toFixed(1) : "—")
                    }
                }

                QGCLabel {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Компас")
                    font.bold: true
                }

                QGCCompassWidget {
                    Layout.alignment: Qt.AlignHCenter
                    size: Math.min(root.height * 0.25, ScreenTools.defaultFontPixelHeight * 13)
                    vehicle: root.activeVehicle
                    usedByMultipleVehicleList: false
                }

                QGCLabel {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Курс: %1°").arg(root.activeVehicle ? root.activeVehicle.heading.rawValue.toFixed(0) : "—")
                }

                Item {
                    Layout.fillHeight: true
                }
            }
        }
    }
}
