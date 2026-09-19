#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VsratyiTranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen = load_module(ROOT / "tools" / "generate_vsratyi_translations.py", "vsratyi_gen")
        cls.patch = (ROOT / "tools" / "apply_vsratyi_language.py").read_text(encoding="utf-8")
        cls.default_patch = (ROOT / "patches" / "0002-ukrainian-default.patch").read_text(encoding="utf-8")

    def test_core_pirate_style_strings(self):
        cases = {
            "Ready To Fly": "Ну, наче полетить",
            "Error": "Ой, всьо",
            "Firmware": "Прошивка-шаманство",
            "Parameters": "Священні параметрики",
            "Arm": "Завести цю шайтан-машину",
            "GPS": "Супутникова магія",
        }
        for source, expected in cases.items():
            self.assertEqual(self.gen.funny_translation(source, "baseline", "AnyContext"), expected)

    def test_contextual_parameter_flavor(self):
        self.assertEqual(
            self.gen.funny_translation("Some parameter", "Параметр тесту", "ParameterEditor"),
            "Параметрик тесту",
        )

    def test_vsratyi_uses_custom_id_and_ukrainian_locale(self):
        self.assertIn("QLocale::Esperanto", self.patch)
        self.assertIn("return QLocale::Ukrainian", self.patch)
        self.assertNotIn("10001", self.patch)
        self.assertIn("qgc_source_vsratyi", self.patch)
        self.assertIn("qgc_json_vsratyi", self.patch)
        self.assertIn('QStringLiteral("Всратий")', self.patch)

    def test_clean_install_keeps_build_120_ukrainian_default(self):
        self.assertIn("settings.setValue(qLocaleLanguageName, QLocale::Ukrainian)", self.default_patch)
        self.assertIn("return QLocale::Ukrainian", self.default_patch)


if __name__ == "__main__":
    unittest.main()
