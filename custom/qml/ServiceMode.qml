import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QGroundControl
import QGroundControl.Controls
import QGroundControl.Palette
import QGroundControl.ScreenTools

Rectangle {
    id: setupView
    color: qgcPal.window

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle
    property string currentPage: "summary"
    property bool parametersReady: QGroundControl.multiVehicleManager.parameterReadyVehicleAvailable &&
                                   activeVehicle &&
                                   !activeVehicle.parameterManager.missingParameters
    property var sensorComponent: findSensorComponent()
    property var mpParamsWindow: null

    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    function findSensorComponent() {
        if (!activeVehicle || !activeVehicle.autopilotPlugin) {
            return null
        }

        const components = activeVehicle.autopilotPlugin.vehicleComponents
        if (!components) {
            return null
        }

        // QGC v5.0.8 exposes vehicleComponents as QVariantList, which is a
        // JavaScript array in QML. Prefer length/indexing; keep a fallback for
        // list-model based customs.
        const componentCount = components.length !== undefined ? components.length : components.count
        for (let i = 0; i < componentCount; i++) {
            const component = components[i] !== undefined ? components[i] : components.get(i)
            if (!component) {
                continue
            }
            const name = component.name ? component.name.toLowerCase() : ""
            const source = component.setupSource ? component.setupSource.toString().toLowerCase() : ""
            if (name.indexOf("sensor") >= 0 || source.indexOf("sensor") >= 0) {
                return component
            }
        }
        return null
    }

    function showSummary() {
        currentPage = "summary"
    }

    function showFirmware() {
        currentPage = "firmware"
    }

    function showParameters() {
        currentPage = "parameters"
    }

    function showSensors() {
        currentPage = "sensors"
    }

    function showServoSafety() {
        currentPage = "servoSafety"
    }

    function showMavlinkStatus() {
        currentPage = "mavlinkStatus"
    }

    function showMPParams() {
        if (mpParamsWindow) {
            mpParamsWindow.show()
            mpParamsWindow.raise()
            mpParamsWindow.requestActivate()
            return
        }

        const component = Qt.createComponent("qrc:/qml/QGroundControl/Custom/ServiceMPParamsWindow.qml")
        if (component.status !== Component.Ready) {
            console.warn("MP Params window load failed:", component.errorString())
            return
        }

        mpParamsWindow = component.createObject(null)
        if (mpParamsWindow) {
            mpParamsWindow.show()
            mpParamsWindow.raise()
            mpParamsWindow.requestActivate()
        }
    }

    function reconnectVehicle() {
        if (activeVehicle) {
            activeVehicle.rebootVehicle()
        }
    }

    // VehicleSummary.qml calls this when a summary card is clicked. In service
    // mode only the Sensors component is allowed to open.
    function showVehicleComponentPanel(vehicleComponent) {
        if (!vehicleComponent) {
            return
        }
        const name = vehicleComponent.name ? vehicleComponent.name.toLowerCase() : ""
        const source = vehicleComponent.setupSource ? vehicleComponent.setupSource.toString().toLowerCase() : ""
        if (name.indexOf("sensor") >= 0 || source.indexOf("sensor") >= 0) {
            showSensors()
        }
    }

    function currentPanelSource() {
        if (currentPage === "firmware") {
            return "qrc:/qml/QGroundControl/VehicleSetup/FirmwareUpgrade.qml"
        }
        if (currentPage === "parameters") {
            return parametersReady ? "qrc:/qml/QGroundControl/Custom/ServiceParameterEditor.qml" : ""
        }
        if (currentPage === "sensors") {
            return sensorComponent ? sensorComponent.setupSource : ""
        }
        if (currentPage === "servoSafety") {
            return parametersReady ? "qrc:/qml/QGroundControl/Custom/ServiceServoSafety.qml" : ""
        }
        if (currentPage === "mavlinkStatus") {
            return activeVehicle ? "qrc:/qml/QGroundControl/Custom/ServiceMavlinkStatus.qml" : ""
        }
        if (currentPage === "summary") {
            return activeVehicle ? "qrc:/qml/QGroundControl/VehicleSetup/VehicleSummary.qml" : ""
        }
        return ""
    }

    function emptyPanelMessage() {
        if (currentPage === "parameters") {
            return "Підключіть борт і дочекайтеся повного завантаження параметрів."
        }
        if (currentPage === "sensors") {
            return activeVehicle
                    ? "Для цього борту не знайдено сторінку налаштування датчиків."
                    : "Підключіть борт, щоб відкрити налаштування датчиків."
        }
        if (currentPage === "servoSafety") {
            return "Підключіть борт і дочекайтеся завантаження параметрів."
        }
        if (currentPage === "mavlinkStatus") {
            return "Підключіть борт, щоб відкрити MAVLink Status."
        }
        if (currentPage === "summary") {
            return "Підключіть борт, щоб відкрити огляд."
        }
        return ""
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
                    text: "Спрощ. режим для сервісу"
                    font.pointSize: ScreenTools.mediumFontPointSize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: activeVehicle ? "Борт підключено" : "Борт не підключено"
                    color: activeVehicle ? qgcPal.text : qgcPal.warningText
                    wrapMode: Text.WordWrap
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "Огляд"
                    checked: currentPage === "summary"
                    onClicked: showSummary()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "Прошивка"
                    checked: currentPage === "firmware"
                    onClicked: showFirmware()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "Параметри"
                    checked: currentPage === "parameters"
                    enabled: parametersReady
                    onClicked: showParameters()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "Датчики"
                    checked: currentPage === "sensors"
                    enabled: activeVehicle && sensorComponent
                    onClicked: showSensors()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "Servo/Saf.Mask"
                    checked: currentPage === "servoSafety"
                    enabled: parametersReady && activeVehicle && activeVehicle.apmFirmware
                    onClicked: showServoSafety()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "MAVLink Status"
                    checked: currentPage === "mavlinkStatus"
                    enabled: !!activeVehicle
                    onClicked: showMavlinkStatus()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "MP Params"
                    onClicked: showMPParams()
                }

                QGCButton {
                    Layout.fillWidth: true
                    text: "Реконнект"
                    enabled: !!activeVehicle
                    onClicked: reconnectVehicle()
                }

                Item {
                    Layout.fillHeight: true
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: "Сервісний режим: огляд, прошивка, параметри, MP Params, датчики, Servo/Saf.Mask, MAVLink Status та перезавантаження борту."
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
                source: currentPanelSource()

                // Existing setup pages use this context property when they need
                // to know which autopilot component they belong to.
                property var vehicleComponent: currentPage === "sensors" ? sensorComponent : null
            }

            QGCLabel {
                anchors.centerIn: parent
                width: parent.width * 0.8
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                visible: serviceLoader.source.toString() === "" && emptyPanelMessage() !== ""
                text: emptyPanelMessage()
                font.pointSize: ScreenTools.mediumFontPointSize
            }
        }

        Rectangle {
            id: serviceInfoPanel

            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 32
            Layout.fillHeight: true
            radius: ScreenTools.defaultFontPixelWidth / 2
            color: qgcPal.windowShade

            readonly property real instrumentSize: Math.min(
                                                       ScreenTools.defaultFontPixelHeight * 7.5,
                                                       width * 0.72)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth * 0.65
                spacing: ScreenTools.defaultFontPixelHeight * 0.28

                QGCLabel {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: "GPS info"
                    font.bold: true
                    font.pointSize: ScreenTools.smallFontPointSize
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: gpsGrid.implicitHeight + ScreenTools.defaultFontPixelHeight * 0.8
                    radius: ScreenTools.defaultFontPixelWidth / 3
                    color: qgcPal.window

                    GridLayout {
                        id: gpsGrid
                        anchors.fill: parent
                        anchors.margins: ScreenTools.defaultFontPixelWidth * 0.45
                        columns: 4
                        columnSpacing: ScreenTools.defaultFontPixelWidth * 0.4
                        rowSpacing: ScreenTools.defaultFontPixelHeight * 0.08

                        QGCLabel { text: "Супутники:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel { text: activeVehicle ? activeVehicle.gps.count.valueString : "—"; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel { text: "GPS Fix:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel {
                            Layout.fillWidth: true
                            text: activeVehicle ? activeVehicle.gps.lock.enumStringValue : "—"
                            font.pointSize: ScreenTools.smallFontPointSize
                            elide: Text.ElideRight
                        }

                        QGCLabel { text: "HDOP:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel { text: activeVehicle ? activeVehicle.gps.hdop.valueString : "—"; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel { text: "VDOP:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel { text: activeVehicle ? activeVehicle.gps.vdop.valueString : "—"; font.pointSize: ScreenTools.smallFontPointSize }

                        QGCLabel { text: "Курс GPS:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel { text: activeVehicle ? activeVehicle.gps.courseOverGround.valueString + "°" : "—"; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel { text: "Висота:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel {
                            text: activeVehicle && activeVehicle.coordinate.isValid
                                  ? activeVehicle.coordinate.altitude.toFixed(1) + " м"
                                  : "—"
                            font.pointSize: ScreenTools.smallFontPointSize
                        }

                        QGCLabel { text: "Широта:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel {
                            text: activeVehicle && activeVehicle.coordinate.isValid
                                  ? activeVehicle.coordinate.latitude.toFixed(6)
                                  : "—"
                            font.pointSize: ScreenTools.smallFontPointSize
                        }
                        QGCLabel { text: "Довгота:"; font.bold: true; font.pointSize: ScreenTools.smallFontPointSize }
                        QGCLabel {
                            Layout.fillWidth: true
                            text: activeVehicle && activeVehicle.coordinate.isValid
                                  ? activeVehicle.coordinate.longitude.toFixed(6)
                                  : "—"
                            font.pointSize: ScreenTools.smallFontPointSize
                        }
                    }
                }

                QGCLabel {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: "Компас"
                    font.bold: true
                    font.pointSize: ScreenTools.smallFontPointSize
                }

                QGCCompassWidget {
                    Layout.alignment: Qt.AlignHCenter
                    size: serviceInfoPanel.instrumentSize
                    vehicle: activeVehicle
                    usedByMultipleVehicleList: false
                }

                QGCLabel {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: "Курс %1°".arg(activeVehicle ? activeVehicle.heading.rawValue.toFixed(0) : "—")
                    font.pointSize: ScreenTools.smallFontPointSize
                }

                QGCLabel {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: "Положення польотника"
                    font.bold: true
                    font.pointSize: ScreenTools.smallFontPointSize
                }

                QGCAttitudeWidget {
                    Layout.alignment: Qt.AlignHCenter
                    size: serviceInfoPanel.instrumentSize
                    vehicle: activeVehicle
                    showPitch: true
                    showHeading: true
                }

                QGCLabel {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: "Крен %1°   Тангаж %2°"
                          .arg(activeVehicle ? activeVehicle.roll.rawValue.toFixed(1) : "—")
                          .arg(activeVehicle ? activeVehicle.pitch.rawValue.toFixed(1) : "—")
                    font.pointSize: ScreenTools.smallFontPointSize
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
