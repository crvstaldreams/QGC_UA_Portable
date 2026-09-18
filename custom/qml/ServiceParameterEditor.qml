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
    property bool hasSelectedFact: selectedFact && selectedFact.componentId > 0
    property real rowHeight: ScreenTools.defaultFontPixelHeight * 2.15

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

    ColumnLayout {
        anchors.fill: parent
        spacing: ScreenTools.defaultFontPixelHeight / 2

        RowLayout {
            Layout.fillWidth: true
            spacing: ScreenTools.defaultFontPixelWidth

            QGCTextField {
                id: searchText
                Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 24
                placeholderText: qsTr("Пошук за назвою або описом")
                onDisplayTextChanged: controller.searchText = displayText
            }

            QGCButton {
                text: qsTr("Очистити")
                onClicked: {
                    searchText.text = ""
                    controller.searchText = ""
                }
            }

            QGCCheckBox {
                text: qsTr("Тільки змінені")
                checked: controller.showModifiedOnly
                visible: root.activeVehicle && root.activeVehicle.px4Firmware
                onClicked: controller.showModifiedOnly = checked
            }

            Item {
                Layout.fillWidth: true
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
                Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 23
                Layout.fillHeight: true
                radius: ScreenTools.defaultFontPixelWidth / 3
                color: qgcPal.window

                QGCFlickable {
                    anchors.fill: parent
                    anchors.margins: ScreenTools.defaultFontPixelWidth / 2
                    contentHeight: categoryColumn.height
                    flickableDirection: Flickable.VerticalFlick
                    clip: true

                    ColumnLayout {
                        id: categoryColumn
                        width: parent.width
                        spacing: ScreenTools.defaultFontPixelHeight / 4

                        QGCLabel {
                            Layout.fillWidth: true
                            text: qsTr("Дерево параметрів")
                            font.bold: true
                            font.pointSize: ScreenTools.mediumFontPointSize
                        }

                        Repeater {
                            model: controller.categories

                            Column {
                                Layout.fillWidth: true
                                spacing: ScreenTools.defaultFontPixelHeight / 4

                                SectionHeader {
                                    id: categoryHeader
                                    width: parent.width
                                    text: object.name
                                    checked: object === controller.currentCategory

                                    onCheckedChanged: {
                                        if (checked) {
                                            controller.currentCategory = object
                                        }
                                    }
                                }

                                Repeater {
                                    model: categoryHeader.checked ? object.groups : 0

                                    QGCButton {
                                        width: categoryHeader.width
                                        height: root.rowHeight
                                        text: object.name
                                        checkable: true
                                        autoExclusive: true
                                        checked: object === controller.currentGroup

                                        onClicked: {
                                            checked = true
                                            controller.currentGroup = object
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScreenTools.defaultFontPixelHeight / 2

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
                                           ? ScreenTools.defaultFontPixelWidth * 18
                                           : (column === 1
                                              ? ScreenTools.defaultFontPixelWidth * 15
                                              : ScreenTools.defaultFontPixelWidth * 34)
                            implicitHeight: Math.max(root.rowHeight, cellLabel.implicitHeight + ScreenTools.defaultFontPixelHeight / 2)
                            color: root.hasSelectedFact && fact === root.selectedFact
                                   ? qgcPal.buttonHighlight
                                   : (row % 2 ? qgcPal.windowShade : qgcPal.window)

                            QGCLabel {
                                id: cellLabel
                                anchors.fill: parent
                                anchors.margins: ScreenTools.defaultFontPixelWidth / 3
                                text: column === 1 ? valueText() : display
                                color: root.hasSelectedFact && fact === root.selectedFact
                                       ? qgcPal.buttonHighlightText
                                       : qgcPal.text
                                wrapMode: column === 2 ? Text.WordWrap : Text.NoWrap
                                elide: column === 2 ? Text.ElideNone : Text.ElideRight

                                function valueText() {
                                    if (!fact) {
                                        return ""
                                    }
                                    if (fact.enumStrings.length === 0) {
                                        return fact.valueString + (fact.units === "" ? "" : " " + fact.units)
                                    }
                                    if (fact.bitmaskStrings.length !== 0) {
                                        return fact.selectedBitmaskStrings.join(", ")
                                    }
                                    return fact.enumStringValue
                                }
                            }

                            QGCMouseArea {
                                anchors.fill: parent
                                onClicked: root.selectedFact = fact
                                onDoubleClicked: {
                                    root.selectedFact = fact
                                    editorDialogComponent.createObject(mainWindow).open()
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 13
                    radius: ScreenTools.defaultFontPixelWidth / 3
                    color: qgcPal.window

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: ScreenTools.defaultFontPixelWidth
                        spacing: ScreenTools.defaultFontPixelHeight / 3

                        RowLayout {
                            Layout.fillWidth: true

                            QGCLabel {
                                Layout.fillWidth: true
                                text: root.hasSelectedFact ? root.selectedFact.name : qsTr("Виберіть параметр")
                                font.bold: true
                                font.pointSize: ScreenTools.mediumFontPointSize
                            }

                            QGCButton {
                                text: qsTr("Редагувати")
                                enabled: root.hasSelectedFact && !root.selectedFact.readOnly
                                onClicked: editorDialogComponent.createObject(mainWindow).open()
                            }
                        }

                        QGCFlickable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            contentHeight: descriptionColumn.height
                            flickableDirection: Flickable.VerticalFlick
                            clip: true

                            ColumnLayout {
                                id: descriptionColumn
                                width: parent.width
                                spacing: ScreenTools.defaultFontPixelHeight / 3

                                QGCLabel {
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                    text: root.hasSelectedFact
                                          ? (root.selectedFact.longDescription !== ""
                                             ? root.selectedFact.longDescription
                                             : root.selectedFact.shortDescription)
                                          : qsTr("Тут відображатиметься призначення параметра, допустимий діапазон і типове значення.")
                                }

                                QGCLabel {
                                    visible: root.hasSelectedFact
                                    text: root.hasSelectedFact
                                          ? qsTr("Поточне: %1 %2").arg(root.selectedFact.valueString).arg(root.selectedFact.units)
                                          : ""
                                    font.bold: true
                                }

                                QGCLabel {
                                    visible: root.hasSelectedFact
                                    text: root.hasSelectedFact
                                          ? qsTr("Мін.: %1    Макс.: %2    Типове: %3")
                                                .arg(root.selectedFact.minString)
                                                .arg(root.selectedFact.maxString)
                                                .arg(root.selectedFact.defaultValueAvailable ? root.selectedFact.defaultValueString : "—")
                                          : ""
                                    wrapMode: Text.WordWrap
                                }

                                QGCLabel {
                                    visible: root.hasSelectedFact && root.selectedFact.vehicleRebootRequired
                                    text: qsTr("Після зміни потрібне перезавантаження борту.")
                                    color: qgcPal.warningText
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
