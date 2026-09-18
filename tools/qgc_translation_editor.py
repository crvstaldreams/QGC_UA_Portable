#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tkinter as tk
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk


@dataclass
class Record:
    context: str
    source: str
    translation: str
    locations: tuple[str, ...]


def element_text(element):
    return "" if element is None else "".join(element.itertext())


def load_records(source_root: Path) -> list[Record]:
    result: list[Record] = []
    for filename in ("qgc_source_uk_UA.ts", "qgc_json_uk_UA.ts"):
        path = source_root / "translations" / filename
        if not path.is_file():
            raise FileNotFoundError(f"Не знайдено {path}")
        root = ET.parse(path).getroot()
        for context in root.findall("context"):
            context_name = element_text(context.find("name"))
            for message in context.findall("message"):
                source = element_text(message.find("source"))
                if not source:
                    continue
                translation = element_text(message.find("translation"))
                locations = tuple(
                    node.attrib.get("filename", "")
                    for node in message.findall("location")
                    if node.attrib.get("filename")
                )
                result.append(Record(context_name, source, translation, locations))
    return result


def load_overrides(path: Path) -> dict[tuple[str, str], str]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[tuple[str, str], str] = {}
    for entry in data.get("entries", []):
        if not isinstance(entry, dict):
            continue
        source = str(entry.get("source", "")).strip()
        translation = str(entry.get("translation", "")).strip()
        context = str(entry.get("context", "")).strip()
        if source and translation:
            result[(context, source)] = translation
    return result


