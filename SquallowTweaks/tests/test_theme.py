import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import theme  # noqa: E402


def lum(h: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = theme._rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class ThemeTests(unittest.TestCase):
    def test_all_themes_build_and_are_readable(self):
        self.assertGreaterEqual(len(theme.THEMES), 8)
        for name, base in theme.THEMES.items():
            p = theme.build(base)
            for key in ("bg", "card", "text", "accent", "deep1", "chip_on", "hero_base", "track", "danger_bg"):
                self.assertRegex(p[key], r"^#[0-9a-fA-F]{6}$", f"{name}.{key}")
            self.assertGreaterEqual(contrast(p["text"], p["bg"]), 7, f"{name}: Text auf Hintergrund")
            self.assertGreaterEqual(contrast(p["text"], p["card"]), 7, f"{name}: Text auf Karte")
            self.assertGreaterEqual(contrast(p["muted"], p["card"]), 3.5, f"{name}: gedaempfter Text")
            self.assertGreaterEqual(contrast(p["on_accent"], p["accent"]), 3.0, f"{name}: Button-Text")
            for sem in ("green", "red", "cyan", "yellow"):
                self.assertGreaterEqual(contrast(p[sem], p["card"]), 3.0, f"{name}: {sem}")

    def test_unknown_theme_falls_back(self):
        self.assertIn(theme.load_name(), theme.THEMES)


if __name__ == "__main__":
    unittest.main()
