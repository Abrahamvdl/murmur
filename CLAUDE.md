# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Murmur is a real-time voice-to-text transcription system for Linux Wayland that uses OpenAI's Whisper model with AMD GPU (ROCm) acceleration. It provides system-wide voice input through keyboard shortcuts via a daemon-based architecture.

**Repository**: https://github.com/Abrahamvdl/murmur

## Core Architecture

### Multi-Process Design

The system uses a **daemon-based architecture** with three key processes:

1. **CLI Tool** (`whi`) - User-facing command interface
2. **Background Daemon** (`murmur-daemon`) - Persistent service managing transcription
3. **GUI Window** (PyQt6) - Floating overlay showing real-time feedback

**Critical**: These processes communicate via Unix domain socket IPC at `/tmp/murmur-daemon.sock`. The daemon keeps the Whisper model loaded in memory to avoid startup latency (~2GB idle, ~3GB during transcription).

### Module Structure

```
murmur_daemon/          # Core daemon service
├── daemon.py            # Main daemon orchestration & Qt event loop
├── transcriber.py       # Whisper model management (faster-whisper)
├── audio_capture.py     # Audio capture + VAD (sounddevice + webrtcvad)
├── ipc_server.py        # Unix socket server for CLI communication
├── text_injector.py     # 3-tier text insertion system
└── config.py            # YAML configuration management

murmur_gui/             # PyQt6 GUI overlay
├── window.py            # Main Qt window with layer-shell
├── waveform.py          # Real-time audio visualization
└── styles.py            # Qt stylesheets

murmur_cli/             # Command-line interface
└── cli.py               # CLI commands (start/stop/status)
```

## Critical Implementation Details

### Threading Model

**The daemon uses multiple threads that MUST be synchronized properly:**

1. **Main Thread** - Qt event loop (QApplication.exec())
2. **IPC Server Thread** - Handles CLI commands via Unix socket
3. **Audio Capture Thread** - Continuous audio capture with VAD
4. **Transcription Thread** - Whisper model inference

**Thread Safety**:
- Use Qt signals/slots for GUI updates from other threads
- Use thread-safe queues for audio chunks
- Lock access to shared state (recording status, transcription buffer)

### Text Insertion 3-Tier System

The `TextInjector` implements a fallback system (critical to user experience):

1. **Direct Injection** - `ydotool type` character-by-character (primary)
2. **Auto-Paste** - Clipboard + `ydotool key Ctrl+v` (secondary)
3. **Clipboard Only** - `pyperclip` copy only (tertiary fallback)

**Important**: Always try methods in order and log which succeeded. Users rely on this fallback for reliability.

### Real-Time Transcription Pipeline

```
Microphone → sounddevice (16kHz mono)
           → webrtcvad filter
           → Audio chunks (2s default)
           → faster-whisper (ROCm GPU)
           → Partial transcriptions
           → GUI update (Qt signal)
           → Final text insertion
```

**Latency targets**: <100ms CLI response, <1s chunk processing, <3s total speech-to-text

## Development Commands

### Running in Development

```bash
# Setup (from project root)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/
pip install -e ".[dev]"

# Run daemon in foreground with debug logging
python -m murmur_daemon.daemon --log-level DEBUG

# Test CLI (in separate terminal)
source venv/bin/activate
python -m murmur_cli.cli start
python -m murmur_cli.cli stop
python -m murmur_cli.cli status

# Format code
black murmur_daemon/ murmur_gui/ murmur_cli/

# Lint
flake8 murmur_daemon/ murmur_gui/ murmur_cli/
```

### Systemd Service Management

```bash
# Install service
cp systemd/murmur-daemon.service ~/.config/systemd/user/
systemctl --user daemon-reload

# Control daemon
systemctl --user start murmur-daemon
systemctl --user stop murmur-daemon
systemctl --user status murmur-daemon
systemctl --user enable murmur-daemon  # Auto-start

# View logs
journalctl --user -u murmur-daemon -f
```

### Testing Audio/GPU

```bash
# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test ROCm
rocminfo | grep "Name:"
python -c "from faster_whisper import WhisperModel; model = WhisperModel('medium', device='cuda')"

# Check ydotool
systemctl --user status ydotool
groups | grep input  # User must be in 'input' group
```

## Configuration System

**Location**: `~/.config/murmur/config.yaml` (primary), fallbacks to `~/.whisper/config.yaml` and `/etc/whisper/config.yaml`

**Format**: YAML (see `config.example.yaml`)

**Key settings**:
- `model.size`: "tiny" | "base" | "small" | "medium" | "large" (medium is default)
- `model.device`: "cuda" (ROCm backend for AMD GPUs)
- `audio.chunk_duration`: 1.0-5.0s (balance latency vs accuracy, default 2.0)
- `audio.vad_aggressiveness`: 0-3 (higher = more aggressive silence filtering)
- `text_insertion.method`: "auto" | "direct" | "auto_paste" | "clipboard"

## ROCm/GPU Considerations

**Critical environment variables** (may be needed in systemd service):
- `HSA_OVERRIDE_GFX_VERSION` - Override GPU version for compatibility (e.g., "10.3.0" for RX 6000 series)
- `QT_QPA_PLATFORM=wayland` - Required for Qt Wayland support

**GPU usage**: Whisper inference uses 30-50% GPU, ~2GB VRAM for medium model

## IPC Protocol

**Request format**:
```json
{"command": "start|stop|status", "args": {}}
```

**Response format**:
```json
{"status": "success|error", "message": "...", "result": {}}
```

**Socket path**: `/tmp/murmur-daemon.sock` (0o600 permissions, owner-only)

## Common Gotchas

1. **ydotool requires user in 'input' group**: `sudo usermod -aG input $USER` then logout/login
2. **ydotool daemon must be running**: `systemctl --user enable --now ydotool.service`
3. **Qt requires Wayland platform**: Set `QT_QPA_PLATFORM=wayland` if GUI doesn't appear
4. **Model loading failures**: Usually ROCm misconfiguration - check `rocminfo` and fallback to CPU
5. **VAD too aggressive**: If transcription cuts off words, lower `audio.vad_aggressiveness` to 0 or 1
6. **Daemon won't start**: Check logs with `journalctl --user -u murmur-daemon -n 50`

## Code Style

- **Formatter**: black (line length 100)
- **Type hints**: Encouraged (Python 3.10+ syntax)
- **Docstrings**: Google style
- **Logging**: Use module-level logger, levels: DEBUG (diagnostics), INFO (lifecycle), WARNING (recoverable), ERROR (failures)
- **Imports**: Use `from typing import Optional, Dict, List` for type hints

## Key Design Patterns

1. **Signal/Slot pattern** for Qt GUI updates from background threads
2. **Fallback pattern** for text insertion (try primary, fall back to secondary/tertiary)
3. **Thread-safe queues** for audio chunk passing between capture and transcription
4. **Command handler registration** in IPC server for extensible command dispatch

## Performance Profiling

```bash
# Profile daemon
python -m cProfile -o profile.stats -m murmur_daemon.daemon

# Monitor GPU
rocm-smi -d --showuse
watch -n 1 rocm-smi -d --showmeminfo
```

## Testing Strategy

**Manual test checklist**:
1. Start daemon: `systemctl --user start murmur-daemon`
2. Check status: `murmur status`
3. Start recording: `murmur start` - verify GUI appears
4. Speak - verify waveform animates and transcription updates
5. Stop: `murmur stop` - verify text inserted
6. Check logs for errors

**Note**: Automated tests are TODO - contributions welcome
