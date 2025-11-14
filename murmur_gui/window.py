"""Main GUI window for Murmur."""

import time
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFrame,
)

from murmur_gui.waveform import WaveformWidget
from murmur_gui.styles import get_theme


class MurmurWindow(QMainWindow):
    """Main floating window for voice input."""

    # Signals for thread-safe GUI updates
    transcription_updated = pyqtSignal(str, bool)
    waveform_updated = pyqtSignal(np.ndarray)
    stop_requested = pyqtSignal()  # Signal to request stop from daemon

    def __init__(
        self,
        width: int = 600,
        height: int = 300,
        theme: str = "dark",
        show_waveform: bool = True,
        show_timer: bool = True,
    ):
        """Initialize window.

        Args:
            width: Window width in pixels
            height: Window height in pixels
            theme: Color theme ('dark' or 'light')
            show_waveform: Whether to show waveform visualization
            show_timer: Whether to show recording timer
        """
        super().__init__()

        self.theme = theme
        self.show_waveform_enabled = show_waveform
        self.show_timer_enabled = show_timer

        # Recording state
        self.recording_start_time = 0
        self.is_recording = False

        # Setup window
        self.setWindowTitle("Murmur")
        self.setFixedSize(width, height)

        # Make window frameless and stay on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Don't show in taskbar
        )

        # Set transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Setup UI
        self._setup_ui()

        # Apply theme
        self.setStyleSheet(get_theme(theme))

        # Timer for updating elapsed time
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_timer_display)

        # Connect signals
        self.transcription_updated.connect(self._on_transcription_updated)
        self.waveform_updated.connect(self._on_waveform_updated)

        # Center window on screen
        self._center_on_screen()

    def _setup_ui(self):
        """Setup user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Timer (centered at top)
        if self.show_timer_enabled:
            timer_layout = QHBoxLayout()
            timer_layout.addStretch()
            self.timer_label = QLabel("00:00")
            self.timer_label.setObjectName("timer")
            timer_layout.addWidget(self.timer_label)
            timer_layout.addStretch()
            layout.addLayout(timer_layout)

        # Waveform (takes most space)
        if self.show_waveform_enabled:
            self.waveform = WaveformWidget(sample_count=80)
            self.waveform.set_theme(self.theme)
            layout.addWidget(self.waveform, stretch=1)

        # Stop button (centered at bottom)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Transcribe Now")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self._request_stop)
        button_layout.addWidget(close_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _center_on_screen(self):
        """Center window on the primary screen."""
        if QApplication.primaryScreen():
            screen_geometry = QApplication.primaryScreen().geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def start_recording(self):
        """Start recording session."""
        self.is_recording = True
        self.recording_start_time = time.time()

        if self.show_waveform_enabled:
            self.waveform.reset()

        # Start timer updates
        self.update_timer.start(100)  # Update every 100ms

    def stop_recording(self):
        """Stop recording session."""
        self.is_recording = False
        self.update_timer.stop()

    def update_transcription(self, text: str, is_final: bool = False):
        """Update transcription text (thread-safe).

        Args:
            text: Transcription text
            is_final: Whether this is the final transcription
        """
        self.transcription_updated.emit(text, is_final)

    def _on_transcription_updated(self, text: str, is_final: bool):
        """Handle transcription update in GUI thread.

        Args:
            text: Transcription text
            is_final: Whether this is the final transcription
        """
        # No longer showing live transcription in record-then-transcribe mode
        pass

    def update_waveform(self, audio_data: np.ndarray):
        """Update waveform visualization (thread-safe).

        Args:
            audio_data: Audio samples
        """
        if self.show_waveform_enabled:
            self.waveform_updated.emit(audio_data)

    def _on_waveform_updated(self, audio_data: np.ndarray):
        """Handle waveform update in GUI thread.

        Args:
            audio_data: Audio samples
        """
        if self.show_waveform_enabled:
            self.waveform.update_data(audio_data)

    def _update_timer_display(self):
        """Update the timer display."""
        if not self.show_timer_enabled:
            return

        if self.is_recording:
            elapsed = time.time() - self.recording_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        self.start_recording()

    def hideEvent(self, event):
        """Handle window hide event."""
        super().hideEvent(event)
        self.stop_recording()

    def closeEvent(self, event):
        """Handle window close event (e.g., Alt+F4 or window manager close).

        Args:
            event: Close event
        """
        # If recording, request stop from daemon instead of closing directly
        if self.is_recording:
            self.stop_requested.emit()
            event.ignore()  # Don't close yet, let daemon handle it
        else:
            event.accept()

    def _request_stop(self):
        """Request stop recording from daemon."""
        if self.is_recording:
            self.stop_requested.emit()


# Standalone testing
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    # Create window
    window = MurmurWindow(theme="dark")
    window.show()

    # Simulate some updates for testing
    def test_updates():
        import random

        # Simulate waveform data
        audio_data = np.random.random(1000).astype(np.float32) * 0.5
        window.update_waveform(audio_data)

        # Simulate transcription updates
        test_texts = [
            "Hello world",
            "Hello world, this is",
            "Hello world, this is a test",
            "Hello world, this is a test of the",
            "Hello world, this is a test of the voice input system",
        ]

        import threading

        def update_text():
            for text in test_texts:
                window.update_transcription(text, is_final=False)
                time.sleep(1)

        threading.Thread(target=update_text, daemon=True).start()

    # Start test updates after a short delay
    QTimer.singleShot(500, test_updates)

    sys.exit(app.exec())
