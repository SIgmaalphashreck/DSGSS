"""SquallowTweaks - Jedes Design hat seinen eigenen animierten Hintergrund-Effekt im Hero-Banner.

Lila: Nebel mit Sternen und Sternschnuppe · Blau: Wellen mit Blasen · Gruen: Viren (Bio-Scan) · Rot: aufsteigende Glut
Orange: Synthwave-Sonne mit Gitter · Pink: fallende Bluetenblaetter · Schwarz: Matrix-Code · Weiss: weiche Lichter (Bokeh)
Alles ist reine Optik und laeuft nur, solange das Banner sichtbar ist.
"""
from __future__ import annotations

import math
import random
import time
import weakref

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

import theme
from ui_common import ACCENT, ACCENT2, BG, CARD, CYAN, GREEN, PINK, RED, YELLOW, Card, alpha, lerp


def glow(p: QPainter, cx: float, cy: float, r: float, color, a: int) -> None:
    g = QRadialGradient(cx, cy, r)
    g.setColorAt(0, alpha(color, a))
    g.setColorAt(1, alpha(color, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(QPointF(cx, cy), r, r)


class Effect:
    def __init__(self, seed: int = 0):
        self.r = random.Random(seed)

    def paint(self, p: QPainter, w: int, h: int, t: float) -> None:  # pragma: no cover - ueberschrieben
        pass


class Nebula(Effect):
    """Lila: wandernde Farbnebel, funkelnde Sterne und gelegentlich eine Sternschnuppe."""

    def __init__(self):
        super().__init__(1)
        self.stars = [(self.r.random(), self.r.random(), self.r.uniform(0.8, 2.2), self.r.uniform(0, 6.28)) for _ in range(46)]

    def paint(self, p, w, h, t):
        for col, sp, ph in ((ACCENT, 0.35, 0.0), (CYAN, 0.27, 2.1), (PINK, 0.21, 4.2)):
            cx = w * (0.25 + 0.5 * (0.5 + 0.5 * math.sin(t * sp + ph)))
            cy = h * (0.35 + 0.3 * math.sin(t * sp * 1.3 + ph))
            glow(p, cx, cy, h * 1.2, col, 60)
        p.setPen(Qt.NoPen)
        for x, y, s, ph in self.stars:
            p.setBrush(alpha("#ffffff", int(70 + 110 * (0.5 + 0.5 * math.sin(t * 1.4 + ph)))))
            p.drawEllipse(QPointF(x * w, y * h), s, s)
        k = (t % 8.0) / 1.3
        if k < 1:
            x0, y0 = w * 0.9 - k * w * 0.5, h * 0.05 + k * h * 0.5
            g = QLinearGradient(x0, y0, x0 + 90, y0 - 45)
            g.setColorAt(0, alpha("#ffffff", int(230 * (1 - k))))
            g.setColorAt(1, alpha("#ffffff", 0))
            p.setPen(QPen(g, 2))
            p.drawLine(QPointF(x0, y0), QPointF(x0 + 90, y0 - 45))


class Waves(Effect):
    """Blau: uebereinanderliegende Wellen und aufsteigende Blasen."""

    def __init__(self):
        super().__init__(2)
        self.bubbles = [(self.r.random(), self.r.uniform(18, 50), self.r.uniform(3, 9), self.r.uniform(0, 6.28)) for _ in range(16)]

    def paint(self, p, w, h, t):
        for i, (amp, freq, sp, a) in enumerate(((16, 0.011, 0.9, 70), (11, 0.017, -1.3, 55), (8, 0.025, 1.8, 45))):
            path = QPainterPath()
            path.moveTo(0, h)
            x = 0
            while x <= w + 8:
                path.lineTo(x, h * (0.62 + 0.09 * i) + amp * math.sin(x * freq + t * sp + i))
                x += 8
            path.lineTo(w + 8, h)
            path.closeSubpath()
            g = QLinearGradient(0, h * 0.5, 0, h)
            g.setColorAt(0, alpha(ACCENT if i != 1 else CYAN, a))
            g.setColorAt(1, alpha(ACCENT, 8))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawPath(path)
        p.setBrush(Qt.NoBrush)
        for x0, sp, size, ph in self.bubbles:
            y = h - ((t * sp + ph * 30) % (h + 30)) + 10
            p.setPen(QPen(alpha("#ffffff", 90), 1.2))
            p.drawEllipse(QPointF(x0 * w + 7 * math.sin(t + ph), y), size, size)


class Virus(Effect):
    """Gruen: Bio-Scan. Treibende Viren mit Stacheln, Sechseck-Gitter und sich ausbreitende Infektionsringe."""

    def __init__(self):
        super().__init__(3)
        self.v = [(self.r.uniform(0.08, 0.95), self.r.uniform(0.15, 0.85), self.r.uniform(13, 27), self.r.uniform(0.3, 0.8), self.r.uniform(0, 6.28))
                  for _ in range(9)]
        self._grid_key = None
        self._grid = QPainterPath()

    def _hex_grid(self, w, h) -> QPainterPath:
        if self._grid_key == (w, h):
            return self._grid
        path = QPainterPath()
        s = 26.0
        dx, dy = s * 1.5, s * math.sqrt(3) / 2
        col = 0
        x = 0.0
        while x < w + s:
            y = (dy if col % 2 else 0.0) - dy
            while y < h + s:
                pts = [QPointF(x + s * math.cos(math.radians(60 * k)), y + s * math.sin(math.radians(60 * k))) for k in range(6)]
                path.moveTo(pts[0])
                for q in pts[1:] + [pts[0]]:
                    path.lineTo(q)
                y += dy * 2
            x += dx
            col += 1
        self._grid_key, self._grid = (w, h), path
        return path

    def paint(self, p, w, h, t):
        p.setPen(QPen(alpha(GREEN, 22), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(self._hex_grid(w, h))
        sx = (t * 0.12 % 1.4 - 0.2) * w
        g = QLinearGradient(sx - 60, 0, sx + 60, 0)
        g.setColorAt(0, alpha(GREEN, 0))
        g.setColorAt(0.5, alpha(GREEN, 40))
        g.setColorAt(1, alpha(GREEN, 0))
        p.fillRect(QRectF(sx - 60, 0, 120, h), g)
        n = len(self.v)
        for i, (x0, y0, rad, sp, ph) in enumerate(self.v):
            cx = x0 * w + 26 * math.sin(t * sp + ph)
            cy = y0 * h + 14 * math.cos(t * sp * 0.8 + ph)
            glow(p, cx, cy, rad * 3.2, GREEN, 55)
            p.save()
            p.translate(cx, cy)
            p.rotate(math.degrees(t * 0.25 + ph))
            pulse = 1 + 0.06 * math.sin(t * 2.2 + ph)
            p.setPen(QPen(alpha(GREEN, 190), 1.6))
            for k in range(12):
                a = k * math.pi / 6
                p.drawLine(QPointF(math.cos(a) * rad * pulse, math.sin(a) * rad * pulse), QPointF(math.cos(a) * rad * 1.42, math.sin(a) * rad * 1.42))
            p.setBrush(alpha(GREEN, 230))
            p.setPen(Qt.NoPen)
            for k in range(12):
                a = k * math.pi / 6
                p.drawEllipse(QPointF(math.cos(a) * rad * 1.45, math.sin(a) * rad * 1.45), rad * 0.11, rad * 0.11)
            p.setBrush(alpha(GREEN, 45))
            p.setPen(QPen(alpha(GREEN, 210), 2))
            p.drawEllipse(QPointF(0, 0), rad * pulse, rad * pulse)
            p.setPen(Qt.NoPen)
            p.setBrush(alpha(GREEN, 120))
            for dx, dy, s in ((-0.3, -0.2, 0.22), (0.25, 0.1, 0.18), (-0.05, 0.38, 0.14)):
                p.drawEllipse(QPointF(dx * rad, dy * rad), s * rad, s * rad)
            p.restore()
        k = (t % 6.0) / 2.4
        if k < 1:
            x0, y0, rad, sp, ph = self.v[int(t // 6.0) % n]
            cx = x0 * w + 26 * math.sin(t * sp + ph)
            cy = y0 * h + 14 * math.cos(t * sp * 0.8 + ph)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(alpha(GREEN, int(200 * (1 - k))), 2))
            p.drawEllipse(QPointF(cx, cy), rad * (1.6 + 5 * k), rad * (1.6 + 5 * k))


class Embers(Effect):
    """Rot: aufsteigende Glut mit Flackern und pulsierender Hitze am Boden."""

    def __init__(self):
        super().__init__(4)
        self.e = [(self.r.random(), self.r.uniform(18, 55), self.r.uniform(1.8, 4.6), self.r.uniform(0, 6.28), self.r.random() * 300) for _ in range(90)]

    def paint(self, p, w, h, t):
        g = QLinearGradient(0, h, 0, h * 0.35)
        g.setColorAt(0, alpha(RED, int(90 + 30 * math.sin(t * 2))))
        g.setColorAt(1, alpha(RED, 0))
        p.fillRect(QRectF(0, 0, w, h), g)
        p.setPen(Qt.NoPen)
        for x0, sp, size, ph, off in self.e:
            prog = ((t * sp + off) % (h * 1.1)) / (h * 1.1)
            y = h - prog * h * 1.1
            x = x0 * w + 14 * math.sin(t * 1.7 + ph) * (0.4 + prog)
            col = lerp(YELLOW, RED, prog)
            fl = 0.6 + 0.4 * math.sin(t * 9 + ph)
            glow(p, x, y, size * 5, col, int(120 * (1 - prog) * fl))
            p.setBrush(alpha(col, int(240 * (1 - prog) * fl)))
            p.drawEllipse(QPointF(x, y), size * (1 - prog * 0.5), size * (1 - prog * 0.5))


class Synthwave(Effect):
    """Orange: gestreifte Retro-Sonne ueber einem Perspektiv-Gitter, das auf dich zufaehrt."""

    def paint(self, p, w, h, t):
        hor = h * 0.62
        cx, cy, r = w * 0.74, hor - h * 0.02, h * 0.52
        p.save()
        p.setClipRect(QRectF(0, 0, w, hor))
        g = QLinearGradient(0, cy - r, 0, cy + r)
        g.setColorAt(0, alpha(YELLOW, 210))
        g.setColorAt(1, alpha(PINK, 210))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setBrush(QColor(CARD))
        for i in range(7):
            yy = cy + r * (0.05 + i * 0.14)
            p.drawRect(QRectF(cx - r, yy, 2 * r, 1.5 + i * 1.3))
        p.restore()
        glow(p, cx, hor, r * 1.6, ACCENT2, 36)
        p.setPen(QPen(alpha(ACCENT2, 200), 1.5))
        p.drawLine(QPointF(0, hor), QPointF(w, hor))
        for k in range(-14, 15):
            p.setPen(QPen(alpha(ACCENT, 110), 1))
            p.drawLine(QPointF(w / 2 + k * 6, hor), QPointF(w / 2 + k * w / 13, h))
        for i in range(9):
            z = ((i + t * 0.7) % 9) / 9
            y = hor + (h - hor) * z * z
            p.setPen(QPen(alpha(ACCENT, int(30 + 150 * z)), 1))
            p.drawLine(QPointF(0, y), QPointF(w, y))


class Petals(Effect):
    """Pink: fallende Kirschbluetenblaetter."""

    def __init__(self):
        super().__init__(6)
        self.p = [(self.r.random(), self.r.uniform(16, 38), self.r.uniform(6, 13), self.r.uniform(0, 6.28), self.r.uniform(-1.4, 1.4), self.r.random() * 300) for _ in range(26)]

    def paint(self, p, w, h, t):
        p.setPen(Qt.NoPen)
        for x0, sp, size, ph, rot, off in self.p:
            y = ((t * sp + off) % (h + 50)) - 25
            x = x0 * w + 32 * math.sin(t * 0.8 + ph)
            p.save()
            p.translate(x, y)
            p.rotate(math.degrees(t * rot + ph))
            p.scale(1, 0.55 + 0.45 * math.cos(t * 1.3 + ph))
            g = QLinearGradient(-size, 0, size, 0)
            g.setColorAt(0, alpha(PINK, 200))
            g.setColorAt(1, alpha("#ffffff", 190))
            p.setBrush(g)
            path = QPainterPath()
            path.moveTo(-size, 0)
            path.cubicTo(-size * 0.4, -size * 0.9, size * 0.9, -size * 0.5, size, 0)
            path.cubicTo(size * 0.9, size * 0.5, -size * 0.4, size * 0.9, -size, 0)
            p.drawPath(path)
            p.restore()


class Matrix(Effect):
    """Schwarz: fallender Code-Regen in Silber."""
    CHARS = "01SQTWEAKFPSMS<>/\\|=+*#$%&"

    def __init__(self):
        super().__init__(7)
        self.cols = [(self.r.uniform(40, 110), self.r.random() * 600, self.r.randint(7, 14)) for _ in range(80)]
        self.font = QFont("Consolas")
        self.font.setStyleHint(QFont.Monospace)
        self.font.setPixelSize(13)

    def paint(self, p, w, h, t):
        p.setFont(self.font)
        step = 19
        n = len(self.CHARS)
        for ci in range(int(w // step) + 1):
            sp, off, ln = self.cols[ci % len(self.cols)]
            head = ((t * sp + off) % (h + ln * 15)) - ln * 2
            for i in range(ln):
                y = head - i * 15
                if y < -10 or y > h + 10:
                    continue
                ch = self.CHARS[(ci * 7 + i * 3 + int(t * 7) * (1 if i else 0)) % n]
                a = 255 if i == 0 else int(190 * (1 - i / ln))
                p.setPen(QColor(255, 255, 255, a) if i == 0 else alpha("#C8CCD2", a))
                p.drawText(QPointF(ci * step, y), ch)


class Bokeh(Effect):
    """Weiss: weiche Lichtkreise und ein gleitender Lichtstreifen."""

    def __init__(self):
        super().__init__(8)
        self.b = [(self.r.random(), self.r.random(), self.r.uniform(30, 90), self.r.uniform(0.1, 0.35), self.r.uniform(0, 6.28), self.r.choice((ACCENT, CYAN, PINK))) for _ in range(14)]

    def paint(self, p, w, h, t):
        for x0, y0, r, sp, ph, col in self.b:
            cx = (x0 * w + 40 * math.sin(t * sp + ph)) % w
            cy = y0 * h + 18 * math.cos(t * sp * 1.2 + ph)
            glow(p, cx, cy, r, col, 54)
        sx = (t * 0.16 % 1.6 - 0.3) * w
        g = QLinearGradient(sx - 90, 0, sx + 90, h)
        g.setColorAt(0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(255, 255, 255, 120))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(sx - 90, 0, 180, h), g)


EFFECTS = {"Lila": Nebula, "Blau": Waves, "Grün": Virus, "Rot": Embers, "Orange": Synthwave, "Pink": Petals, "Schwarz": Matrix, "Weiß": Bokeh}
EFFECT_NAMES = {"Lila": "Nebel", "Blau": "Wellen", "Grün": "Viren", "Rot": "Glut", "Orange": "Synthwave", "Pink": "Blüten", "Schwarz": "Matrix", "Weiß": "Bokeh"}


_BANNERS: "weakref.WeakSet" = weakref.WeakSet()


def set_effects_enabled(on: bool) -> None:
    theme.set_flag("effects", bool(on))
    for b in list(_BANNERS):
        b.set_animated(bool(on))


class FxBanner(Card):
    """Hero-Karte mit dem animierten Effekt des gewaehlten Designs (nur aktiv, solange sichtbar)."""

    def __init__(self, strength: float = 1.0):
        super().__init__("hero")
        self.strength = strength
        _BANNERS.add(self)
        self.effect = EFFECTS.get(theme.CURRENT, Nebula)()
        self.t0 = time.time()
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self.update)

    def showEvent(self, e):
        if theme.get_flag("effects", True):
            self.timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)

    def set_animated(self, on: bool):
        if on and self.isVisible():
            self.timer.start()
        elif not on:
            self.timer.stop()
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        if not theme.get_flag("effects", True):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), self.radius, self.radius)
        p.setClipPath(clip)
        p.setOpacity(self.strength)
        w, h = self.width(), self.height()
        self.effect.paint(p, w, h, time.time() - self.t0)
        # linke Seite abdunkeln, damit Texte lesbar bleiben
        p.setOpacity(1.0)
        g = QLinearGradient(0, 0, w * 0.78, 0)
        g.setColorAt(0, alpha(self.base, 235))
        g.setColorAt(0.55, alpha(self.base, 175))
        g.setColorAt(1, alpha(self.base, 0))
        p.fillRect(self.rect(), g)
