import QtQuick
import QtQuick.Controls
import QtLocation
import QtPositioning

import QGroundControl
import QGroundControl.Controls
import QGroundControl.FlightMap
import QGroundControl.Palette
import QGroundControl.ScreenTools

Item {
    id: root

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle

    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    FlightMap {
        id: serviceMap
        anchors.fill: parent
        mapName: "ServiceMap"
        allowGCSLocationCenter: true
        allowVehicleLocationCenter: true
        planView: false
        zoomLevel: QGroundControl.flightMapZoom
        center: QGroundControl.flightMapPosition

        onZoomLevelChanged: QGroundControl.flightMapZoom = zoomLevel
        onCenterChanged: QGroundControl.flightMapPosition = center

        MapPolyline {
            id: trajectoryPolyline
            line.width: 3
            line.color: qgcPal.buttonHighlight
            z: QGroundControl.zOrderTrajectoryLines
            path: root.activeVehicle ? root.activeVehicle.trajectoryPoints.list() : []

            Connections {
                target: root.activeVehicle ? root.activeVehicle.trajectoryPoints : null
                function onPointAdded(coordinate) { trajectoryPolyline.addCoordinate(coordinate) }
                function onUpdateLastPoint(coordinate) {
                    if (trajectoryPolyline.pathLength() > 0) {
                        trajectoryPolyline.replaceCoordinate(trajectoryPolyline.pathLength() - 1, coordinate)
                    }
                }
                function onPointsCleared() { trajectoryPolyline.path = [] }
            }
        }

        MapItemView {
            model: QGroundControl.multiVehicleManager.vehicles

            delegate: VehicleMapItem {
                vehicle: object
                coordinate: object.coordinate
                map: serviceMap
                size: ScreenTools.defaultFontPixelHeight * 3
                z: QGroundControl.zOrderVehicles
            }
        }
    }

    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: ScreenTools.defaultFontPixelWidth * 0.7
        width: mapControls.implicitWidth + ScreenTools.defaultFontPixelWidth
        height: mapControls.implicitHeight + ScreenTools.defaultFontPixelHeight * 0.6
        radius: ScreenTools.defaultBorderRadius
        color: qgcPal.windowShade
        border.color: qgcPal.buttonBorder
        border.width: 1
        opacity: 0.94

        Row {
            id: mapControls
            anchors.centerIn: parent
            spacing: ScreenTools.defaultFontPixelWidth * 0.45

            QGCButton {
                text: "На борт"
                enabled: root.activeVehicle && root.activeVehicle.coordinate.isValid
                onClicked: {
                    serviceMap.center = root.activeVehicle.coordinate
                    if (serviceMap.zoomLevel < 16) {
                        serviceMap.zoomLevel = 16
                    }
                }
            }

            QGCButton {
                text: "На GCS"
                enabled: serviceMap.gcsPosition.isValid
                onClicked: {
                    serviceMap.center = serviceMap.gcsPosition
                    if (serviceMap.zoomLevel < 16) {
                        serviceMap.zoomLevel = 16
                    }
                }
            }
        }
    }
}
