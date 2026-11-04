"""SquallowTweaks - Seiten Teil 1: Gemeinsames, Dashboard, Tweaks, Fortnite, Benchmark."""
from __future__ import annotations

import time
import webbrowser

import psutil
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QVBoxLayout, QWidget)

import catalog
import engine as eng
import fnmon
import netlab
import service as svc
from effects import FxBanner
from ui_common import (ACCENT, ACCENT2, CYAN, DIM, GREEN, MUTED, PINK, RED, TEXT, YELLOW, AnimButton, Card, Chips, ElidedLabel, LineChart,
                       OrbBanner, RingGauge, Sparkline, StatTile, Toggle, TweakRow, label)


def page_layout(widget: QWidget, title: str, subtitle: str = "") -> QVBoxLayout:
    lay = QVBoxLayout(widget)
    lay.setContentsMargins(28, 22, 28, 24)
    lay.setSpacing(14)
    head = QVBoxLayout()
    head.setSpacing(2)
    head.addWidget(label(title, "h1"))
    if subtitle:
        head.addWidget(label(subtitle, "muted"))
    lay.addLayout(head)
    return lay


class BasePage(QWidget):
    navigate = Signal(str)


# ===========================================================================
# ===========================================================================
class TweaksList(QWidget):
    """Zeilen werden einmal gebaut und nur ein-/ausgeblendet (kein Neuaufbau, kein Lag)."""

    def __init__(self, service: svc.Service, tweaks: list, with_filters: bool = True):
        super().__init__()
        self.service = service
        self.rows: dict[str, TweakRow] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.filter, self.query = "Alle", ""
        if with_filters:
            top = QHBoxLayout()
            top.setSpacing(12)
            self.search = QLineEdit()
            self.search.setPlaceholderText("Suchen …")
            self.search.setFixedWidth(220)
            self.search.textChanged.connect(self._q)
            top.addWidget(self.search)
            self.chips = Chips(["Alle", "Empfohlen", "Belegt", "FPS", "Latenz", "Netzwerk", "Aktiv"])
            self.chips.changed.connect(self._f)
            top.addWidget(self.chips, 1)
            lay.addLayout(top)
        box = QVBoxLayout()
        box.setSpacing(8)
        lay.addLayout(box)
        for t in tweaks:
            r = TweakRow(t, service.admin)
            r.toggled.connect(service.set_tweak)
            box.addWidget(r)
            self.rows[t.id] = r
        self.empty = label("Keine Tweaks für diese Auswahl.", "muted")
        self.empty.setAlignment(Qt.AlignCenter)
        box.addWidget(self.empty)
        self.empty.hide()
        service.states_changed.connect(self.sync)
        self.sync()

    def _q(self, text: str):
        self.query = text.strip().lower()
        self.sync()

    def _f(self, name: str):
        self.filter = name
        self.sync()

    def sync(self):
        shown = 0
        for tid, row in self.rows.items():
            t = row.tweak
            st = self.service.states.get(tid, (eng.STATUS_UNKNOWN, ""))
            if tid in self.service.states:
                row.set_state(*st)
            ok = True
            if self.filter == "Empfohlen":
                ok = bool(t.recommended)
            elif self.filter == "Belegt":
                ok = t.evidence == "belegt"
            elif self.filter in ("FPS", "Latenz"):
                ok = self.filter.upper() in t.tags
            elif self.filter == "Netzwerk":
                ok = catalog.N in t.categories
            elif self.filter == "Aktiv":
                ok = st[0] == eng.STATUS_ACTIVE
            if self.query and self.query not in (t.name + " " + t.description + " " + " ".join(t.tags)).lower():
                ok = False
            row.setVisible(ok)
            shown += ok
        self.empty.setVisible(shown == 0)


