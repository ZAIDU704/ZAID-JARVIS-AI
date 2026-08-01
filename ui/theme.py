"""
theme.py
Qt stylesheet (QSS) for JARVIS AI's dark, futuristic, cyan/blue "glass"
theme. Kept in its own module so contributors can add alternate themes
without touching window logic.
"""

DARK_CYAN_GLASS_QSS = """
QWidget {
    background-color: #0b0f14;
    color: #d7f4ff;
    font-family: 'Segoe UI', 'Consolas', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0b0f14;
}

#GlassPanel {
    background-color: rgba(20, 30, 40, 180);
    border: 1px solid rgba(0, 220, 255, 60);
    border-radius: 14px;
}

QLabel#TitleLabel {
    color: #00e5ff;
    font-size: 22px;
    font-weight: 600;
    letter-spacing: 2px;
}

QLabel#StatusLabel {
    color: #6be3ff;
    font-size: 13px;
}

QLabel#SectionHeader {
    color: #00c3e3;
    font-weight: 600;
    font-size: 13px;
    padding-top: 6px;
}

QPushButton {
    background-color: rgba(0, 200, 255, 30);
    border: 1px solid rgba(0, 220, 255, 90);
    border-radius: 8px;
    padding: 6px 14px;
    color: #d7f4ff;
}

QPushButton:hover {
    background-color: rgba(0, 220, 255, 60);
}

QPushButton:pressed {
    background-color: rgba(0, 220, 255, 110);
}

QProgressBar {
    background-color: rgba(255, 255, 255, 15);
    border: 1px solid rgba(0, 220, 255, 60);
    border-radius: 6px;
    text-align: center;
    color: #d7f4ff;
}

QProgressBar::chunk {
    background-color: #00c3e3;
    border-radius: 6px;
}

QListWidget, QTextEdit {
    background-color: rgba(255, 255, 255, 10);
    border: 1px solid rgba(0, 220, 255, 40);
    border-radius: 8px;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: rgba(0, 220, 255, 90);
    border-radius: 4px;
}
"""
