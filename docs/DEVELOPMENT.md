# Murmur - Development Guide

## Development Setup

### Prerequisites

#### System Requirements
- Linux with Wayland compositor (tested on Hyprland)
- Python 3.10 or higher
- AMD GPU with ROCm support (RX 6000/7000 series recommended)
- Git

#### Install System Dependencies

**Arch Linux**:
```bash
# Base development tools
sudo pacman -S python python-pip git base-devel

# ROCm for AMD GPU
sudo pacman -S rocm-hip-sdk rocm-opencl-sdk

# Audio dependencies
sudo pacman -S portaudio

# Text injection tool
sudo pacman -S ydotool

# Qt dependencies for GUI
sudo pacman -S qt6-base qt6-wayland
```

**Ubuntu/Debian**:
```bash
# Base development tools
sudo apt install python3 python3-pip git build-essential

# ROCm (requires adding AMD repository)
# Follow: https://rocm.docs.amd.com/en/latest/deploy/linux/quick_start.html

# Audio dependencies
sudo apt install portaudio19-dev

# ydotool (may need to build from source)
# See: https://github.com/ReimuNotMoe/ydotool

# Qt dependencies
sudo apt install qt6-base-dev qt6-wayland
```

### Clone Repository

```bash
cd ~/Workspace/Linux
git clone https://github.com/Abrahamvdl/murmur.git
cd murmur
```

### Setup Python Environment

#### Option 1: venv (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Option 2: System-wide

```bash
# Not recommended, but possible
pip install --user -e .
```

### Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install ctranslate2-rocm from arlo-phoenix
pip install ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/

# Install development dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Check Python imports
python -c "import faster_whisper; import sounddevice; import PyQt6; print('All imports successful')"

# Check ROCm
rocminfo | grep "Name:"

# Check ydotool
ydotool --version
```

### Configure ydotool

```bash
# Add user to input group (required for /dev/uinput access)
sudo usermod -aG input $USER

# Enable ydotool daemon
systemctl --user enable --now ydotool.service

# Verify access
ls -l /dev/uinput
# Should show: crw-rw---- 1 root input ...

# Log out and back in for group changes to take effect
```

---

## Project Structure

```
Whisper/
├── murmur_daemon/          # Background service
│   ├── __init__.py
│   ├── daemon.py            # Main daemon process
│   ├── transcriber.py       # Whisper model handler
│   ├── audio_capture.py     # Audio input & VAD
│   ├── ipc_server.py        # Unix socket communication
│   ├── text_injector.py     # Text insertion with fallbacks
│   └── config.py            # Configuration management
│
├── murmur_gui/             # GUI window
│   ├── __init__.py
│   ├── window.py            # Main Qt window
│   ├── waveform.py          # Audio visualization
│   └── styles.py            # UI theming
│
├── murmur_cli/             # Command-line interface
│   ├── __init__.py
│   └── cli.py               # CLI commands
│
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEVELOPMENT.md
│   └── INSTALLATION.md
│
├── systemd/                 # Systemd service files
│   └── murmur-daemon.service
│
├── tests/                   # Unit tests (TODO)
│
├── pyproject.toml           # Project metadata
├── requirements.txt         # Python dependencies
├── config.example.yaml      # Example configuration
├── PRD.md                   # Product requirements
└── README.md                # User documentation
```

---

## Running in Development Mode

### Start Daemon Manually

```bash
# Activate virtual environment
source venv/bin/activate

# Run daemon in foreground with debug logging
python -m murmur_daemon.daemon --log-level DEBUG
```

### Test CLI Commands

In a separate terminal:

```bash
# Activate virtual environment
source venv/bin/activate

# Test status
python -m murmur_cli.cli status

# Test recording
python -m murmur_cli.cli start
# ... speak ...
python -m murmur_cli.cli stop
```

### Run GUI Standalone

For testing GUI independently:

```bash
python -m murmur_gui.window
```

---

## Development Workflow

### 1. Making Changes

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes
# ... edit files ...

# Format code
black murmur_daemon/ murmur_gui/ murmur_cli/

# Check linting
flake8 murmur_daemon/ murmur_gui/ murmur_cli/

# Type checking (optional)
mypy murmur_daemon/ murmur_gui/ murmur_cli/
```

### 2. Testing Changes

```bash
# Stop daemon if running
systemctl --user stop murmur-daemon

# Run daemon in debug mode
python -m murmur_daemon.daemon --log-level DEBUG

# In another terminal, test your changes
python -m murmur_cli.cli start
```

### 3. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

---

## Debugging

### Enable Debug Logging

Edit configuration:

```yaml
logging:
  level: "DEBUG"
```

Or run daemon with flag:

```bash
python -m murmur_daemon.daemon --log-level DEBUG
```

### View Logs

```bash
# Tail log file
tail -f ~/.local/share/murmur/whisper.log

# If using systemd
journalctl --user -u murmur-daemon -f
```

### Debug Specific Components

#### Audio Capture

```python
# In murmur_daemon/audio_capture.py, add:
logger.debug(f"Audio chunk: {len(audio_data)} samples, RMS: {np.sqrt(np.mean(audio_data**2))}")
```

#### Whisper Transcription

```python
# In murmur_daemon/transcriber.py, add:
logger.debug(f"Processing audio chunk of {duration}s")
logger.debug(f"Transcription result: {text}")
```

#### Text Injection

```python
# In murmur_daemon/text_injector.py, add:
logger.debug(f"Attempting method: {method.value}")
logger.debug(f"Text to insert: {text[:50]}...")
```

