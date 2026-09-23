#include "CompassTelemetryController.h"
#include "Vehicle.h"
#include <QtMath>

CompassTelemetryController::CompassTelemetryController(QObject* parent):QObject(parent){}

void CompassTelemetryController::setVehicle(Vehicle* vehicle) {
    if (_vehicle == vehicle) return;
    if (_vehicle) disconnect(_vehicle, nullptr, this, nullptr);
    _vehicle=vehicle; _valid={{false,false,false}};
    if (_vehicle) connect(_vehicle, &Vehicle::mavlinkMessageReceived, this, &CompassTelemetryController::_message);
    emit vehicleChanged(); emit headingsChanged();
}
void CompassTelemetryController::_set(int i,double x,double y,double z) {
    if (qFuzzyIsNull(x) && qFuzzyIsNull(y) && qFuzzyIsNull(z)) return;
    double d=qRadiansToDegrees(qAtan2(y,x)); if(d<0)d+=360.0;
    _x[i]=x; _y[i]=y; _z[i]=z; _field[i]=qSqrt(x*x+y*y+z*z);
    _heading[i]=d; _valid[i]=true; emit headingsChanged();
}
void CompassTelemetryController::_message(const mavlink_message_t& m) {
    switch(m.msgid) {
    case MAVLINK_MSG_ID_RAW_IMU: { mavlink_raw_imu_t v; mavlink_msg_raw_imu_decode(&m,&v); _set(0,v.xmag,v.ymag,v.zmag); break; }
    case MAVLINK_MSG_ID_SCALED_IMU2: { mavlink_scaled_imu2_t v; mavlink_msg_scaled_imu2_decode(&m,&v); _set(1,v.xmag,v.ymag,v.zmag); break; }
    case MAVLINK_MSG_ID_SCALED_IMU3: { mavlink_scaled_imu3_t v; mavlink_msg_scaled_imu3_decode(&m,&v); _set(2,v.xmag,v.ymag,v.zmag); break; }
    default: break;
    }
}
