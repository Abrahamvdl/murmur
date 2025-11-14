"""Main Whisper daemon service."""

import argparse
import logging
import signal
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from murmur_daemon.audio_capture import AudioCapture
from murmur_daemon.config import Config
from murmur_daemon.ipc_server import IPCServer
from murmur_daemon.text_injector import TextInjector, InsertionMethod
from murmur_daemon.transcriber import Transcriber
from murmur_gui.window import WhisperWindow


logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Recording session states."""

    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"


class WhisperDaemon(QObject):
    """Main daemon service for Murmur."""

    # Qt signals for thread-safe GUI operations
    show_window_signal = pyqtSignal()
    hide_window_signal = pyqtSignal()
    update_transcription_signal = pyqtSignal(str, bool)
    update_waveform_signal = pyqtSignal(np.ndarray)

    def __init__(self, config_path: Optional[str] = None):
        """Initialize daemon.

        Args:
            config_path: Optional path to configuration file
        """
        # Initialize QObject first
        super().__init__()

        # Load configuration
        self.config = Config(config_path)
        logger.info("Whisper daemon initializing...")

        # Session state
        self.state = SessionState.IDLE
        self.session_start_time = 0
        self.sessions_count = 0
        self.daemon_start_time = time.time()

        # Components
        self.ipc_server: Optional[IPCServer] = None
        self.transcriber: Optional[Transcriber] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.text_injector: Optional[TextInjector] = None

        # GUI components
        self.qapp: Optional[QApplication] = None
        self.gui_window: Optional[WhisperWindow] = None

        # Shutdown flag
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()

    def initialize(self):
        """Initialize all components."""
        logger.info("Initializing components...")

        try:
            # Initialize Qt Application for GUI
            self.qapp = QApplication.instance()
            if self.qapp is None:
                self.qapp = QApplication(sys.argv)
                self.qapp.setQuitOnLastWindowClosed(False)  # Don't quit when window closes

            # Initialize GUI window
            self.gui_window = WhisperWindow(
                width=self.config.get("gui", "window_width"),
                height=self.config.get("gui", "window_height"),
                theme=self.config.get("gui", "theme"),
                show_waveform=self.config.get("gui", "show_waveform"),
                show_timer=self.config.get("gui", "show_timer"),
            )

            # Connect Qt signals for thread-safe GUI operations
            self.show_window_signal.connect(self.gui_window.show)
            self.hide_window_signal.connect(self.gui_window.hide)
            self.update_transcription_signal.connect(self.gui_window.update_transcription)
            self.update_waveform_signal.connect(self.gui_window.update_waveform)

            # Connect stop request from GUI back to daemon
            self.gui_window.stop_requested.connect(self._handle_gui_stop_request)

            logger.info("GUI window initialized")

            # Initialize transcriber
            self.transcriber = Transcriber(
                model_size=self.config.get("model", "size"),
                device=self.config.get("model", "device"),
                compute_type=self.config.get("model", "compute_type"),
                language=self.config.get("model", "language"),
                model_path=self.config.get("model", "model_path"),
            )

            # Load model
            logger.info("Loading Whisper model (this may take a moment)...")
            self.transcriber.load_model()
            self.transcriber.set_transcription_callback(self._on_transcription)

            # Initialize audio capture
            self.audio_capture = AudioCapture(
                sample_rate=self.config.get("audio", "sample_rate"),
                channels=self.config.get("audio", "channels"),
                chunk_duration=self.config.get("audio", "chunk_duration"),
                vad_aggressiveness=self.config.get("audio", "vad_aggressiveness"),
                device_index=self.config.get("audio", "device_index"),
            )
            # NO chunk callback - we'll transcribe everything at once on stop!
            # self.audio_capture.set_chunk_callback(self._on_audio_chunk)  # DISABLED for full-context mode
            self.audio_capture.set_waveform_callback(self._on_waveform_data)

            # Initialize text injector
            self.text_injector = TextInjector(
                preferred_method=self.config.get("text_insertion", "method")
            )

            # Initialize IPC server
            socket_path = self.config.get("ipc", "socket_path")
            self.ipc_server = IPCServer(socket_path=socket_path)

            # Register command handlers
            self.ipc_server.register_handler("start", self._handle_start_command)
            self.ipc_server.register_handler("stop", self._handle_stop_command)
            self.ipc_server.register_handler("status", self._handle_status_command)
            self.ipc_server.register_handler("shutdown", self._handle_shutdown_command)

            # Start IPC server
            self.ipc_server.start()

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}", exc_info=True)
            raise

    def _handle_start_command(self) -> dict:
        """Handle 'start' command from CLI."""
        try:
            if self.state != SessionState.IDLE:
                return {
                    "success": False,
                    "message": f"Cannot start: already {self.state.value}",
                }

            logger.info("Starting recording session...")

            # Reset transcriber (but don't start processing yet - only on stop)
            self.transcriber.reset_transcription()

            # Start audio capture (no chunk callback - just record)
            self.audio_capture.start()

            # Update state
            self.state = SessionState.RECORDING
            self.session_start_time = time.time()
            self.sessions_count += 1

            # Show GUI window using thread-safe signal
            if self.gui_window:
                self.show_window_signal.emit()

            logger.info("Recording session started")

            return {
                "success": True,
                "message": "Recording started",
                "session_id": f"session_{self.sessions_count}",
                "start_time": self.session_start_time,
            }

        except Exception as e:
            logger.error(f"Error starting recording: {e}", exc_info=True)
            self.state = SessionState.IDLE
            return {"success": False, "message": f"Failed to start recording: {str(e)}"}

    def _handle_stop_command(self) -> dict:
        """Handle 'stop' command from CLI."""
        try:
            if self.state != SessionState.RECORDING:
                return {
                    "success": False,
                    "message": "No recording in progress",
                }

            logger.info("Stopping recording session...")

            # Hide GUI window immediately for instant feedback
            if self.gui_window:
                self.hide_window_signal.emit()

            # Update state
            self.state = SessionState.PROCESSING

            # Stop audio capture and get ALL recorded audio
            all_audio = self.audio_capture.stop()
            logger.info(f"Captured {len(all_audio)/16000:.1f}s of audio")

            # Transcribe entire audio in ONE shot with full context (much faster & more accurate!)
            transcription = ""
            if len(all_audio) > 8000:  # At least 0.5 seconds
                logger.info("Transcribing full audio with complete context...")
                transcription = self.transcriber.transcribe_full_audio(all_audio)
            else:
                logger.warning("Audio too short to transcribe")

            # Calculate duration
            duration = time.time() - self.session_start_time

            # Insert text
            insertion_method = None
            if transcription and transcription.strip():
                try:
                    insertion_method = self.text_injector.insert_text(transcription)
                    logger.info(f"Text inserted using method: {insertion_method.value}")
                except Exception as e:
                    logger.error(f"Failed to insert text: {e}", exc_info=True)
                    insertion_method = InsertionMethod.CLIPBOARD

            # Reset state
            self.state = SessionState.IDLE

            logger.info(f"Recording session stopped (duration: {duration:.1f}s)")

            return {
                "success": True,
                "message": "Recording stopped",
                "transcription": transcription,
                "duration": duration,
                "insertion_method": insertion_method.value if insertion_method else "none",
                "word_count": len(transcription.split()) if transcription else 0,
            }

        except Exception as e:
            logger.error(f"Error stopping recording: {e}", exc_info=True)
            self.state = SessionState.IDLE
            return {"success": False, "message": f"Failed to stop recording: {str(e)}"}

    def _handle_gui_stop_request(self):
        """Handle stop request from GUI window (close button or window close).

        This is a Qt slot connected to the GUI window's stop_requested signal.
        """
        logger.info("GUI stop requested")

        # Stop the recording (this also inserts the text)
        result = self._handle_stop_command()

        # Hide the window after stopping
        if self.gui_window and result.get("success"):
            self.hide_window_signal.emit()

    def _handle_status_command(self) -> dict:
        """Handle 'status' command from CLI."""
        try:
            uptime = time.time() - self.daemon_start_time

            # Get component statuses
            transcriber_status = self.transcriber.get_status() if self.transcriber else {}
            audio_status = self.audio_capture.get_status() if self.audio_capture else {}
            injector_status = self.text_injector.get_status() if self.text_injector else {}

            return {
                "success": True,
                "daemon_running": True,
                "recording": self.state == SessionState.RECORDING,
                "state": self.state.value,
                "model_loaded": transcriber_status.get("model_loaded", False),
                "model_name": f"{transcriber_status.get('model_size', 'unknown')}.{transcriber_status.get('language', 'unknown')}",
                "uptime": uptime,
                "sessions_count": self.sessions_count,
                "audio_device": audio_status.get("device", "unknown"),
                "text_injection_available": {
                    "direct": injector_status.get("ydotool_available", False),
                    "auto_paste": injector_status.get("ydotool_available", False),
                    "clipboard": True,
                },
                "current_transcription": transcriber_status.get("current_transcription", ""),
                "memory_usage_mb": self._estimate_memory_usage(),
            }

        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            return {"success": False, "message": f"Failed to get status: {str(e)}"}

    def _handle_shutdown_command(self) -> dict:
        """Handle 'shutdown' command from CLI."""
        logger.info("Shutdown command received")

        # Stop any active recording
        if self.state == SessionState.RECORDING:
            self._handle_stop_command()

        # Schedule shutdown
        import threading

        threading.Timer(0.5, self.shutdown).start()

        return {"success": True, "message": "Daemon shutting down"}

    def _on_audio_chunk(self, audio_data: np.ndarray, timestamp: float):
        """Callback for audio chunks from audio capture.

        Args:
            audio_data: Audio samples
            timestamp: Timestamp of chunk
        """
        if self.state == SessionState.RECORDING and self.transcriber:
            # Send to transcriber
            self.transcriber.transcribe_chunk(audio_data, timestamp)

    def _on_waveform_data(self, audio_data: np.ndarray):
        """Callback for waveform visualization data.

        Args:
            audio_data: Audio samples for visualization
        """
        # Send to GUI window using thread-safe signal
        if self.gui_window:
            try:
                self.update_waveform_signal.emit(audio_data)
            except Exception as e:
                logger.error(f"Error updating waveform: {e}")

    def _on_transcription(self, text: str, is_final: bool):
        """Callback for transcription results.

        Args:
            text: Transcribed text
            is_final: Whether this is the final transcription
        """
        # Update GUI window using thread-safe signal
        if self.gui_window:
            try:
                self.update_transcription_signal.emit(text, is_final)
            except Exception as e:
                logger.error(f"Error updating transcription: {e}")

        if is_final:
            logger.info(f"Final transcription: {text[:100]}...")

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in MB.

        Returns:
            Estimated memory usage in MB
        """
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            return int(process.memory_info().rss / 1024 / 1024)
        except ImportError:
            # psutil not available, return estimate
            return 2000 if self.transcriber and self.transcriber.model_loaded else 100

    def run(self):
        """Main daemon loop."""
        logger.info("Whisper daemon started and ready")

        try:
            # Use Qt event loop instead of simple sleep loop
            # This allows the GUI to work properly
            if self.qapp:
                # Create a timer to check if we should shut down
                shutdown_timer = QTimer()
                shutdown_timer.timeout.connect(lambda: None if self.running else self.qapp.quit())
                shutdown_timer.start(1000)  # Check every second

                # Run Qt event loop
                self.qapp.exec()
            else:
                # Fallback to simple loop if no Qt
                while self.running:
                    time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)

        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown daemon gracefully."""
        if not self.running:
            return

        logger.info("Shutting down daemon...")
        self.running = False

        # Stop any active recording
        if self.state == SessionState.RECORDING:
            try:
                self.audio_capture.stop()
                self.transcriber.stop_processing()
            except Exception as e:
                logger.error(f"Error stopping recording during shutdown: {e}")

        # Shutdown components
        if self.ipc_server:
            try:
                self.ipc_server.stop()
            except Exception as e:
                logger.error(f"Error stopping IPC server: {e}")

        if self.transcriber:
            try:
                self.transcriber.unload_model()
            except Exception as e:
                logger.error(f"Error unloading model: {e}")

        # Close GUI if open
        if self.gui_window:
            try:
                self.gui_window.close()
            except Exception as e:
                logger.error(f"Error closing GUI: {e}")

        logger.info("Daemon shut down successfully")


def main():
    """Main entry point for daemon."""
    parser = argparse.ArgumentParser(
        prog="whisper-daemon",
        description="Murmur Daemon",
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
        default=None,
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override log level from config",
        default=None,
    )

    args = parser.parse_args()

    # Create daemon
    try:
        daemon = WhisperDaemon(config_path=args.config)

        # Override log level if specified
        if args.log_level:
            logging.getLogger().setLevel(args.log_level)

        # Initialize components
        daemon.initialize()

        # Run main loop
        daemon.run()

        return 0

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
        return 130

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
