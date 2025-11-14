"""Audio capture module with Voice Activity Detection."""

import logging
import queue
import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import webrtcvad


logger = logging.getLogger(__name__)


class AudioCapture:
    """Captures audio with Voice Activity Detection for streaming transcription."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 2.0,
        vad_aggressiveness: int = 3,
        device_index: Optional[int] = None,
    ):
        """Initialize audio capture.

        Args:
            sample_rate: Audio sample rate (Hz). Whisper requires 16000.
            channels: Number of audio channels (1 for mono).
            chunk_duration: Duration of each audio chunk in seconds.
            vad_aggressiveness: VAD aggressiveness level (0-3, 3 is most aggressive).
            device_index: Audio device index, None for default.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.device_index = device_index

        # VAD settings
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.vad_frame_duration = 30  # ms (10, 20, or 30 for webrtcvad)

        # Audio stream
        self.stream: Optional[sd.InputStream] = None
        self.recording = False

        # Buffers and queues
        self.audio_buffer = []
        self.chunk_queue = queue.Queue()
        self.waveform_queue = queue.Queue(maxsize=10)  # For visualization

        # Threading
        self.capture_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Callbacks
        self.chunk_callback: Optional[Callable] = None
        self.waveform_callback: Optional[Callable] = None

        # Statistics
        self.start_time = 0
        self.total_chunks = 0
        self.voiced_frames = 0
        self.total_frames = 0

    def set_chunk_callback(self, callback: Callable[[np.ndarray, float], None]):
        """Set callback for when audio chunks are ready.

        Args:
            callback: Function called with (audio_data, timestamp)
        """
        self.chunk_callback = callback

    def set_waveform_callback(self, callback: Callable[[np.ndarray], None]):
        """Set callback for waveform visualization data.

        Args:
            callback: Function called with audio data for visualization
        """
        self.waveform_callback = callback

    def list_devices(self) -> list:
        """List available audio input devices."""
        devices = sd.query_devices()
        input_devices = [d for d in devices if d.get('max_input_channels', 0) > 0]
        return input_devices

    def start(self):
        """Start audio capture."""
        if self.recording:
            logger.warning("Audio capture already running")
            return

        with self.lock:
            self.recording = True
            self.audio_buffer = []
            self.start_time = time.time()
            self.total_chunks = 0
            self.voiced_frames = 0
            self.total_frames = 0

        # Start audio stream
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device_index,
                callback=self._audio_callback,
                blocksize=int(self.sample_rate * self.vad_frame_duration / 1000),
            )
            self.stream.start()
            logger.info(f"Audio capture started (device: {self.device_index or 'default'})")

        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}", exc_info=True)
            self.recording = False
            raise

        # Start processing thread ONLY if chunk callback is set (streaming mode)
        # In record-then-transcribe mode, we don't need this - just capture everything!
        if self.chunk_callback:
            self.capture_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.capture_thread.start()
            logger.debug("Audio processing thread started (streaming mode)")
        else:
            logger.debug("Skipping processing thread (record-then-transcribe mode)")

    def stop(self) -> np.ndarray:
        """Stop audio capture and return remaining audio.

        Returns:
            Remaining audio data in buffer
        """
        with self.lock:
            self.recording = False

        # Stop stream
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        # Wait for processing thread
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)

        # Get remaining audio
        remaining_audio = np.array(self.audio_buffer, dtype=np.float32)

        # Log statistics
        duration = time.time() - self.start_time
        voice_ratio = self.voiced_frames / max(self.total_frames, 1)
        logger.info(
            f"Audio capture stopped. Duration: {duration:.1f}s, "
            f"Chunks: {self.total_chunks}, Voice: {voice_ratio:.1%}"
        )

        return remaining_audio

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback for audio stream. Called by sounddevice."""
        if status:
            logger.warning(f"Audio callback status: {status}")

        if not self.recording:
            return

        # Copy audio data (indata is a view, will be overwritten)
        audio_data = indata[:, 0].copy() if self.channels == 1 else indata.copy()

        # Add to buffer
        with self.lock:
            self.audio_buffer.extend(audio_data)

        # Send waveform data for visualization
        if self.waveform_callback:
            try:
                self.waveform_callback(audio_data)
            except Exception as e:
                logger.error(f"Error in waveform callback: {e}")

    def _process_audio(self):
        """Process audio buffer, apply VAD, and emit chunks."""
        chunk_samples = int(self.sample_rate * self.chunk_duration)
        frame_samples = int(self.sample_rate * self.vad_frame_duration / 1000)

        while self.recording or len(self.audio_buffer) > 0:
            with self.lock:
                if len(self.audio_buffer) < chunk_samples:
                    # Not enough audio yet
                    time.sleep(0.1)
                    continue

                # Get chunk
                chunk = self.audio_buffer[:chunk_samples]
                self.audio_buffer = self.audio_buffer[chunk_samples:]

            # Apply VAD to determine if chunk contains voice
            if self._contains_voice(chunk, frame_samples):
                # Emit chunk for transcription
                chunk_array = np.array(chunk, dtype=np.float32)

                if self.chunk_callback:
                    try:
                        timestamp = time.time() - self.start_time
                        self.chunk_callback(chunk_array, timestamp)
                        self.total_chunks += 1
                    except Exception as e:
                        logger.error(f"Error in chunk callback: {e}", exc_info=True)
            else:
                logger.debug(f"Chunk rejected by VAD (likely silence)")

    def _contains_voice(self, audio: list, frame_samples: int) -> bool:
        """Check if audio contains voice using VAD.

        Args:
            audio: Audio samples (list of floats)
            frame_samples: Number of samples per VAD frame

        Returns:
            True if voice detected
        """
        # Convert to int16 for webrtcvad
        audio_array = np.array(audio, dtype=np.float32)
        audio_int16 = (audio_array * 32767).astype(np.int16)

        # Split into frames and check each
        voiced_count = 0
        frame_count = 0

        for i in range(0, len(audio_int16) - frame_samples, frame_samples):
            frame = audio_int16[i : i + frame_samples].tobytes()

            try:
                is_speech = self.vad.is_speech(frame, self.sample_rate)
                frame_count += 1
                self.total_frames += 1

                if is_speech:
                    voiced_count += 1
                    self.voiced_frames += 1

            except Exception as e:
                logger.debug(f"VAD error on frame: {e}")
                continue

        # Require at least 15% of frames to be voiced (lower = more responsive)
        if frame_count == 0:
            return False

        voice_ratio = voiced_count / frame_count
        return voice_ratio >= 0.15  # Lower threshold for more responsive streaming (was 0.3)

    def get_status(self) -> dict:
        """Get audio capture status.

        Returns:
            Status dictionary
        """
        return {
            "recording": self.recording,
            "duration": time.time() - self.start_time if self.recording else 0,
            "chunks_processed": self.total_chunks,
            "voice_activity": self.voiced_frames / max(self.total_frames, 1),
            "buffer_size": len(self.audio_buffer),
            "sample_rate": self.sample_rate,
            "device": self.device_index or "default",
        }


class AudioLevelMonitor:
    """Simple audio level monitoring for visualization."""

    @staticmethod
    def calculate_rms(audio_data: np.ndarray) -> float:
        """Calculate RMS (Root Mean Square) audio level.

        Args:
            audio_data: Audio samples

        Returns:
            RMS value (0.0 to 1.0)
        """
        return float(np.sqrt(np.mean(audio_data**2)))

    @staticmethod
    def calculate_peak(audio_data: np.ndarray) -> float:
        """Calculate peak audio level.

        Args:
            audio_data: Audio samples

        Returns:
            Peak value (0.0 to 1.0)
        """
        return float(np.max(np.abs(audio_data)))

    @staticmethod
    def normalize_for_visualization(audio_data: np.ndarray, target_samples: int = 100) -> np.ndarray:
        """Downsample audio for waveform visualization.

        Args:
            audio_data: Raw audio samples
            target_samples: Number of samples for visualization

        Returns:
            Downsampled audio data
        """
        if len(audio_data) <= target_samples:
            return audio_data

        # Downsample by taking peak values in windows
        window_size = len(audio_data) // target_samples
        downsampled = []

        for i in range(target_samples):
            start = i * window_size
            end = start + window_size
            window = audio_data[start:end]
            downsampled.append(np.max(np.abs(window)))

        return np.array(downsampled)
