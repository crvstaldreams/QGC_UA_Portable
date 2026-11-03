#pragma once

#include <QtCore/QObject>
#include <QtCore/QPointer>
#include <QtCore/QTimer>
#include <QtCore/QElapsedTimer>
#include <QtCore/QByteArray>
#include <QtCore/QString>
#include <cstdint>
#include "Vehicle.h"

// Manual, short-lived UBX-MON-VER probe over MAVLink SERIAL_CONTROL.
// Never runs automatically: SERIAL_CONTROL EXCLUSIVE temporarily locks GPS UART.
class ARGNGpsProbeController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(Vehicle* vehicle READ vehicle WRITE setVehicle NOTIFY vehicleChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY statusChanged)
    Q_PROPERTY(QString gps1Info READ gps1Info NOTIFY statusChanged)
    Q_PROPERTY(QString gps2Info READ gps2Info NOTIFY statusChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY statusChanged)
    Q_PROPERTY(QString zedInfo READ zedInfo NOTIFY statusChanged)
    Q_PROPERTY(QString neoInfo READ neoInfo NOTIFY statusChanged)
    Q_PROPERTY(QString activePort READ activePort NOTIFY statusChanged)
    Q_PROPERTY(bool zedVerified READ zedVerified NOTIFY statusChanged)
    Q_PROPERTY(bool neoVerified READ neoVerified NOTIFY statusChanged)
    Q_PROPERTY(bool zedResponded READ zedResponded NOTIFY statusChanged)
    Q_PROPERTY(bool neoResponded READ neoResponded NOTIFY statusChanged)
    Q_PROPERTY(int syncState READ syncState NOTIFY statusChanged)

public:
    explicit ARGNGpsProbeController(QObject *parent = nullptr);
    ~ARGNGpsProbeController() override;

    Vehicle* vehicle() const { return _vehicle.data(); }
    void setVehicle(Vehicle* vehicle);
    bool busy() const { return _busy; }
    QString gps1Info() const { return _gps1Info; }
    QString gps2Info() const { return _gps2Info; }
    QString statusText() const { return _statusText; }
    QString zedInfo() const { return _zedInfo; }
    QString neoInfo() const { return _neoInfo; }
    QString activePort() const { return _activePort; }
    bool zedVerified() const { return _zedVerified; }
    bool neoVerified() const { return _neoVerified; }
    bool zedResponded() const { return _zedResponded; }
    bool neoResponded() const { return _neoResponded; }
    int syncState() const; // 0 disconnected, 1 waiting, 2 measured sync, 3 measured fault

    Q_INVOKABLE void probeGps(int port); // 1=GPS1, 2=GPS2; disarmed only
    Q_INVOKABLE void probeAll(); // Legacy individual-port probing
    Q_INVOKABLE void probeDual(); // Both GNSS receivers on one physical UART
    Q_INVOKABLE void probeDualPort(int port); // Choose GPS1/GPS2 explicitly
    Q_INVOKABLE void cancel();

signals:
    void vehicleChanged();
    void statusChanged();

private:
    void sendSerial(uint8_t flags, const QByteArray &data, uint16_t timeoutMs);
    void onSerialControl(uint8_t device, uint8_t flags, uint16_t timeout,
                         uint32_t baudrate, QByteArray data);
    void poll();
    void onVehicleMavlink(const mavlink_message_t &message);
    void complete(const QString &message);
    void release();
    void startDualPort(int port);
    void beginDualReceiver(int selector);
    void beginDualRead();
    void advanceDual(bool timedOut);
    void finishDual();

    QPointer<Vehicle> _vehicle;
    QTimer _timer;
    QTimer _syncUpdateTimer;
    QElapsedTimer _syncLastMessage;
    int _syncReported = -1;
    QByteArray _buffer;
    QString _gps1Info = QStringLiteral("Не опитано");
    QString _gps2Info = QStringLiteral("Не опитано");
    QString _statusText = QStringLiteral("Натисніть UART для ручного опитування UBX-MON-VER");
    int _device = -1;
    int _polls = 0;
    bool _busy = false;
    bool _probeAll = false;
    bool _nextGpsPending = false;
    bool _dualMode = false;
    bool _dualRetryOtherPort = false;
    bool _dualAnyResponse = false;
    bool _dualMonVer = false;
    bool _dualUniqueIdReceived = false;
    bool _zedVerified = false;
    bool _neoVerified = false;
    bool _zedResponded = false;
    bool _neoResponded = false;
    int _dualReceiver = 0; // 1 ZED, 2 NEO
    int _dualPolls = 0;
    int _dualOriginalSelector = 1;
    bool _dualOriginalKnown = false;
    QString _activePort = QStringLiteral("Не визначено");
    QString _zedInfo = QStringLiteral("Не перевірено");
    QString _neoInfo = QStringLiteral("Не перевірено");
    QString _dualVersion;
    QString _dualUniqueId;
    QString _zedUniqueId;
    QString _neoUniqueId;
};
