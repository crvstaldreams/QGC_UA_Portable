#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MANUAL_TRANSLATIONS = {
    "System": "Системна",
    "Language": "Мова",
    "Vehicle Configuration": "Налаштування борту",
    "Application Settings": "Налаштування застосунку",
    "Plan Flight": "Планування польоту",
    "Analyze Tools": "Інструменти аналізу",
    "Close %1": "Закрити %1",
    "%1 Version": "Версія %1",
    "Exit": "Вийти",
    "Advanced Mode": "Розширений режим",
    "Turn off Advanced Mode?": "Вимкнути розширений режим?",
    "Comms Lost": "Зв’язок втрачено",
    "Ready To Fly": "Готовий до польоту",
    "Not Ready": "Не готовий",
    "Disconnected - Click to manually connect": "Від’єднано — натисніть для ручного підключення",
    "Armed": "Озброєно",
    "Flying": "У польоті",
    "Landing": "Посадка",
    "Arm": "Озброїти",
    "Disarm": "Роззброїти",
    "Force Arm": "Примусово озброїти",
    "Vehicle Messages": "Повідомлення борту",
    "Sensor Status": "Стан датчиків",
    "Overall Status": "Загальний стан",
    "No Messages": "Немає повідомлень",
    "Edit Parameter": "Редагувати параметр",
    "Waiting for parameters...": "Очікування параметрів...",
    "Vehicle Error": "Помилка борту",
    "Additional errors received": "Отримано додаткові помилки",
    "EMERGENCY": "АВАРІЯ",
    "ALERT": "ТРИВОГА",
    "Critical": "Критично",
    "Error": "Помилка",
    "Warning": "Попередження",
    "Notice": "Сповіщення",
    "Info": "Інформація",
    "Debug": "Налагодження",
    "General": "Загальні",
    "General Settings": "Загальні налаштування",
    "Settings": "Налаштування",
    "Comm Links": "Канали зв’язку",
    "Link Settings": "Налаштування зв’язку",
    "Add": "Додати",
    "Delete": "Видалити",
    "Edit": "Редагувати",
    "Connect": "Підключити",
    "Disconnect": "Відключити",
    "Cancel": "Скасувати",
    "Save": "Зберегти",
    "Open": "Відкрити",
    "Close": "Закрити",
    "OK": "OK",
    "Yes": "Так",
    "No": "Ні",
    "Apply": "Застосувати",
    "Reset": "Скинути",
    "Refresh": "Оновити",
    "Name": "Назва",
    "Type": "Тип",
    "Status": "Стан",
    "Enabled": "Увімкнено",
    "Disabled": "Вимкнено",
    "Auto": "Авто",
    "Manual": "Ручний",
    "Serial": "Послідовний порт",
    "Baud Rate": "Швидкість порту",
    "UDP Port": "UDP-порт",
    "TCP Port": "TCP-порт",
    "Host Address": "Адреса вузла",
    "Port": "Порт",
    "Mission": "Місія",
    "Parameters": "Параметри",
    "Parameter": "Параметр",
    "Value": "Значення",
    "Units": "Одиниці",
    "Description": "Опис",
    "Default": "Типово",
    "Vehicle": "Борт",
    "Vehicles": "Борти",
    "Firmware": "Прошивка",
    "Airframe": "Рама",
    "Sensors": "Датчики",
    "Radio": "Радіоканал",
    "Flight Modes": "Режими польоту",
    "Power": "Живлення",
    "Motors": "Мотори",
    "Safety": "Безпека",
    "Camera": "Камера",
    "Joystick": "Джойстик",
    "Telemetry": "Телеметрія",
    "Video": "Відео",
    "Maps": "Карти",
    "Offline Maps": "Офлайн-карти",
    "Log Download": "Завантаження журналів",
    "MAVLink Console": "Консоль MAVLink",
    "MAVLink Inspector": "Інспектор MAVLink",
    "Analyze": "Аналіз",
    "Fly": "Політ",
    "Plan": "План",
    "Setup": "Налаштування",
    "Position": "Позиція",
    "Altitude": "Висота",
    "Speed": "Швидкість",
    "Distance": "Відстань",
    "Heading": "Курс",
    "Battery": "Акумулятор",
    "Voltage": "Напруга",
    "Current": "Струм",
    "Temperature": "Температура",
    "Signal": "Сигнал",
    "GPS": "GPS",
    "Home": "Дім",
    "Takeoff": "Зліт",
    "Land": "Посадка",
    "Return": "Повернення",
    "Pause": "Пауза",
    "Resume": "Продовжити",
    "Start": "Почати",
    "Stop": "Зупинити",
    "Clear": "Очистити",
    "Search": "Пошук",
    "File": "Файл",
    "Folder": "Папка",
    "Browse": "Огляд",
    "Select": "Вибрати",
    "Selected": "Вибрано",
    "None": "Немає",
    "Off": "Вимкнено",
    "On": "Увімкнено",
    "Indoor": "У приміщенні",
    "Outdoor": "На вулиці",
    "Color Scheme": "Колірна схема",
    "Map Provider": "Провайдер карти",
    "Map Type": "Тип карти",
    "Application Load/Save Path": "Шлях завантаження/збереження застосунку",
    "Mute all audio output": "Вимкнути весь звук",
    "Clear all settings on next start": "Очистити всі налаштування під час наступного запуску",
    "UI Scaling": "Масштаб інтерфейсу",
    "Version": "Версія",
    "About": "Про застосунок",
    "Help": "Довідка",
}

