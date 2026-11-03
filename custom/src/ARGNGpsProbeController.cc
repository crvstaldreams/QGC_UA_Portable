#include "ARGNGpsProbeController.h"

#include "Vehicle.h"
#include "VehicleLinkManager.h"
#include "MAVLinkProtocol.h"
#include "MAVLinkLib.h"

#include <QtCore/QStringList>
#include <cstring>

ARGNGpsProbeController::ARGNGpsProbeController(QObject *parent) : QObject(parent)
{
    _timer.setInterval(180);
    _timer.setSingleShot(false);
    connect(&_timer, &QTimer::timeout, this, &ARGNGpsProbeController::poll);
    _syncUpdateTimer.setInterval(1000);
    connect(&_syncUpdateTimer, &QTimer::timeout, this, [this]() { emit statusChanged(); });
    _syncUpdateTimer.start();
}

ARGNGpsProbeController::~ARGNGpsProbeController()
{
    cancel();
}

void ARGNGpsProbeController::setVehicle(Vehicle *vehicle)
{
    if (_vehicle == vehicle) return;
    cancel();
    if (_vehicle) disconnect(_vehicle, nullptr, this, nullptr);
    _vehicle = vehicle;
    if (_vehicle) {
        connect(_vehicle, &Vehicle::mavlinkSerialControl,
                this, &ARGNGpsProbeController::onSerialControl);
        connect(_vehicle, &Vehicle::mavlinkMessageReceived,
                this, &ARGNGpsProbeController::onVehicleMavlink);
        connect(_vehicle, &QObject::destroyed, this, [this]() {
            _timer.stop();
            _device = -1;
            _busy = false;
            _buffer.clear();
            _vehicle.clear();
            emit vehicleChanged();
            emit statusChanged();
        });
    }
    _syncReported = -1;
    _syncLastMessage.invalidate();
    _gps1Info = QStringLiteral("Не опитано");
    _zedInfo = QStringLiteral("Не перевірено");
    _neoInfo = QStringLiteral("Не перевірено");
    _zedVerified = false;
    _neoVerified = false;
    _activePort = QStringLiteral("Не визначено");
    _gps2Info = QStringLiteral("Не опитано");
    _statusText = QStringLiteral("Виберіть UART GPS1 або GPS2");
    emit vehicleChanged();
    emit statusChanged();
}

int ARGNGpsProbeController::syncState() const
{
    if (!_vehicle) return 0;
    if (!_syncLastMessage.isValid() || _syncLastMessage.elapsed() > 3000)
        return 1;
    return _syncReported == 1 ? 2 : _syncReported == 0 ? 3 : 1;
}

void ARGNGpsProbeController::onVehicleMavlink(const mavlink_message_t &message)
{
    if (message.msgid != MAVLINK_MSG_ID_NAMED_VALUE_INT) return;
    mavlink_named_value_int_t info{};
    mavlink_msg_named_value_int_decode(&message, &info);
    const QByteArray name(info.name, sizeof(info.name));
    if (name.left(9) != QByteArrayLiteral("GNSS_SYNC")) return;

    // An independent monitor must measure phase of two PPS/LED edges.
    // 1=synchronized, 0=measured out-of-phase; unreported/expired is UNKNOWN.
    _syncReported = info.value == 1 ? 1 : info.value == 0 ? 0 : -1;
    _syncLastMessage.restart();
    emit statusChanged();
}

void ARGNGpsProbeController::sendSerial(uint8_t flags, const QByteArray &data, uint16_t timeoutMs)
{
    if (!_vehicle || _device < 0) return;
    const auto link = _vehicle->vehicleLinkManager()->primaryLink().lock();
    if (!link) return;
    uint8_t payload[70] = {};
    const int n = static_cast<int>(qMin(data.size(), qsizetype(70)));
    if (n) memcpy(payload, data.constData(), size_t(n));
    mavlink_message_t message{};
    mavlink_msg_serial_control_pack(
        uint8_t(MAVLinkProtocol::instance()->getSystemId()),
        uint8_t(MAVLinkProtocol::getComponentId()), &message,
        uint8_t(_device), flags, timeoutMs, 0, uint8_t(n), payload,
        uint32_t(_vehicle->id()), uint8_t(_vehicle->defaultComponentId()));
    _vehicle->sendMessageOnLinkThreadSafe(link.get(), message);
}

