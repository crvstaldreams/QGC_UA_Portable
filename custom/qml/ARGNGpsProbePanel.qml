import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QGroundControl
import QGroundControl.Controls
import QGroundControl.Custom

Item {
    id: root
    property var vehicle: QGroundControl.multiVehicleManager.activeVehicle
    readonly property string gps1Info: gnssProbe.gps1Info
    readonly property string gps2Info: gnssProbe.gps2Info
    readonly property bool busy: gnssProbe.busy

    function requestAll() {
        if (!vehicle || vehicle.armed) return
        details.open()
        gnssProbe.probeAll()
    }
    function openDetails() { details.open() }

    ARGNGpsProbeController {
        id: gnssProbe
        vehicle: root.vehicle
    }
    Popup {
        id: details
        parent: Overlay.overlay
        width: Math.min(600, parent.width - 30)
        height: 290
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape
        onClosed: gnssProbe.cancel()
        background: Rectangle { color: "#171717"; radius: 8; border.color: "#FFD400" }
        contentItem: ColumnLayout {
            spacing: 9
            Text { text: "GNSS UART · UBX-MON-VER"; font.bold: true; font.pixelSize: 17; color: "#FFD400" }
            Text {
                Layout.fillWidth: true
                text: "Опитування GPS UART тимчасово блокує GPS-драйвер. Лише на землі, без озброєння."
                color: "#F0D363"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
            RowLayout {
                spacing: 5
                Button { text: "Обидва"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeAll() }
                Button { text: "GPS1"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeGps(1) }
                Button { text: "GPS2"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeGps(2) }
                Button { text: "Стоп"; enabled: gnssProbe.busy; onClicked: gnssProbe.cancel() }
                Button { text: "Закрити"; onClicked: details.close() }
            }
            Text { Layout.fillWidth: true; text: "GPS1: " + gnssProbe.gps1Info; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Text { Layout.fillWidth: true; text: "GPS2: " + gnssProbe.gps2Info; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Text { Layout.fillWidth: true; text: gnssProbe.statusText; wrapMode: Text.WordWrap; font.pixelSize: 12; color: "#F0D363" }
            Item { Layout.fillHeight: true }
        }
    }
}
