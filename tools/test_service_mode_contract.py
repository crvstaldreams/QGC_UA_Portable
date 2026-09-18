#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_MODE = ROOT / "custom" / "qml" / "ServiceMode.qml"
PARAM_EDITOR = ROOT / "custom" / "qml" / "ServiceParameterEditor.qml"
SERVO_PAGE = ROOT / "custom" / "qml" / "ServiceServoSafety.qml"
MAVLINK_PAGE = ROOT / "custom" / "qml" / "ServiceMavlinkStatus.qml"
MP_PARAMS_PAGE = ROOT / "custom" / "qml" / "ServiceMPParams.qml"
MP_PARAMS_CONTROLLER = ROOT / "custom" / "src" / "MPParamsController.cc"


class ServiceModeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = SERVICE_MODE.read_text(encoding="utf-8")
        cls.params = PARAM_EDITOR.read_text(encoding="utf-8")
        cls.servo = SERVO_PAGE.read_text(encoding="utf-8")
        cls.mavlink = MAVLINK_PAGE.read_text(encoding="utf-8")
        cls.mp_params = MP_PARAMS_PAGE.read_text(encoding="utf-8")
        cls.mp_controller = MP_PARAMS_CONTROLLER.read_text(encoding="utf-8")

    def test_only_required_service_sections_are_exposed(self):
        for label in ("Огляд", "Прошивка", "Параметри", "MP Params", "Датчики", "Servo/Saf.Mask", "MAVLink Status", "Реконнект"):
            self.assertIn(f'text: "{label}"', self.service)

    def test_service_panel_contains_live_orientation_map_gps_and_compass(self):
        self.assertIn("QGCAttitudeWidget", self.service)
        self.assertIn("FlightMap", self.service)
        self.assertIn("activeVehicle.gps.count.valueString", self.service)
        self.assertIn("activeVehicle.gps.lock.enumStringValue", self.service)
        self.assertIn("activeVehicle.gps.hdop.valueString", self.service)
        self.assertIn("QGCCompassWidget", self.service)

    def test_service_telemetry_fits_one_screen_without_scroll(self):
        self.assertNotIn("QGCFlickable {\n                id: serviceInfoScroll", self.service)
        self.assertIn("id: serviceInfoPanel", self.service)
        self.assertIn("RowLayout {", self.service)
        self.assertIn("columns: 4", self.service)
        self.assertIn("Крен %1°   Тангаж %2°", self.service)

    def test_service_sidebar_is_compact_and_compass_is_half_size(self):
        self.assertIn("Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 32", self.service)
        self.assertIn("compassSize: attitudeSize * 0.5", self.service)
        self.assertIn("Layout.preferredHeight: ScreenTools.defaultFontPixelHeight * 5.8", self.service)
        self.assertIn("Layout.preferredWidth: parent.width * 0.52", self.servo)
        self.assertIn("Layout.preferredHeight: visible ? ScreenTools.defaultFontPixelHeight * 1.95 : 0", self.servo)

    def test_sensor_component_uses_v508_qvariantlist_and_reconnect_reboots_vehicle(self):
        self.assertIn("components.length", self.service)
        self.assertIn("components[i]", self.service)
        self.assertIn('text: "Реконнект"', self.service)
        self.assertIn("activeVehicle.rebootVehicle()", self.service)

    def test_parameter_view_has_service_tree_without_explanation_panel(self):
        self.assertIn("Дерево параметрів", self.params)
        self.assertIn("serviceTreeModel", self.params)
        self.assertIn("BRD_", self.params)
        self.assertIn("SERVO", self.params)
        self.assertIn("controller.parameters", self.params)
        self.assertNotIn("longDescription", self.params)
        self.assertNotIn("defaultValueString", self.params)

    def test_mp_params_mission_planner_workflow(self):
        self.assertIn("ServiceMPParams.qml", self.service)
        for marker in ("Read Params", "Write Params", "Load File", "Save File", "Compare", "LinkConfiguration.TypeSerial"):
            self.assertIn(marker, self.mp_params)
        for marker in ("Mission Planner Params (*.param *.parm)", "MP Parameter Tree", "controller.treeModel", "controller.compareModel"):
            self.assertIn(marker, self.mp_params)
        for marker in ("_parseMpFile", "separator(QStringLiteral(\"[,\\\\s]+\"))", "stream << name << ',' << value", "writePending", "_rebuildTree"):
            self.assertIn(marker, self.mp_controller)

    def test_service_mavlink_status_refreshes_every_five_seconds(self):
        self.assertIn("ServiceMavlinkStatus.qml", self.service)
        self.assertIn("interval: 5000", self.mavlink)
        self.assertIn("messageFontPointSize: ScreenTools.defaultFontPointSize * 1.60", self.mavlink)
        self.assertIn("refreshMessages()", self.mavlink)

    def test_servo_safety_page_is_registered_in_service_mode(self):
        self.assertIn("ServiceServoSafety.qml", self.service)
        self.assertIn("activeVehicle.apmFirmware", self.service)
        self.assertIn("BRD_SAFETY_MASK", self.servo)
        self.assertIn("SERVO", self.servo)
        self.assertIn("activeVehicle.motorTest", self.servo)
        self.assertIn("СТОП", self.servo)


if __name__ == "__main__":
    unittest.main()