void ARGNGpsProbeController::probeDual()
{
    if (!_vehicle || _busy || _nextGpsPending) return;
    if (_vehicle->armed()) {
        _statusText = QStringLiteral("Відмовлено: борт озброєний");
        emit statusChanged();
        return;
    }
    _dualRetryOtherPort = true;
    _zedInfo = QStringLiteral("Очікуємо відповідь…");
    _neoInfo = QStringLiteral("Очікуємо відповідь…");
    _zedVerified = false;
    _neoVerified = false;
    _zedUniqueId.clear();
    _neoUniqueId.clear();
    startDualPort(1);
}

void ARGNGpsProbeController::probeDualPort(int port)
{
    if (!_vehicle || _busy || (port != 1 && port != 2)) return;
    if (_vehicle->armed()) {
        _statusText = QStringLiteral("Відмовлено: борт озброєний");
        emit statusChanged();
        return;
    }
    _dualRetryOtherPort = false;
    _zedInfo = QStringLiteral("Очікуємо відповідь…");
    _neoInfo = QStringLiteral("Очікуємо відповідь…");
    _zedVerified = false;
    _neoVerified = false;
    _zedUniqueId.clear();
    _neoUniqueId.clear();
    startDualPort(port);
}

void ARGNGpsProbeController::startDualPort(int port)
{
    if (!_vehicle || _vehicle->armed() ||
        !_vehicle->vehicleLinkManager()->primaryLink().lock())
        return;
    _timer.stop();
    _device = port + 1;
    _dualMode = true;
    _dualReceiver = 0;
    _dualPolls = 0;
    _dualOriginalSelector = 1;
    _dualOriginalKnown = false;
    _dualAnyResponse = false;
    _busy = true;
    _activePort = QStringLiteral("GPS%1").arg(port);
    _buffer.clear();
    _statusText = QStringLiteral("GPS%1: читаємо поточний вибір приймача…").arg(port);
    emit statusChanged();

    // UBX-CFG-VALGET, RAM layer, key 0xAC100001 from supplied u-center
    // selector. An unsupported query is not a fatal error.
    sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE | SERIAL_CONTROL_FLAG_RESPOND),
               QByteArray::fromHex("b562068b080000000000010010ac5661"), 60);
    QTimer::singleShot(320, this, [this]() {
        if (_busy && _dualMode && _dualReceiver == 0) beginDualReceiver(1);
    });
}

void ARGNGpsProbeController::beginDualReceiver(int selector)
{
    if (!_busy || !_dualMode || !_vehicle || _vehicle->armed()) {
        cancel();
        return;
    }
    _timer.stop();
    _dualReceiver = selector;
    _dualPolls = 0;
    _dualVersion.clear();
    _dualUniqueId.clear();
    _dualMonVer = false;
    _dualUniqueIdReceived = false;
    _buffer.clear();
    _statusText = QStringLiteral("%1: перемикаємо приймач через RAM selector…")
        .arg(selector == 1 ? QStringLiteral("ZED") : QStringLiteral("NEO"));
    emit statusChanged();

    // User-supplied validated CFG-VALSET packets. Volatile RAM only.
    const QByteArray selectorFrame = selector == 1
        ? QByteArray::fromHex("b562068a090000010000010010ac0158bf")
        : QByteArray::fromHex("b562068a090000010000010010ac0259c0");
    sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE), selectorFrame, 0);
    QTimer::singleShot(350, this, [this, selector]() {
        if (_busy && _dualMode && _dualReceiver == selector) beginDualRead();
    });
}

void ARGNGpsProbeController::beginDualRead()
{
    if (!_busy || !_dualMode || !_vehicle || _vehicle->armed()) {
        cancel();
        return;
    }
    _buffer.clear();
    // MON-VER provides presence and firmware. SEC-UNIQID provides
    // a physically unique chip ID when supported by this firmware.
    sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE | SERIAL_CONTROL_FLAG_RESPOND),
               QByteArray::fromHex("b5620a0400000e34"), 70);
    sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE | SERIAL_CONTROL_FLAG_RESPOND),
               QByteArray::fromHex("b562270300002a54"), 70);
    _timer.start();
}

