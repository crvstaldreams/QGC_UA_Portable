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
    readonly property int fcCompassState: gnssProbe.fcCompassState
    readonly property string fcCompassInfo: gnssProbe.fcCompassInfo
    readonly property int externalCompassState: gnssProbe.externalCompassState
    readonly property string externalCompassInfo: gnssProbe.externalCompassInfo
    readonly property bool scanStarted: gnssProbe.zedInfo !== "Не перевірено" ||
        gnssProbe.neoInfo !== "Не перевірено"
    readonly property bool zedVerified: gnssProbe.zedVerified
    readonly property bool neoVerified: gnssProbe.neoVerified
    readonly property bool zedResponded: gnssProbe.zedResponded
    readonly property bool neoResponded: gnssProbe.neoResponded
    readonly property string zedInfo: gnssProbe.zedInfo
    readonly property string neoInfo: gnssProbe.neoInfo
    readonly property string activePort: gnssProbe.activePort
    readonly property int syncState: gnssProbe.syncState
    readonly property bool scanComplete: !gnssProbe.busy &&
        (gnssProbe.zedInfo !== "Не перевірено" || gnssProbe.neoInfo !== "Не перевірено")

    function requestAll() {
        if (!vehicle || vehicle.armed) return
        details.open()
        gnssProbe.requestExternalCompass()
        gnssProbe.probeDual()
    }
    function openDetails() { details.open() }

    // Independent, read-only MAVLink GNSS data. These are GPS stream
    // indexes, not proof of which u-blox chip is currently selected.
    property int telemetryTick: 0
    function gpsFact(gps, field) {
        const tick = telemetryTick
        if (!gps || !gps[field]) return "—"
        return gps[field].valueString !== undefined
            ? gps[field].valueString : String(gps[field].rawValue)
    }
    function gpsFix(gps) {
        const tick = telemetryTick
        return gps && gps.lock ? gps.lock.enumStringValue : "—"
    }
    function gpsLink(gps) {
        const tick = telemetryTick
        return gps && gps.telemetryAvailable ? "Дані надходять" : "Немає даних"
    }
    Timer {
        interval: 1000
        running: telemetryPopup.visible
        repeat: true
        onTriggered: root.telemetryTick++
    }
    Popup {
        id: telemetryPopup
        parent: Overlay.overlay
        width: Math.min(720, parent.width - 30)
        height: Math.min(490, parent.height - 30)
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape
        background: Rectangle { radius: 8; color: "#151515"; border.color: "#FFD400" }
        contentItem: ColumnLayout {
            spacing: 10
            Text {
                text: "GNSS · телеметрія в реальному часі"
                color: "#FFD400"; font.pixelSize: 18; font.bold: true
            }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#E5BC35"; font.pixelSize: 12
                text: "GPS1/GPS2 — логічні потоки MAVLink, не фізичні назви ZED/NEO. " +
                      "Показники супутників та GPS Fix не впливають на індикатор справності приймача."
            }
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 12
                rowSpacing: 9
                Text { text: "Показник"; color: "#FFD400"; font.bold: true }
                Text { text: "GPS1"; color: "#FFD400"; font.bold: true }
                Text { text: "GPS2"; color: "#FFD400"; font.bold: true }
                Text { text: "Зв'язок"; color: "white" }
                Text { text: root.gpsLink(root.vehicle ? root.vehicle.gps : null); color: "white" }
                Text { text: root.gpsLink(root.vehicle ? root.vehicle.gps2 : null); color: "white" }
                Text { text: "Тип фіксації"; color: "white" }
                Text { text: root.gpsFix(root.vehicle ? root.vehicle.gps : null); color: "white" }
                Text { text: root.gpsFix(root.vehicle ? root.vehicle.gps2 : null); color: "white" }
                Text { text: "Супутники"; color: "white" }
                Text { text: root.gpsFact(root.vehicle ? root.vehicle.gps : null, "count"); color: "white" }
                Text { text: root.gpsFact(root.vehicle ? root.vehicle.gps2 : null, "count"); color: "white" }
                Text { text: "HDOP"; color: "white" }
                Text { text: root.gpsFact(root.vehicle ? root.vehicle.gps : null, "hdop"); color: "white" }
                Text { text: root.gpsFact(root.vehicle ? root.vehicle.gps2 : null, "hdop"); color: "white" }
                Text { text: "VDOP"; color: "white" }
                Text { text: root.gpsFact(root.vehicle ? root.vehicle.gps : null, "vdop"); color: "white" }
                Text { text: root.gpsFact(root.vehicle ? root.vehicle.gps2 : null, "vdop"); color: "white" }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#555555" }
            Text {
                Layout.fillWidth: true
                text: "ZED: " + gnssProbe.zedInfo
                font.pixelSize: 12; color: "#FFFFFF"; wrapMode: Text.WrapAnywhere
            }
            Text {
                Layout.fillWidth: true
                text: "NEO: " + gnssProbe.neoInfo
                font.pixelSize: 12; color: "#FFFFFF"; wrapMode: Text.WrapAnywhere
            }
            Text {
                Layout.fillWidth: true
                text: "FC COMPASS: " + gnssProbe.fcCompassInfo
                font.pixelSize: 12; color: "#FFFFFF"; wrapMode: Text.WrapAnywhere
            }
            Text {
                Layout.fillWidth: true
                text: "Q/F9P COMPASS: " + gnssProbe.externalCompassInfo
                font.pixelSize: 12; color: "#FFFFFF"; wrapMode: Text.WrapAnywhere
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button { text: "Запит ідентифікації"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: { telemetryPopup.close(); root.requestAll() } }
                Button { text: "Закрити"; onClicked: telemetryPopup.close() }
            }
        }
    }

    ARGNGpsProbeController {
        id: gnssProbe
        vehicle: root.vehicle
    }
    Popup {
        id: details
        parent: Overlay.overlay
        width: Math.min(600, parent.width - 30)
        height: 445
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
                Button { text: "Повний запит"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: root.requestAll() }
                Button { text: "Один UART GPS1"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeDualPort(1) }
                Button { text: "Один UART GPS2"; enabled: !!root.vehicle && !root.vehicle.armed && !gnssProbe.busy; onClicked: gnssProbe.probeDualPort(2) }
                Button { text: "Жива телеметрія"; onClicked: telemetryPopup.open() }
                Button { text: "Стоп"; enabled: gnssProbe.busy; onClicked: gnssProbe.cancel() }
                Button { text: "Закрити"; onClicked: details.close() }
            }
            Text { Layout.fillWidth: true; text: "Порт: " + gnssProbe.activePort; font.pixelSize: 12; color: "#F0D363" }
            Text { Layout.fillWidth: true; text: "ZED: " + gnssProbe.zedInfo; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Text { Layout.fillWidth: true; text: "NEO: " + gnssProbe.neoInfo; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Text { Layout.fillWidth: true; text: "FC COMPASS: " + gnssProbe.fcCompassInfo; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Text { Layout.fillWidth: true; text: "Q/F9P COMPASS: " + gnssProbe.externalCompassInfo; wrapMode: Text.WrapAnywhere; font.pixelSize: 12; color: "#FFFFFF" }
            Button {
                text: "Опитати Q/F9P COMPASS"
                enabled: !!root.vehicle && !gnssProbe.busy
                onClicked: gnssProbe.requestExternalCompass()
            }
            Text {
                Layout.fillWidth: true
                text: "SYNC: зелений лише за зовнішнім MAVLink GNSS_SYNC=1 (контроль обох PPS/LED); без цього — очікуємо дані"
                font.pixelSize: 12; wrapMode: Text.WordWrap; color: "#E5BC35"
            }
            Text { Layout.fillWidth: true; text: gnssProbe.statusText; wrapMode: Text.WordWrap; font.pixelSize: 12; color: "#F0D363" }
            Item { Layout.fillHeight: true }
        }
    }
}
