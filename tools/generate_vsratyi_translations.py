#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# Deliberately silly Ukrainian localization inspired by old pirate game/movie
# dubs. Technical identifiers, numbers, placeholders and markup are inherited
# from the normal Ukrainian translation and remain intact.
EXACT = {
    "System": "Системка, не чіпай",
    "Language": "Балаканина",
    "Vehicle Configuration": "Гараж шайтан-машини",
    "Application Settings": "Крутилки цієї програми",
    "Plan Flight": "Намалювати куди летіти",
    "Analyze Tools": "Розбирати польоти",
    "Exit": "Вийти красиво",
    "Advanced Mode": "Режим для тих, хто знає що робить",
    "Turn off Advanced Mode?": "Точно сховати дорослі крутилки?",
    "Comms Lost": "Зв'язок утік у ліс",
    "Ready To Fly": "Ну, наче полетить",
    "Not Ready": "Не готово, шеф",
    "Disconnected - Click to manually connect": "Відвалилось. Тицяй сюди й причіпляй вручну",
    "Armed": "Шайтан-машина заряджена",
    "Flying": "Летимо. Куди — не питай",
    "Landing": "Сідаємо, тримайся",
    "Arm": "Завести цю шайтан-машину",
    "Disarm": "Заглушити цю халепу",
    "Force Arm": "Завести силою, бо дуже треба",
    "Vehicle Messages": "Що борт бурмоче",
    "Sensor Status": "Чи живі чуйки",
    "Overall Status": "Як воно взагалі",
    "No Messages": "Тиша. Підозріло",
    "Edit Parameter": "Покрутити параметрик",
    "Waiting for parameters...": "Чекаємо священні параметрики...",
    "Vehicle Error": "Борт каже «ой»",
    "Additional errors received": "Ще помилок підвезли",
    "EMERGENCY": "ВСЕ ПРОПАЛО",
    "ALERT": "ШЕФ, АЛЯРМ!",
    "Critical": "Припливли",
    "Error": "Ой, всьо",
    "Warning": "Тривожний дзвіночок",
    "Notice": "До відома, громадяни",
    "Info": "Інфа сотка",
    "Debug": "Копання в кишках",
    "General": "Усяке-різне",
    "General Settings": "Головні крутилки",
    "Settings": "Крутилки",
    "Comm Links": "Шнурки до космосу",
    "Link Settings": "Крутилки зв'язку",
    "Add": "Докинути",
    "Delete": "Видалити к бісам",
    "Edit": "Поколупати",
    "Connect": "Причепитися",
    "Disconnect": "Відчепитися",
    "Cancel": "Та ну його",
    "Save": "Зберегти це неподобство",
    "Open": "Розпакувати дверцята",
    "Close": "Зачинити лавочку",
    "OK": "Ага",
    "Yes": "Таки так",
    "No": "Нє-а",
    "Apply": "Влупити зміни",
    "Reset": "Скинути до заводського чаклунства",
    "Refresh": "Смикнути ще раз",
    "Name": "Як це звати",
    "Type": "Що воно таке",
    "Status": "Як там справи",
    "Enabled": "Врублено",
    "Disabled": "Вирублено",
    "Auto": "Само якось",
    "Manual": "Ручками",
    "Serial": "Послідовний дріт",
    "Baud Rate": "Швидкість бітів по трубі",
    "Port": "Дірка",
    "Mission": "Великий план",
    "Parameters": "Священні параметрики",
    "Parameter": "Параметрик",
    "Value": "Циферка",
    "Units": "В чому міряємо",
    "Description": "Що це за штука",
    "Default": "Як було з заводу",
    "Vehicle": "Літаюче відро",
    "Vehicles": "Літаючі відра",
    "Firmware": "Прошивка-шаманство",
    "Airframe": "Рама цього пепелаца",
    "Sensors": "Чуйки-датчики",
    "Radio": "Радійка",
    "Flight Modes": "Режими польотного цирку",
    "Power": "Електрика й магія",
    "Motors": "Крутилки-мотори",
    "Safety": "Щоб не бахнуло",
    "Camera": "Око Саурона",
    "Joystick": "Палка керування",
    "Telemetry": "Телеметрія з космосу",
    "Video": "Кіно",
    "Maps": "Карти: де ми взагалі?",
    "Offline Maps": "Карти на випадок апокаліпсису",
    "Log Download": "Тягнути чорну скриньку",
    "MAVLink Console": "Шайтан-консоль MAVLink",
    "MAVLink Inspector": "Підглядальник MAVLink",
    "Analyze": "Розбір польотів",
    "Fly": "Полетіли",
    "Plan": "План Б",
    "Setup": "Шаманство",
    "Position": "Де ця штука",
    "Altitude": "Наскільки високо залізли",
    "Speed": "Як швидко несемось",
    "Distance": "Скільки ще пиляти",
    "Heading": "Куди носом",
    "Battery": "Батарейка, живи",
    "Voltage": "Вольтики",
    "Current": "Ампери, що тікають",
    "Temperature": "Наскільки гаряче",
    "Signal": "Палички зв'язку",
    "GPS": "Супутникова магія",
    "Home": "Хата",
    "Takeoff": "Рвонути в небо",
    "Land": "Приземлити це чудо",
    "Return": "Вернути як було",
    "Pause": "Стоп-кран",
    "Resume": "Далі поїхали",
    "Start": "Погнали",
    "Stop": "Харош",
    "Clear": "Вимести це добро",
    "Search": "Шукати по засіках",
    "File": "Файлик",
    "Folder": "Папочка",
    "Browse": "Покопатися",
    "Select": "Тицнути",
    "Selected": "Натицяно",
    "None": "Нічого нема",
    "Off": "Вирублено",
    "On": "Врублено",
    "Indoor": "У хаті",
    "Outdoor": "На свіжому повітрі",
    "Color Scheme": "Фарбування кабіни",
    "Map Provider": "Хто малює карти",
    "Map Type": "Яка саме карта",
    "Mute all audio output": "Заткнути всі звуки",
    "Clear all settings on next start": "На наступному старті забути все як страшний сон",
    "UI Scaling": "Зум інтерфейсу",
    "Version": "Якої воно давності",
    "About": "Хто це наробив",
    "Help": "Рятуйте",
    "Summary": "Коротше, шо маємо",
    "Compass": "Компасик, не бреши",
    "Accelerometer": "Аксель, який усе відчуває",
    "Gyroscope": "Крутилка простору",
    "Magnetometer": "Магнітна чуйка",
    "Barometer": "Тискомір",
    "Calibration": "Калібровка через чаклунство",
    "Calibrate": "Почаклувати",
    "Reboot Vehicle": "Перезавантажити літаюче відро",
    "Vehicle Setup": "Гараж літаючого відра",
    "Vehicle Settings": "Крутилки літаючого відра",
    "Parameter Editor": "Крутилка параметриків",
    "Parameter Description": "Шо робить цей параметрик",
    "Default Value": "Заводська циферка",
    "Current Value": "Що стоїть зараз",
    "Minimum": "Нижче вже нікуди",
    "Maximum": "Стеля",
    "Roll": "Крен, тобто завалило боком",
    "Pitch": "Тангаж, тобто носом туди-сюди",
    "Yaw": "Рискання, тобто крутить хвостом",
    "Throttle": "Газюлька",
    "Failsafe": "План «ой лишенько»",
    "Failsafes": "Плани «ой лишенько»",
    "Waypoint": "Точка пригод",
    "Waypoints": "Точки пригод",
    "Motor Test": "Покрутити мотори й не злякатись",
    "Frame Setup": "Вибрати раму для пепелаца",
}