def save_overrides(path: Path, values: dict[tuple[str, str], str]) -> None:
    entries = [
        {"context": context, "source": source, "translation": translation}
        for (context, source), translation in sorted(
            values.items(), key=lambda item: (item[0][0].casefold(), item[0][1].casefold())
        )
    ]
    payload = {
        "version": 1,
        "description": "Manual Ukrainian translations. Context-specific entries override global entries and all automatic translation rules.",
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Editor:
    def __init__(self, root: tk.Tk, source_root: Path, override_path: Path):
        self.root = root
        self.override_path = override_path
        self.records = load_records(source_root)
        self.overrides = load_overrides(override_path)
        self.visible: list[Record] = []
        self.selected: Record | None = None

        root.title("QGroundControl UA — редактор перекладу")
        root.geometry("1380x820")
        root.minsize(1020, 620)

        self.search = tk.StringVar()
        self.manual_only = tk.BooleanVar(value=False)
        self.global_override = tk.BooleanVar(value=False)
        self.status = tk.StringVar()

        toolbar = ttk.Frame(root, padding=8)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text="Пошук:").pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.search, width=55).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Checkbutton(
            toolbar, text="Лише мої правки", variable=self.manual_only
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text="Зберегти все", command=self.save_all).pack(side=tk.RIGHT)

        panes = ttk.Panedwindow(root, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes, padding=(10, 0, 0, 0))
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        self.table = ttk.Treeview(
            left, columns=("context", "source", "translation"), show="headings"
        )
        for key, title, width in (
            ("context", "Контекст", 220),
            ("source", "Оригінал", 420),
            ("translation", "Переклад", 420),
        ):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, stretch=key != "context")
        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.bind("<<TreeviewSelect>>", self.select_record)

        self.context_label = ttk.Label(right, wraplength=520)
        self.location_label = ttk.Label(right, wraplength=520)
        ttk.Label(right, text="Контекст:").pack(anchor=tk.W)
        self.context_label.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(right, text="Файл/місце:").pack(anchor=tk.W)
        self.location_label.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(right, text="Оригінал").pack(anchor=tk.W)
        self.source_text = tk.Text(right, height=7, wrap=tk.WORD)
        self.source_text.pack(fill=tk.X, pady=(2, 8))

        ttk.Label(right, text="Поточний переклад").pack(anchor=tk.W)
        self.current_text = tk.Text(right, height=6, wrap=tk.WORD)
        self.current_text.pack(fill=tk.X, pady=(2, 8))

        ttk.Label(right, text="Ваш переклад — має найвищий пріоритет").pack(anchor=tk.W)
        self.override_text = tk.Text(right, height=8, wrap=tk.WORD)
        self.override_text.pack(fill=tk.BOTH, expand=True, pady=(2, 6))

        ttk.Checkbutton(
            right,
            text="Застосовувати до цього тексту у всіх контекстах",
            variable=self.global_override,
        ).pack(anchor=tk.W, pady=(0, 8))

        buttons = ttk.Frame(right)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Зберегти правку", command=self.save_selected).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Видалити правку", command=self.remove_selected).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(buttons, text="Взяти поточний переклад", command=self.copy_current).pack(
            side=tk.LEFT
        )

        ttk.Label(root, textvariable=self.status, padding=(8, 0, 8, 8)).pack(fill=tk.X)

        self.search.trace_add("write", lambda *_: self.refresh())
        self.manual_only.trace_add("write", lambda *_: self.refresh())
        self.refresh()

    def effective(self, record: Record) -> str:
        return (
            self.overrides.get((record.context, record.source))
            or self.overrides.get(("", record.source))
            or ""
        )

    def refresh(self):
        query = self.search.get().strip().casefold()
        manual_only = self.manual_only.get()
        self.visible = []
        for record in self.records:
            override = self.effective(record)
            text = " ".join(
                [record.context, record.source, record.translation, override, *record.locations]
            ).casefold()
            if query and query not in text:
                continue
            if manual_only and not override:
                continue
            self.visible.append(record)

        self.table.delete(*self.table.get_children())
        for index, record in enumerate(self.visible):
            self.table.insert(
                "",
                tk.END,
                iid=str(index),
                values=(record.context, record.source, self.effective(record) or record.translation),
            )
        self.status.set(
            f"Показано {len(self.visible)} з {len(self.records)} | ручних правок: {len(self.overrides)} | {self.override_path}"
        )

    @staticmethod
    def put_text(widget: tk.Text, text: str):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)

    def select_record(self, _event=None):
        selected = self.table.selection()
        if not selected:
            return
        self.selected = self.visible[int(selected[0])]
        record = self.selected
        self.context_label.configure(text=record.context or "(без контексту)")
        self.location_label.configure(text="\n".join(record.locations) or "—")
        self.put_text(self.source_text, record.source)
        self.put_text(self.current_text, record.translation)

        context_value = self.overrides.get((record.context, record.source))
        global_value = self.overrides.get(("", record.source))
        if context_value is not None:
            self.global_override.set(False)
            value = context_value
        elif global_value is not None:
            self.global_override.set(True)
            value = global_value
        else:
            self.global_override.set(False)
            value = record.translation
        self.put_text(self.override_text, value)

    def key_for_selected(self):
        if self.selected is None:
            return None
        return (
            "" if self.global_override.get() else self.selected.context,
            self.selected.source,
        )

    def save_selected(self):
        key = self.key_for_selected()
        if key is None:
            return
        value = self.override_text.get("1.0", tk.END).strip()
        if not value:
            messagebox.showwarning("Переклад", "Переклад не може бути порожнім.")
            return
        self.overrides[key] = value
        save_overrides(self.override_path, self.overrides)
        self.refresh()

    def remove_selected(self):
        if self.selected is None:
            return
        self.overrides.pop((self.selected.context, self.selected.source), None)
        self.overrides.pop(("", self.selected.source), None)
        save_overrides(self.override_path, self.overrides)
        self.refresh()

    def copy_current(self):
        if self.selected is not None:
            self.put_text(self.override_text, self.selected.translation)

    def save_all(self):
        save_overrides(self.override_path, self.overrides)
        messagebox.showinfo(
            "QGroundControl UA",
            "Збережено. Під час наступної збірки ці правки матимуть пріоритет над автоперекладом.",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--overrides", required=True, type=Path)
    args = parser.parse_args()

    root = tk.Tk()
    try:
        Editor(root, args.source_root.resolve(), args.overrides.resolve())
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("Помилка", str(exc))
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
