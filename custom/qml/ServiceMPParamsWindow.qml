import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QGroundControl.Palette
import QGroundControl.ScreenTools

ApplicationWindow {
    id: root
    visible: false
    width: Math.min(Screen.width * 0.90, 1600)
    height: Math.min(Screen.height * 0.88, 980)
    minimumWidth: 1050
    minimumHeight: 650
    title: "MP Params"
    color: qgcPal.window
    flags: Qt.Window

    QGCPalette {
        id: qgcPal
        colorGroupEnabled: true
    }

    onClosing: (close) => {
        close.accepted = false
        root.hide()
    }

    Loader {
        anchors.fill: parent
        anchors.margins: ScreenTools.defaultFontPixelWidth * 0.5
        source: "qrc:/qml/QGroundControl/Custom/ServiceMPParams.qml"
    }
}
