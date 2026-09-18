#!/usr/bin/env python3
import unittest

from generate_ukrainian_translations import contextual_override, find_manual_override


class UkrainianLocalizationRulesTest(unittest.TestCase):
    def test_airframe_frame_is_rama(self):
        self.assertEqual(
            contextual_override(
                "Frame",
                "APMAirframeComponent",
                ["../src/AutoPilotPlugins/APM/APMAirframeComponent.qml"],
            ),
            "Рама",
        )

    def test_bare_frame_defaults_to_vehicle_rama(self):
        self.assertEqual(contextual_override("Frame", "", []), "Рама")

    def test_airframe_frame_type_is_typ_ramy(self):
        self.assertEqual(
            contextual_override(
                "Frame Type",
                "APMAirframeComponent",
                ["../src/AutoPilotPlugins/APM/APMAirframeComponent.qml"],
            ),
            "Тип рами",
        )

    def test_video_frame_is_kadr(self):
        self.assertEqual(
            contextual_override(
                "Frame",
                "VideoSettings",
                ["../src/VideoManager/VideoSettings.qml"],
            ),
            "Кадр",
        )

    def test_attitude_terms_use_aviation_vocabulary(self):
        location = ["../src/FlightMap/Widgets/QGCAttitudeWidget.qml"]
        self.assertEqual(contextual_override("Roll", "Attitude", location), "Крен")
        self.assertEqual(contextual_override("Pitch", "Attitude", location), "Тангаж")
        self.assertEqual(contextual_override("Yaw", "Attitude", location), "Рискання")

    def test_current_depends_on_context(self):
        self.assertEqual(
            contextual_override(
                "Current",
                "PowerComponent",
                ["../src/AutoPilotPlugins/PX4/PowerComponent.qml"],
            ),
            "Струм",
        )
        self.assertEqual(
            contextual_override(
                "Current",
                "ParameterEditor",
                ["../src/QmlControls/ParameterEditor.qml"],
            ),
            "Поточне",
        )

    def test_arm_home_and_attitude_use_uav_vocabulary(self):
        self.assertEqual(contextual_override("Arm", "MainStatusIndicator", []), "Озброїти")
        self.assertEqual(contextual_override("Armed", "MainStatusIndicator", []), "Озброєно")
        self.assertEqual(contextual_override("Home", "FlyView", []), "HOME")
        self.assertEqual(contextual_override("Attitude", "FlyView", []), "Просторова орієнтація")

    def test_manual_override_is_context_specific_and_authoritative(self):
        overrides = {
            ("VideoSettings", "Frame"): "Кадр відео",
            ("", "Save"): "Зберегти вручну",
        }
        self.assertEqual(find_manual_override("Frame", "VideoSettings", overrides), "Кадр відео")
        self.assertIsNone(find_manual_override("Frame", "APMAirframeComponent", overrides))
        self.assertEqual(find_manual_override("Save", "AnyContext", overrides), "Зберегти вручну")

    def test_terrain_frame_is_coordinate_frame(self):
        self.assertEqual(
            contextual_override(
                "Terrain Frame",
                "MissionItem",
                ["../src/MissionManager/MissionItem.qml"],
            ),
            "Система координат рельєфу",
        )


if __name__ == "__main__":
    unittest.main()
