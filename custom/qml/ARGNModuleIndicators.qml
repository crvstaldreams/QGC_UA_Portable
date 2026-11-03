import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtCore
import QGroundControl
import QGroundControl.Controls
import QGroundControl.Controllers
import QGroundControl.Custom
import QGroundControl.Palette

Rectangle {
    id: root
    radius: 8
    color: "#141414"
    border.width: 1
    border.color: "#3c3c3c"
    property var vehicle: QGroundControl.multiVehicleManager.activeVehicle
    property int secondsConnected: 0
    property bool ready: !!vehicle && QGroundControl.multiVehicleManager.parameterReadyVehicleAvailable

    Settings {
        id: moduleSettings
        category: "ARGNModuleIndicators"
        property bool swapped: false
    }
    FactPanelController { id: params }
    ARGNGpsProbeController {
        id: uartProbe
        vehicle: root.vehicle
    }

    Popup {
        id: uartProbePopup
        parent: Overlay.overlay
        width: Math.min(520, parent.width - 20)
        height: 255
        x: (parent.width - width) / 2
        y: Math.max(8, parent.height - height - 65)
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        onClosed: uartProbe.cancel()
        background: Rectangle { color: "#181818"; radius: 8; border.color: "#777777" }
        contentItem: ColumnLayout {
            spacing: 8
            QGCLabel { text: "GNSS UART · UBX-MON-VER"; font.bold: true; color: "#ffffff" }
            QGCLabel {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Тільки на роззброєному борту. На короткий час GPS-драйвер відпустить UART. Не використовуйте під час польоту."
                color: "#e5bc35"
            }
            RowLayout {
                QGCButton {
                    text: "Запит обох"
                    enabled: !!root.vehicle && !root.vehicle.armed && !uartProbe.busy
                    onClicked: uartProbe.probeAll()
                }
                QGCButton {
                    text: "Запит GPS1"
                    enabled: !!root.vehicle && !root.vehicle.armed && !uartProbe.busy
                    onClicked: uartProbe.probeGps(1)
                }
                QGCButton {
                    text: "Запит GPS2"
                    enabled: !!root.vehicle && !root.vehicle.armed && !uartProbe.busy
                    onClicked: uartProbe.probeGps(2)
                }
                QGCButton {
                    text: "Стоп"
                    enabled: uartProbe.busy
                    onClicked: uartProbe.cancel()
                }
            }
            QGCLabel {
                Layout.fillWidth: true
                wrapMode: Text.WrapAnywhere
                text: "GPS1: " + uartProbe.gps1Info
                color: "#ffffff"
            }
            QGCLabel {
                Layout.fillWidth: true
                wrapMode: Text.WrapAnywhere
                text: "GPS2: " + uartProbe.gps2Info
                color: "#ffffff"
            }
            QGCLabel {
                Layout.fillWidth: true
                wrapMode: Text.WrapAnywhere
                text: uartProbe.statusText
                color: "#e5bc35"
            }
            Item { Layout.fillHeight: true }
        }
    }


    function fact(name) {
        return ready && params.parameterExists(-1, name)
                ? params.getParameterFact(-1, name, false) : null
    }
    function externalCompassConfigured() {
        if (!ready) return false
        for (let i = 0; i < 3; ++i) {
            const suffix = i === 0 ? "" : String(i + 1)
            const id = fact("COMPASS_DEV_ID" + suffix)
            const ex = fact(i === 0 ? "COMPASS_EXTERNAL" : "COMPASS_EXTERN" + suffix)
            const used = fact("COMPASS_USE" + suffix)
            if (id && Number(id.rawValue) > 0 && ex && Number(ex.rawValue) !== 0 &&
                    (!used || Number(used.rawValue) !== 0)) return true
        }
        return false
    }
    function gpsState(gps) {
        if (!vehicle) return 0
        if (!gps || !gps.telemetryAvailable)
            return secondsConnected < 10 ? 1 : 0
        const fix = Number(gps.lock.rawValue)
        const hdop = Number(gps.hdop.rawValue)
        if (fix >= 3 && isFinite(hdop) && hdop > 10) return 3
        if (fix >= 3) return 2
        if (fix === 1 || fix === 2 || fix === 0) return 1
        return 3
    }
    function compassState() {
        if (!vehicle) return 0
        if (!ready) return 1
        if (!externalCompassConfigured()) return 0
        const present = vehicle.sensorsPresentBits
        const enabled = vehicle.sensorsEnabledBits
        const health = vehicle.sensorsHealthBits
        const magnetic = 4 // MAV_SYS_STATUS_SENSOR_3D_MAG
        if (!(present & magnetic)) return secondsConnected < 10 ? 1 : 0
        if (!(enabled & magnetic) || !(health & magnetic)) return 3
        return 2
    }
    function stateColor(s) {
        return s === 2 ? "#31bf59" : s === 1 ? "#e5bc35" : s === 3 ? "#f04242" : "#111111"
    }
    function stateText(s, name) {
        return s === 2 ? name + ": OK" :
               s === 1 ? name + ": очікуємо інформацію" :
               s === 3 ? "module " + name + " is bad" :
               name + ": немає зв'язку"
    }

    onVehicleChanged: secondsConnected = 0
    Timer {
        interval: 1000
        running: !!root.vehicle
        repeat: true
        onTriggered: root.secondsConnected += 1
    }
    RowLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 12

        Repeater {
            model: ["ZED", "NEO", "COMPASS"]
            delegate: RowLayout {
                required property int index
                required property string modelData
                spacing: 5
                readonly property var gps: moduleSettings.swapped
                    ? (index === 0 ? root.vehicle && root.vehicle.gps2 : root.vehicle && root.vehicle.gps)
                    : (index === 0 ? root.vehicle && root.vehicle.gps : root.vehicle && root.vehicle.gps2)
                readonly property int healthState: index === 2 ? root.compassState() : root.gpsState(gps)
                Rectangle {
                    width: 13
                    height: 13
                    radius: 7
                    color: root.stateColor(parent.healthState)
                    border.width: 1
                    border.color: "#777777"
                }
                QGCLabel {
                    text: modelData
                    color: "#f0f0f0"
                    font.bold: true
                    font.pixelSize: 13
                }
                ToolTip.visible: hover.hovered
                ToolTip.text: root.stateText(healthState, modelData) +
                    (index === 2 ? "\nОцінка за параметрами зовнішнього компаса та загальним MAG health"
                                 : "\nMAVLink " + ((moduleSettings.swapped ? 1-index : index) === 0 ? "GPS_RAW_INT" : "GPS2_RAW"))
                HoverHandler { id: hover }
            }
        }
        ToolButton {
            text: "ЗАПИТ СТАНУ"
            Layout.preferredWidth: 124
            enabled: !!root.vehicle && !root.vehicle.armed && !uartProbe.busy
            onClicked: {
                uartProbePopup.open()
                uartProbe.probeAll()
            }
            ToolTip.visible: hovered
            ToolTip.text: "Разове ручне опитування GPS1 і GPS2 через MAVLink UART (UBX-MON-VER); тільки роззброєний борт"
        }
        ToolButton {
            text: "⇄"
            Layout.preferredWidth: 24
            onClicked: moduleSettings.swapped = !moduleSettings.swapped
            ToolTip.visible: hovered
            ToolTip.text: "Поміняти відповідність ZED/NEO до GPS1/GPS2"
        }
    }
}