void ARGNGpsProbeController::advanceDual(bool)
{
    if (!_busy || !_dualMode) return;
    _timer.stop();
    const QString name = _dualReceiver == 1 ? QStringLiteral("ZED") : QStringLiteral("NEO");
    QString result;
    if (_dualMonVer) {
        result = QStringLiteral("MON-VER OK | ") + _dualVersion;
        if (_dualUniqueIdReceived) result += QStringLiteral(" | UID=") + _dualUniqueId;
        else result += QStringLiteral(" | UID недоступний");
        _dualAnyResponse = true;
    } else {
        result = QStringLiteral("Немає відповіді UBX після вибору ") + name;
    }
    if (_dualReceiver == 1) {
        _zedInfo = result;
        _zedUniqueId = _dualUniqueIdReceived ? _dualUniqueId : QString();
        _zedVerified = _dualMonVer;
        emit statusChanged();
        beginDualReceiver(2);
        return;
    }

    _neoInfo = result;
    _neoUniqueId = _dualUniqueIdReceived ? _dualUniqueId : QString();
    _neoVerified = _dualMonVer;
    // A duplicated silicon ID means selection is not actually isolated:
    // do not claim two distinct working receivers.
    if (!_zedUniqueId.isEmpty() && !_neoUniqueId.isEmpty() &&
        _zedUniqueId == _neoUniqueId) {
        _zedVerified = false;
        _neoVerified = false;
        _statusText = QStringLiteral("Обидва запити повернули однаковий UID: незалежні приймачі не підтверджено");
    }
    emit statusChanged();
    finishDual();
}

void ARGNGpsProbeController::finishDual()
{
    _timer.stop();
    if (_device >= 0 && _vehicle && !_vehicle->armed()) {
        const int restore = _dualOriginalKnown ? _dualOriginalSelector : 1;
        const QByteArray frame = restore == 2
            ? QByteArray::fromHex("b562068a090000010000010010ac0259c0")
            : QByteArray::fromHex("b562068a090000010000010010ac0158bf");
        sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE), frame, 0);
    }
    const int port = _device - 1;
    release();
    _device = -1;
    _busy = false;
    _dualMode = false;
    emit statusChanged();

    // Search the other physical port only if neither receiver answered.
    if (_dualRetryOtherPort && !_dualAnyResponse && port == 1) {
        _dualRetryOtherPort = false;
        QTimer::singleShot(280, this, [this]() {
            if (_vehicle && !_vehicle->armed() && !_busy) {
                _zedInfo = QStringLiteral("Очікуємо GPS2…");
                _neoInfo = QStringLiteral("Очікуємо GPS2…");
                startDualPort(2);
            }
        });
    } else {
        _dualRetryOtherPort = false;
        if (_statusText.startsWith(QStringLiteral("Обидва запити"))) return;
        _statusText = QStringLiteral("%1: сканування завершено; %2")
            .arg(_activePort, _dualOriginalKnown
                ? QStringLiteral("початковий вибір відновлено")
                : QStringLiteral("вибір ZED відновлено за замовчуванням (початковий невідомий)"));
        emit statusChanged();
    }
}

void ARGNGpsProbeController::probeAll()
{
    if (!_vehicle || _busy || _nextGpsPending) return;
    if (_vehicle->armed()) {
        _statusText = QStringLiteral("Відмовлено: спочатку роззбройте борт");
        emit statusChanged();
        return;
    }
    _probeAll = true;
    _gps1Info = QStringLiteral("Очікуємо запит…");
    _gps2Info = QStringLiteral("Очікуємо запит…");
    probeGps(1);
    if (!_busy) _probeAll = false;
}

