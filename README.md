# Whisper Voice Input

**Real-time voice-to-text transcription for Linux Wayland systems**

Transform your voice into text anywhere on your system with a simple keyboard shortcut. Powered by OpenAI's Whisper model with AMD GPU acceleration.

![Status: In Development](https://img.shields.io/badge/status-in%20development-yellow)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- 🎤 **System-wide voice input** - Works in any application
- ⚡ **Real-time transcription** - See text as you speak
- 🎯 **High accuracy** - Powered by Whisper medium model
- 🚀 **AMD GPU accelerated** - Fast inference with ROCm
- 🖼️ **Visual feedback** - Floating window with waveform and live transcription
- ⌨️ **Smart text insertion** - Direct injection, auto-paste, or clipboard
- 🔒 **100% local** - No data sent to external servers
- 🎨 **Wayland native** - Designed for modern Linux compositors

---

## 🎬 Quick Demo

```bash
# Press Super+Shift+Space
# Speak: "This is a test of voice input"
# Press Super+Shift+R
# Text appears: "This is a test of voice input"
```

---

## 📋 Requirements

- **OS**: Linux with Wayland (Hyprland, Sway, KDE, GNOME)
- **GPU**: AMD RX 6000/7000 series (RDNA2/3)
- **RAM**: 4GB minimum, 8GB recommended
- **Python**: 3.10 or higher
- **ROCm**: 5.x or higher

---

## 🚀 Quick Start

### Arch Linux

```bash
# Install dependencies
sudo pacman -S python python-pip rocm-hip-sdk portaudio ydotool qt6-wayland

# Clone and install
git clone https://github.com/yourusername/Whisper.git
cd Whisper
pip install --user -r requirements.txt
pip install --user ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/
pip install --user -e .

# Configure ydotool
sudo usermod -aG input $USER
systemctl --user enable --now ydotool.service

# Start daemon
systemctl --user enable --now whisper-daemon

# Add to Hyprland config (~/.config/hypr/hyprland.conf)
bind = SUPER SHIFT, Space, exec, whi start
bind = SUPER SHIFT, R, exec, whi stop

# Reload Hyprland
hyprctl reload
```

**Detailed installation instructions**: [docs/INSTALLATION.md](docs/INSTALLATION.md)

---

## 📖 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup for all distributions
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API.md)** - CLI commands and IPC protocol
- **[Development Guide](docs/DEVELOPMENT.md)** - Contributing and development setup

---

## 🎯 Usage

### Basic Commands

```bash
# Start recording
whi start

# Stop recording and insert text
whi stop

# Check status
whi status
```

### With Hyprland Keybindings

1. Press `Super+Shift+Space` to start recording
2. Speak clearly into your microphone
3. Watch the floating window show:
   - Real-time waveform visualization
   - Live transcription text
   - Recording timer
4. Press `Super+Shift+R` to stop and insert text

### Text Insertion Methods

Whisper tries three methods automatically:

1. **Direct injection** - Types text character-by-character (most reliable)
2. **Auto-paste** - Copies to clipboard and simulates Ctrl+V
3. **Clipboard only** - Copies text, you paste manually with Ctrl+V

---

## ⚙️ Configuration

Configuration file: `~/.config/whisper/config.yaml`

```yaml
model:
  size: "medium"           # tiny, base, small, medium, large
  device: "cuda"           # Use AMD GPU via ROCm
  compute_type: "float16"

audio:
  chunk_duration: 2.0      # Balance speed vs accuracy
  vad_aggressiveness: 3    # Voice detection sensitivity (0-3)

gui:
  theme: "dark"
  show_waveform: true
  show_timer: true

text_insertion:
  method: "auto"           # auto, direct, auto_paste, clipboard
```

See [config.example.yaml](config.example.yaml) for all options.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│ Hyprland Keybinding → CLI (whi start)   │
└──────────────┬──────────────────────────────┘
               │ Unix Socket
┌──────────────▼──────────────────────────────┐
│          Background Daemon                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Audio   │→ │ Whisper  │→ │   Text   │  │
│  │ Capture  │  │ (ROCm)   │  │ Injector │  │
│  │   +VAD   │  │          │  │ 3-tier   │  │
│  └──────────┘  └─────┬────┘  └──────────┘  │
│                      │                      │
│              ┌───────▼────────┐             │
│              │  PyQt6 Window  │             │
│              │  Waveform +    │             │
│              │  Transcription │             │
│              └────────────────┘             │
└─────────────────────────────────────────────┘
```

For detailed architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🛠️ Components

### whisper (CLI)
User-facing command-line tool for controlling recording sessions.

### whisper-daemon (Background Service)
Persistent service that:
- Keeps Whisper model loaded (fast startup)
- Manages audio capture and VAD
- Runs GPU-accelerated transcription
- Controls GUI window
- Handles text insertion

### GUI Window (PyQt6)
Floating overlay that displays:
- Real-time audio waveform
- Live transcription as you speak
- Recording timer

---

## 🔧 Development

```bash
# Clone repository
git clone https://github.com/yourusername/Whisper.git
cd Whisper

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run daemon in debug mode
python -m whisper_daemon.daemon --log-level DEBUG

# Format code
black .

# Run tests (TODO)
pytest tests/
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guide.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Format code with black
5. Commit using conventional commits (`feat: add amazing feature`)
6. Push and create a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 🐛 Troubleshooting

### Daemon won't start
```bash
# Check logs
journalctl --user -u whisper-daemon -n 50

# Verify ROCm
rocminfo
```

### No audio input
```bash
# List devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Text not inserting
```bash
# Check ydotool
systemctl --user status ydotool
groups | grep input  # Should show "input"
```

Full troubleshooting guide: [docs/INSTALLATION.md#troubleshooting](docs/INSTALLATION.md#troubleshooting)

---

## 📊 Performance

- **Latency**: <3s from speech to text display
- **Memory**: ~2GB idle, ~3GB during transcription
- **GPU Usage**: 30-50% during transcription
- **Model Size**: ~1.5GB (medium model)

---

## 🔒 Privacy & Security

- ✅ **100% local processing** - No internet required, no data sent anywhere
- ✅ **No data retention** - Transcriptions not saved by default
- ✅ **Microphone only active during recording** - Full user control
- ✅ **Open source** - Audit the code yourself

---

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized Whisper implementation
- [arlo-phoenix](https://github.com/arlo-phoenix) - ROCm-optimized CTranslate2
- [ydotool](https://github.com/ReimuNotMoe/ydotool) - Wayland input injection

---

## 🗺️ Roadmap

- [x] Core transcription pipeline
- [x] GUI with waveform visualization
- [x] 3-tier text insertion
- [x] Hyprland integration
- [ ] Multi-language support
- [ ] Custom model selection
- [ ] Transcription history
- [ ] In-window text editing
- [ ] Configuration GUI
- [ ] AUR package
- [ ] Comprehensive tests

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Whisper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/Whisper/discussions)
- **Documentation**: [docs/](docs/)

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Made with ❤️ for the Linux community**
