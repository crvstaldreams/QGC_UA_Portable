import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import QGroundControl
import QGroundControl.Controls
import QGroundControl.Palette
import QGroundControl.ScreenTools

Rectangle {
    id: root
    color: qgcPal.window
    radius: ScreenTools.defaultFontPixelWidth / 3

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle

    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    Timer {
        interval: 5000
        repeat: true
        running: root.visible && !!root.activeVehicle
        onTriggered: vehicleMessageList.refreshMessages()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: ScreenTools.defaultFontPixelWidth
        spacing: ScreenTools.defaultFontPixelHeight * 0.5

        RowLayout {
            Layout.fillWidth: true

            QGCLabel {
                Layout.fillWidth: true
                text: "MAVLink Status"
                font.bold: true
                font.pointSize: ScreenTools.largeFontPointSize
            }

            QGCLabel {
                text: activeVehicle ? "Оновлення кожні 5 с" : "Борт не підключено"
                color: activeVehicle ? qgcPal.text : qgcPal.warningText
            }

            QGCButton {
                text: "Оновити"
                enabled: !!activeVehicle
                onClicked: vehicleMessageList.refreshMessages()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: qgcPal.windowShadeDark
            radius: ScreenTools.defaultBorderRadius
            border.width: 2
            border.color: qgcPal.buttonBorder
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
                    activeVehicle: root.activeVehicle
                    messageFontPointSize: ScreenTools.defaultFontPointSize
                    messagePanelWidth: mavlinkStatusScroll.availableWidth
                    messagePanelMinHeight: mavlinkStatusScroll.availableHeight
                }
            }
        }
    }
}
