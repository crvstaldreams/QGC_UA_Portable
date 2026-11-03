import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QGroundControl

// Keep the health strip independent from optional custom QML types.
// An error in the UART probe must never hide ZED / NEO / COMPASS indicators.
Rectangle {
    id: root
    radius: 8
    color: "#141414"
    property var vehicle: QGroundControl.multiVehicleManager.activeVehicle
    property bool swapped: false
    property int secondsConnected: 0

    Loader {
        id: probeLoader
        active: true
        visible: false
        source: "qrc:/qml/QGroundControl/Custom/ARGNGpsProbePanel.qml"
        onStatusChanged: {
            if (status === Loader.Error)
                console.error("ARGN GPS UART probe could not be loaded:", source)
        }
    }

    readonly property string zedIdInfo: probeLoader.item
        ? (swapped ? probeLoader.item.gps2Info : probeLoader.item.gps1Info)
        : "UART діагностика недоступна"
    readonly property string neoIdInfo: probeLoader.item
        ? (swapped ? probeLoader.item.gps1Info : probeLoader.item.gps2Info)
        : "UART діагностика недоступна"

    function gpsHealth(gps) {
        if (!vehicle) return 0
        if (!gps || !gps.telemetryAvailable)
            return secondsConnected < 10 ? 1 : 0
        const fix = Number(gps.lock.rawValue)
        const hdop = Number(gps.hdop.rawValue)
        if (fix >= 3 && isFinite(hdop) && hdop > 10 && hdop < 650) return 3
        if (fix >= 3) return 2
        return 1
    }
    function compassHealth() {
        if (!vehicle) return 0
        const present = vehicle.sensorsPresentBits
        const enabled = vehicle.sensorsEnabledBits
        const health = vehicle.sensorsHealthBits
        const mag = 4
        if (!(present & mag)) return secondsConnected < 10 ? 1 : 0
        if (!(enabled & mag) || !(health & mag)) return 3
        return 2
    }
    function statusColor(status) {
        return status === 2 ? "#31bf59"
             : status === 1 ? "#e5bc35"
             : status === 3 ? "#f04242" : "#090909"
    }
    function stateHint(status, label) {
        return status === 2 ? label + ": телеметрія ОК" :
               status === 1 ? label + ": очікуємо інформацію" :
               status === 3 ? "module " + label + " is bad" :
               label + ": немає зв'язку"
    }

    onVehicleChanged: secondsConnected = 0
    Timer {
        interval: 1000
        running: !!root.vehicle
        repeat: true
        onTriggered: root.secondsConnected++
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 10
        spacing: 12

        RowLayout {
            spacing: 5
            readonly property int health: root.gpsHealth(root.swapped
                ? (root.vehicle ? root.vehicle.gps2 : null)
                : (root.vehicle ? root.vehicle.gps : null))
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "ZED"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
        }
        RowLayout {
            spacing: 5
            readonly property int health: root.gpsHealth(root.swapped
                ? (root.vehicle ? root.vehicle.gps : null)
                : (root.vehicle ? root.vehicle.gps2 : null))
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "NEO"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
        }
        RowLayout {
            spacing: 5
            readonly property int health: root.compassHealth()
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "COMPASS"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
        }

        Item { Layout.fillWidth: true }

        Button {
            text: "ЗАПИТ СТАНУ"
            Layout.preferredWidth: 135
            enabled: !!root.vehicle && !root.vehicle.armed && probeLoader.item && !probeLoader.item.busy
            onClicked: probeLoader.item.requestAll()
            ToolTip.visible: hovered
            ToolTip.text: "Ручна діагностика GPS1 / GPS2 (UBX-MON-VER); лише на роззброєному борту"
        }
        Button {
            text: "⇄"
            Layout.preferredWidth: 36
            onClicked: root.swapped = !root.swapped
            ToolTip.visible: hovered
            ToolTip.text: "Поміняти відповідність ZED і NEO до GPS1/GPS2"
        }
    }
}
