"""Qt stylesheet definitions for the GUI."""

DARK_THEME = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif;
    font-size: 12pt;
}

QMainWindow {
    border: 2px solid #313244;
    border-radius: 12px;
}

QLabel {
    color: #cdd6f4;
    background-color: transparent;
}

QLabel#title {
    font-size: 14pt;
    font-weight: 600;
    color: #89b4fa;
}

QLabel#timer {
    font-size: 16pt;
    font-weight: 600;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    color: #f38ba8;
}

QTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 12px;
    font-size: 13pt;
    line-height: 1.5;
}

QTextEdit:focus {
    border: 1px solid #89b4fa;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #45475a;
    border: 1px solid #585b70;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton#closeButton {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    font-weight: 600;
}

QPushButton#closeButton:hover {
    background-color: #eba0ac;
}

QFrame#separator {
    background-color: #313244;
    max-height: 1px;
    min-height: 1px;
}

QWidget#waveformWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
}
"""

LIGHT_THEME = """
QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif;
    font-size: 12pt;
}

QMainWindow {
    border: 2px solid #ccd0da;
    border-radius: 12px;
}

QLabel {
    color: #4c4f69;
    background-color: transparent;
}

QLabel#title {
    font-size: 14pt;
    font-weight: 600;
    color: #1e66f5;
}

QLabel#timer {
    font-size: 16pt;
    font-weight: 600;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    color: #d20f39;
}

QTextEdit {
    background-color: #ffffff;
    color: #4c4f69;
    border: 1px solid #ccd0da;
    border-radius: 8px;
    padding: 12px;
    font-size: 13pt;
    line-height: 1.5;
}

QTextEdit:focus {
    border: 1px solid #1e66f5;
}

QPushButton {
    background-color: #ccd0da;
    color: #4c4f69;
    border: 1px solid #acb0be;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #bcc0cc;
    border: 1px solid #9ca0b0;
}

QPushButton:pressed {
    background-color: #acb0be;
}

QPushButton#closeButton {
    background-color: #d20f39;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#closeButton:hover {
    background-color: #e64553;
}

QFrame#separator {
    background-color: #ccd0da;
    max-height: 1px;
    min-height: 1px;
}

QWidget#waveformWidget {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    border-radius: 8px;
}
"""


def get_theme(theme_name: str = "dark") -> str:
    """Get Qt stylesheet for specified theme.

    Args:
        theme_name: Theme name ('dark' or 'light')

    Returns:
        Qt stylesheet string
    """
    if theme_name.lower() == "light":
        return LIGHT_THEME
    return DARK_THEME