class TweaksPage(BasePage):
    def __init__(self, service: svc.Service):
        super().__init__()
        self.service = service
        lay = page_layout(self, "Tweaks", "Schalter umlegen, fertig. Jede Änderung wird gesichert, geprüft und lässt sich zurücknehmen.")
        hero = FxBanner(0.8)
        h = QHBoxLayout(hero)
        h.setContentsMargins(22, 18, 22, 18)
        h.setSpacing(20)
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(label("Ein Klick für alles", "h2"))
        self.msg = label("Erkennt dein System und setzt alle passenden Tweaks selbst. Punkte: grün = belegt, gelb = klein, grau = kaum belegt.", "muted", True)
        left.addWidget(self.msg)
        self.sys = label("", "h2")
        self.sys.setStyleSheet(f"color:{ACCENT2};")
        left.addWidget(self.sys)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1000)
        left.addSpacing(6)
        left.addWidget(self.bar)
        h.addLayout(left, 1)
        self.profile = Chips([v[0] for v in catalog.PROFILES.values()], "Competitive")
        h.addWidget(self.profile)
        self.btn = AnimButton("Auto Optimize", "accent")
        self.btn.clicked.connect(self.run_auto)
        h.addWidget(self.btn)
        lay.addWidget(hero)
        self.list = TweaksList(service, service.catalog)
        lay.addWidget(self.list)
        lay.addStretch(1)
        service.progress.connect(self._progress)
        service.auto_finished.connect(self._finished)

    def set_system(self, text: str):
        if self.sys.text() != text:
            self.sys.setText(text)

    def run_auto(self):
        key = next(k for k, v in catalog.PROFILES.items() if v[0] == self.profile.current)
        self.btn.setEnabled(False)
        self.bar.setValue(10)
        self.service.auto(key)

    def _progress(self, frac: float, text: str):
        self.bar.setValue(int(frac * 1000))
        self.msg.setText(text)

    def _finished(self, profile, results, skipped, cleaned):
        self.btn.setEnabled(True)
        ok = sum(1 for r in results if r[0])
        bad = [r for r in results if not r[0]]
        txt = f"{ok} Tweaks angewendet" if results else "Alles war schon optimal eingestellt"
        if bad:
            txt += f" · {len(bad)} fehlgeschlagen"
        if ok and any("Neustart" in (self.service.by_id[t].restart or "") for t in self.service.by_id if self.service.engine.has_backup(t)):
            txt += " · Neustart empfohlen"
        self.msg.setText(txt + (f" · {cleaned}" if cleaned else ""))
        if bad:
            QMessageBox.warning(self, "SquallowTweaks", "Nicht alles ließ sich anwenden:\n\n" + "\n".join(f"• {n}: {m}" for _o, n, m in bad))


# ===========================================================================
class FortnitePage(BasePage):
    INGAME = (("Rendering-Modus: Performance", "Der größte FPS- und Latenz-Hebel. Alternativ DirectX 11 (stabiler als DX12)."),
              ("NVIDIA Reflex: An + Boost", "Senkt die System-Latenz. Bei AMD: Radeon Anti-Lag 2."),
              ("Fenstermodus: Vollbild", "Niedrigste Eingabelatenz."),
              ("Schatten aus, Rest niedrig", "Schatten kosten am meisten FPS. Sichtweite hoch lassen."),
              ("Keine Startoption -high", "Kann den Anti-Cheat stören. Die Priorität setzt SquallowTweaks selbst, falls du es willst."))

    def __init__(self, service: svc.Service):
        super().__init__()
        self.service = service
        lay = page_layout(self, "Fortnite", "Config-Tweaks für FPS und Latenz · Fortnite muss dafür beendet sein")
        hero = FxBanner(0.8)
        h = QHBoxLayout(hero)
        h.setContentsMargins(22, 18, 22, 18)
        h.setSpacing(20)
        left = QVBoxLayout()
        self.state = label("", "h2")
        self.cfg = label("", "muted", True)
        left.addWidget(self.state)
        left.addWidget(self.cfg)
        self.sys = label("", "h2")
        self.sys.setStyleSheet(f"color:{ACCENT2};")
        left.addWidget(self.sys)
        pr = QHBoxLayout()
        pr.setSpacing(10)
        self.prio = Toggle()
        self.prio.clicked.connect(lambda c: setattr(self, "prio_on", bool(c)))
        pr.addWidget(self.prio)
        pr.addWidget(label("Priorität HOCH, sobald Fortnite läuft (Standard: aus)", "muted"))
        pr.addStretch(1)
        left.addLayout(pr)
        h.addLayout(left, 1)
        self.btn = AnimButton("Fortnite optimieren", "accent")
        self.btn.clicked.connect(self.optimize)
        h.addWidget(self.btn)
        lay.addWidget(hero)
        lay.addWidget(label("Im Spiel einstellen", "h2"))
        card = Card()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(20, 14, 20, 14)
        cv.setSpacing(6)
        for t, d in self.INGAME:
            row = QHBoxLayout()
            row.addWidget(label("▸", "muted"))
            row.addWidget(label(t, "h2"))
            row.addWidget(label(d, "muted"), 1)
            cv.addLayout(row)
        cv.addWidget(label("Diese Optionen liegen nur im Spiel; SquallowTweaks setzt nichts, was es nicht sicher prüfen kann.", "dim", True))
        lay.addWidget(card)
        lay.addWidget(label("Config & Windows für Fortnite", "h2"))
        fn_tweaks = [t for t in service.catalog if catalog.F in t.categories]
        lay.addWidget(TweaksList(service, fn_tweaks, with_filters=False))
        bench = AnimButton("Messung vorher/nachher starten", "ghost")
        bench.clicked.connect(lambda: self.navigate.emit("Benchmark"))
        lay.addWidget(bench, 0, Qt.AlignLeft)
        lay.addStretch(1)
        self.prio_on = False
        self.refresh()

    def set_system(self, text: str):
        if self.sys.text() != text:
            self.sys.setText(text)

    def refresh(self):
        ini = eng.fortnite_ini_path()
        self.cfg.setText("Config gefunden." if ini.exists() else "Keine GameUserSettings.ini gefunden. Starte Fortnite einmal bis ins Menü und beende es wieder.")
        self.state.setText("Fortnite läuft" if self.service.fortnite_running else "Fortnite ist beendet")
        self.state.setStyleSheet(f"color:{GREEN if self.service.fortnite_running else TEXT};")

    def optimize(self):
        if not eng.fortnite_ini_path().exists():
            QMessageBox.information(self, "SquallowTweaks", "Keine GameUserSettings.ini gefunden. Starte Fortnite einmal bis ins Menü, beende es und klicke dann erneut.")
            return
        if self.service.fortnite_running:
            if QMessageBox.question(self, "SquallowTweaks", "Fortnite läuft und muss beendet werden, sonst überschreibt es die Config.\n\nJetzt beenden und optimieren?") != QMessageBox.Yes:
                return
            for p in psutil.process_iter(["name"]):
                try:
                    if (p.info.get("name") or "").lower() == svc.FORTNITE_EXE:
                        p.terminate()
                except Exception:  # noqa: BLE001
                    pass
            self.service.fortnite_running = False
        self.btn.setEnabled(False)
        self.service.auto_finished.connect(self._done)
        self.service.auto("competitive", only_fortnite=True)

    def _done(self, *_a):
        try:
            self.service.auto_finished.disconnect(self._done)
        except (RuntimeError, TypeError):
            pass
        self.btn.setEnabled(True)
        self.cfg.setText("Fertig. Starte Fortnite jetzt normal.")


