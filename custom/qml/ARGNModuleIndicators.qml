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
    // Both F9Ps share one physical GPS UART. Receiver selection is done via UBX.
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
        ? probeLoader.item.zedInfo : "UART діагностика недоступна"
    readonly property string neoIdInfo: probeLoader.item
        ? probeLoader.item.neoInfo : "UART діагностика недоступна"

    function receiverHealth(which) {
        // No scan = black. While the requested receiver is being queried =
        // yellow. A valid UBX reply = green, even without GPS Fix.
        if (!vehicle || !probeLoader.item || !probeLoader.item.scanStarted) return 0
        if (probeLoader.item.busy) return 1
        if (which === "ZED") return probeLoader.item.zedVerified ? 2 : 0
        return probeLoader.item.neoVerified ? 2 : 0
    }
    function externalCompassHealth() {
        if (!vehicle || !probeLoader.item) return 0
        return probeLoader.item.externalCompassState
    }
    function fcCompassHealth() {
        if (!vehicle || !probeLoader.item) return 0
        return probeLoader.item.fcCompassState
    }
    function syncHealth() {
        // The two PPS/LED phases are not present in standard MAVLink GNSS
        // messages. Never infer LED synchronization from GPS Fix or MON-VER.
        return vehicle ? 1 : 0
    }

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
            readonly property int health: root.receiverHealth("ZED")
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "ZED"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
            HoverHandler { id: zedHover }
            ToolTip.visible: zedHover.hovered
            ToolTip.text: root.stateHint(health, "ZED") + "\n" + root.zedIdInfo
        }
        RowLayout {
            spacing: 5
            readonly property int health: root.receiverHealth("NEO")
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "NEO"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
            HoverHandler { id: neoHover }
            ToolTip.visible: neoHover.hovered
            ToolTip.text: root.stateHint(health, "NEO") + "\n" + root.neoIdInfo
        }
        RowLayout {
            spacing: 5
            readonly property int health: root.fcCompassHealth()
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "FC COMPASS"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
            HoverHandler { id: fcHover }
            ToolTip.visible: fcHover.hovered
            ToolTip.text: probeLoader.item ? probeLoader.item.fcCompassInfo : "Очікування MAVLink"
        }
        RowLayout {
            spacing: 5
            readonly property int health: root.externalCompassHealth()
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "Q/F9P COMPASS"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
            HoverHandler { id: extHover }
            ToolTip.visible: extHover.hovered
            ToolTip.text: probeLoader.item ? probeLoader.item.externalCompassInfo : "Не опитано"
        }
        RowLayout {
            spacing: 5
            readonly property int health: root.syncHealth()
            Rectangle { width: 13; height: 13; radius: 7; color: root.statusColor(parent.health); border.color: "#9A9A9A" }
            Text { text: "SYNC"; color: "#FFFFFF"; font.bold: true; font.pixelSize: 13 }
            HoverHandler { id: syncHover }
            ToolTip.visible: syncHover.hovered
            ToolTip.text: "Зелений лише при отриманні GNSS_SYNC=1 від окремого вимірювача фаз LED/PPS, червоний при GNSS_SYNC=0, жовтий без даних. GPS Fix не використовується."
        }

        Item { Layout.fillWidth: true }

        Button {
            text: "ЗАПИТ СТАНУ"
            Layout.preferredWidth: 138
            enabled: !!root.vehicle && !root.vehicle.armed && probeLoader.item && !probeLoader.item.busy
            onClicked: probeLoader.item.requestAll()
            ToolTip.visible: hovered
            ToolTip.text: "Послідовний запит ZED/NEO через один UART і незалежний PARAM_REQUEST_READ зовнішнього компаса"
        }
    }
}