### Common Issues

#### "Daemon not running"

**Cause**: Daemon not started or crashed

**Solution**:
```bash
# Check if running
ps aux | grep murmur-daemon

# Check logs
journalctl --user -u murmur-daemon --no-pager -n 50

# Restart
systemctl --user restart murmur-daemon
```

#### "Failed to load model"

**Cause**: ROCm not configured, model not downloaded

**Solution**:
```bash
# Check ROCm
rocminfo

# Check environment
echo $HSA_OVERRIDE_GFX_VERSION

# Test faster-whisper
python -c "from faster_whisper import WhisperModel; model = WhisperModel('medium', device='cuda')"
```

#### "ydotool command failed"

**Cause**: Not in input group, ydotool daemon not running

**Solution**:
```bash
# Check groups
groups | grep input

# Check ydotool daemon
systemctl --user status ydotool

# Check /dev/uinput permissions
ls -l /dev/uinput
```

#### "No audio input"

**Cause**: Wrong device, permissions issue

**Solution**:
```bash
# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Test audio capture
python -c "import sounddevice as sd; import numpy as np; print(sd.rec(16000, samplerate=16000, channels=1))"
```

---

## Testing

### Manual Testing Checklist

- [ ] Start daemon: `systemctl --user start murmur-daemon`
- [ ] Check status: `murmur status`
- [ ] Start recording: `murmur start`
- [ ] Verify GUI window appears
- [ ] Speak some text
- [ ] Verify waveform animates
- [ ] Verify transcription appears in real-time
- [ ] Stop recording: `murmur stop`
- [ ] Verify text is inserted/copied
- [ ] Check logs for errors

### Unit Tests (TODO)

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_ipc_server.py

# Run with coverage
pytest --cov=murmur_daemon tests/
```

### Integration Tests (TODO)

```bash
# Test full pipeline
python tests/integration_test.py
```

---

## Code Style

### Formatting

We use `black` for code formatting:

```bash
# Format all Python files
black .

# Check without modifying
black --check .
```

**Configuration** (in `pyproject.toml`):
```toml
[tool.black]
line-length = 100
```

### Linting

We use `flake8` for linting:

```bash
# Lint all Python files
flake8 murmur_daemon/ murmur_gui/ murmur_cli/
```

### Type Hints

We encourage type hints but don't enforce strict typing:

```python
from typing import Optional, Dict, List

def process_audio(audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
    """Process audio and return transcription."""
    ...
```

### Documentation

#### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this is raised
    """
    ...
```

#### Comments

```python
# Use comments to explain WHY, not WHAT
# Good:
chunk_size = 2048  # Balance latency vs transcription accuracy

# Bad:
chunk_size = 2048  # Set chunk size to 2048
```

---

## Contributing

### Contribution Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Format and lint your code
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): brief description

Longer description if needed

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Code style changes (formatting)
- refactor: Code refactoring
- perf: Performance improvements
- test: Adding tests
- chore: Build process, dependencies
```

**Examples**:
```
feat(transcriber): add support for custom models
fix(audio): resolve VAD false positives
docs(api): update IPC protocol documentation
```

---

## Performance Profiling

### Profile Python Code

```bash
# Profile daemon startup
python -m cProfile -o profile.stats -m murmur_daemon.daemon

# Analyze results
python -m pstats profile.stats
> sort cumulative
> stats 20
```

### Profile GPU Usage

```bash
# Monitor GPU usage while transcribing
rocm-smi -d --showuse

# Monitor GPU memory
watch -n 1 rocm-smi -d --showmeminfo
```

### Profile Memory Usage

```bash
# Use memory_profiler
pip install memory_profiler

# Add @profile decorator to functions
@profile
def load_model():
    ...

# Run with profiler
python -m memory_profiler murmur_daemon/transcriber.py
```

---

## Release Process (TODO)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag -a v0.1.0 -m "Release v0.1.0"`
4. Push tag: `git push origin v0.1.0`
5. Build package: `python -m build`
6. Upload to PyPI (if public): `twine upload dist/*`
7. Create GitHub release with binaries

---

## IDE Configuration

### VS Code

Recommended `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### PyCharm

1. File → Settings → Project → Python Interpreter → Add → Existing environment
2. Select `venv/bin/python`
3. Enable black formatter: Settings → Tools → Black
4. Enable flake8: Settings → Tools → External Tools

---

## Resources

### Documentation
- [faster-whisper GitHub](https://github.com/guillaumekln/faster-whisper)
- [PyQt6 Documentation](https://doc.qt.io/qtforpython/)
- [ydotool GitHub](https://github.com/ReimuNotMoe/ydotool)
- [ROCm Documentation](https://rocm.docs.amd.com/)

### Community
- Project Issues: https://github.com/Abrahamvdl/murmur/issues
- Discussions: https://github.com/Abrahamvdl/murmur/discussions

---

## FAQ

**Q: Why Python instead of C++?**
A: Rapid development, easier integration with ML libraries, sufficient performance with native extensions.

**Q: Why PyQt6 over GTK?**
A: Better Wayland layer-shell support, more features for waveform visualization, better documentation.

**Q: Why ydotool over other input tools?**
A: Native Wayland support, active development, works with modern compositors.

**Q: Can I use this with X11?**
A: Yes, but some features may behave differently. Wayland is the primary target.

**Q: How do I add a new text insertion method?**
A: Extend `TextInjector` class in `murmur_daemon/text_injector.py`, add new `InsertionMethod` enum value, implement insertion logic.
