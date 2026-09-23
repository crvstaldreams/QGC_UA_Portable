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
    property bool isArduPilot: activeVehicle ? activeVehicle.apmFirmware : false
    readonly property int preflightCalibrationCommand: 241
    readonly property int preflightRebootShutdownCommand: 246
    property bool magnetometerRebootPending: false
    property string magnetometerRebootStatus: ""

    QGCPalette { id: qgcPal; colorGroupEnabled: true }
    FactPanelController { id: controller }

    function exists(name) { return controller.parameterExists(-1, name) }
    function fact(name) { return exists(name) ? controller.getParameterFact(-1, name, false) : null }
    function idName(i) { return isArduPilot ? (i === 0 ? "COMPASS_DEV_ID" : "COMPASS_DEV_ID" + (i + 1)) : "CAL_MAG" + i + "_ID" }
    function rotName(i) { return isArduPilot ? (i === 0 ? "COMPASS_ORIENT" : "COMPASS_ORIENT" + (i + 1)) : "CAL_MAG" + i + "_ROT" }
    function extName(i) { return isArduPilot ? (i === 0 ? "COMPASS_EXTERNAL" : "COMPASS_EXTERN" + (i + 1)) : rotName(i) }
    function useName(i) { return isArduPilot ? (i === 0 ? "COMPASS_USE" : "COMPASS_USE" + (i + 1)) : "" }
    function compassId(i) { const f=fact(idName(i)); return f ? Number(f.rawValue) : 0 }
    function connected(i) { return compassId(i) > 0 }
    function external(i) { const f=fact(extName(i)); if (!f) return i > 0; return isArduPilot ? Number(f.rawValue)!==0 : Number(f.rawValue)>=0 }
    function enabledCompass(i) { const n=useName(i); const f=n ? fact(n) : null; return f ? Number(f.rawValue)!==0 : connected(i) }
    function orientation(i) { const f=fact(rotName(i)); return f ? f.enumStringValue : "—" }
    function orientationYaw(i) {
        const label = orientation(i).toUpperCase()
        if (label.indexOf("YAW_315") >= 0) return 315
        if (label.indexOf("YAW_270") >= 0) return 270
        if (label.indexOf("YAW_225") >= 0) return 225
        if (label.indexOf("YAW_180") >= 0) return 180
        if (label.indexOf("YAW_135") >= 0) return 135
        if (label.indexOf("YAW_90") >= 0) return 90
        if (label.indexOf("YAW_45") >= 0) return 45
        return 0
    }
    function compassVisualAngle(i) { return orientationYaw(i) }
    function setOrientation(i, value) { const f=fact(rotName(i)); if (f) f.rawValue=value }
    function calibrate() {
        if (activeVehicle) activeVehicle.sendCommand(1, preflightCalibrationCommand, true, 0, 1, 0, 0, 0, 0, 0)
    }
    function rebootMagnetometers() {
        if (!activeVehicle || magnetometerRebootPending) return
        // MAVLink has no portable command that power-cycles only magnetometers.
        // Reboot the autopilot so all internal/external MAG drivers are reinitialised.
        magnetometerRebootPending = true
        magnetometerRebootStatus = "Перезавантаження магнітометрів…"
        activeVehicle.sendCommand(1, preflightRebootShutdownCommand, true, 1, 0, 0, 0, 0, 0, 0)
        magnetometerRebootTimer.restart()
    }

    Timer {
        id: magnetometerRebootTimer
        interval: 8000
        repeat: false
        onTriggered: {
            root.magnetometerRebootPending = false
            root.magnetometerRebootStatus = root.activeVehicle ? "Магнітометри повторно ініціалізовано" : "Очікування повторного підключення борту"
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.implicitHeight + ScreenTools.defaultFontPixelHeight
        clip: true
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: content
            width: parent.width
            spacing: ScreenTools.defaultFontPixelHeight * 0.7

            RowLayout {
                Layout.fillWidth: true
                QGCLabel { text: "◈"; font.pixelSize: ScreenTools.defaultFontPixelHeight * 2.2; color: "#ffd400" }
                ColumnLayout {
                    Layout.fillWidth: true
                    QGCLabel { text: "Компаси"; font.bold: true; font.pointSize: ScreenTools.largeFontPointSize }
                    QGCLabel { Layout.fillWidth: true; text: "Перегляньте підключені компаси, їх положення та стан. Орієнтацію можна змінити безпосередньо тут."; wrapMode: Text.WordWrap }
                }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 4; color: "#ffd400" }

            QGCLabel {
                text: "Виявлені компаси (" + ([0,1,2].filter(function(i){return connected(i)}).length) + ")"
                font.bold: true; font.pointSize: ScreenTools.mediumFontPointSize
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: ScreenTools.defaultFontPixelWidth

                Repeater {
                    model: 3
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 29
                        visible: connected(index)
                        radius: ScreenTools.defaultFontPixelWidth / 2
                        color: qgcPal.window
                        border.width: 1
                        border.color: qgcPal.buttonText

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: ScreenTools.defaultFontPixelWidth
                            spacing: ScreenTools.defaultFontPixelHeight * 0.3

                            RowLayout {
                                Layout.fillWidth: true
                                QGCLabel { Layout.fillWidth: true; text: "Компас " + (index+1) + " (" + (external(index) ? "зовнішній" : "внутрішній") + ")"; font.bold: true; font.pointSize: ScreenTools.mediumFontPointSize; elide: Text.ElideRight }
                                Rectangle {
                                    implicitWidth: stateText.implicitWidth + ScreenTools.defaultFontPixelWidth * 2
                                    implicitHeight: stateText.implicitHeight + 8; radius: height/2
                                    color: enabledCompass(index) ? "#075b20" : qgcPal.windowShade
                                    QGCLabel { id: stateText; anchors.centerIn: parent; text: enabledCompass(index) ? "Увімкнено" : "Вимкнено" }
                                }
                            }
                            QGCLabel { text: "Тип:  " + (external(index) ? "Зовнішній (GPS/MAG)" : "Внутрішній (FMU)") }
                            QGCLabel { text: "Device ID:  " + compassId(index) }
                            QGCLabel { text: "Орієнтація:  " + orientation(index); Layout.fillWidth: true; elide: Text.ElideRight }
                            QGCLabel { text: "Прошивка:  " + (isArduPilot ? "ArduPilot (COMPASS_*)" : "PX4 (CAL_MAG" + (index+1) + "_*)") }

                            Item {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: Math.min(parent.width, ScreenTools.defaultFontPixelHeight * 13)
                                Layout.preferredHeight: Layout.preferredWidth
                                Rectangle { anchors.fill: parent; radius: width/2; color: "#090909"; border.width: 1; border.color: qgcPal.buttonText }
                                QGCLabel { text:"N"; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: 5 }
                                QGCLabel { text:"S"; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 5 }
                                QGCLabel { text:"W"; anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 7 }
                                QGCLabel { text:"E"; anchors.verticalCenter: parent.verticalCenter; anchors.right: parent.right; anchors.rightMargin: 7 }
                                Canvas {
                                    anchors.centerIn: parent; width: parent.width*0.55; height: width
                                    rotation: root.compassVisualAngle(index)
                                    onPaint: {
                                        const ctx=getContext("2d"); ctx.clearRect(0,0,width,height); ctx.beginPath()
                                        ctx.moveTo(width/2,2); ctx.lineTo(width*0.78,height*0.72); ctx.lineTo(width/2,height*0.58); ctx.lineTo(width*0.22,height*0.72); ctx.closePath()
                                        ctx.fillStyle="#ef3123"; ctx.fill(); ctx.strokeStyle="#ffffff"; ctx.lineWidth=1.5; ctx.stroke()
                                    }
                                }
                                QGCLabel { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: ScreenTools.defaultFontPixelHeight; text: root.compassVisualAngle(index) + "°"; font.bold:true }
                            }

                            QGCComboBox {
                                Layout.fillWidth: true
                                enabled: external(index) && fact(rotName(index))
                                model: fact(rotName(index)) ? fact(rotName(index)).enumStrings : []
                                currentIndex: fact(rotName(index)) ? fact(rotName(index)).enumIndex : -1
                                onActivated: {
                                    const f=fact(rotName(index))
                                    if (f && currentIndex >= 0) f.enumIndex=currentIndex
                                }
                            }
                            QGCButton { Layout.fillWidth: true; text: "Калібрувати"; onClicked: root.calibrate() }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                QGCButton {
                    Layout.fillWidth: true
                    text: root.magnetometerRebootPending ? "Перезавантаження…" : "Перезавантажити магнітометри"
                    enabled: !!root.activeVehicle && !root.magnetometerRebootPending
                    onClicked: root.rebootMagnetometers()
                }
                QGCLabel {
                    Layout.fillWidth: true
                    text: root.magnetometerRebootStatus
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: info.implicitHeight + ScreenTools.defaultFontPixelHeight
                radius: ScreenTools.defaultFontPixelWidth/3; color: qgcPal.window
                QGCLabel {
                    id: info; anchors.fill: parent; anchors.margins: ScreenTools.defaultFontPixelWidth
                    wrapMode: Text.WordWrap
                    text: "Внутрішній компас знаходиться на польотному контролері. Зовнішні компаси можуть бути підключені через GPS/MAG модулі. Кожна картка прив'язана до власного набору параметрів компаса. Круговий індикатор показує індивідуальну орієнтацію встановлення цього компаса, а не спільний курс борту. Device ID, тип, стан та орієнтація читаються окремо для кожного компаса."
                }
            }
        }
    }
}
