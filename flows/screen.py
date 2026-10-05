"""Telas de fluxo. O JSON declara o componente. O render vira o generic do widget.

component:
  buttons — text + buttons[{label, value}]
  form — title, name, fields[{key, title, widget, validationType, help, placeholder, required}]

validationType é prop. O título do campo fica limpo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_COMPONENTS = {"buttons", "form"}
_WIDGETS = {"text": "TextWidget"}


def load_screens(path: Path) -> dict[str, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    screens = raw.get("screens")
    if not isinstance(screens, dict) or not screens:
        raise ValueError(f"{path.name}: screens vazio")
    for name, screen in screens.items():
        if not isinstance(screen, dict):
            raise ValueError(f"{path.name}: tela {name} invalida")
        _validate_screen(path.name, str(name), screen)
    return screens


def screen_text(screen: dict[str, Any]) -> str:
    text = screen.get("text") or screen.get("title") or ""
    return str(text)


def render_screen(screen: dict[str, Any]) -> dict[str, Any]:
    component = screen.get("component")
    if component == "buttons":
        return {
            "response_type": "option",
            "title": screen_text(screen),
            "options": [
                {"label": button["label"], "value": button["value"]}
                for button in screen["buttons"]
            ],
        }
    if component == "form":
        return _render_form(screen)
    raise ValueError(f"component desconhecido: {component}")


def _validate_screen(filename: str, name: str, screen: dict[str, Any]) -> None:
    component = screen.get("component")
    if component not in _COMPONENTS:
        raise ValueError(f"{filename}: tela {name} component invalido")
    if component == "buttons":
        if not str(screen.get("text") or "").strip():
            raise ValueError(f"{filename}: tela {name} sem text")
        buttons = screen.get("buttons")
        if not isinstance(buttons, list) or not buttons:
            raise ValueError(f"{filename}: tela {name} sem buttons")
        for button in buttons:
            if not str(button.get("label") or "").strip():
                raise ValueError(f"{filename}: tela {name} button sem label")
            if not str(button.get("value") or "").strip():
                raise ValueError(f"{filename}: tela {name} button sem value")
        return
    if not str(screen.get("title") or "").strip():
        raise ValueError(f"{filename}: tela {name} sem title")
    if not str(screen.get("name") or "").strip():
        raise ValueError(f"{filename}: tela {name} sem name")
    fields = screen.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError(f"{filename}: tela {name} sem fields")
    seen: set[str] = set()
    for field in fields:
        key = str(field.get("key") or "").strip()
        if not key or key in seen:
            raise ValueError(f"{filename}: tela {name} field key invalido")
        seen.add(key)
        if not str(field.get("title") or "").strip():
            raise ValueError(f"{filename}: tela {name} field {key} sem title")
        widget = str(field.get("widget") or "text")
        if widget not in _WIDGETS:
            raise ValueError(f"{filename}: tela {name} widget {widget} invalido")


def _render_form(screen: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    ui_schema: dict[str, Any] = {"ui:order": []}
    required: list[str] = []
    for field in screen["fields"]:
        key = str(field["key"])
        title = str(field["title"])
        widget = _WIDGETS[str(field.get("widget") or "text")]
        ui_schema["ui:order"].append(key)
        properties[key] = {"type": "string", "title": title}
        field_ui: dict[str, Any] = {
            "ui:title": title,
            "ui:widget": widget,
            "ui:help": str(field.get("help") or ""),
            "ui:placeholder": str(field.get("placeholder") or ""),
        }
        validation_type = str(field.get("validationType") or "").strip()
        if validation_type:
            field_ui["ui:options"] = {"validationType": validation_type}
        ui_schema[key] = field_ui
        if field.get("required", True):
            required.append(key)
    return {
        "response_type": "forms",
        "name": screen["name"],
        "json_schema": {
            "type": "object",
            "title": screen["title"],
            "required": required,
            "properties": properties,
        },
        "ui_schema": ui_schema,
        "form_data": {},
    }
