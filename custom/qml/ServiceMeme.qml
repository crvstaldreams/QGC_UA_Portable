import QtQuick
import QtQuick.Dialogs
import QtQuick.Controls
import QtQuick.Layouts
import QGroundControl
import QGroundControl.Controls
import QGroundControl.Palette

Rectangle {
    id: player
    color: pal.window
    property var vehicle: QGroundControl.multiVehicleManager.activeVehicle
    property real lengthSeconds: 158.609
    property string trackName: "Undertale — Megalovania"
    property string loadError: ""
    property bool playing: false
    property real positionSeconds: 0

    QGCPalette { id: pal; colorGroupEnabled: true }

    FileDialog {
        id: midiPicker
        title: "Виберіть MIDI-файл"
        nameFilters: ["MIDI (*.mid *.midi)", "Усі файли (*)"]
        fileMode: FileDialog.OpenFile
        onAccepted: {
            if (!player.vehicle) return
            player.loadError = ""
            if (!player.vehicle.loadServiceMidi(selectedFile)) {
                player.loadError = "Не вдалося прочитати MIDI (підтримуються SMF типу 0/1 без SMPTE)."
                return
            }
            player.playing = false
            player.positionSeconds = 0
            player.lengthSeconds = player.vehicle.serviceMidiDurationSeconds()
            player.trackName = decodeURIComponent(selectedFile.toString().split("/").pop())
            timeline.value = 0
        }
    }

    function stop() {
        if (vehicle) vehicle.stopServiceMidi()
        playing = false
        positionSeconds = 0
        timeline.value = 0
    }
    function pause() {
        if (vehicle) {
            positionSeconds = vehicle.serviceMidiPositionSeconds()
            vehicle.pauseServiceMidi()
        }
        playing = false
    }
    function play() {
        if (!vehicle || vehicle.armed) return
        vehicle.playServiceMidi(positionSeconds)
        playing = true
    }
    function formatTime(value) {
        const seconds = Math.floor(Math.max(0, value))
        return Math.floor(seconds / 60) + ":" + ("0" + seconds % 60).slice(-2)
    }

    Component.onDestruction: {
        if (vehicle) vehicle.stopServiceMidi()
    }
    onVehicleChanged: {
        playing = false
        positionSeconds = 0
    }

    Timer {
        interval: 120
        running: playing
        repeat: true
        onTriggered: {
            if (!vehicle) { playing = false; return }
            positionSeconds = vehicle.serviceMidiPositionSeconds()
            if (!timeline.pressed) timeline.value = positionSeconds
            if (positionSeconds >= lengthSeconds) playing = false
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        QGCLabel {
            text: "Мемне · MIDI-плеєр"
            font.bold: true
            font.pixelSize: 22
            Layout.fillWidth: true
        }
        QGCLabel {
            text: player.trackName + " (MIDI, одноголосна мелодія)"
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        QGCLabel {
            text: vehicle
                  ? (vehicle.armed ? "Відтворення заблоковано: борт озброєний" :
                     "Відтворення через бузер польотного контролера · 230 BPM")
                  : "Для відтворення підключіть польотний контролер"
            color: vehicle && !vehicle.armed ? pal.text : pal.warningText
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        QGCButton {
            text: "Завантажити MIDI…"
            enabled: !!vehicle && !vehicle.armed
            onClicked: midiPicker.open()
        }
        QGCLabel {
            visible: player.loadError.length > 0
            text: player.loadError
            color: pal.warningText
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            QGCLabel { text: formatTime(timeline.pressed ? timeline.value : positionSeconds) }
            Slider {
                id: timeline
                Layout.fillWidth: true
                from: 0
                to: player.lengthSeconds
                enabled: !!vehicle && !vehicle.armed
                onPressedChanged: {
                    if (!pressed) {
                        player.positionSeconds = value
                        if (player.playing && player.vehicle) player.vehicle.playServiceMidi(value)
                        else if (player.vehicle) player.vehicle.seekServiceMidi(value)
                    }
                }
            }
            QGCLabel { text: formatTime(lengthSeconds) }
        }

        RowLayout {
            spacing: 8
            QGCButton {
                text: playing ? "Пауза" : "Відтворити"
                enabled: !!vehicle && !vehicle.armed
                onClicked: playing ? pause() : play()
            }
            QGCButton { text: "Стоп"; enabled: !!vehicle; onClicked: stop() }
            QGCButton {
                text: "−10 с"
                enabled: !!vehicle && !vehicle.armed
                onClicked: {
                    const value = Math.max(0, player.positionSeconds - 10)
                    player.positionSeconds = value
                    timeline.value = value
                    if (playing) vehicle.playServiceMidi(value)
                    else vehicle.seekServiceMidi(value)
                }
            }
            QGCButton {
                text: "+10 с"
                enabled: !!vehicle && !vehicle.armed
                onClicked: {
                    const value = Math.min(lengthSeconds, player.positionSeconds + 10)
                    player.positionSeconds = value
                    timeline.value = value
                    if (playing) vehicle.playServiceMidi(value)
                    else vehicle.seekServiceMidi(value)
                }
            }
        }
        QGCLabel {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Бузер відтворює одну ноту за раз. Під час перемотки попереднє відтворення зупиняється; початок після перемотки відповідає вибраній позиції MIDI. Підтримка MAVLink PLAY_TUNE залежить від прошивки."
        }
        RowLayout {
            Layout.fillWidth: true
            QGCLabel { text: "Гучність бузера" }
            Slider {
                Layout.fillWidth: true
                from: 0
                to: 100
                value: 100
                enabled: false
            }
        }
        QGCLabel {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Регулювання гучності недоступне через MAVLink PLAY_TUNE: протокол не передає амплітуду звуку. Рівень залежить від обладнання та прошивки."
        }
        Item { Layout.fillHeight: true }
    }
}