# ===========================================================================
class BenchmarkPage(BasePage):
    def __init__(self, service: svc.Service):
        super().__init__()
        self.service = service
        lay = page_layout(self, "Benchmark", "Miss, ob die Tweaks bei dir wirklich etwas bringen: Messung vorher, Tweaks umlegen, Messung nachher")
        card = Card()
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(label("Fortnite-Messung (PresentMon)", "h2"))
        top.addStretch(1)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Name, z. B. Vorher")
        self.name.setFixedWidth(180)
        top.addWidget(self.name)
        self.dur = Chips(["30 s", "60 s"], "30 s")
        top.addWidget(self.dur)
        self.btn = AnimButton("Messung starten", "accent")
        self.btn.clicked.connect(self.measure)
        top.addWidget(self.btn)
        v.addLayout(top)
        self.msg = label("Starte ein Match oder den Übungsmodus, bleib im Spiel und klicke auf Messung starten.", "muted", True)
        v.addWidget(self.msg)
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.t = {k: StatTile(n, c) for k, n, c in (("avg", "Ø FPS", TEXT), ("low1", "1% Low", CYAN), ("low01", "0,1% Low", PINK), ("stut", "Ruckler", YELLOW))}
        for x in self.t.values():
            tiles.addWidget(x)
        v.addLayout(tiles)
        self.chart = LineChart(None, " ms", 200, show_legend=False)
        self.chart.add_series("Frametime", ACCENT2)
        self.chart.setMinimumHeight(150)
        v.addWidget(label("Frametime-Verlauf (niedriger und gleichmäßiger ist besser)", "dim"))
        v.addWidget(self.chart)
        lay.addWidget(card)
        hist = Card()
        hv = QVBoxLayout(hist)
        hv.setContentsMargins(20, 16, 20, 16)
        hv.setSpacing(6)
        head = QHBoxLayout()
        head.addWidget(label("Verlauf", "h2"))
        head.addStretch(1)
        clr = AnimButton("Leeren", "ghost")
        clr.clicked.connect(self.clear_history)
        head.addWidget(clr)
        hv.addLayout(head)
        self.hist_box = QVBoxLayout()
        self.hist_box.setSpacing(4)
        hv.addLayout(self.hist_box)
        lay.addWidget(hist)
        net = Card()
        nv = QVBoxLayout(net)
        nv.setContentsMargins(20, 16, 20, 16)
        nv.setSpacing(10)
        nt = QHBoxLayout()
        nt.addWidget(label("Ping-Test (20 Messungen)", "h2"))
        nt.addStretch(1)
        self.pbtn = AnimButton("Ping testen", "ghost")
        self.pbtn.clicked.connect(self.ping_test)
        nt.addWidget(self.pbtn)
        nv.addLayout(nt)
        pt = QHBoxLayout()
        pt.setSpacing(12)
        self.p = {k: StatTile(n, c) for k, n, c in (("avg", "Ø Ping", TEXT), ("jit", "Jitter", CYAN), ("loss", "Verlust", YELLOW), ("dns", "DNS", PINK))}
        for x in self.p.values():
            pt.addWidget(x)
        nv.addLayout(pt)
        lay.addWidget(net)
        lay.addStretch(1)
        self.render_history()

    # ---- PresentMon
    def measure(self):
        exe = fnmon.find_presentmon()
        if not exe:
            if QMessageBox.question(self, "SquallowTweaks", "PresentMon.exe wurde nicht gefunden (Intel, kostenlos).\n\nLege die Datei neben SquallowTweaks.exe. Download-Seite öffnen?") == QMessageBox.Yes:
                webbrowser.open("https://github.com/GameTechDev/PresentMon/releases")
            return
        if not self.service.fortnite_running:
            QMessageBox.information(self, "SquallowTweaks", "Fortnite läuft nicht. Starte ein Match oder den Übungsmodus.")
            return
        secs = 60 if self.dur.current == "60 s" else 30
        self.btn.setEnabled(False)
        self.msg.setText(f"Messung läuft {secs} s … bleib im Spiel.")
        out = svc.APP_DIR / "capture.csv"

        def work():
            ok, err = fnmon.run_capture(exe, out, secs)
            if not ok:
                return err
            frames = fnmon.parse_presentmon_csv(out)
            return frames, fnmon.compute_frame_stats(frames)

        def done(res):
            self.btn.setEnabled(True)
            if isinstance(res, (str, Exception)) or res is None or res[1] is None:
                self.msg.setText("Messung fehlgeschlagen oder zu wenige Frames (Fortnite im Vordergrund? Administratorrechte?).")
                return
            frames, st = res
            step = max(1, len(frames) // 200)
            self.chart.set_data("Frametime", [sum(frames[i:i + step]) / len(frames[i:i + step]) for i in range(0, len(frames), step)])
            self.t["avg"].set(f"{st.avg_fps:.0f}", "")
            self.t["low1"].set(f"{st.low1_fps:.0f}", "")
            self.t["low01"].set(f"{st.low01_fps:.0f}", "")
            self.t["stut"].set(str(st.stutters), f"p99 {st.p99_ms:.1f} ms")
            self.msg.setText(f"{st.frames} Frames in {st.duration_s:.0f} s gemessen.")
            svc.save_benchmark({"t": time.strftime("%d.%m. %H:%M"), "name": self.name.text().strip() or "Messung", "avg": st.avg_fps, "low1": st.low1_fps,
                                "low01": st.low01_fps, "stut": st.stutters, "tweaks": self.service.active_count()})
            self.render_history()
        svc.run_async(work, done)

    def render_history(self):
        while self.hist_box.count():
            w = self.hist_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        runs = svc.load_benchmarks()
        if not runs:
            self.hist_box.addWidget(label("Noch keine Messungen.", "muted"))
            return
        prev = None
        rows = []
        for r in runs:
            d = ""
            if prev and prev.get("avg"):
                d = f"  ({(r['avg'] / prev['avg'] - 1) * 100:+.0f}% Ø · {(r['low1'] / max(prev['low1'], 0.1) - 1) * 100:+.0f}% 1% Low)"
            rows.append(f"{r['t']}  ·  {r['name']}  ·  Ø {r['avg']:.0f} FPS  ·  1% Low {r['low1']:.0f}  ·  0,1% Low {r['low01']:.0f}  ·  {r['stut']} Ruckler  ·  {r['tweaks']} Tweaks aktiv{d}")
            prev = r
        for text in reversed(rows[-8:]):
            self.hist_box.addWidget(label(text, "muted"))

    def clear_history(self):
        try:
            svc.BENCH_FILE.unlink()
        except OSError:
            pass
        self.render_history()

    # ---- Ping
    def ping_test(self):
        self.pbtn.setEnabled(False)

        def work():
            res = netlab.ping_series("1.1.1.1", 20, 0.4, 900)
            dns, _ = netlab.dns_lookup_ms("www.epicgames.com")
            return res, dns

        def done(r):
            self.pbtn.setEnabled(True)
            if isinstance(r, Exception):
                return
            res, dns = r
            self.p["avg"].set(f"{res.avg:.0f} ms" if res.avg is not None else "–", f"min {res.min:.0f} · max {res.max:.0f}" if res.avg is not None else "keine Antwort")
            self.p["jit"].set(f"{res.jitter:.1f} ms" if res.jitter is not None else "–", "mittlere Schwankung")
            self.p["loss"].set(f"{res.loss_pct:.0f}%" if res.loss_pct is not None else "–", f"{res.received} von {res.sent}")
            self.p["dns"].set(f"{dns:.0f} ms" if dns is not None else "–", "epicgames.com")
        svc.run_async(work, done)
