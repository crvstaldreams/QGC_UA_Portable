import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtLocation
import QtPositioning

import QGroundControl
import QGroundControl.Controls
import QGroundControl.Palette
import QGroundControl.ScreenTools
import QGroundControl.FlightMap

Rectangle {
    id: setupView
    color: qgcPal.window

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle
    property string currentPage: "summary"
    property bool parametersReady: QGroundControl.multiVehicleManager.parameterReadyVehicleAvailable &&
                                   activeVehicle &&
                                   !activeVehicle.parameterManager.missingParameters
    property var sensorComponent: findSensorComponent()

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

        for (let i = 0; i < components.count; i++) {
            const component = components.get(i)
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

                Item {
                    Layout.fillHeight: true
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: "Сервісний режим: огляд стану, прошивка, параметри та датчики без зайвих сторінок налаштування."
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
                property var vehicleComponent: sensorComponent
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
            Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 30
            Layout.fillHeight: true
            radius: ScreenTools.defaultFontPixelWidth / 2
            color: qgcPal.windowShade

            QGCFlickable {
                id: serviceInfoScroll
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth * 0.75
                contentWidth: width
                contentHeight: inspectorColumn.height
                flickableDirection: Flickable.VerticalFlick
                clip: true

                Column {
                    id: inspectorColumn
                    width: serviceInfoScroll.width
                    spacing: ScreenTools.defaultFontPixelHeight * 0.75

                    QGCLabel {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "Положення польотника"
                        font.pointSize: ScreenTools.mediumFontPointSize
                        font.bold: true
                    }

                    QGCAttitudeWidget {
                        anchors.horizontalCenter: parent.horizontalCenter
                        size: Math.min(inspectorColumn.width * 0.72, ScreenTools.defaultFontPixelHeight * 14)
                        vehicle: activeVehicle
                        showPitch: true
                        showHeading: true
                    }

                    RowLayout {
                        width: parent.width

                        QGCLabel {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: "Крен\n%1°".arg(activeVehicle ? activeVehicle.roll.rawValue.toFixed(1) : "—")
                        }

                        QGCLabel {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: "Тангаж\n%1°".arg(activeVehicle ? activeVehicle.pitch.rawValue.toFixed(1) : "—")
                        }
                    }

                    QGCLabel {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "Міні-карта"
                        font.bold: true
                    }

                    Rectangle {
                        width: parent.width
                        height: Math.max(ScreenTools.defaultFontPixelHeight * 10, width * 0.55)
                        radius: ScreenTools.defaultFontPixelWidth / 3
                        color: qgcPal.window
                        clip: true

                        FlightMap {
                            id: miniMap
                            anchors.fill: parent
                            mapName: "serviceMiniMap"
                            allowGCSLocationCenter: false
                            allowVehicleLocationCenter: true
                            planView: false
                            zoomLevel: 16
                            center: activeVehicle && activeVehicle.coordinate.isValid
                                    ? activeVehicle.coordinate
                                    : QGroundControl.flightMapPosition

                            MapQuickItem {
                                visible: activeVehicle && activeVehicle.coordinate.isValid
                                coordinate: activeVehicle ? activeVehicle.coordinate : QtPositioning.coordinate()
                                anchorPoint.x: vehicleArrow.width / 2
                                anchorPoint.y: vehicleArrow.height / 2

                                sourceItem: Image {
                                    id: vehicleArrow
                                    width: ScreenTools.defaultFontPixelHeight * 2.2
                                    height: width
                                    source: "/res/QGCLogoArrow.svg"
                                    mipmap: true
                                    fillMode: Image.PreserveAspectFit
                                    transform: Rotation {
                                        origin.x: vehicleArrow.width / 2
                                        origin.y: vehicleArrow.height / 2
                                        angle: activeVehicle ? activeVehicle.heading.rawValue : 0
                                    }
                                }
                            }
                        }
                    }

                    QGCLabel {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "GPS"
                        font.bold: true
                    }

                    Rectangle {
                        width: parent.width
                        height: gpsGrid.implicitHeight + (ScreenTools.defaultFontPixelHeight * 1.5)
                        radius: ScreenTools.defaultFontPixelWidth / 3
                        color: qgcPal.window

                        GridLayout {
                            id: gpsGrid
                            anchors.fill: parent
                            anchors.margins: ScreenTools.defaultFontPixelWidth
                            columns: 2
                            columnSpacing: ScreenTools.defaultFontPixelWidth
                            rowSpacing: ScreenTools.defaultFontPixelHeight / 4

                            QGCLabel { text: "Супутники:"; font.bold: true }
                            QGCLabel { text: activeVehicle ? activeVehicle.gps.count.valueString : "—" }

                            QGCLabel { text: "GPS Fix:"; font.bold: true }
                            QGCLabel { text: activeVehicle ? activeVehicle.gps.lock.enumStringValue : "—" }

                            QGCLabel { text: "HDOP:"; font.bold: true }
                            QGCLabel { text: activeVehicle ? activeVehicle.gps.hdop.valueString : "—" }

                            QGCLabel { text: "VDOP:"; font.bold: true }
                            QGCLabel { text: activeVehicle ? activeVehicle.gps.vdop.valueString : "—" }

                            QGCLabel { text: "Курс GPS:"; font.bold: true }
                            QGCLabel { text: activeVehicle ? activeVehicle.gps.courseOverGround.valueString + "°" : "—" }

                            QGCLabel { text: "Широта:"; font.bold: true }
                            QGCLabel { text: activeVehicle && activeVehicle.coordinate.isValid ? activeVehicle.coordinate.latitude.toFixed(6) : "—" }

                            QGCLabel { text: "Довгота:"; font.bold: true }
                            QGCLabel { text: activeVehicle && activeVehicle.coordinate.isValid ? activeVehicle.coordinate.longitude.toFixed(6) : "—" }

                            QGCLabel { text: "Висота:"; font.bold: true }
                            QGCLabel { text: activeVehicle && activeVehicle.coordinate.isValid ? activeVehicle.coordinate.altitude.toFixed(1) + " м" : "—" }
                        }
                    }

                    QGCLabel {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "Компас"
                        font.bold: true
                    }

                    QGCCompassWidget {
                        anchors.horizontalCenter: parent.horizontalCenter
                        size: Math.min(inspectorColumn.width * 0.75, ScreenTools.defaultFontPixelHeight * 13)
                        vehicle: activeVehicle
                        usedByMultipleVehicleList: false
                    }

                    QGCLabel {
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "Курс: %1°".arg(activeVehicle ? activeVehicle.heading.rawValue.toFixed(0) : "—")
                    }
                }
            }
        }
    }
}
