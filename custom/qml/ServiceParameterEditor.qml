import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import QGroundControl
import QGroundControl.Controls
import QGroundControl.Controllers
import QGroundControl.FactSystem
import QGroundControl.Palette
import QGroundControl.ScreenTools

Item {
    id: root

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle
    property Fact selectedFact: Fact { }
    property bool hasSelectedFact: selectedFact && selectedFact.name !== ""
    property real rowHeight: ScreenTools.defaultFontPixelHeight * 2.1
    property string treeQuery: ""

    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    ParameterEditorController {
        id: controller
    }

    Component {
        id: editorDialogComponent

        ParameterEditorDialog {
            fact: root.selectedFact
            showRCToParam: false
        }
    }

    function applyTreeQuery(query) {
        root.treeQuery = query
        searchText.text = query
        controller.searchText = query
    }

    ListModel {
        id: serviceTreeModel

        ListElement { title: "ВСІ ПАРАМЕТРИ"; query: ""; header: false; level: 0 }

        ListElement { title: "СИСТЕМА / ПЛАТА"; query: ""; header: true; level: 0 }
        ListElement { title: "Board (BRD_)"; query: "BRD_"; header: false; level: 1 }
        ListElement { title: "Safety (BRD_SAFETY)"; query: "BRD_SAFETY"; header: false; level: 1 }
        ListElement { title: "Serial / TELEM (SERIAL_)"; query: "SERIAL_"; header: false; level: 1 }
        ListElement { title: "Живлення (BATT_)"; query: "BATT_"; header: false; level: 1 }

        ListElement { title: "ДАТЧИКИ"; query: ""; header: true; level: 0 }
        ListElement { title: "GPS"; query: "GPS_"; header: false; level: 1 }
        ListElement { title: "Компас"; query: "COMPASS_"; header: false; level: 1 }
        ListElement { title: "INS / IMU"; query: "INS_"; header: false; level: 1 }
        ListElement { title: "EKF3"; query: "EK3_"; header: false; level: 1 }
        ListElement { title: "AHRS"; query: "AHRS_"; header: false; level: 1 }

        ListElement { title: "ВИХОДИ / КЕРУВАННЯ"; query: ""; header: true; level: 0 }
        ListElement { title: "Servo outputs"; query: "SERVO"; header: false; level: 1 }
        ListElement { title: "Motors"; query: "MOT_"; header: false; level: 1 }
        ListElement { title: "RC"; query: "RC"; header: false; level: 1 }
        ListElement { title: "Attitude control"; query: "ATC_"; header: false; level: 1 }
        ListElement { title: "Arming"; query: "ARMING_"; header: false; level: 1 }
        ListElement { title: "Failsafe"; query: "FS_"; header: false; level: 1 }

        ListElement { title: "НАВІГАЦІЯ"; query: ""; header: true; level: 0 }
        ListElement { title: "Waypoint navigation"; query: "WPNAV_"; header: false; level: 1 }
        ListElement { title: "Loiter"; query: "LOIT_"; header: false; level: 1 }
        ListElement { title: "RTL"; query: "RTL_"; header: false; level: 1 }
        ListElement { title: "Landing"; query: "LAND_"; header: false; level: 1 }
        ListElement { title: "Position control"; query: "PSC_"; header: false; level: 1 }

        ListElement { title: "СЕРВІС"; query: ""; header: true; level: 0 }
        ListElement { title: "Logging"; query: "LOG_"; header: false; level: 1 }
        ListElement { title: "Notifications"; query: "NTF_"; header: false; level: 1 }
        ListElement { title: "OSD"; query: "OSD_"; header: false; level: 1 }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: ScreenTools.defaultFontPixelHeight / 2

        RowLayout {
            Layout.fillWidth: true
            spacing: ScreenTools.defaultFontPixelWidth

            QGCTextField {
                id: searchText
                Layout.fillWidth: true
                placeholderText: qsTr("Пошук параметра")
                onDisplayTextChanged: {
                    controller.searchText = displayText
                    if (displayText !== root.treeQuery) {
                        root.treeQuery = ""
                    }
                }
            }

            QGCButton {
                text: qsTr("Очистити")
                onClicked: root.applyTreeQuery("")
            }

            QGCCheckBox {
                text: qsTr("Тільки змінені")
                checked: controller.showModifiedOnly
                visible: root.activeVehicle && root.activeVehicle.px4Firmware
                onClicked: controller.showModifiedOnly = checked
            }

            QGCButton {
                text: qsTr("Оновити")
                onClicked: controller.refresh()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScreenTools.defaultFontPixelWidth

            Rectangle {
                Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 25
                Layout.fillHeight: true
                radius: ScreenTools.defaultFontPixelWidth / 3
                color: qgcPal.window

                QGCFlickable {
                    anchors.fill: parent
                    anchors.margins: ScreenTools.defaultFontPixelWidth / 2
                    contentWidth: width
                    contentHeight: treeColumn.height
                    flickableDirection: Flickable.VerticalFlick
                    clip: true

                    Column {
                        id: treeColumn
                        width: parent.width
                        spacing: ScreenTools.defaultFontPixelHeight * 0.18

                        QGCLabel {
                            width: parent.width
                            text: qsTr("Дерево параметрів")
                            font.bold: true
                            font.pointSize: ScreenTools.mediumFontPointSize
                            bottomPadding: ScreenTools.defaultFontPixelHeight * 0.25
                        }

                        Repeater {
                            model: serviceTreeModel

                            Item {
                                width: treeColumn.width
                                height: header
                                        ? treeHeader.implicitHeight + ScreenTools.defaultFontPixelHeight * 0.45
                                        : root.rowHeight

                                QGCLabel {
                                    id: treeHeader
                                    visible: header
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.bottom: parent.bottom
                                    text: title
                                    font.bold: true
                                    font.pointSize: ScreenTools.smallFontPointSize
                                    color: qgcPal.text
                                }

                                QGCButton {
                                    visible: !header
                                    anchors.fill: parent
                                    anchors.leftMargin: level * ScreenTools.defaultFontPixelWidth * 1.2
                                    text: title
                                    checkable: true
                                    checked: root.treeQuery === query &&
                                             (query !== "" || index === 0)
                                    onClicked: root.applyTreeQuery(query)
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScreenTools.defaultFontPixelHeight * 0.3

                RowLayout {
                    Layout.fillWidth: true

                    QGCLabel {
                        Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 22
                        text: qsTr("Параметр")
                        font.bold: true
                    }

                    QGCLabel {
                        Layout.fillWidth: true
                        text: qsTr("Значення")
                        font.bold: true
                    }

                    QGCButton {
                        text: qsTr("Редагувати")
                        enabled: root.hasSelectedFact && !root.selectedFact.readOnly
                        onClicked: editorDialogComponent.createObject(mainWindow).open()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: ScreenTools.defaultFontPixelWidth / 3
                    color: qgcPal.window

                    TableView {
                        id: tableView
                        anchors.fill: parent
                        anchors.margins: ScreenTools.defaultFontPixelWidth / 2
                        columnSpacing: ScreenTools.defaultFontPixelWidth / 2
                        rowSpacing: 1
                        clip: true
                        model: controller.parameters

                        delegate: Rectangle {
                            implicitWidth: column === 0
                                           ? ScreenTools.defaultFontPixelWidth * 22
                                           : (column === 1
                                              ? Math.max(ScreenTools.defaultFontPixelWidth * 24,
                                                         tableView.width - ScreenTools.defaultFontPixelWidth * 25)
                                              : 0)
                            implicitHeight: column < 2 ? root.rowHeight : 0
                            visible: column < 2
                            color: root.hasSelectedFact && fact === root.selectedFact
                                   ? qgcPal.buttonHighlight
                                   : (row % 2 ? qgcPal.windowShade : qgcPal.window)

                            QGCLabel {
                                anchors.fill: parent
                                anchors.margins: ScreenTools.defaultFontPixelWidth / 3
                                text: column === 1 ? valueText() : display
                                color: root.hasSelectedFact && fact === root.selectedFact
                                       ? qgcPal.buttonHighlightText
                                       : qgcPal.text
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter

                                function valueText() {
                                    if (!fact) {
                                        return ""
                                    }
                                    if (fact.bitmaskStrings.length !== 0) {
                                        return fact.selectedBitmaskStrings.join(", ")
                                    }
                                    if (fact.enumStrings.length !== 0) {
                                        return fact.enumStringValue
                                    }
                                    return fact.valueString + (fact.units === "" ? "" : " " + fact.units)
                                }
                            }

                            QGCMouseArea {
                                anchors.fill: parent
                                onClicked: root.selectedFact = fact
                                onDoubleClicked: {
                                    root.selectedFact = fact
                                    if (!fact.readOnly) {
                                        editorDialogComponent.createObject(mainWindow).open()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
