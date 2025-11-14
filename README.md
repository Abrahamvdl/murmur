# Murmur

**Real-time voice-to-text transcription for Linux Wayland systems with AMD GPU acceleration**

Transform your voice into text anywhere on your system with a simple keyboard shortcut. Powered by OpenAI's Whisper model with ROCm-accelerated inference.

> *A quieter alternative to Whisper - system-wide voice input for Linux*

![Status: Alpha](https://img.shields.io/badge/status-alpha-yellow)
![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Platform: Linux](https://img.shields.io/badge/platform-linux%20%7C%20wayland-blueviolet)
![GPU: AMD ROCm](https://img.shields.io/badge/gpu-AMD%20ROCm-red)

> **⚠️ Alpha Quality**: This project is functional but under active development. It works well for my setup (Arch + Hyprland + RX 6000 series), but you may encounter issues with different configurations. Contributions and bug reports welcome!

---

## 🎯 Project Scope

**This project is specifically designed for:**
- ✅ **AMD GPUs** with ROCm support (RX 6000/7000 series, RDNA 2/3)
- ✅ **Wayland compositors** (Hyprland, Sway, KDE Wayland, GNOME Wayland)
- ✅ **Linux** (Arch, Ubuntu 22.04+, Fedora, etc.)

**Known limitations:**
- ❌ **NVIDIA/Intel GPUs**: Not currently supported (contributions welcome for CUDA/OpenVINO backends)
- ⚠️ **X11**: May work but untested; Wayland is the primary target
- ⚠️ **CPU-only mode**: Possible but slow (~10x slower than GPU)
- ⚠️ **Non-English**: Single language only (contributions welcome for multi-language)

If this matches your setup, read on! Otherwise, consider alternatives like [Nerd Dictation](https://github.com/ideasman42/nerd-dictation) or [Talon Voice](https://talonvoice.com/).

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

> **Note**: Installation requires compiling CTranslate2 with ROCm support. Budget 30-60 minutes for first-time setup.

### Step 1: Install System Dependencies

**Arch Linux:**
```bash
sudo pacman -S python python-pip rocm-hip-sdk portaudio ydotool qt6-wayland cmake clang base-devel
```

**Ubuntu 22.04+:**
```bash
# Add ROCm repository first: https://rocm.docs.amd.com/en/latest/deploy/linux/quick_start.html
sudo apt install python3 python3-pip rocm-hip-sdk portaudio19-dev qt6-base-dev qt6-wayland cmake clang build-essential

# Install ydotool manually (not in Ubuntu repos)
# See: https://github.com/ReimuNotMoe/ydotool#building
```

### Step 2: Clone Repository

```bash
git clone https://github.com/Abrahamvdl/murmur.git
cd murmur
```

### Step 3: Install CTranslate2 with ROCm

**Option A: Pre-built Wheels (Fastest)**

Try this first - if it works, skip to Step 4:
```bash
pip install --user ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/
```

**Option B: Build from Source (Recommended for compatibility)**

If pre-built wheels don't work or aren't available:

```bash
# 1. Identify your GPU architecture
rocminfo | grep -E "(Marketing Name|gfx)"
# Example output: gfx1030 (RX 6600/6700), gfx1031 (RX 6800/6900), gfx1100 (RX 7900)

# 2. Clone and build CTranslate2-rocm
git clone https://github.com/arlo-phoenix/CTranslate2-rocm.git --recurse-submodules --depth 1
cd CTranslate2-rocm
mkdir build && cd build

# 3. Configure build (replace gfx1030 with YOUR architecture)
export PYTORCH_ROCM_ARCH=gfx1030
export CXX=clang++
export HIPCXX=/opt/rocm/lib/llvm/bin/clang
export HIP_PATH=/opt/rocm

cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=$HOME/.local \
      -DWITH_MKL=OFF \
      -DWITH_HIP=ON \
      -DWITH_CUDNN=ON \
      -DBUILD_TESTS=OFF \
      -DOPENMP_RUNTIME=COMP \
      ..

# 4. Build (takes 10-20 minutes)
make -j$(nproc)

# 5. Install C++ library
cp libctranslate2.so* ~/.local/lib/
mkdir -p ~/.local/include
cp -r ../include/ctranslate2 ~/.local/include/
cp -r ../include/half_float ~/.local/include/
cp -r ../include/nlohmann ~/.local/include/

# 6. Build Python package
cd ../python
export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH
export CFLAGS="-I$HOME/.local/include"
export CXXFLAGS="-I$HOME/.local/include"
export LDFLAGS="-L$HOME/.local/lib -Wl,-rpath,$HOME/.local/lib"
pip install --user --no-build-isolation .

# 7. Verify
python -c "import ctranslate2; print(f'CTranslate2 version: {ctranslate2.__version__}')"

# 8. Return to project directory
cd ../..
```

**See [docs/ROCM_BUILD.md](docs/ROCM_BUILD.md) for detailed build instructions and troubleshooting.**

### Step 4: Install Murmur

```bash
# Install Python dependencies
pip install --user -r requirements.txt

# Install in editable mode
pip install --user -e .

# Verify installation
whi --help
```

### Step 5: Configure ydotool

```bash
# Add user to input group (required for keyboard injection)
sudo usermod -aG input $USER

# Enable ydotool daemon
systemctl --user enable --now ydotool.service

# IMPORTANT: Log out and log back in for group changes to take effect
```

### Step 6: Install and Start Daemon

```bash
# Copy systemd service
mkdir -p ~/.config/systemd/user
cp systemd/murmur-daemon.service ~/.config/systemd/user/

# If you built CTranslate2 from source, update the service file:
# Edit ~/.config/systemd/user/murmur-daemon.service and add:
#   Environment="LD_LIBRARY_PATH=/home/YOUR_USERNAME/.local/lib"

# Reload systemd and start daemon
systemctl --user daemon-reload
systemctl --user enable --now murmur-daemon

# Check daemon status
whi status
```

### Step 7: Configure Keybindings

**Hyprland** (`~/.config/hypr/hyprland.conf`):
```bash
bind = SUPER SHIFT, Space, exec, murmur start
bind = SUPER SHIFT, R, exec, murmur stop
```

**Sway** (`~/.config/sway/config`):
```bash
bindsym $mod+Shift+Space exec whi start
bindsym $mod+Shift+r exec whi stop
```

Then reload your compositor configuration.

---

**🔍 Troubleshooting**: See [docs/INSTALLATION.md](docs/INSTALLATION.md) for detailed troubleshooting and distribution-specific instructions.

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

Configuration file: `~/.config/murmur/config.yaml`

```yaml
model:
  size: "medium"           # tiny, base, small, medium, large
  device: "cuda"           # Device name for GPU (works with AMD ROCm, not NVIDIA)
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

### murmur-daemon (Background Service)
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
git clone https://github.com/Abrahamvdl/murmur.git
cd murmur

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run daemon in debug mode
python -m murmur_daemon.daemon --log-level DEBUG

# Format code
black .

# Run tests (TODO)
pytest tests/
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guide.

---

## 🤝 Contributing

Contributions are welcome! This is an alpha project with plenty of room for improvement.

**High-priority contributions:**
- NVIDIA/Intel GPU backend support
- Multi-language support
- Automated tests (pytest)
- Distribution packaging (AUR, Deb, RPM)

**Process:**
1. Open an issue to discuss major changes first
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Format code with `black` (line length 100)
4. Use conventional commits (`feat:`, `fix:`, `docs:`)
5. Push and create a Pull Request

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development setup.

---

## 🐛 Troubleshooting

### Daemon won't start
```bash
# Check logs
journalctl --user -u murmur-daemon -n 50

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

## 📞 Support & Contributing

**Before opening an issue**, please:
1. Check [docs/INSTALLATION.md](docs/INSTALLATION.md) troubleshooting section
2. Search existing issues
3. Include your setup: distro, GPU model, ROCm version, compositor

**Contributions welcome for:**
- NVIDIA/Intel GPU support (CUDA, OpenVINO backends)
- Multi-language support
- Automated tests
- Packaging (AUR, Debian, Fedora)
- Bug fixes and documentation improvements

**Links:**
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: [docs/](docs/)

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

---

## 📢 Project Status & Disclaimer

This is a personal project developed and tested on my specific setup:
- **Hardware**: AMD RX 6000 series GPU
- **Distro**: Arch Linux
- **Compositor**: Hyprland
- **ROCm**: 6.0+

**It works well for this configuration**, but your mileage may vary with different hardware, distributions, or compositors. I'm sharing this project in the hope it's useful to others, but cannot guarantee it will work perfectly on all setups.

**Please contribute** if you:
- Get it working on different hardware/distros
- Find and fix bugs
- Want to add features (especially NVIDIA/Intel GPU support)

---

**Made with ❤️ for the Linux community**
