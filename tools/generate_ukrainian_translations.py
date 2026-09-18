#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MANUAL_TRANSLATIONS = {
    "System": "Система",
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
    "Default": "За замовчуванням",
    "Vehicle": "Борт",
    "Vehicles": "Борти",
    "Firmware": "Прошивка",
    "Airframe": "Рама",
    "Sensors": "Датчики",
    "Radio": "Радіокерування",
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
    "Position": "Положення",
    "Altitude": "Висота",
    "Speed": "Швидкість",
    "Distance": "Відстань",
    "Heading": "Курс",
    "Battery": "Акумулятор",
    "Voltage": "Напруга",
    "Current": "Поточне",
    "Temperature": "Температура",
    "Signal": "Сигнал",
    "GPS": "GPS",
    "Home": "HOME",
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

AVIATION_EXACT = {
    "Summary": "Огляд",
    "Firmware": "Прошивка",
    "Sensors": "Датчики",
    "Parameters": "Параметри",
    "Arm": "Озброїти",
    "Armed": "Озброєно",
    "Disarm": "Роззброїти",
    "Force Arm": "Примусово озброїти",
    "Home": "HOME",
    "Return to Home": "Повернення до HOME",
    "Attitude": "Просторова орієнтація",
    "Orientation": "Орієнтація",
    "Rotation": "Поворот",
    "Ground Speed": "Шляхова швидкість",
    "Airspeed": "Повітряна швидкість",
    "Vertical Speed": "Вертикальна швидкість",
    "Course Over Ground": "Шляховий курс",
    "GPS Lock": "Фіксація GPS",
    "Satellites": "Супутники",
    "Accuracy": "Точність",
    "Link": "Канал зв’язку",
    "Communication Link": "Канал зв’язку",
    "Servo": "Сервопривід",
    "Actuator": "Виконавчий механізм",
    "Actuators": "Виконавчі механізми",
    "Level Horizon": "Вирівняти горизонт",
    "Sensor Settings": "Налаштування датчиків",
    "Airframe": "Рама",
    "Airframe Type": "Тип рами",
    "Frame Type": "Тип рами",
    "Frame Class": "Клас рами",
    "Frame selection": "Вибір рами",
    "Frame Setup": "Налаштування рами",
    "Frame: %1": "Рама: %1",
    "Roll": "Крен",
    "Pitch": "Тангаж",
    "Yaw": "Рискання",
    "Roll Angle": "Кут крену",
    "Pitch Angle": "Кут тангажу",
    "Yaw Angle": "Кут рискання",
    "Heading": "Курс",
    "Heading to Home": "Курс на HOME",
    "Flight Mode": "Режим польоту",
    "Flight Modes": "Режими польоту",
    "Throttle": "Газ",
    "Failsafe": "Аварійний захист",
    "Failsafes": "Аварійні захисти",
    "Arming": "Озброєння",
    "Disarming": "Роззброєння",
    "Waypoint": "Точка маршруту",
    "Waypoints": "Точки маршруту",
    "Home Position": "Точка HOME",
    "Terrain Frame": "Система координат рельєфу",
    "Frame Rate": "Частота кадрів",
    "Frame rate": "Частота кадрів",
    "Motor Test": "Тест моторів",
    "Compass": "Компас",
    "Accelerometer": "Акселерометр",
    "Gyroscope": "Гіроскоп",
    "Magnetometer": "Магнітометр",
    "Barometer": "Барометр",
    "Calibration": "Калібрування",
    "Calibrate": "Калібрувати",
    "Reboot Vehicle": "Перезавантажити борт",
    "Vehicle Setup": "Налаштування борту",
    "Vehicle Settings": "Налаштування борту",
    "Parameter Editor": "Редактор параметрів",
    "Parameter Description": "Опис параметра",
    "Default Value": "Типове значення",
    "Current Value": "Поточне значення",
    "Minimum": "Мінімум",
    "Maximum": "Максимум",
}