void ARGNGpsProbeController::probeGps(int port)
{
    if (!_vehicle || _busy || (port != 1 && port != 2)) return;
    if (_vehicle->armed()) {
        _statusText = QStringLiteral("Відмовлено: спочатку роззбройте борт");
        emit statusChanged();
        return;
    }
    if (!_vehicle->vehicleLinkManager()->primaryLink().lock()) {
        _statusText = QStringLiteral("Немає активного MAVLink-з'єднання");
        emit statusChanged();
        return;
    }

    // Do not reconfigure GNSS baudrate or configuration.
    // MAVLink SERIAL_CONTROL DEV_GPS1=2, DEV_GPS2=3.
    _device = port + 1;
    _buffer.clear();
    _polls = 0;
    _busy = true;
    _statusText = QStringLiteral("Опитування GPS%1: UBX-MON-VER…").arg(port);
    if (port == 1) _gps1Info = QStringLiteral("Опитування…");
    else _gps2Info = QStringLiteral("Опитування…");
    emit statusChanged();

    // UBX-MON-VER poll, class 0x0A ID 0x04, zero payload, checksum 0x0E 0x34.
    const QByteArray pollFrame = QByteArray::fromHex("b5620a0400000e34");
    sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE | SERIAL_CONTROL_FLAG_RESPOND),
               pollFrame, 60);
    _timer.start();
}

void ARGNGpsProbeController::poll()
{
    if (!_busy) return;
    if (_dualMode) {
        if (!_vehicle || _vehicle->armed() ||
            !_vehicle->vehicleLinkManager()->primaryLink().lock()) {
            cancel();
            return;
        }
        if (++_dualPolls >= 13 ||
            (_dualMonVer && _dualUniqueIdReceived) ||
            (_dualMonVer && _dualPolls >= 6)) {
            advanceDual(_dualPolls >= 13);
            return;
        }
        sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE | SERIAL_CONTROL_FLAG_RESPOND),
                   QByteArray(), 60);
        return;
    }
    if (!_vehicle || _vehicle->armed()) {
        complete(QStringLiteral("Запит зупинено: немає з'єднання або борт озброєний"));
        return;
    }
    if (++_polls >= 12) {
        complete(QStringLiteral("Немає відповіді MON-VER (UART зайнятий, спільна шина або passthrough не підтримується)"));
        return;
    }
    sendSerial(uint8_t(SERIAL_CONTROL_FLAG_EXCLUSIVE | SERIAL_CONTROL_FLAG_RESPOND),
               QByteArray(), 50);
}

