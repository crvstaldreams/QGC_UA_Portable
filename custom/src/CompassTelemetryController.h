#pragma once
#include <QObject>
#include <QtQml/qqml.h>
#include <array>
#include "QGCMAVLink.h"
#include "Vehicle.h"

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
    Q_PROPERTY(double x1 READ x1 NOTIFY headingsChanged)
    Q_PROPERTY(double y1 READ y1 NOTIFY headingsChanged)
    Q_PROPERTY(double z1 READ z1 NOTIFY headingsChanged)
    Q_PROPERTY(double field1 READ field1 NOTIFY headingsChanged)
    Q_PROPERTY(double x2 READ x2 NOTIFY headingsChanged)
    Q_PROPERTY(double y2 READ y2 NOTIFY headingsChanged)
    Q_PROPERTY(double z2 READ z2 NOTIFY headingsChanged)
    Q_PROPERTY(double field2 READ field2 NOTIFY headingsChanged)
    Q_PROPERTY(double x3 READ x3 NOTIFY headingsChanged)
    Q_PROPERTY(double y3 READ y3 NOTIFY headingsChanged)
    Q_PROPERTY(double z3 READ z3 NOTIFY headingsChanged)
    Q_PROPERTY(double field3 READ field3 NOTIFY headingsChanged)
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
    double x1() const { return _x[0]; } double y1() const { return _y[0]; } double z1() const { return _z[0]; } double field1() const { return _field[0]; }
    double x2() const { return _x[1]; } double y2() const { return _y[1]; } double z2() const { return _z[1]; } double field2() const { return _field[1]; }
    double x3() const { return _x[2]; } double y3() const { return _y[2]; } double z3() const { return _z[2]; } double field3() const { return _field[2]; }
signals:
    void vehicleChanged();
    void headingsChanged();
private slots:
    void _message(const mavlink_message_t& message);
private:
    void _set(int index, double x, double y, double z);
    Vehicle* _vehicle=nullptr;
    std::array<double,3> _heading{{0,0,0}};
    std::array<bool,3> _valid{{false,false,false}};
    std::array<double,3> _x{{0,0,0}}, _y{{0,0,0}}, _z{{0,0,0}}, _field{{0,0,0}};
};
