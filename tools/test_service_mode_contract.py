#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE_MODE = ROOT / "custom" / "qml" / "ServiceMode.qml"
PARAM_EDITOR = ROOT / "custom" / "qml" / "ServiceParameterEditor.qml"


class ServiceModeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = SERVICE_MODE.read_text(encoding="utf-8")
        cls.params = PARAM_EDITOR.read_text(encoding="utf-8")

    def test_only_required_service_sections_are_exposed(self):
        for label in ("Огляд", "Прошивка", "Параметри", "Датчики", "Servo/Saf.Mask", "Реконнект"):
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

    def test_servo_safety_page_is_registered_in_service_mode(self):
        self.assertIn("ServiceServoSafety.qml", self.service)


if __name__ == "__main__":
    unittest.main()
