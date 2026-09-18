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
        for label in ("Summary", "Firmware", "Параметри", "Sensors"):
            self.assertIn(f'text: qsTr("{label}")', self.service)

    def test_service_panel_contains_live_orientation_map_gps_and_compass(self):
        self.assertIn("QGCAttitudeWidget", self.service)
        self.assertIn("FlightMap", self.service)
        self.assertIn("activeVehicle.gps.count.valueString", self.service)
        self.assertIn("activeVehicle.gps.lock.enumStringValue", self.service)
        self.assertIn("activeVehicle.gps.hdop.valueString", self.service)
        self.assertIn("QGCCompassWidget", self.service)

    def test_parameter_view_has_tree_table_and_explanation_panel(self):
        self.assertIn("Дерево параметрів", self.params)
        self.assertIn("controller.categories", self.params)
        self.assertIn("controller.parameters", self.params)
        self.assertIn("longDescription", self.params)
        self.assertIn("shortDescription", self.params)
        self.assertIn("defaultValueString", self.params)


if __name__ == "__main__":
    unittest.main()
