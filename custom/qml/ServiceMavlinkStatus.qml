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

    QGCPalette { id: qgcPal; colorGroupEnabled: true }

    // VehicleMessageList listens for the vehicle's newFormattedMessage signal
    // and inserts each incoming MAVLink status message immediately.
    // No polling, refresh timer, title, or redundant controls in this view.
    function focusNewest() {
        Qt.callLater(function() {
            if (mavlinkStatusScroll.ScrollBar.vertical)
                mavlinkStatusScroll.ScrollBar.vertical.position = 0
            vehicleMessageList.cursorPosition = 0
            vehicleMessageList.deselect()
        })
    }
    Connections {
        target: vehicleMessageList
        function onTextChanged() { root.focusNewest() }
    }

    ScrollView {
        id: mavlinkStatusScroll
        anchors.fill: parent
        anchors.margins: ScreenTools.defaultFontPixelWidth * 0.75
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        VehicleMessageList {
            id: vehicleMessageList
            width: mavlinkStatusScroll.availableWidth
            activeVehicle: root.activeVehicle
            messagePanelWidth: mavlinkStatusScroll.availableWidth
            messagePanelMinHeight: mavlinkStatusScroll.availableHeight
            showClearButton: false
            messageFontPointSize: Math.max(2, ScreenTools.defaultFontPointSize * 1.5)
            spaciousMessages: false
            followNewest: true
            font.pointSize: messageFontPointSize
        }
    }
}
