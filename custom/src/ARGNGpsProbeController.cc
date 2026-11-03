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
    _gps1Info = QStringLiteral("Не опитано");
    _gps2Info = QStringLiteral("Не опитано");
    _statusText = QStringLiteral("Виберіть UART GPS1 або GPS2");
    emit vehicleChanged();
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
    _probeAll = false;
    _nextGpsPending = false;
    if (!_busy) return;
    complete(QStringLiteral("Опитування скасовано"));
}
