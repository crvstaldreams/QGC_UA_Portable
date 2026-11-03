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
    readonly property bool zedVerified: gnssProbe.zedVerified
    readonly property bool neoVerified: gnssProbe.neoVerified
    readonly property string zedInfo: gnssProbe.zedInfo
    readonly property string neoInfo: gnssProbe.neoInfo
    readonly property string activePort: gnssProbe.activePort
    readonly property bool scanComplete: !gnssProbe.busy &&
        (gnssProbe.zedInfo !== "Не перевірено" || gnssProbe.neoInfo !== "Не перевірено")

    function requestAll() {
        if (!vehicle || vehicle.armed) return
        details.open()
        gnssProbe.probeDual()
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
        height: 365
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape
        onClosed: gnssProbe.cancel()
        background: Rectangle { color: "#171717"; radius: 8; border.color: "#FFD400" }
        contentItem: ColumnLayout {
            spacing: 9
            Text { text: "GNSS · ZED + NEO на одному UART"; font.bold: true; font.pixelSize: 17; color: "#FFD400" }
            Text {
                Layout.fillWidth: true
                text: "Земля, роззброєно. Команди u-center тимчасово перемикають RAM selector ZED/NEO. Після опитування відновлюється попередній вибір (якщо доступний), інакше ZED."
                color: "#F0D363"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
            RowLayout {
                spacing: 5
                Button { text: "Авто GPS1/GPS2"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeDual() }
                Button { text: "Один UART GPS1"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeDualPort(1) }
                Button { text: "Один UART GPS2"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeDualPort(2) }
                Button { text: "Стоп"; enabled: gnssProbe.busy; onClicked: gnssProbe.cancel() }
                Button { text: "Закрити"; onClicked: details.close() }
            }
            Text { Layout.fillWidth: true; text: "Порт: " + gnssProbe.activePort; font.pixelSize: 12; color: "#F0D363" }
            Text { Layout.fillWidth: true; text: "ZED: " + gnssProbe.zedInfo; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Text { Layout.fillWidth: true; text: "NEO: " + gnssProbe.neoInfo; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Text {
                Layout.fillWidth: true
                text: "SYNC: немає даних про фази LED / 1PPS у MAVLink; стан не підтверджено"
                font.pixelSize: 12; wrapMode: Text.WordWrap; color: "#E5BC35"
            }
            Text { Layout.fillWidth: true; text: gnssProbe.statusText; wrapMode: Text.WordWrap; font.pixelSize: 12; color: "#F0D363" }
            Item { Layout.fillHeight: true }
        }
    }
}
