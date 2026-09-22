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
FEATURE_PATCH = ROOT / "tools" / "apply_qgc_ua_features.py"


class ServiceModeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = SERVICE_MODE.read_text(encoding="utf-8")
        cls.params = PARAM_EDITOR.read_text(encoding="utf-8")
        cls.servo = SERVO_PAGE.read_text(encoding="utf-8")
        cls.mavlink = MAVLINK_PAGE.read_text(encoding="utf-8")
        cls.mp_params = MP_PARAMS_PAGE.read_text(encoding="utf-8")
        cls.mp_controller = MP_PARAMS_CONTROLLER.read_text(encoding="utf-8")
        cls.feature_patch = FEATURE_PATCH.read_text(encoding="utf-8")

    def test_only_required_service_sections_are_exposed(self):
        for label in ("Огляд", "Прошивка", "Параметри", "MP Params", "Датчики", "Servo/Saf.Mask", "MAVLink Status", "Реконнект"):
            self.assertIn(f'text: "{label}"', self.service)

    def test_service_mode_imports_flightmap_widgets(self):
        self.assertIn("import QGroundControl.FlightMap", self.service)

    def test_service_panel_contains_live_orientation_gps_and_compass(self):
        self.assertIn("QGCAttitudeWidget", self.service)
        self.assertNotIn("FlightMap {", self.service)
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

    def test_service_sidebar_instruments_are_equal_and_centered(self):
        self.assertIn("Layout.preferredWidth: ScreenTools.defaultFontPixelWidth * 32", self.service)
        self.assertIn("readonly property real instrumentSize", self.service)
        self.assertIn("ScreenTools.defaultFontPixelHeight * 10.5", self.service)
        self.assertEqual(self.service.count("Layout.preferredWidth: serviceInfoPanel.instrumentSize"), 2)
        self.assertEqual(self.service.count("Layout.preferredHeight: serviceInfoPanel.instrumentSize"), 2)
        self.assertGreaterEqual(self.service.count("Layout.alignment: Qt.AlignHCenter"), 2)
        self.assertIn("Layout.preferredWidth: parent.width * 0.52", self.servo)
        self.assertIn("Layout.preferredHeight: visible ? ScreenTools.defaultFontPixelHeight * 1.95 : 0", self.servo)

    def test_sensor_component_uses_v508_qvariantlist_and_reconnect_reboots_vehicle(self):
        self.assertIn("components.length", self.service)
        self.assertIn("components[i]", self.service)
        self.assertIn('text: "Реконнект"', self.service)
        self.assertIn("mainWindow.restartActiveConnections()", self.service)

    def test_parameter_view_has_service_tree_without_explanation_panel(self):
        self.assertIn("Дерево параметрів", self.params)
        self.assertIn("serviceTreeModel", self.params)
        self.assertIn("BRD_", self.params)
        self.assertIn("SERVO", self.params)
        self.assertIn("controller.parameters", self.params)
        self.assertNotIn("longDescription", self.params)
        self.assertNotIn("defaultValueString", self.params)

    def test_mp_params_controller_is_qml_registerable(self):
        header = (ROOT / "custom" / "src" / "MPParamsController.h").read_text(encoding="utf-8")
        self.assertIn("class MPParamsController : public FactPanelController", header)
        self.assertNotIn("class MPParamsController final", header)

    def test_mp_params_mission_planner_workflow(self):
        self.assertIn("ServiceMPParams.qml", self.service)
        for marker in ("Read Params", "Write Params", "Load File", "Save File", "Compare", "LinkConfiguration.TypeSerial"):
            self.assertIn(marker, self.mp_params)
        for marker in ("Mission Planner Params (*.param *.parm)", "controller.compareModel", "uiScale: 0.82", "columnFractions"):
            self.assertIn(marker, self.mp_params)
        self.assertNotIn("MP Parameter Tree", self.mp_params)
        self.assertNotIn("TreeView {", self.mp_params)
        self.assertIn('currentPage = "mpParams"', self.service)
        self.assertIn('qrc:/qml/QGroundControl/Custom/ServiceMPParams.qml', self.service)
        self.assertNotIn("ServiceMPParamsWindow.qml", self.service)
        for marker in ("_parseMpFile", "separator(QStringLiteral(\"[,\\\\s]+\"))", "stream << name << ',' << value", "writePending", "_rebuildTree"):
            self.assertIn(marker, self.mp_controller)

    def test_service_firmware_suppresses_advanced_popup_only_when_embedded(self):
        self.assertIn("item.serviceModeEmbedded = true", self.service)
        self.assertIn("property bool serviceModeEmbedded: false", self.feature_patch)
        self.assertIn("showAdvanced:   !serviceModeEmbedded", self.feature_patch)

    def test_service_mavlink_status_has_vertical_scrolling(self):
        self.assertIn("ScrollView {", self.mavlink)
        self.assertIn("ScrollBar.vertical.policy: ScrollBar.AlwaysOn", self.mavlink)
        self.assertIn("messagePanelMinHeight: mavlinkStatusScroll.availableHeight", self.mavlink)

    def test_service_mavlink_status_refreshes_every_five_seconds(self):
        self.assertIn("ServiceMavlinkStatus.qml", self.service)
        self.assertIn("interval: 5000", self.mavlink)
        self.assertIn("messageFontPointSize: ScreenTools.defaultFontPointSize", self.mavlink)
        self.assertIn("refreshMessages()", self.mavlink)

    def test_servo_safety_page_is_registered_in_service_mode(self):
        self.assertIn("ServiceServoSafety.qml", self.service)
        self.assertIn("activeVehicle.apmFirmware", self.service)
        self.assertIn("BRD_SAFETY_MASK", self.servo)
        self.assertIn("SERVO", self.servo)
        self.assertIn("activeVehicle.motorTest", self.servo)
        self.assertIn("СТОП", self.servo)
        self.assertIn('text: "FMU PWM OUT (AUX)"', self.servo)
        self.assertIn('text: "I/O PWM OUT (MAIN)"', self.servo)
        self.assertIn("safetyMaskFact.rawValue = maskValue", self.servo)
        self.assertIn("            255,", self.servo)
        self.assertIn("            65280,", self.servo)
        for marker in ('"9": 33', '"10": 34', '"11": 35', '"12": 36', '"13": 37', '"14": 38', '"15": 60'):
            self.assertIn(marker, self.servo)
        for marker in ('"1": 33', '"2": 34', '"3": 35', '"4": 36', '"5": 37', '"6": 38', '"7": 60'):
            self.assertIn(marker, self.servo)
        self.assertIn("setServoFunction(output, 0)", self.servo)
        self.assertIn('"15": 60', self.servo)
        self.assertIn('"7": 60', self.servo)
        self.assertIn("applyServoProfile", self.servo)
        self.assertIn("presetRevision", self.servo)
        self.assertIn("motorInterlock", self.servo)
        self.assertIn("ЗАПОБІЖНИК ЗНЯТО", self.servo)
        self.assertIn("ЗАПОБІЖНИК УВІМКНЕНО", self.servo)


if __name__ == "__main__":
    unittest.main()
