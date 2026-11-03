#pragma once

#include <QtCore/QObject>
#include <QtCore/QPointer>
#include <QtCore/QTimer>
#include <QtCore/QByteArray>
#include <QtCore/QString>

class Vehicle;

// Manual, short-lived UBX-MON-VER probe over MAVLink SERIAL_CONTROL.
// Never runs automatically: SERIAL_CONTROL EXCLUSIVE temporarily locks GPS UART.
class ARGNGpsProbeController final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(Vehicle* vehicle READ vehicle WRITE setVehicle NOTIFY vehicleChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY statusChanged)
    Q_PROPERTY(QString gps1Info READ gps1Info NOTIFY statusChanged)
    Q_PROPERTY(QString gps2Info READ gps2Info NOTIFY statusChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY statusChanged)

public:
    explicit ARGNGpsProbeController(QObject *parent = nullptr);
    ~ARGNGpsProbeController() override;

    Vehicle* vehicle() const { return _vehicle.data(); }
    void setVehicle(Vehicle* vehicle);
    bool busy() const { return _busy; }
    QString gps1Info() const { return _gps1Info; }
    QString gps2Info() const { return _gps2Info; }
    QString statusText() const { return _statusText; }

    Q_INVOKABLE void probeGps(int port); // 1=GPS1, 2=GPS2; disarmed only
    Q_INVOKABLE void cancel();

signals:
    void vehicleChanged();
    void statusChanged();

private:
    void sendSerial(uint8_t flags, const QByteArray &data, uint16_t timeoutMs);
    void onSerialControl(uint8_t device, uint8_t flags, uint16_t timeout,
                         uint32_t baudrate, QByteArray data);
    void poll();
    void complete(const QString &message);
    void release();

    QPointer<Vehicle> _vehicle;
    QTimer _timer;
    QByteArray _buffer;
    QString _gps1Info = QStringLiteral("Не опитано");
    QString _gps2Info = QStringLiteral("Не опитано");
    QString _statusText = QStringLiteral("Натисніть UART для ручного опитування UBX-MON-VER");
    int _device = -1;
    int _polls = 0;
    bool _busy = false;
};
