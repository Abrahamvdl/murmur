"""Configuration management for Murmur daemon."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for Murmur daemon."""

    DEFAULT_CONFIG = {
        "model": {
            "size": "medium",
            "language": "en",
            "device": "cuda",
            "compute_type": "float16",
            "model_path": None,
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_duration": 2.0,
            "vad_aggressiveness": 3,
            "device_index": None,
        },
        "gui": {
            "window_width": 600,
            "window_height": 300,
            "theme": "dark",
            "font_size": 12,
            "show_waveform": True,
            "show_timer": True,
        },
        "text_insertion": {
            "method": "auto",
            "fallback_enabled": True,
        },
        "ipc": {
            "socket_path": "/tmp/murmur-daemon.sock",
        },
        "logging": {
            "level": "INFO",
            "file": "~/.local/share/murmur/murmur.log",
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to configuration file. If None, uses default locations.
        """
        self.config_path = self._find_config_path(config_path)
        self.config = self._load_config()
        self._setup_logging()

    def _find_config_path(self, config_path: Optional[str]) -> Optional[Path]:
        """Find configuration file in standard locations."""
        if config_path:
            path = Path(config_path).expanduser()
            if path.exists():
                return path
            logger.warning(f"Specified config file not found: {config_path}")

        # Check standard locations
        possible_paths = [
            Path("~/.config/murmur/config.yaml").expanduser(),
            Path("~/.murmur/config.yaml").expanduser(),
            Path("/etc/murmur/config.yaml"),
        ]

        for path in possible_paths:
            if path.exists():
                logger.info(f"Using config file: {path}")
                return path

        logger.info("No config file found, using defaults")
        return None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        config = self.DEFAULT_CONFIG.copy()

        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    user_config = yaml.safe_load(f) or {}

                # Deep merge user config with defaults
                config = self._deep_merge(config, user_config)
                logger.info(f"Loaded configuration from {self.config_path}")

            except Exception as e:
                logger.error(f"Error loading config file: {e}. Using defaults.")

        return config

    def _deep_merge(self, base: Dict, overlay: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _setup_logging(self):
        """Setup logging based on configuration."""
        log_level = self.config["logging"]["level"]
        log_file = Path(self.config["logging"]["file"]).expanduser()

        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),
            ],
        )

    def get(self, *keys, default=None) -> Any:
        """Get configuration value by key path.

        Args:
            *keys: Key path (e.g., 'model', 'size')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys, value: Any):
        """Set configuration value by key path.

        Args:
            *keys: Key path (e.g., 'model', 'size')
            value: Value to set
        """
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    def save(self, path: Optional[str] = None):
        """Save configuration to file.

        Args:
            path: Path to save to. If None, uses current config path or default.
        """
        save_path = Path(path).expanduser() if path else self.config_path

        if not save_path:
            save_path = Path("~/.config/murmur/config.yaml").expanduser()

        # Create directory if it doesn't exist
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Save configuration
        try:
            with open(save_path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