AIRFRAME_CONTEXT_HINTS = (
    "airframe",
    "autopilotplugins",
    "vehiclesetup",
    "vehicle/setup",
    "motor",
    "actuator",
)

VIDEO_CONTEXT_HINTS = (
    "video",
    "camera",
    "stream",
    "image",
)

POWER_CONTEXT_HINTS = (
    "power",
    "battery",
    "currentmonitor",
    "current monitor",
    "esc",
)

FLIGHT_CONTEXT_HINTS = (
    "flyview",
    "flight",
    "mission",
    "vehicle",
    "autopilot",
    "toolbar",
)

FRAME_FORM_REPLACEMENTS = (
    (r"\bкошика\b", "рами"),
    (r"\bкошиком\b", "рамою"),
    (r"\bкошику\b", "рамі"),
    (r"\bкошики\b", "рами"),
    (r"\bкошиків\b", "рам"),
    (r"\bкошик\b", "рама"),
    (r"\bкадру\b", "рами"),
    (r"\bкадром\b", "рамою"),
    (r"\bкадрі\b", "рамі"),
    (r"\bкадри\b", "рами"),
    (r"\bкадрів\b", "рам"),
    (r"\bкадр\b", "рама"),
    (r"\bрамки\b", "рами"),
    (r"\bрамку\b", "раму"),
    (r"\bрамкою\b", "рамою"),
    (r"\bрамці\b", "рамі"),
    (r"\bрамка\b", "рама"),
    (r"\bкаркаса\b", "рами"),
    (r"\bкаркасом\b", "рамою"),
    (r"\bкаркасі\b", "рамі"),
    (r"\bкаркаси\b", "рами"),
    (r"\bкаркасів\b", "рам"),
    (r"\bкаркас\b", "рама"),
    (r"\bфрейму\b", "рами"),
    (r"\bфрейм\b", "рама"),
)


def _context_blob(context_name: str, locations: list[str] | tuple[str, ...]) -> str:
    return (context_name + " " + " ".join(locations)).lower()


def _has_context(context_blob: str, hints: tuple[str, ...]) -> bool:
    return any(hint in context_blob for hint in hints)


def _frame_means_airframe(
    source: str,
    context_name: str,
    locations: list[str] | tuple[str, ...],
) -> bool:
    if not re.search(r"\bframe\b", source, flags=re.IGNORECASE):
        return False
    if source in {"Terrain Frame", "Frame Rate", "Frame rate"}:
        return False
    context_blob = _context_blob(context_name, locations)
    if _has_context(context_blob, VIDEO_CONTEXT_HINTS):
        return False
    return _has_context(context_blob, AIRFRAME_CONTEXT_HINTS)


def contextual_override(source: str, context_name: str = "", locations: list[str] | tuple[str, ...] = ()) -> str | None:
    """Return a domain-correct Ukrainian translation for ambiguous QGC terminology."""
    context_blob = _context_blob(context_name, locations)

    if source == "Frame":
        if _has_context(context_blob, VIDEO_CONTEXT_HINTS):
            return "Кадр"
        if _has_context(context_blob, AIRFRAME_CONTEXT_HINTS):
            return "Рама"
        # In QGC a bare Frame label overwhelmingly refers to the vehicle frame.
        return "Рама"

    if source == "Current":
        if _has_context(context_blob, POWER_CONTEXT_HINTS):
            return "Струм"
        return "Поточне"

    if source in AVIATION_EXACT:
        return AVIATION_EXACT[source]

    if source in MANUAL_TRANSLATIONS:
        return MANUAL_TRANSLATIONS[source]

    return None


