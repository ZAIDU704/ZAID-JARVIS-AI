"""
main_window.py
JARVIS AI's main PySide6 window: futuristic dark/cyan "glass" theme with a
status/avatar area, waveform/listening animation, memory + reminder
panels, system stats (CPU/RAM/mic), and a log view.

This module is only imported when PySide6 is installed and a display is
available; main.py falls back to a console interface otherwise so the
assistant's core logic can run headless (e.g. in this dev/CI sandbox).
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from assistant import system
from ui.theme import DARK_CYAN_GLASS_QSS


class WaveformWidget(QWidget):
    """A simple animated sine-wave 'listening' indicator drawn with QPainter
    (no image assets required)."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self._phase = 0.0
        self._active = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def _tick(self) -> None:
        if self._active:
            self._phase += 0.35
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor("#00e5ff") if self._active else QColor("#245263")
        pen = QPen(color, 2)
        painter.setPen(pen)

        width = self.width()
        height = self.height()
        mid = height / 2
        amplitude = (height / 3) if self._active else 4

        points = []
        for x in range(0, width, 4):
            y = mid + amplitude * math.sin((x / 18.0) + self._phase)
            points.append((x, y))

        for i in range(len(points) - 1):
            painter.drawLine(int(points[i][0]), int(points[i][1]),
                              int(points[i + 1][0]), int(points[i + 1][1]))


class GlassPanel(QFrame):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")


class MainWindow(QMainWindow):
    """JARVIS AI's primary window."""

    command_submitted = Signal(str)

    def __init__(self, app_name: str = "JARVIS AI", owner: str = "ZAID BILAL"):
        super().__init__()
        self.setWindowTitle(f"{app_name} — by {owner}")
        self.resize(760, 560)
        self.setStyleSheet(DARK_CYAN_GLASS_QSS)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ---- Header ----
        header_panel = GlassPanel()
        header_layout = QVBoxLayout(header_panel)
        self.title_label = QLabel(app_name)
        self.title_label.setObjectName("TitleLabel")
        self.status_label = QLabel("Sleeping — say \"Wake up Jarvis\"")
        self.status_label.setObjectName("StatusLabel")
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.status_label)
        root.addWidget(header_panel)

        # ---- Waveform ----
        wave_panel = GlassPanel()
        wave_layout = QVBoxLayout(wave_panel)
        wave_layout.addWidget(QLabel("Microphone", objectName="SectionHeader"))
        self.waveform = WaveformWidget()
        wave_layout.addWidget(self.waveform)
        root.addWidget(wave_panel)

        # ---- Middle row: memory / reminders ----
        middle = QHBoxLayout()

        memory_panel = GlassPanel()
        memory_layout = QVBoxLayout(memory_panel)
        memory_layout.addWidget(QLabel("Memory", objectName="SectionHeader"))
        self.memory_list = QListWidget()
        memory_layout.addWidget(self.memory_list)
        middle.addWidget(memory_panel)

        reminders_panel = GlassPanel()
        reminders_layout = QVBoxLayout(reminders_panel)
        reminders_layout.addWidget(QLabel("Reminders", objectName="SectionHeader"))
        self.reminders_list = QListWidget()
        reminders_layout.addWidget(self.reminders_list)
        middle.addWidget(reminders_panel)

        root.addLayout(middle)

        # ---- System stats ----
        stats_panel = GlassPanel()
        stats_layout = QHBoxLayout(stats_panel)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("CPU %p%")
        self.ram_bar = QProgressBar()
        self.ram_bar.setFormat("RAM %p%")
        stats_layout.addWidget(self.cpu_bar)
        stats_layout.addWidget(self.ram_bar)
        root.addWidget(stats_panel)

        # ---- Logs ----
        log_panel = GlassPanel()
        log_layout = QVBoxLayout(log_panel)
        log_layout.addWidget(QLabel("Activity Log", objectName="SectionHeader"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        root.addWidget(log_panel, stretch=1)

        # ---- Buttons ----
        button_row = QHBoxLayout()
        self.sleep_button = QPushButton("Sleep")
        self.settings_button = QPushButton("Settings")
        button_row.addWidget(self.sleep_button)
        button_row.addWidget(self.settings_button)
        root.addLayout(button_row)

        # Poll system stats every 2 seconds.
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(2000)
        self._refresh_stats()

    # ---------------------------------------------------------------- API
    def set_listening(self, listening: bool) -> None:
        self.waveform.set_active(listening)
        self.status_label.setText(
            "Listening…" if listening else "Sleeping — say \"Wake up Jarvis\""
        )

    def append_log(self, message: str) -> None:
        self.log_view.append(message)

    def refresh_memory_list(self, items) -> None:
        self.memory_list.clear()
        self.memory_list.addItems(items)

    def refresh_reminders_list(self, items) -> None:
        self.reminders_list.clear()
        self.reminders_list.addItems(items)

    def _refresh_stats(self) -> None:
        stats = system.get_system_stats()
        self.cpu_bar.setValue(int(stats.cpu_percent))
        self.ram_bar.setValue(int(stats.ram_percent))


def run_app(app_name: str = "JARVIS AI", owner: str = "ZAID BILAL") -> None:
    """Standalone launcher, mostly useful for quickly previewing the UI."""
    app = QApplication([])
    window = MainWindow(app_name, owner)
    window.show()
    app.exec()
