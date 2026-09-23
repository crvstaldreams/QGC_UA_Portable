#pragma once
#include <QObject>
#include <QtQml/qqml.h>
#include <array>
#include "QGCMAVLink.h"

class Vehicle;

class CompassTelemetryController : public QObject {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(Vehicle* vehicle READ vehicle WRITE setVehicle NOTIFY vehicleChanged)
    Q_PROPERTY(double heading1 READ heading1 NOTIFY headingsChanged)
    Q_PROPERTY(double heading2 READ heading2 NOTIFY headingsChanged)
    Q_PROPERTY(double heading3 READ heading3 NOTIFY headingsChanged)
    Q_PROPERTY(bool valid1 READ valid1 NOTIFY headingsChanged)
    Q_PROPERTY(bool valid2 READ valid2 NOTIFY headingsChanged)
    Q_PROPERTY(bool valid3 READ valid3 NOTIFY headingsChanged)
public:
    explicit CompassTelemetryController(QObject* parent=nullptr);
    Vehicle* vehicle() const { return _vehicle; }
    void setVehicle(Vehicle* vehicle);
    double heading1() const { return _heading[0]; }
    double heading2() const { return _heading[1]; }
    double heading3() const { return _heading[2]; }
    bool valid1() const { return _valid[0]; }
    bool valid2() const { return _valid[1]; }
    bool valid3() const { return _valid[2]; }
signals:
    void vehicleChanged();
    void headingsChanged();
private slots:
    void _message(const mavlink_message_t& message);
private:
    void _set(int index, double x, double y);
    Vehicle* _vehicle=nullptr;
    std::array<double,3> _heading{{0,0,0}};
    std::array<bool,3> _valid{{false,false,false}};
};
