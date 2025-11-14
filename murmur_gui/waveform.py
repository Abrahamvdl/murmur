"""Waveform visualization widget."""

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from PyQt6.QtWidgets import QWidget


class WaveformWidget(QWidget):
    """Real-time audio waveform visualization."""

    def __init__(self, parent=None, sample_count: int = 100):
        """Initialize waveform widget.

        Args:
            parent: Parent widget
            sample_count: Number of waveform bars to display
        """
        super().__init__(parent)

        self.sample_count = sample_count
        self.samples = [0.0] * sample_count
        self.peak_hold = [0.0] * sample_count
        self.peak_decay = 0.95

        # Colors
        self.bg_color = QColor(24, 24, 37)  # Dark background
        self.wave_color = QColor(137, 180, 250)  # Blue
        self.peak_color = QColor(243, 139, 168)  # Pink

        # Animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._decay_peaks)
        self.timer.start(50)  # 20 FPS

        # Set size
        self.setMinimumHeight(80)
        self.setObjectName("waveformWidget")

    def update_data(self, audio_data: np.ndarray):
        """Update waveform with new audio data.

        Args:
            audio_data: Audio samples (float32)
        """
        if len(audio_data) == 0:
            return

        # Downsample audio to match sample count
        window_size = max(len(audio_data) // self.sample_count, 1)

        new_samples = []
        for i in range(self.sample_count):
            start = i * window_size
            end = min(start + window_size, len(audio_data))

            if start < len(audio_data):
                window = audio_data[start:end]
                # Calculate RMS for this window
                rms = float(np.sqrt(np.mean(window**2)))
                new_samples.append(min(rms * 3.0, 1.0))  # Amplify and clamp
            else:
                new_samples.append(0.0)

        # Update samples
        self.samples = new_samples

        # Update peak hold
        for i, sample in enumerate(self.samples):
            if sample > self.peak_hold[i]:
                self.peak_hold[i] = sample

        # Trigger repaint
        self.update()

    def _decay_peaks(self):
        """Decay peak hold values over time."""
        self.peak_hold = [p * self.peak_decay for p in self.peak_hold]
        self.update()

    def set_theme(self, theme: str):
        """Set color theme.

        Args:
            theme: 'dark' or 'light'
        """
        if theme == "light":
            self.bg_color = QColor(255, 255, 255)
            self.wave_color = QColor(30, 102, 245)
            self.peak_color = QColor(210, 15, 57)
        else:
            self.bg_color = QColor(24, 24, 37)
            self.wave_color = QColor(137, 180, 250)
            self.peak_color = QColor(243, 139, 168)

    def paintEvent(self, event):
        """Paint the waveform."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), self.bg_color)

        if not self.samples:
            return

        # Calculate bar width
        width = self.width()
        height = self.height()
        bar_width = width / self.sample_count
        max_bar_height = height * 0.8
        center_y = height / 2

        # Draw waveform bars
        for i, amplitude in enumerate(self.samples):
            x = i * bar_width
            bar_height = amplitude * max_bar_height

            # Draw main bar (symmetric around center)
            path = QPainterPath()
            path.addRoundedRect(
                x + bar_width * 0.2,
                center_y - bar_height / 2,
                bar_width * 0.6,
                bar_height,
                2,
                2,
            )

            painter.fillPath(path, self.wave_color)

            # Draw peak indicator
            if self.peak_hold[i] > 0.1:
                peak_height = self.peak_hold[i] * max_bar_height
                peak_y = center_y - peak_height / 2

                painter.setPen(QPen(self.peak_color, 2))
                painter.drawLine(
                    int(x + bar_width * 0.2),
                    int(peak_y),
                    int(x + bar_width * 0.8),
                    int(peak_y),
                )

        painter.end()

    def reset(self):
        """Reset waveform to zero."""
        self.samples = [0.0] * self.sample_count
        self.peak_hold = [0.0] * self.sample_count
        self.update()