def postprocess_translation(
    source: str,
    translated: str,
    context_name: str = "",
    locations: list[str] | tuple[str, ...] = (),
) -> str:
    """Apply context-sensitive terminology after raw machine translation."""
    context_blob = _context_blob(context_name, locations)
    result = translated

    if _frame_means_airframe(source, context_name, locations):
        for pattern, replacement in FRAME_FORM_REPLACEMENTS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # HOME is a conventional navigation label in autopilot UIs. Avoid literal
    # household translations in flight/mission contexts.
    if re.search(r"\bhome\b", source, flags=re.IGNORECASE) and _has_context(context_blob, FLIGHT_CONTEXT_HINTS):
        result = re.sub(r"\bдодому\b", "до HOME", result, flags=re.IGNORECASE)
        result = re.sub(r"\bдомівк(?:а|и|у|ою|ці)\b", "HOME", result, flags=re.IGNORECASE)
        result = re.sub(r"\bдім\b", "HOME", result, flags=re.IGNORECASE)

    return result


def audit_translation(
    source: str,
    translated: str,
    context_name: str = "",
    locations: list[str] | tuple[str, ...] = (),
) -> None:
    """Fail the build when known dangerous terminology regressions reappear."""
    context_blob = _context_blob(context_name, locations)
    lowered = translated.lower()

    if _frame_means_airframe(source, context_name, locations):
        if "рам" not in lowered:
            raise ValueError(
                f"Airframe terminology regression: {source!r} -> {translated!r} "
                f"({context_name}, {locations})"
            )
        if any(bad in lowered for bad in ("кошик", "кадр", "каркас", "фрейм")):
            raise ValueError(
                f"Bad airframe translation remains: {source!r} -> {translated!r} "
                f"({context_name}, {locations})"
            )

    if source == "Current":
        expected = "струм" if _has_context(context_blob, POWER_CONTEXT_HINTS) else "поточ"
        if expected not in lowered:
            raise ValueError(
                f"Ambiguous Current translation regression: {source!r} -> {translated!r} "
                f"({context_name}, {locations})"
            )


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


def translate_one(
    source: str,
    translator,
    cache: dict[str, str],
    context_name: str = "",
    locations: list[str] | tuple[str, ...] = (),
) -> str:
    override = contextual_override(source, context_name, locations)
    if override is not None:
        audit_translation(source, override, context_name, locations)
        return override

    if source in cache:
        raw_result = cache[source]
    elif should_leave_as_technical(source):
        raw_result = source
        cache[source] = raw_result
    else:
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

        raw_result = f"{leading}{translated}{trailing}"
        # Cache only the raw machine translation. Context-sensitive terminology
        # is applied below per message, so one source string can safely appear
        # in different QGC contexts.
        cache[source] = raw_result

    result = postprocess_translation(source, raw_result, context_name, locations)
    audit_translation(source, result, context_name, locations)
    return result


def process_ts(path: Path, translator, cache: dict[str, str]) -> tuple[int, int, int]:
    tree = ET.parse(path)
    root = tree.getroot()
    translated_count = 0
    manual_count = 0
    unchanged_count = 0

    for context in root.findall("context"):
        context_name_element = context.find("name")
        context_name = "".join(context_name_element.itertext()) if context_name_element is not None else ""

        for message in context.findall("message"):
            source_element = message.find("source")
            translation_element = message.find("translation")
            if source_element is None or translation_element is None:
                continue

            # Clear Qt Linguist's unfinished marker even for the few upstream
            # bookkeeping messages which have an empty <source/>. Those entries
            # have no user-visible text to translate.
            translation_element.attrib.pop("type", None)

            source = "".join(source_element.itertext())
            if not source:
                continue

            locations = [
                location.attrib.get("filename", "")
                for location in message.findall("location")
                if location.attrib.get("filename")
            ]

            if contextual_override(source, context_name, locations) is not None:
                manual_count += 1

            plural_forms = translation_element.findall("numerusform")
            if plural_forms:
                translated = translate_one(source, translator, cache, context_name, locations)
                for form in plural_forms:
                    form.text = translated
            else:
                translated = translate_one(source, translator, cache, context_name, locations)
                translation_element.text = translated

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
