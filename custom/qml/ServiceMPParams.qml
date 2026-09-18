import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

import QGroundControl
import QGroundControl.Controls
import QGroundControl.Palette
import QGroundControl.ScreenTools
import QGroundControl.Custom 1.0

Item {
    id: root

    property var activeVehicle: QGroundControl.multiVehicleManager.activeVehicle
    property var linkManager: QGroundControl.linkManager
    property var appSettings: QGroundControl.settingsManager.appSettings
    property var mpLinkConfig: null
    property var tableWidths: [
        ScreenTools.defaultFontPixelWidth * 20,
        ScreenTools.defaultFontPixelWidth * 14,
        ScreenTools.defaultFontPixelWidth * 12,
        ScreenTools.defaultFontPixelWidth * 8,
        ScreenTools.defaultFontPixelWidth * 24,
        ScreenTools.defaultFontPixelWidth * 40,
        ScreenTools.defaultFontPixelWidth * 5
    ]

    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    MPParamsController {
        id: controller
    }

    function connectSelectedCom() {
        if (portCombo.currentIndex < 0 || portCombo.currentIndex >= linkManager.serialPorts.length) {
            return
        }
        disconnectSelectedCom()

        const portPath = linkManager.serialPorts[portCombo.currentIndex]
        const config = linkManager.createConfiguration(LinkConfiguration.TypeSerial, "MP Params " + portPath)
        if (!config) {
            return
        }

        config.dynamic = true
        config.portName = portPath
        config.baud = parseInt(baudCombo.currentText)
        linkManager.endCreateConfiguration(config)
        mpLinkConfig = config
        linkManager.createConnectedLink(config)
    }

    function disconnectSelectedCom() {
        if (mpLinkConfig) {
            linkManager.removeConfiguration(mpLinkConfig)
            mpLinkConfig = null
        }
    }

    Component.onDestruction: disconnectSelectedCom()

    QGCFileDialog {
        id: loadDialog
        folder: appSettings.parameterSavePath
        nameFilters: [ "Mission Planner Params (*.param *.parm)", "All Files (*)" ]
        title: "Завантажити MP параметри"
        onAcceptedForLoad: (file) => controller.loadMpFile(file)
    }

    QGCFileDialog {
        id: saveDialog
        folder: appSettings.parameterSavePath
        nameFilters: [ "Mission Planner Params (*.param *.parm)", "All Files (*)" ]
        defaultSuffix: "param"
        title: "Зберегти MP параметри"
        onAcceptedForSave: (file) => controller.saveMpFile(file)
    }

    QGCFileDialog {
        id: compareDialog
        folder: appSettings.parameterSavePath
        nameFilters: [ "Mission Planner Params (*.param *.parm)", "All Files (*)" ]
        title: "Звірити параметри з MP файлом"
        onAcceptedForLoad: (file) => {
            if (controller.compareMpFile(file)) {
                comparePopup.open()
            }
        }
    }

    Popup {
        id: comparePopup
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        width: Math.min(root.width * 0.82, ScreenTools.defaultFontPixelWidth * 115)
        height: Math.min(root.height * 0.82, ScreenTools.defaultFontPixelHeight * 36)
        x: (root.width - width) / 2
        y: (root.height - height) / 2

        background: Rectangle {
            color: qgcPal.window
            border.color: qgcPal.buttonBorder
            border.width: 2
            radius: ScreenTools.defaultBorderRadius
        }

        contentItem: ColumnLayout {
            spacing: ScreenTools.defaultFontPixelHeight * 0.5

            RowLayout {
                Layout.fillWidth: true

                QGCLabel {
                    Layout.fillWidth: true
                    text: "Compare Params — відмінностей: " + controller.compareCount
                    font.bold: true
                    font.pointSize: ScreenTools.largeFontPointSize
                }

                QGCButton {
                    text: "Вибрати все"
                    onClicked: controller.setAllCompareUse(true)
                }

                QGCButton {
                    text: "Зняти все"
                    onClicked: controller.setAllCompareUse(false)
                }

                QGCButton {
                    text: "Закрити"
                    onClicked: comparePopup.close()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 1

                Repeater {
                    model: ["Use", "Parameter", "Current", "File"]
                    Rectangle {
                        Layout.preferredWidth: index === 0
                                               ? ScreenTools.defaultFontPixelWidth * 7
                                               : (index === 1
                                                  ? ScreenTools.defaultFontPixelWidth * 30
                                                  : ScreenTools.defaultFontPixelWidth * 22)
                        Layout.fillWidth: index === 1
                        Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 2
                        color: qgcPal.windowShadeDark
                        border.color: qgcPal.buttonBorder
                        border.width: 1

                        QGCLabel {
                            anchors.centerIn: parent
                            text: modelData
                            font.bold: true
                        }
                    }
                }
            }

            TableView {
                id: compareTable
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: controller.compareModel
                columnSpacing: 1
                rowSpacing: 1

                columnWidthProvider: function(column) {
                    if (column === 0) return ScreenTools.defaultFontPixelWidth * 7
                    if (column === 1) return Math.max(ScreenTools.defaultFontPixelWidth * 30,
                                                      compareTable.width - ScreenTools.defaultFontPixelWidth * 51)
                    return ScreenTools.defaultFontPixelWidth * 22
                }

                delegate: Rectangle {
                    implicitWidth: compareTable.columnWidthProvider(column)
                    implicitHeight: ScreenTools.defaultFontPixelHeight * 2.1
                    color: row % 2 ? qgcPal.windowShade : qgcPal.window
                    border.color: qgcPal.groupBorder
                    border.width: 1

                    QGCCheckBox {
                        visible: column === 0
                        anchors.centerIn: parent
                        checked: model.use
                        onClicked: controller.setCompareUse(row, checked)
                    }

                    QGCLabel {
                        visible: column !== 0
                        anchors.fill: parent
                        anchors.margins: ScreenTools.defaultFontPixelWidth * 0.35
                        text: model.display
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true

                QGCLabel {
                    Layout.fillWidth: true
                    text: "Вибрані значення спочатку потраплять у чергу змін. Фактичний запис — тільки через Write Params."
                    wrapMode: Text.WordWrap
                }

                QGCButton {
                    text: "Додати вибране"
                    enabled: controller.compareCount > 0
                    onClicked: {
                        controller.applyCompareSelection()
                        comparePopup.close()
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: ScreenTools.defaultFontPixelHeight * 0.45

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: connectionRow.implicitHeight + ScreenTools.defaultFontPixelHeight
            color: qgcPal.windowShade
            radius: ScreenTools.defaultBorderRadius
            border.color: qgcPal.groupBorder
            border.width: 1

            RowLayout {
                id: connectionRow
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth * 0.7
                spacing: ScreenTools.defaultFontPixelWidth * 0.7

                QGCLabel {
                    text: "COM:"
                    font.bold: true
                }

                QGCComboBox {
                    id: portCombo
                    Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 26
                    model: linkManager.serialPortStrings
                    enabled: !mpLinkConfig
                }

                QGCLabel {
                    text: "Baud:"
                    font.bold: true
                }

                QGCComboBox {
                    id: baudCombo
                    Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 14
                    model: linkManager.serialBaudRates
                    enabled: !mpLinkConfig

                    Component.onCompleted: {
                        const preferred = ["115200", "57600"]
                        for (let p = 0; p < preferred.length; p++) {
                            const idx = linkManager.serialBaudRates.indexOf(preferred[p])
                            if (idx >= 0) {
                                currentIndex = idx
                                break
                            }
                        }
                    }
                }

                QGCButton {
                    text: mpLinkConfig && mpLinkConfig.link ? "Disconnect" : "Connect"
                    enabled: portCombo.currentIndex >= 0
                    onClicked: {
                        if (mpLinkConfig) {
                            disconnectSelectedCom()
                        } else {
                            connectSelectedCom()
                        }
                    }
                }

                QGCLabel {
                    Layout.fillWidth: true
                    text: mpLinkConfig
                          ? ((mpLinkConfig.link ? "Підключено: " : "Підключення: ") +
                             mpLinkConfig.portDisplayName + " @ " + mpLinkConfig.baud)
                          : (activeVehicle ? "Активний MAVLink-борт підключений" : "COM не підключено")
                    color: (mpLinkConfig && mpLinkConfig.link) || activeVehicle ? qgcPal.text : qgcPal.warningText
                    elide: Text.ElideRight
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: ScreenTools.defaultFontPixelWidth * 0.6

            QGCButton {
                text: "Read Params"
                enabled: !!activeVehicle
                onClicked: controller.refresh()
            }

            QGCButton {
                text: "Write Params (" + controller.changedCount + ")"
                enabled: !!activeVehicle && controller.changedCount > 0
                onClicked: {
                    mainWindow.showMessageDialog(
                        "Write Params",
                        "Буде записано " + controller.changedCount + " параметрів:\n\n" +
                            controller.pendingSummary() +
                            "\n\nПродовжити?",
                        Dialog.Cancel | Dialog.Ok,
                        function() { controller.writePending() })
                }
            }

            QGCButton {
                text: "Load File"
                onClicked: loadDialog.openForLoad()
            }

            QGCButton {
                text: "Save File"
                enabled: controller.parameterCount > 0
                onClicked: saveDialog.openForSave()
            }

            QGCButton {
                text: "Compare"
                enabled: !!activeVehicle
                onClicked: compareDialog.openForLoad()
            }

            QGCButton {
                text: "Discard Changes"
                enabled: controller.changedCount > 0
                onClicked: controller.discardPending()
            }

            Item { Layout.fillWidth: true }

            QGCCheckBox {
                text: "Modified only"
                checked: controller.showModifiedOnly
                onClicked: controller.showModifiedOnly = checked
            }
        }

        ProgressBar {
            Layout.fillWidth: true
            visible: controller.loadProgress > 0 && controller.loadProgress < 1
            from: 0
            to: 1
            value: controller.loadProgress
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: ScreenTools.defaultFontPixelWidth * 0.6

            Rectangle {
                Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 26
                Layout.fillHeight: true
                color: qgcPal.window
                radius: ScreenTools.defaultBorderRadius
                border.color: qgcPal.groupBorder
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: ScreenTools.defaultFontPixelWidth * 0.5
                    spacing: ScreenTools.defaultFontPixelHeight * 0.3

                    QGCLabel {
                        Layout.fillWidth: true
                        text: "MP Parameter Tree"
                        font.bold: true
                    }

                    TreeView {
                        id: paramTree
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: controller.treeModel

                        delegate: TreeViewDelegate {
                            implicitWidth: paramTree.width
                            text: model.display
                            onClicked: controller.selectTreeFilter(model.prefix, model.leaf)
                        }

                        Component.onCompleted: expand(0)
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: ScreenTools.defaultFontPixelHeight * 0.3

                RowLayout {
                    Layout.fillWidth: true

                    QGCTextField {
                        id: searchField
                        Layout.fillWidth: true
                        placeholderText: "Search parameter / description"
                        onDisplayTextChanged: controller.searchText = displayText
                    }

                    QGCButton {
                        text: "Clear"
                        onClicked: {
                            searchField.text = ""
                            controller.searchText = ""
                            controller.selectTreeFilter("", false)
                        }
                    }

                    QGCLabel {
                        text: "Params: " + controller.parameterCount + "   Changes: " + controller.changedCount
                        font.bold: true
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Repeater {
                        model: ["Parameter", "Value", "Default", "Units", "Options", "Description", "Fav"]
                        Rectangle {
                            Layout.preferredWidth: root.tableWidths[index]
                            Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 2
                            color: qgcPal.windowShadeDark
                            border.color: qgcPal.buttonBorder
                            border.width: 1

                            QGCLabel {
                                anchors.centerIn: parent
                                text: modelData
                                font.bold: true
                            }
                        }
                    }
                }

                TableView {
                    id: paramsTable
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: controller.parameters
                    columnSpacing: 1
                    rowSpacing: 1

                    columnWidthProvider: function(column) {
                        return root.tableWidths[column]
                    }

                    delegate: Rectangle {
                        implicitWidth: root.tableWidths[column]
                        implicitHeight: ScreenTools.defaultFontPixelHeight * 2.25
                        color: model.changed
                               ? qgcPal.buttonHighlight
                               : (row % 2 ? qgcPal.windowShade : qgcPal.window)
                        border.color: qgcPal.groupBorder
                        border.width: 1

                        QGCTextField {
                            visible: column === 1
                            anchors.fill: parent
                            anchors.margins: 1
                            text: model.pendingValue
                            enabled: !model.readOnly
                            onEditingFinished: {
                                if (!controller.setPendingValue(row, text)) {
                                    text = model.pendingValue
                                }
                            }
                        }

                        QGCLabel {
                            visible: column !== 1 && column !== 6
                            anchors.fill: parent
                            anchors.margins: ScreenTools.defaultFontPixelWidth * 0.3
                            text: model.display
                            color: model.changed ? qgcPal.buttonHighlightText : qgcPal.text
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }

                        QGCButton {
                            visible: column === 6
                            anchors.fill: parent
                            text: model.favorite ? "★" : "☆"
                            onClicked: controller.toggleFavorite(row)
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: statusLabel.implicitHeight + ScreenTools.defaultFontPixelHeight * 0.7
            color: qgcPal.windowShadeDark
            radius: ScreenTools.defaultBorderRadius
            border.color: qgcPal.groupBorder
            border.width: 1

            QGCLabel {
                id: statusLabel
                anchors.fill: parent
                anchors.margins: ScreenTools.defaultFontPixelWidth * 0.5
                text: controller.statusText.length > 0
                      ? controller.statusText
                      : "MP Params: редагування накопичується локально; Write Params виконує фактичний запис на польотник."
                wrapMode: Text.WordWrap
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
