"""Whisper transcription module with streaming support."""

import logging
import queue
import threading
import time
from typing import Callable, Optional

import numpy as np
from faster_whisper import WhisperModel


logger = logging.getLogger(__name__)


class Transcriber:
    """Handles Whisper model loading and transcription."""

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cuda",
        compute_type: str = "float16",
        language: str = "en",
        model_path: Optional[str] = None,
    ):
        """Initialize transcriber.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            device: Device to run model on (cuda for ROCm, cpu)
            compute_type: Precision (float16, int8, float32)
            language: Language code (en for English)
            model_path: Optional custom model path
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model_path = model_path

        self.model: Optional[WhisperModel] = None
        self.model_loaded = False

        # Processing queue and threads
        self.transcription_queue = queue.Queue()
        self.processing_thread: Optional[threading.Thread] = None
        self.running = False

        # Callbacks
        self.transcription_callback: Optional[Callable] = None

        # Transcription buffer
        self.current_transcription = []
        self.lock = threading.Lock()

        # Statistics
        self.total_audio_duration = 0
        self.total_processing_time = 0
        self.transcriptions_count = 0

    def load_model(self):
        """Load Whisper model into memory."""
        if self.model_loaded:
            logger.info("Model already loaded")
            return

        try:
            logger.info(f"Loading Whisper {self.model_size} model on {self.device}...")
            start_time = time.time()

            # Load model
            model_identifier = self.model_path if self.model_path else self.model_size

            self.model = WhisperModel(
                model_identifier,
                device=self.device,
                compute_type=self.compute_type,
            )

            load_time = time.time() - start_time
            self.model_loaded = True

            logger.info(f"Model loaded successfully in {load_time:.2f}s")

        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)

            # Try CPU fallback if GPU failed
            if self.device != "cpu":
                logger.warning("Attempting CPU fallback...")
                self.device = "cpu"
                self.compute_type = "int8"
                try:
                    self.model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                    )
                    self.model_loaded = True
                    logger.info("Model loaded successfully on CPU")
                except Exception as e2:
                    logger.error(f"CPU fallback failed: {e2}", exc_info=True)
                    raise

    def set_transcription_callback(self, callback: Callable[[str, bool], None]):
        """Set callback for transcription results.

        Args:
            callback: Function called with (text, is_final)
        """
        self.transcription_callback = callback

    def start_processing(self):
        """Start transcription processing thread."""
        if self.running:
            logger.warning("Processing already running")
            return

        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        self.running = True
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        logger.info("Transcription processing started")

    def stop_processing(self):
        """Stop transcription processing thread."""
        self.running = False

        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)

        # Clear transcription buffer to free memory
        with self.lock:
            self.current_transcription.clear()

        # Clear any remaining items in queue
        while not self.transcription_queue.empty():
            try:
                self.transcription_queue.get_nowait()
            except queue.Empty:
                break

        # Force garbage collection to free GPU memory
        import gc
        gc.collect()

        logger.info("Transcription processing stopped and memory cleared")

    def transcribe_chunk(self, audio_data: np.ndarray, timestamp: float):
        """Add audio chunk to transcription queue.

        Args:
            audio_data: Audio samples (float32)
            timestamp: Timestamp of chunk
        """
        if not self.running:
            logger.warning("Transcriber not running, ignoring chunk")
            return

        self.transcription_queue.put((audio_data, timestamp))

    def _process_queue(self):
        """Process transcription queue."""
        while self.running or not self.transcription_queue.empty():
            try:
                # Get chunk from queue
                try:
                    audio_data, timestamp = self.transcription_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Transcribe chunk
                try:
                    text = self._transcribe_audio(audio_data)

                    if text and text.strip():
                        with self.lock:
                            self.current_transcription.append(text.strip())
                            self.transcriptions_count += 1

                        # Emit partial transcription
                        if self.transcription_callback:
                            full_text = " ".join(self.current_transcription)
                            try:
                                self.transcription_callback(full_text, is_final=False)
                            except Exception as e:
                                logger.error(f"Error in transcription callback: {e}")

                        logger.debug(f"Chunk transcribed: '{text.strip()}'")
                    else:
                        logger.debug("Empty transcription for chunk")

                except Exception as e:
                    logger.error(f"Error transcribing chunk: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)

    def _transcribe_audio(self, audio_data: np.ndarray) -> str:
        """Transcribe audio chunk.

        Args:
            audio_data: Audio samples (float32, mono, 16kHz)

        Returns:
            Transcribed text
        """
        if not self.model:
            raise RuntimeError("Model not loaded")

        start_time = time.time()
        audio_duration = len(audio_data) / 16000  # Assuming 16kHz

        try:
            # Get previous transcription for context (last 224 tokens max)
            with self.lock:
                previous_text = " ".join(self.current_transcription[-3:]) if self.current_transcription else None

            # Transcribe with context from previous chunks
            segments, info = self.model.transcribe(
                audio_data,
                language=self.language,
                beam_size=1,  # Greedy decoding (fastest)
                best_of=1,  # Don't try multiple samples
                temperature=0.0,  # Greedy (no sampling randomness)
                patience=1.0,  # Early stopping
                vad_filter=False,  # We already did VAD
                without_timestamps=True,  # Faster
                condition_on_previous_text=True,  # Use context from previous chunks
                initial_prompt=previous_text,  # Provide context
                repetition_penalty=1.0,  # No penalty computation
            )

            # Collect all segments (ensure generator is fully consumed to free memory)
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            text = " ".join(text_parts).strip()

            # Explicitly delete segments generator to free GPU memory
            del segments
            del info

            # Update statistics
            processing_time = time.time() - start_time
            self.total_audio_duration += audio_duration
            self.total_processing_time += processing_time

            rtf = processing_time / audio_duration if audio_duration > 0 else 0
            logger.info(
                f"Transcribed {audio_duration:.2f}s audio in {processing_time:.2f}s (RTF: {rtf:.2f}x) - '{text[:50]}...'"
            )

            return text

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            return ""

    def get_full_transcription(self, final: bool = True) -> str:
        """Get the complete transcription.

        Args:
            final: Whether this is the final transcription

        Returns:
            Complete transcription text
        """
        with self.lock:
            text = " ".join(self.current_transcription)

        # Emit final transcription
        if final and self.transcription_callback and text:
            try:
                self.transcription_callback(text, is_final=True)
            except Exception as e:
                logger.error(f"Error in final transcription callback: {e}")

        return text

    def reset_transcription(self):
        """Clear transcription buffer."""
        with self.lock:
            self.current_transcription = []

    def transcribe_full_audio(self, audio_data: np.ndarray) -> str:
        """Transcribe entire audio recording in one shot with full context.

        This is MUCH faster and more accurate than chunked transcription.

        Args:
            audio_data: Complete audio recording (float32, mono, 16kHz)

        Returns:
            Full transcription text
        """
        if not self.model:
            raise RuntimeError("Model not loaded")

        start_time = time.time()
        audio_duration = len(audio_data) / 16000

        try:
            logger.info(f"Transcribing {audio_duration:.1f}s of audio in one shot...")

            # Transcribe entire audio with full context (optimal for Whisper!)
            segments, info = self.model.transcribe(
                audio_data,
                language=self.language,
                beam_size=1,  # Greedy decoding (fastest)
                best_of=1,
                temperature=0.0,
                vad_filter=False,  # We already did VAD
                without_timestamps=True,
                condition_on_previous_text=True,  # Full context within audio
            )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            text = " ".join(text_parts).strip()

            # Clean up
            del segments
            del info

            # Stats
            processing_time = time.time() - start_time
            rtf = processing_time / audio_duration if audio_duration > 0 else 0

            logger.info(
                f"Full transcription complete: {audio_duration:.1f}s audio → {processing_time:.1f}s processing (RTF: {rtf:.2f}x)"
            )
            logger.info(f"Result: '{text[:100]}{'...' if len(text) > 100 else ''}'")

            return text

        except Exception as e:
            logger.error(f"Full audio transcription error: {e}", exc_info=True)
            return ""

    def get_status(self) -> dict:
        """Get transcriber status.

        Returns:
            Status dictionary
        """
        avg_rtf = 0
        if self.total_audio_duration > 0:
            avg_rtf = self.total_processing_time / self.total_audio_duration

        with self.lock:
            current_text = " ".join(self.current_transcription)

        return {
            "model_loaded": self.model_loaded,
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "language": self.language,
            "running": self.running,
            "transcriptions_count": self.transcriptions_count,
            "queue_size": self.transcription_queue.qsize(),
            "average_rtf": avg_rtf,
            "current_transcription": current_text,
            "total_audio_duration": self.total_audio_duration,
            "total_processing_time": self.total_processing_time,
        }

    def unload_model(self):
        """Unload model from memory."""
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_processing()

        if self.model:
            del self.model
            self.model = None
            self.model_loaded = False
            logger.info("Model unloaded")
