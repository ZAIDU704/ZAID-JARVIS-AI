"""
tray.py
System tray icon and menu for JARVIS AI: show/hide the main window, toggle
sleep/wake, and exit. Kept separate from main_window.py so the tray can be
constructed independently of whether the main window is currently visible.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtGui import QAction, QIcon, QPixmap, QColor
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget


def _fallback_icon() -> QIcon:
    """Generate a simple cyan circular icon in-memory so the tray works even
    without a bundled logo.png asset."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    return QIcon(pixmap)


class JarvisTray(QSystemTrayIcon):
    def __init__(
        self,
        window: QWidget,
        on_wake: Optional[Callable[[], None]] = None,
        on_sleep: Optional[Callable[[], None]] = None,
        icon_path: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        icon = QIcon(icon_path) if icon_path else _fallback_icon()
        super().__init__(icon, parent)
        self.window = window
        self.on_wake = on_wake
        self.on_sleep = on_sleep

        self.setToolTip("JARVIS AI")
        menu = QMenu()

        show_action = QAction("Show / Hide", menu)
        show_action.triggered.connect(self._toggle_window)
        menu.addAction(show_action)

        wake_action = QAction("Wake JARVIS", menu)
        wake_action.triggered.connect(lambda: self.on_wake() if self.on_wake else None)
        menu.addAction(wake_action)

        sleep_action = QAction("Sleep", menu)
        sleep_action.triggered.connect(lambda: self.on_sleep() if self.on_sleep else None)
        menu.addAction(sleep_action)

        menu.addSeparator()

        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _toggle_window(self) -> None:
        self.window.setVisible(not self.window.isVisible())
        if self.window.isVisible():
            self.window.activateWindow()

    def _on_activated(self, reason) -> None:  # noqa: ANN001
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window()