TECHNICAL_TERMS = (
    "QGroundControl", "MAVLink", "PX4", "ArduPilot", "GPS", "RTK", "UDP", "TCP",
    "COM", "USB", "GCS", "RC", "ESC", "VTOL", "RTL", "QML", "JSON", "RTSP", "RTP",
)

PROTECT_RE = re.compile(
    r"(%L?\d+|%n|https?://\S+|(?:[A-Z][A-Z0-9]*_)+[A-Z0-9_]+|"
    + r"\b(?:" + "|".join(re.escape(x) for x in TECHNICAL_TERMS) + r")\b|<[^>]+>)"
)

TECHNICAL_ONLY_RE = re.compile(r"^[A-Z][A-Z0-9_.:/+-]{1,}$")


def protect_tokens(text: str) -> tuple[str, list[str]]:
    values: list[str] = []

    def repl(match: re.Match[str]) -> str:
        values.append(match.group(0))
        return f"ZXQGCTOKEN{len(values) - 1}ZX"

    return PROTECT_RE.sub(repl, text), values


def restore_tokens(text: str, values: list[str]) -> str:
    for index, value in enumerate(values):
        token = f"ZXQGCTOKEN{index}ZX"
        if token not in text:
            raise ValueError(f"translation dropped protected token {value!r}")
        text = text.replace(token, value)
    return text


def load_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def ensure_argos_translation():
    try:
        import argostranslate.package
        import argostranslate.translate
    except Exception as exc:
        raise RuntimeError(
            "argostranslate is required. Install argostranslate==1.11.0 before running this script"
        ) from exc

    installed = argostranslate.translate.get_installed_languages()
    source = next((x for x in installed if x.code == "en"), None)
    target = next((x for x in installed if x.code == "uk"), None)
    if source and target:
        translation = source.get_translation(target)
        if translation is not None:
            return translation

    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    package = next((p for p in packages if p.from_code == "en" and p.to_code == "uk"), None)
    if package is None:
        raise RuntimeError("Argos EN->UK translation package was not found")

    model_path = package.download()
    argostranslate.package.install_from_path(model_path)

    installed = argostranslate.translate.get_installed_languages()
    source = next((x for x in installed if x.code == "en"), None)
    target = next((x for x in installed if x.code == "uk"), None)
    if not source or not target:
        raise RuntimeError("Argos EN->UK model installation did not expose both languages")

    translation = source.get_translation(target)
    if translation is None:
        raise RuntimeError("Argos EN->UK translation object is unavailable after installation")
    return translation


def should_leave_as_technical(source: str) -> bool:
    stripped = source.strip()
    if not stripped:
        return True
    if not re.search(r"[A-Za-z]", stripped):
        return True
    if TECHNICAL_ONLY_RE.fullmatch(stripped):
        return True
    return False


def translate_one(source: str, translator, cache: dict[str, str]) -> str:
    if source in MANUAL_TRANSLATIONS:
        return MANUAL_TRANSLATIONS[source]
    if source in cache:
        return cache[source]
    if should_leave_as_technical(source):
        cache[source] = source
        return source

    leading = source[: len(source) - len(source.lstrip())]
    trailing = source[len(source.rstrip()) :]
    core = source.strip()
    protected, values = protect_tokens(core)

    try:
        translated = translator.translate(protected).strip()
        translated = restore_tokens(translated, values)
    except Exception:
        translated = core

    if not translated:
        translated = core

    result = f"{leading}{translated}{trailing}"
    cache[source] = result
    return result


def process_ts(path: Path, translator, cache: dict[str, str]) -> tuple[int, int, int]:
    tree = ET.parse(path)
    root = tree.getroot()
    translated_count = 0
    manual_count = 0
    unchanged_count = 0

    for message in root.findall(".//message"):
        source_element = message.find("source")
        translation_element = message.find("translation")
        if source_element is None or translation_element is None:
            continue

        source = "".join(source_element.itertext())
        if not source:
            continue

        if source in MANUAL_TRANSLATIONS:
            manual_count += 1

        plural_forms = translation_element.findall("numerusform")
        if plural_forms:
            translated = translate_one(source, translator, cache)
            for form in plural_forms:
                form.text = translated
        else:
            translated = translate_one(source, translator, cache)
            translation_element.text = translated

        translation_element.attrib.pop("type", None)
        if translated == source:
            unchanged_count += 1
        else:
            translated_count += 1

    ET.indent(tree, space="  ")
    body = ET.tostring(root, encoding="unicode")
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + body + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return translated_count, manual_count, unchanged_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    targets = [
        source_root / "translations" / "qgc_source_uk_UA.ts",
        source_root / "translations" / "qgc_json_uk_UA.ts",
    ]
    for path in targets:
        if not path.is_file():
            print(f"Missing Ukrainian TS file: {path}", file=sys.stderr)
            return 1

    cache = load_cache(args.cache.resolve())
    translator = ensure_argos_translation()

    total_translated = 0
    total_manual = 0
    total_unchanged = 0
    for path in targets:
        translated, manual, unchanged = process_ts(path, translator, cache)
        total_translated += translated
        total_manual += manual
        total_unchanged += unchanged
        print(
            f"uk-translated {path}: translated={translated} manual={manual} unchanged={unchanged}"
        )

    save_cache(args.cache.resolve(), cache)
    print(
        f"Ukrainian translation summary: translated={total_translated} "
        f"manual={total_manual} unchanged={total_unchanged} cache={len(cache)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