SHORT_SUFFIX_RULES = (
    ("Waiting for", " — сидимо, чекаємо"),
    ("Failed", " — не вийшло, шеф"),
    ("Unknown", " — хто його зна"),
    ("Unavailable", " — нема такого добра"),
)

CONTEXT_REPLACEMENTS = (
    (("parameter", "fact"), (("Параметр", "Параметрик"), ("параметр", "параметрик"))),
    (("sensor", "compass", "imu"), (("датчик", "чуйка"), ("Датчик", "Чуйка"))),
    (("firmware",), (("прошивка", "прошивка-шаманство"), ("Прошивка", "Прошивка-шаманство"))),
)


def _text(element: ET.Element | None) -> str:
    return "" if element is None else "".join(element.itertext())


def funny_translation(source: str, base: str, context: str) -> str:
    if source in EXACT:
        return EXACT[source]

    result = base
    context_lower = context.lower()

    for hints, replacements in CONTEXT_REPLACEMENTS:
        if any(hint in context_lower for hint in hints):
            for old, new in replacements:
                result = result.replace(old, new)

    if len(source) <= 90:
        for prefix, suffix in SHORT_SUFFIX_RULES:
            if source.startswith(prefix) and suffix not in result:
                result = result + suffix
                break

    # Small pirate-dub flavor for common confirmation questions without
    # touching placeholders or technical identifiers.
    if source.endswith("?") and len(source) < 70 and source not in EXACT:
        if result.endswith("?"):
            result = result[:-1] + ", чи шо?"
        elif not result.endswith("чи шо?"):
            result += " — чи шо?"

    return result


def process_file(source_path: Path, output_path: Path) -> tuple[int, int]:
    tree = ET.parse(source_path)
    root = tree.getroot()
    root.set("language", "uk_UA")
    root.set("sourcelanguage", "en")

    changed = 0
    total = 0

    for context in root.findall("context"):
        context_name = _text(context.find("name"))
        for message in context.findall("message"):
            source_element = message.find("source")
            translation = message.find("translation")
            if source_element is None or translation is None:
                continue

            source = _text(source_element)
            if not source:
                translation.attrib.pop("type", None)
                continue

            translation.attrib.pop("type", None)
            plural_forms = translation.findall("numerusform")
            if plural_forms:
                for form in plural_forms:
                    base = _text(form)
                    funny = funny_translation(source, base, context_name)
                    if funny != base:
                        changed += 1
                    form.text = funny
            else:
                base = _text(translation)
                funny = funny_translation(source, base, context_name)
                if funny != base:
                    changed += 1
                translation.text = funny
            total += 1

    ET.indent(tree, space="  ")
    body = ET.tostring(root, encoding="unicode")
    output_path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + body + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return total, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    translations = root / "translations"

    pairs = [
        (translations / "qgc_source_uk_UA.ts", translations / "qgc_source_vsratyi.ts"),
        (translations / "qgc_json_uk_UA.ts", translations / "qgc_json_vsratyi.ts"),
    ]

    total = 0
    changed = 0
    for source, output in pairs:
        if not source.is_file():
            raise FileNotFoundError(source)
        file_total, file_changed = process_file(source, output)
        total += file_total
        changed += file_changed
        print(f"vsratyi {output.name}: messages={file_total} jokes={file_changed}")

    if changed < 80:
        raise RuntimeError(f"Vsratyi translation looks too plain: only {changed} changed messages")

    print(f"Vsratyi summary: messages={total} humorous={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
