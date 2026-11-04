"""SquallowTweaks - Farbthemen. Das gewaehlte Thema wird beim Start geladen (Wechsel = Neustart)."""
from __future__ import annotations

import json
import os
from pathlib import Path

SETTINGS_FILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "SquallowTweaks" / "settings.json"


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(int(round(x + (y - x) * t)) for x, y in zip(ra, rb))


DARK_SEMANTIC = {"cyan": "#5EEAD4", "green": "#4ADE80", "yellow": "#FBBF24", "red": "#F87171", "pink": "#F472B6"}
LIGHT_SEMANTIC = {"cyan": "#0E9F8E", "green": "#15803D", "yellow": "#B45309", "red": "#DC2626", "pink": "#DB2777"}


def _dark(name: str, bg: str, sidebar: str, card: str, card2: str, border: str, accent: str, accent2: str, on_accent: str = "#ffffff") -> dict:
    return dict(name=name, dark=True, bg=bg, sidebar=sidebar, card=card, card2=card2, border=border, text="#EDEDF7", muted="#8C8CA8",
                dim="#5E5E7A", accent=accent, accent2=accent2, on_accent=on_accent, **DARK_SEMANTIC)


THEMES = {
    "Lila": _dark("Lila", "#0A0A10", "#0D0D15", "#13131D", "#1B1B2B", "#23233A", "#8B7CF6", "#B89CFF"),
    "Blau": _dark("Blau", "#080B12", "#0B0F18", "#10151F", "#182030", "#212B40", "#4C8DFF", "#8DBBFF"),
    "Grün": _dark("Grün", "#080D0B", "#0B120F", "#101A15", "#17261E", "#203329", "#2FCB8F", "#86EFAC", "#04140D"),
    "Rot": _dark("Rot", "#0F0809", "#150B0D", "#1D1113", "#2A1A1D", "#3A2226", "#F25C6E", "#FF9AA6"),
    "Orange": _dark("Orange", "#0F0B08", "#150F0A", "#1D1610", "#2A2017", "#3A2D20", "#FB923C", "#FDBA74", "#1A0E03"),
    "Pink": _dark("Pink", "#0F080E", "#150B14", "#1D111B", "#2A1A27", "#3A2236", "#EC6AC9", "#F5A8E3", "#1A0414"),
    "Schwarz": _dark("Schwarz", "#000000", "#040404", "#0B0B0B", "#141414", "#1E1E1E", "#D4D4D8", "#FFFFFF", "#0A0A0A"),
    "Weiß": dict(name="Weiß", dark=False, bg="#F2F3F8", sidebar="#FFFFFF", card="#FFFFFF", card2="#EEF0F7", border="#DCDEEA", text="#14141F",
                 muted="#585B72", dim="#8D90A6", accent="#6D5BF0", accent2="#5240D6", on_accent="#ffffff", **LIGHT_SEMANTIC),
}


def build(base: dict) -> dict:
    p = dict(base)
    bg, card, accent, dark = p["bg"], p["card"], p["accent"], p["dark"]
    p["border_hi"] = mix(p["border"], accent, 0.35)
    p["deep1"] = mix(bg, accent, 0.30 if dark else 0.16)
    p["deep2"] = mix(bg, accent, 0.14 if dark else 0.07)
    p["chip_on"] = mix(card, accent, 0.28 if dark else 0.14)
    p["ghost_hover"] = mix(p["card2"], accent, 0.14 if dark else 0.10)
    p["nav_hover"] = mix(p["sidebar"], accent, 0.16 if dark else 0.08)
    p["hero_base"] = mix(card, accent, 0.14 if dark else 0.06)
    p["hero_hover"] = mix(card, accent, 0.22 if dark else 0.10)
    p["hero_border"] = mix(p["border"], accent, 0.45 if dark else 0.30)
    p["input_focus"] = mix(card, accent, 0.06)
    p["acc_a"] = accent
    p["acc_b"] = p["accent2"] if dark else mix(accent, "#000000", 0.0)
    p["acc_a_hi"] = mix(accent, "#ffffff", 0.18)
    p["acc_b_hi"] = mix(p["accent2"], "#ffffff", 0.18)
    if not dark:
        p["acc_b"] = mix(accent, "#8B5CF6", 0.5)
        p["acc_b_hi"] = mix(p["acc_b"], "#ffffff", 0.15)
    p["track"] = mix(card, p["text"], 0.08)
    p["grid"] = mix(bg, p["text"], 0.08)
    p["toggle_off"] = mix(card, p["text"], 0.16)
    p["toggle_off_hi"] = mix(card, p["text"], 0.26)
    p["disabled"] = mix(card, p["text"], 0.10)
    p["scroll"] = mix(bg, p["text"], 0.18)
    p["scroll_hi"] = mix(bg, p["text"], 0.32)
    p["bar_track"] = mix(card, p["text"], 0.10)
    p["danger_bg"] = mix(card, p["red"], 0.14)
    p["danger_hover"] = mix(card, p["red"], 0.24)
    p["danger_border"] = mix(card, p["red"], 0.40)
    return p


def load_name() -> str:
    try:
        name = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("theme", "Lila")
        return name if name in THEMES else "Lila"
    except Exception:  # noqa: BLE001
        return "Lila"


def save_name(name: str) -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
        data["theme"] = name
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


_FLAGS: dict = {}


def _read_all() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def get_flag(name: str, default=True):
    if not _FLAGS:
        _FLAGS.update(_read_all() or {"_": 1})
    return _FLAGS.get(name, default)


def set_flag(name: str, value) -> None:
    data = _read_all()
    data[name] = value
    _FLAGS.clear()
    _FLAGS.update(data)
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


CURRENT = load_name()
P = build(THEMES[CURRENT])