void ARGNGpsProbeController::onSerialControl(uint8_t device, uint8_t flags, uint16_t,
                                              uint32_t, QByteArray data)
{
    if (!_busy || int(device) != _device || !(flags & SERIAL_CONTROL_FLAG_REPLY))
        return;
    _buffer.append(data);
    if (_buffer.size() > 4096) _buffer = _buffer.right(4096);
    if (_dualMode) {
        // Mixed UBX stream may contain unrelated navigation messages.
        // Validate each full UBX packet checksum before using its data.
        while (_buffer.size() >= 8) {
            const int sync = _buffer.indexOf(QByteArray::fromHex("b562"));
            if (sync < 0) { _buffer.clear(); break; }
            if (sync) _buffer.remove(0, sync);
            if (_buffer.size() < 8) break;
            const int size = int(uint8_t(_buffer[4])) |
                (int(uint8_t(_buffer[5])) << 8);
            if (size > 2048) { _buffer.remove(0, 2); continue; }
            if (_buffer.size() < size + 8) break;
            const QByteArray frame = _buffer.left(size + 8);
            _buffer.remove(0, size + 8);
            uint8_t a = 0, b = 0;
            for (int i = 2; i < frame.size()-2; ++i) {
                a = uint8_t(a + uint8_t(frame[i]));
                b = uint8_t(b + a);
            }
            if (a != uint8_t(frame[frame.size()-2]) ||
                b != uint8_t(frame[frame.size()-1])) continue;
            const uint8_t cls = uint8_t(frame[2]);
            const uint8_t id = uint8_t(frame[3]);
            const QByteArray payload = frame.mid(6, size);
            if (_dualReceiver == 0 && cls == 0x06 && id == 0x8B &&
                payload.size() >= 9 &&
                payload.mid(4, 4) == QByteArray::fromHex("010010ac")) {
                const int val = uint8_t(payload[8]);
                if (val == 1 || val == 2) {
                    _dualOriginalSelector = val;
                    _dualOriginalKnown = true;
                }
            } else if (_dualReceiver != 0 && cls == 0x0A && id == 0x04 &&
                       size >= 40) {
                QStringList fields;
                for (int i = 0; i < payload.size();) {
                    const int length = i == 0 ? 30 : i == 30 ? 10 : 30;
                    QByteArray field = payload.mid(i, length);
                    const int nul = field.indexOf(char(0));
                    if (nul >= 0) field.truncate(nul);
                    const QString value = QString::fromLatin1(field).trimmed();
                    if (!value.isEmpty()) fields << value;
                    i += length;
                }
                _dualVersion = fields.join(QStringLiteral(" | "));
                _dualMonVer = true;
            } else if (_dualReceiver != 0 && cls == 0x27 && id == 0x03 &&
                       size >= 9) {
                _dualUniqueId = QString::fromLatin1(payload.right(5).toHex().toUpper());
                _dualUniqueIdReceived = true;
            }
        }
        emit statusChanged();
        return;
    }

    // Parse a complete UBX-MON-VER frame, not arbitrary unrelated GPS traffic.
    const QByteArray prefix = QByteArray::fromHex("b5620a04");
    int start = 0;
    while ((start = _buffer.indexOf(prefix, start)) >= 0) {
        if (_buffer.size() < start + 8) return;
        const unsigned int size = uint8_t(_buffer[start+4]) | (uint8_t(_buffer[start+5]) << 8);
        if (size > 2048) { ++start; continue; }
        if (_buffer.size() < start + 8 + int(size)) return;

        const QByteArray frame = _buffer.mid(start, 8 + int(size));
        uint8_t ckA = 0, ckB = 0;
        for (int i = 2; i < frame.size()-2; ++i) {
            ckA += uint8_t(frame[i]);
            ckB += ckA;
        }
        if (ckA != uint8_t(frame[frame.size()-2]) || ckB != uint8_t(frame[frame.size()-1])) {
            ++start;
            continue;
        }
        const QByteArray payload = frame.mid(6, int(size));
        QStringList fields;
        // SW VERSION (30), HW VERSION (10), and extension strings (30 each).
        for (int i = 0; i < payload.size();) {
            const int fieldLength = i == 0 ? 30 : i == 30 ? 10 : 30;
            const QByteArray field = payload.mid(i, fieldLength);
            QString value = QString::fromLatin1(field.left(field.indexOf('\0') < 0 ? field.size() : field.indexOf('\0'))).trimmed();
            if (!value.isEmpty()) fields << value;
            i += fieldLength;
        }
        complete(fields.isEmpty() ? QStringLiteral("UBX-MON-VER отримано") : fields.join(QStringLiteral(" | ")));
        return;
    }
}

void ARGNGpsProbeController::release()
{
    if (_device >= 0 && _vehicle && _vehicle->vehicleLinkManager()->primaryLink().lock()) {
        // Clearing EXCLUSIVE releases ArduPilot's GPS lock. No baud or settings change.
        sendSerial(0, QByteArray(), 0);
    }
}

void ARGNGpsProbeController::complete(const QString &message)
{
    if (!_busy) return;
    _timer.stop();
    release();
    if (_device == 2) _gps1Info = message;
    else if (_device == 3) _gps2Info = message;
    const bool requestSecondGps = _probeAll && _device == 2 &&
        _vehicle && !_vehicle->armed() && !_nextGpsPending;
    _statusText = message;
    _device = -1;
    _busy = false;
    emit statusChanged();
    if (requestSecondGps) {
        _nextGpsPending = true;
        QTimer::singleShot(250, this, [this]() {
            _nextGpsPending = false;
            if (!_probeAll || !_vehicle || _vehicle->armed()) {
                _probeAll = false;
                return;
            }
            probeGps(2);
            _probeAll = false;
        });
    }
}

void ARGNGpsProbeController::cancel()
{
    if (_dualMode) {
        _dualRetryOtherPort = false;
        _statusText = QStringLiteral("Сканування скасовано");
        finishDual();
        return;
    }
    _probeAll = false;
    _nextGpsPending = false;
    if (!_busy) return;
    complete(QStringLiteral("Опитування скасовано"));
}
