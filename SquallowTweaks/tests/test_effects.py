import os
import sys
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication
    HAVE_QT = True
except Exception:  # noqa: BLE001
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, "PySide6 nicht installiert")
class EffectTests(unittest.TestCase):
    def test_every_theme_has_an_effect_that_paints(self):
        import effects
        import theme
        QApplication.instance() or QApplication([])
        self.assertEqual(set(effects.EFFECTS), set(theme.THEMES))
        for name, cls in effects.EFFECTS.items():
            fx = cls()
            img = QImage(900, 230, QImage.Format_ARGB32)
            img.fill(0)
            p = QPainter(img)
            for t in (0.0, 1.7, 9.3, 31.0):
                fx.paint(p, 900, 230, t)
            p.end()
            self.assertTrue(any(img.pixelColor(x, y).alpha() for x in range(0, 900, 37) for y in range(0, 230, 23)), f"{name}: nichts gezeichnet")

    def test_hover_widgets_paint_with_spotlight_and_ripple(self):
        from PySide6.QtCore import QPointF
        import ui_common as ui
        QApplication.instance() or QApplication([])
        card = ui.Card()
        card.resize(300, 120)
        card.hv.v = 1.0
        card._mouse = QPointF(80, 40)
        img = card.grab().toImage()
        self.assertGreater(img.width(), 100)
        btn = ui.AnimButton("Test", "accent")
        btn.resize(160, 48)
        btn._rip_pos = QPointF(30, 20)
        btn._rip.start()
        btn._shine.start()
        self.assertGreater(btn.grab().width(), 50)
        tg = ui.Toggle()
        tg.set_checked_silent(True)
        tg._pulse.start()
        self.assertGreater(tg.grab().width(), 10)

    def test_area_chart_modes(self):
        import ui_common as ui
        QApplication.instance() or QApplication([])
        ch = ui.AreaChart()
        ch.resize(300, 130)
        for v in (10, 40, 25, 70, 35):
            ch.push(v)
        for mode in ("Live", "Avg", "Peak"):
            ch.mode = mode
            self.assertGreater(ch.grab().width(), 100)


if __name__ == "__main__":
    unittest.main()
