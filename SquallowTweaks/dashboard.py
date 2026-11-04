"""SquallowTweaks - Dashboard im Stil moderner Monitoring-Oberflaechen (Hero, Live-Karten, Temperatur-Monitor, Discord)."""
from __future__ import annotations

import webbrowser
from collections import deque

import psutil
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

import engine as eng
import service as svc
from effects import FxBanner
from pages_a import BasePage, page_layout
from ui_common import (ACCENT, ACCENT2, BORDER, CYAN, DEEP1, DEEP2, DIM, GREEN, MUTED, PINK, RED, TEXT, YELLOW, AnimButton, AreaChart, Card,
                       Chips, ElidedLabel, HoverFrame, IconWidget, InfoTile, StatTile, alpha, label, pill)

BLURPLE = "#5865F2"


def fmt_uptime(sec: float) -> str:
    d, rem = divmod(int(sec), 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"


def icon_box(icon: str, color: str, size: int = 42) -> HoverFrame:
    box = HoverFrame(12, DEEP2, DEEP1, DEEP1, color, hover_on=False)
    box.setFixedSize(size, size)
    lay = QVBoxLayout(box)
    m = (size - 22) // 2
    lay.setContentsMargins(m, m, m, m)
    lay.addWidget(IconWidget(icon, 22, color))
    return box


class StatCard(Card):
    """CPU / GPU / Speicher: Kopf mit Icon und LIVE-Markierung, grosse Zahl mit Veraenderung, Verlauf, drei Kennwerte."""

    def __init__(self, icon: str, title: str, tag: str, color: str, foot_labels: tuple):
        super().__init__()
        self.color = color
        self.hist: deque = deque(maxlen=60)
        self.value_now = 0.0
        self.available = True
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(icon_box(icon, color))
        col = QVBoxLayout()
        col.setSpacing(1)
        row = QHBoxLayout()
        row.setSpacing(8)
        t = label(title, "h2")
        t.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        t.setMinimumWidth(t.sizeHint().width() + 4)
        row.addWidget(t)
        row.addWidget(pill(tag, color))
        row.addStretch(1)
        col.addLayout(row)
        self.sub = ElidedLabel("", "dim")
        col.addWidget(self.sub)
        head.addLayout(col, 1)
        head.addWidget(pill("● LIVE", GREEN))
        v.addLayout(head)
        mid = QHBoxLayout()
        self.big = label("–", "big")
        self.big.setStyleSheet("font-size:38px;font-weight:800;")
        self.big.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        mid.addWidget(self.big)
        mid.addStretch(1)
        self.delta = pill("0,0%", MUTED)
        mid.addWidget(self.delta)
        v.addLayout(mid)
        self.chart = AreaChart(color)
        v.addWidget(self.chart, 1)
        foot = QHBoxLayout()
        self.foot_vals = []
        for text in foot_labels:
            c = QVBoxLayout()
            c.setSpacing(0)
            c.addWidget(label(text, "dim"))
            val = ElidedLabel("–", "h2")
            val.setStyleSheet("font-size:13px;font-weight:700;")
            val.setMinimumWidth(52)
            c.addWidget(val)
            self.foot_vals.append(val)
            foot.addLayout(c, 1)
        v.addLayout(foot)
        self.mode = "Live"

    def set_mode(self, mode: str):
        self.mode = mode
        self.chart.mode = mode
        self.chart.update()
        self._show_big()

    def _show_big(self):
        if not self.available:
            self.big.setText("N/A")
            return
        vals = list(self.hist) or [0.0]
        v = {"Live": self.value_now, "Avg": sum(vals) / len(vals), "Peak": max(vals)}[self.mode]
        self.big.setText(f"{v:.0f}%")

    def update_data(self, value, sub: str, foot: tuple):
        self.available = value is not None
        v = float(value or 0.0)
        self.value_now = v
        self.hist.append(v)
        self.chart.push(v)
        if self.sub.text() != sub:
            self.sub.setText(sub)
            self.sub.setToolTip(sub)
        for lab, text in zip(self.foot_vals, foot):
            if lab.text() != text:
                lab.setText(text)
        self._show_big()
        if len(self.hist) > 10 and self.available:
            d = v - list(self.hist)[-10]
            arrow = "↑" if d > 0.4 else ("↓" if d < -0.4 else "•")
            color = RED if d > 0.4 else (GREEN if d < -0.4 else MUTED)
            self.delta.setText(f"{arrow} {abs(d):.1f}%")
            c = QColor(color)
            self.delta.setStyleSheet(f"QLabel#pill {{ color: {color}; background: rgba({c.red()},{c.green()},{c.blue()},38); }}")


class TempCard(Card):
    def __init__(self):
        super().__init__()
        self.cpu: deque = deque(maxlen=60)
        self.gpu: deque = deque(maxlen=60)
        self.src = "CPU"
        v = QHBoxLayout(self)
        v.setContentsMargins(24, 18, 24, 18)
        v.setSpacing(24)
        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(label("AKTIVER MONITOR", "dim"))
        self.title = label("CPU-Temperatur", "h2")
        left.addWidget(self.title)
        self.big = label("–", "big")
        self.big.setStyleSheet("font-size:52px;font-weight:800;")
        left.addWidget(self.big)
        self.note = label("", "dim", True)
        left.addWidget(self.note)
        left.addStretch(1)
        v.addLayout(left, 1)
        right = QVBoxLayout()
        top = QHBoxLayout()
        top.addStretch(1)
        self.chips = Chips(["CPU", "GPU"], "CPU")
        self.chips.changed.connect(self.set_source)
        top.addWidget(self.chips)
        right.addLayout(top)
        self.chart = AreaChart(YELLOW, 60, 100.0, "°")
        self.chart.setMinimumHeight(130)
        right.addWidget(self.chart, 1)
        v.addLayout(right, 3)

    def set_source(self, name: str):
        self.src = name
        self.title.setText(f"{name}-Temperatur")
        self.chart.data.clear()
        self.chart.data.extend(self.cpu if name == "CPU" else self.gpu)
        self.chart.update()
        self.refresh_text()

    def refresh_text(self):
        data = self.cpu if self.src == "CPU" else self.gpu
        if data:
            self.big.setText(f"{data[-1]:.0f} °C")
            self.note.setText("")
        else:
            self.big.setText("N/A")
            self.note.setText("Windows liefert die CPU-Temperatur nur auf manchen Mainboards. Die GPU-Temperatur ist bei NVIDIA verfügbar." if self.src == "CPU"
                              else "Kein NVIDIA-Sensor gefunden.")

    def update_data(self, cpu_t, gpu_t):
        if cpu_t is not None:
            self.cpu.append(cpu_t)
        if gpu_t is not None:
            self.gpu.append(gpu_t)
        if (cpu_t is not None and self.src == "CPU") or (gpu_t is not None and self.src == "GPU"):
            self.chart.push(cpu_t if self.src == "CPU" else gpu_t)
        self.refresh_text()


class DiscordCard(Card):
    def __init__(self):
        super().__init__()
        self._loaded = False
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(8)
        top = QHBoxLayout()
        box = HoverFrame(12, "#3A41A8", "#4A52C8", "#5865F2", "#9AA3FF", hover_on=False)
        box.setFixedSize(46, 46)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(11, 11, 11, 11)
        bl.addWidget(IconWidget("chat", 24, "#ffffff"))
        top.addWidget(box)
        top.addStretch(1)
        self.online = pill("", GREEN)
        self.online.hide()
        top.addWidget(self.online)
        v.addLayout(top)
        v.addWidget(pill("COMMUNITY", "#9AA3FF"), 0, Qt.AlignLeft)
        h = label("SquallowTweaks Discord", "h1")
        h.setStyleSheet("font-size:21px;font-weight:800;")
        h.setWordWrap(True)
        v.addWidget(h)
        v.addWidget(label("Neue Tweaks, Presets, Hilfe und Austausch mit der Community.", "muted", True))
        box2 = Card()
        b2 = QVBoxLayout(box2)
        b2.setContentsMargins(14, 10, 14, 10)
        b2.setSpacing(4)
        for t in ("Hilfe & Support", "Tipps und Einstellungen", "Neuigkeiten zuerst"):
            b2.addWidget(label("✓  " + t, "muted"))
        v.addWidget(box2)
        v.addStretch(1)
        btn = AnimButton("Discord beitreten", "discord")
        btn.clicked.connect(lambda: webbrowser.open(svc.DISCORD_URL))
        v.addWidget(btn)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        g = QLinearGradient(r.left(), r.top(), r.right(), r.bottom())
        g.setColorAt(0, QColor("#2A2F7A"))
        g.setColorAt(1, QColor("#161A3F"))
        h = self.hv.v
        p.setPen(QPen(QColor("#5865F2" if h < 0.3 else "#9AA3FF"), 1 + h))
        p.setBrush(g)
        p.drawRoundedRect(r, 14, 14)

    def showEvent(self, e):
        super().showEvent(e)
        if not self._loaded:
            self._loaded = True
            svc.run_async(svc.fetch_discord_online, self._got)

    def _got(self, n):
        if isinstance(n, int):
            self.online.setText(f"● {n:,} online".replace(",", "."))
            self.online.show()


class DashboardPage(BasePage):
    CHECKS = (("Energieplan Höchstleistung", ("power_ultimate", "power_high"), "any"), ("CPU-Takt dauerhaft oben", ("ps_min_cpu",), "all"),
              ("Fortnite-Grafik auf Leistung", ("fn_graphics_perf",), "all"), ("Vollbild & Latenz", ("fn_fullscreen", "fso_global"), "all"),
              ("LAN-Adapter stabil", ("net_adapter_stable",), "all"), ("Game DVR aus", ("game_dvr",), "all"))

    def __init__(self, service: svc.Service):
        super().__init__()
        self.service = service
        lay = page_layout(self, "")
        lay.itemAt(0).layout().itemAt(0).widget().hide()
        lay.setSpacing(16)
        # ---- Hero
        hero = FxBanner()
        hero.setMinimumHeight(220)
        h = QHBoxLayout(hero)
        h.setContentsMargins(30, 24, 24, 24)
        h.setSpacing(24)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(pill("SQUALLOWTWEAKS", ACCENT2), 0, Qt.AlignLeft)
        self.headline = label("Willkommen bei SquallowTweaks", "h1")
        self.headline.setStyleSheet("font-size:30px;font-weight:800;")
        col.addWidget(self.headline)
        self.subline = label("Dein System wird in Echtzeit überwacht. Wende Tweaks an, optimiere für Spiele und behalte Temperaturen im Blick.", "muted", True)
        self.subline.setMaximumWidth(560)
        col.addWidget(self.subline)
        col.addSpacing(8)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        auto = AnimButton("Auto Optimize", "accent")
        auto.clicked.connect(self.auto)
        btns.addWidget(auto)
        scan = AnimButton("System-Check", "ghost")
        scan.clicked.connect(self.scan)
        btns.addWidget(scan)
        btns.addStretch(1)
        col.addLayout(btns)
        col.addStretch(1)
        h.addLayout(col, 1)
        tiles = QVBoxLayout()
        tiles.setSpacing(10)
        self.t_up = InfoTile("clock", "Laufzeit")
        self.t_score = InfoTile("pulse", "Optimierung")
        self.t_tweaks = InfoTile("wrench", "Tweaks aktiv")
        for t in (self.t_up, self.t_score, self.t_tweaks):
            t.setFixedWidth(250)
            tiles.addWidget(t)
        h.addLayout(tiles)
        lay.addWidget(hero)
        # ---- Live-Werte
        head = QHBoxLayout()
        head.addWidget(label("Live-Systemwerte", "h1"))
        head.itemAt(0).widget().setStyleSheet("font-size:20px;font-weight:700;")
        head.addStretch(1)
        self.mode = Chips(["Live", "Ø", "Spitze"], "Live")
        self.mode.changed.connect(self.set_mode)
        head.addWidget(self.mode)
        lay.addLayout(head)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.cpu = StatCard("cpu", "CPU", "CPU", ACCENT2, ("KERNE", "TAKT", "TEMP"))
        self.gpu = StatCard("gpu", "GPU", "GPU", CYAN, ("VRAM", "TREIBER", "TEMP"))
        self.ram = StatCard("ram", "Speicher", "RAM", PINK, ("BELEGT", "FREI", "GESAMT"))
        for c in (self.cpu, self.gpu, self.ram):
            c.setMinimumHeight(330)
            c.setMinimumWidth(205)
            row.addWidget(c, 1)
        row.addWidget(DiscordCard())
        row.itemAt(3).widget().setFixedWidth(268)
        lay.addLayout(row)
        self.temp = TempCard()
        lay.addWidget(self.temp)
        # ---- unten: Bereitschaft, Netzwerk, Hintergrundlast
        low = QHBoxLayout()
        low.setSpacing(16)
        ready = Card()
        rv = QVBoxLayout(ready)
        rv.setContentsMargins(20, 16, 20, 16)
        rv.setSpacing(7)
        rv.addWidget(label("Fortnite-Bereitschaft", "h2"))
        self.check_labels = []
        for text, _i, _m in self.CHECKS:
            lb = label("", "muted")
            rv.addWidget(lb)
            self.check_labels.append(lb)
        rv.addStretch(1)
        fix = AnimButton("Alles beheben", "ghost")
        fix.clicked.connect(self.auto)
        rv.addWidget(fix)
        low.addWidget(ready, 2)
        col2 = QVBoxLayout()
        col2.setSpacing(16)
        self.ping = StatTile("Ping (Cloudflare)", GREEN)
        self.net = StatTile("Netzwerk", CYAN)
        for t in (self.ping, self.net):
            col2.addWidget(t)
        low.addLayout(col2, 2)
        self.top = StatTile("Größter Hintergrund-Verbraucher", YELLOW)
        low.addWidget(self.top, 2)
        lay.addLayout(low)
        lay.addStretch(1)
        service.states_changed.connect(self.refresh_state)
        self.refresh_state()

    def set_mode(self, name: str):
        m = {"Live": "Live", "Ø": "Avg", "Spitze": "Peak"}[name]
        for c in (self.cpu, self.gpu, self.ram):
            c.set_mode(m)

    def auto(self):
        self.navigate.emit("Tweaks")
        self.service.auto("competitive")

    def scan(self):
        self.service.refresh_states()
        self.subline.setText("System-Check läuft … die Karten unten zeigen gleich den aktuellen Stand.")

    def refresh_state(self):
        sc = self.service.score()
        opened = self.service.open_recommended()
        total = len(self.service.catalog)
        self.t_score.set(f"{sc:.0f}/100" if sc is not None else "–")
        self.t_tweaks.set(f"{self.service.active_count()} aktiv")
        if sc is not None:
            self.subline.setText("Alle empfohlenen Tweaks sind aktiv. Dein PC ist startklar." if opened == 0 else
                                 f"{opened} empfohlene Tweaks sind noch offen. Ein Klick auf Auto Optimize erledigt das.")
        for lab, (text, ids, mode) in zip(self.check_labels, self.CHECKS):
            sts = [self.service.states.get(i, (eng.STATUS_UNKNOWN, ""))[0] for i in ids]
            known = [s for s in sts if s != eng.STATUS_UNKNOWN]
            if not known:
                lab.setText(f"○  {text}  ·  nicht verfügbar")
                lab.setStyleSheet(f"color:{DIM};")
                continue
            ok = any(s == eng.STATUS_ACTIVE for s in known) if mode == "any" else all(s == eng.STATUS_ACTIVE for s in known)
            lab.setText(("✔  " if ok else "○  ") + text)
            lab.setStyleSheet(f"color:{GREEN};" if ok else f"color:{MUTED};")

    def on_sample(self, d: dict):
        gpu = d.get("gpu") or {}
        gu = gpu.get("usage")
        mhz = d.get("cpu_mhz")
        ct = d.get("cpu_temp")
        self.cpu.update_data(d["cpu"], self.service.cpu, (f"{psutil.cpu_count()}", f"{mhz / 1000:.2f} GHz" if mhz else "–", f"{ct:.0f} °C" if ct is not None else "N/A"))
        vram = f"{gpu['mem_used'] / 1024:.1f}/{gpu['mem_total'] / 1024:.0f} GB" if gpu.get("mem_used") is not None and gpu.get("mem_total") else "–"
        self.gpu.update_data(gu, gpu.get("name", "Kein NVIDIA-Sensor"), (vram, gpu.get("driver") or "–", f"{gpu['temp']:.0f} °C" if gpu.get("temp") is not None else "N/A"))
        free = d["ram_total"] - d["ram_used"]
        self.ram.update_data(d["ram"], "Arbeitsspeicher", (svc.fmt_bytes(d["ram_used"]), svc.fmt_bytes(free), svc.fmt_bytes(d["ram_total"])))
        self.temp.update_data(ct, gpu.get("temp"))
        self.t_up.set(fmt_uptime(d["uptime"]))
        self.net.set(f"↓ {svc.fmt_bytes(d['down'])}/s", f"↑ {svc.fmt_bytes(d['up'])}/s")
        ping = d.get("ping")
        self.ping.set(f"{ping:.0f} ms" if ping is not None else "–", "Antwortzeit zu 1.1.1.1" if ping is not None else "keine Antwort")
        top = d.get("top")
        self.top.set(top[0][:20] if top else "–", f"{top[1]:.0f}% CPU" if top else "")
