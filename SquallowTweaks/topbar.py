"""SquallowTweaks - Top-Leiste: Suche, Discord, Tweaks-Zaehler, Einstellungen, Auto Optimize."""
from __future__ import annotations

import webbrowser

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

import service as svc
from ui_common import ACCENT2, DIM, AnimButton, HoverFrame, IconButton, IconWidget, label, pill


class SearchBox(HoverFrame):
    submitted = Signal(str)

    def __init__(self):
        super().__init__(12)
        self.setFixedHeight(42)
        self.setMinimumWidth(320)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 0, 10, 0)
        h.setSpacing(10)
        h.addWidget(IconWidget("search", 18, DIM))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Tweaks und Einstellungen suchen …")
        self.edit.setStyleSheet("QLineEdit { border: none; background: transparent; padding: 0; }")
        self.edit.installEventFilter(self)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(260)
        self._debounce.timeout.connect(lambda: self.submitted.emit(self.edit.text().strip()))
        self.edit.textChanged.connect(lambda _t: self._debounce.start())
        h.addWidget(self.edit, 1)
        h.addWidget(pill("STRG K", DIM))

    def eventFilter(self, obj, ev):
        if obj is self.edit:
            if ev.type() == QEvent.FocusIn:
                self.hv.to(1)
            elif ev.type() == QEvent.FocusOut:
                self.hv.to(0)
        return False

    def focus_search(self):
        self.edit.setFocus()
        self.edit.selectAll()


class CountPill(HoverFrame):
    clicked = Signal()

    def __init__(self):
        super().__init__(12)
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 0, 16, 0)
        h.setSpacing(8)
        h.addWidget(IconWidget("bolt", 16, ACCENT2))
        self.text = QLabel("0 Tweaks aktiv")
        self.text.setStyleSheet("font-weight:700;")
        self.text.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        h.addWidget(self.text)
        self.setToolTip("So viele Tweaks sind gerade aktiv. Klick zeigt sie.")

    def set_count(self, n: int, total: int):
        t = f"{n} Tweaks aktiv"
        if self.text.text() != t:
            self.text.setText(t)
            self.setToolTip(f"{n} von {total} Tweaks sind aktiv. Klick zeigt sie.")

    def mouseReleaseEvent(self, e):
        self.clicked.emit()
        super().mouseReleaseEvent(e)


class TopBar(QWidget):
    search = Signal(str)
    navigate = Signal(str)
    auto = Signal()

    def __init__(self):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(28, 14, 28, 10)
        h.setSpacing(10)
        self.box = SearchBox()
        self.box.submitted.connect(self.search)
        h.addWidget(self.box)
        h.addStretch(1)
        d = IconButton("chat", "Discord beitreten", tint="#5865F2")
        d.clicked.connect(lambda: webbrowser.open(svc.DISCORD_URL))
        h.addWidget(d)
        self.count = CountPill()
        self.count.clicked.connect(lambda: self.navigate.emit("Tweaks:Aktiv"))
        h.addWidget(self.count)
        g = IconButton("gear", "Einstellungen")
        g.clicked.connect(lambda: self.navigate.emit("Einstellungen"))
        h.addWidget(g)
        a = AnimButton("Auto Optimize", "accent")
        a.clicked.connect(self.auto)
        h.addWidget(a)
