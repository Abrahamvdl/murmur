"""Text injection module with 3-tier fallback system."""

import logging
import subprocess
import time
from enum import Enum
from typing import Optional

import pyperclip


logger = logging.getLogger(__name__)


class InsertionMethod(Enum):
    """Text insertion methods."""

    DIRECT = "direct"  # Direct keyboard injection via ydotool
    AUTO_PASTE = "auto_paste"  # Simulate Ctrl+V keypress
    CLIPBOARD = "clipboard"  # Copy to clipboard only


class TextInjector:
    """Handles text insertion with multiple fallback methods."""

    def __init__(self, preferred_method: str = "auto"):
        """Initialize text injector.

        Args:
            preferred_method: Preferred insertion method ('auto', 'direct', 'auto_paste', 'clipboard')
        """
        self.preferred_method = preferred_method
        self._ydotool_available = self._check_ydotool()
        self._last_method_used = None

    def _check_ydotool(self) -> bool:
        """Check if ydotool is available."""
        try:
            result = subprocess.run(
                ["which", "ydotool"],
                capture_output=True,
                timeout=1
            )
            available = result.returncode == 0

            if available:
                logger.info("ydotool is available for text insertion")
            else:
                logger.warning("ydotool not found. Install with: sudo pacman -S ydotool")

            return available

        except Exception as e:
            logger.error(f"Error checking for ydotool: {e}")
            return False

    def insert_text(self, text: str) -> InsertionMethod:
        """Insert text using the best available method.

        Args:
            text: Text to insert

        Returns:
            The method that was successfully used

        Raises:
            Exception: If all methods fail
        """
        if not text:
            logger.warning("Attempted to insert empty text")
            return InsertionMethod.CLIPBOARD

        # Try methods in order based on preference
        if self.preferred_method == "auto":
            # AUTO_PASTE is much faster than DIRECT (Ctrl+V vs typing each character)
            methods = [
                InsertionMethod.AUTO_PASTE,
                InsertionMethod.DIRECT,
                InsertionMethod.CLIPBOARD
            ]
        elif self.preferred_method == "direct":
            methods = [InsertionMethod.DIRECT, InsertionMethod.AUTO_PASTE, InsertionMethod.CLIPBOARD]
        elif self.preferred_method == "auto_paste":
            methods = [InsertionMethod.AUTO_PASTE, InsertionMethod.CLIPBOARD]
        else:  # clipboard
            methods = [InsertionMethod.CLIPBOARD]

        last_error = None

        for method in methods:
            try:
                if method == InsertionMethod.DIRECT:
                    if self._insert_direct(text):
                        self._last_method_used = method
                        logger.info("Text inserted using direct injection")
                        return method

                elif method == InsertionMethod.AUTO_PASTE:
                    if self._insert_auto_paste(text):
                        self._last_method_used = method
                        logger.info("Text inserted using auto-paste")
                        return method

                elif method == InsertionMethod.CLIPBOARD:
                    if self._insert_clipboard(text):
                        self._last_method_used = method
                        logger.info("Text copied to clipboard")
                        return method

            except Exception as e:
                logger.warning(f"Method {method.value} failed: {e}")
                last_error = e
                continue

        # If we got here, all methods failed
        error_msg = f"All text insertion methods failed. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def _insert_direct(self, text: str) -> bool:
        """Insert text using direct keyboard injection.

        Args:
            text: Text to insert

        Returns:
            True if successful
        """
        if not self._ydotool_available:
            return False

        try:
            # First copy to clipboard as backup
            pyperclip.copy(text)

            # Use ydotool to type the text
            # Note: ydotool type is slower but more reliable than key sequences
            subprocess.run(
                ["ydotool", "type", text],
                check=True,
                timeout=5,
                capture_output=True
            )

            return True

        except subprocess.TimeoutExpired:
            logger.error("ydotool type command timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"ydotool command failed: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Direct injection failed: {e}")
            return False

    def _insert_auto_paste(self, text: str) -> bool:
        """Insert text by copying to clipboard and simulating Ctrl+V.

        Args:
            text: Text to insert

        Returns:
            True if successful
        """
        if not self._ydotool_available:
            return False

        try:
            # Copy to clipboard
            pyperclip.copy(text)
            time.sleep(0.05)  # Small delay to ensure clipboard is set

            # Simulate Ctrl+V
            # Key codes: 29 = Left Ctrl, 47 = V
            subprocess.run(
                ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                check=True,
                timeout=2,
                capture_output=True
            )

            return True

        except subprocess.TimeoutExpired:
            logger.error("ydotool key command timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"ydotool key command failed: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Auto-paste failed: {e}")
            return False

    def _insert_clipboard(self, text: str) -> bool:
        """Insert text by copying to clipboard only.

        Args:
            text: Text to insert

        Returns:
            True if successful
        """
        try:
            pyperclip.copy(text)
            logger.info("Text copied to clipboard. Press Ctrl+V to paste.")
            return True

        except Exception as e:
            logger.error(f"Clipboard copy failed: {e}")
            return False

    def get_last_method(self) -> Optional[InsertionMethod]:
        """Get the last method that was successfully used."""
        return self._last_method_used

    def get_status(self) -> dict:
        """Get status of available text insertion methods."""
        return {
            "ydotool_available": self._ydotool_available,
            "preferred_method": self.preferred_method,
            "last_method_used": self._last_method_used.value if self._last_method_used else None,
            "available_methods": [
                method.value for method in [
                    InsertionMethod.DIRECT,
                    InsertionMethod.AUTO_PASTE,
                    InsertionMethod.CLIPBOARD
                ] if method == InsertionMethod.CLIPBOARD or self._ydotool_available
            ]
        }
