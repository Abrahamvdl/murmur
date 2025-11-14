# Murmur - Installation Guide

## System Requirements

### Hardware
- **AMD GPU**: RX 6000 or 7000 series (RDNA2/RDNA3 architecture)
  - Minimum 4GB VRAM for medium model
  - 8GB+ VRAM recommended
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 2GB for model files + dependencies
- **Microphone**: Any USB or built-in microphone

### Software
- **OS**: Linux with Wayland compositor
  - Tested on: Hyprland, Sway, KDE Wayland
  - May work on: GNOME Wayland, wlroots-based compositors
- **Python**: 3.10 or higher
- **ROCm**: 5.x or higher

### Supported Distributions
- ✅ Arch Linux (recommended, easiest setup)
- ✅ Ubuntu 22.04+
- ✅ Fedora 37+
- ⚠️  Other distributions may require additional configuration

---

## Installation

### Option 1: Quick Install (Arch Linux)

```bash
# Install system dependencies
sudo pacman -S python python-pip rocm-hip-sdk portaudio ydotool qt6-base qt6-wayland

# Clone repository
cd ~/Downloads
git clone https://github.com/Abrahamvdl/murmur.git
cd murmur

# Install Python dependencies
pip install --user -r requirements.txt

# Install ROCm-optimized ctranslate2
pip install --user ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/

# Install whisper tool
pip install --user -e .

# Configure ydotool
sudo usermod -aG input $USER
systemctl --user enable --now ydotool.service

# Log out and back in for group changes to take effect
```

### Option 2: Manual Installation (Ubuntu/Debian)

#### Step 1: Install ROCm

```bash
# Add AMD repository
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/$(lsb_release -cs)/amdgpu-install_latest_all.deb
sudo dpkg -i amdgpu-install_latest_all.deb
sudo apt update

# Install ROCm
sudo amdgpu-install --usecase=rocm

# Add user to render and video groups
sudo usermod -aG render,video $USER

# Verify installation
rocminfo
```

#### Step 2: Install System Dependencies

```bash
# Python and build tools
sudo apt install python3 python3-pip python3-venv build-essential

# Audio libraries
sudo apt install portaudio19-dev

# Qt6 (for GUI)
sudo apt install qt6-base-dev qt6-wayland

# ydotool (text injection)
# Option A: From package (if available)
sudo apt install ydotool

# Option B: Build from source
git clone https://github.com/ReimuNotMoe/ydotool.git
cd ydotool
mkdir build && cd build
cmake ..
make
sudo make install
```

#### Step 3: Install Whisper

```bash
# Clone repository
cd ~/Downloads
git clone https://github.com/Abrahamvdl/murmur.git
cd murmur

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/

# Install whisper
pip install -e .
```

#### Step 4: Configure ydotool

```bash
# Add user to input group
sudo usermod -aG input $USER

# Enable ydotool service
systemctl --user enable --now ydotool.service

# Log out and back in
```

### Option 3: Installation Script (Coming Soon)

```bash
curl -sSL https://raw.githubusercontent.com/abrahamvdl/murmur/main/install.sh | bash
```

---

## Configuration

### 1. Create Configuration Directory

```bash
mkdir -p ~/.config/whisper
```

### 2. Copy Example Configuration

```bash
cp config.example.yaml ~/.config/murmur/config.yaml
```

### 3. Edit Configuration

```bash
nano ~/.config/murmur/config.yaml
```

**Minimal Configuration**:
```yaml
model:
  size: "medium"        # tiny, base, small, medium, large
  device: "cuda"        # Use CUDA (ROCm backend)
  compute_type: "float16"

audio:
  chunk_duration: 2.0
  vad_aggressiveness: 3

gui:
  theme: "dark"
```

### 4. Test Audio Device

```bash
# List available audio devices
python3 -c "import sounddevice as sd; print(sd.query_devices())"

# If you need to select a specific device, note its index and add to config:
# audio:
#   device_index: 5  # Replace with your device index
```

---

## Setup Daemon

### 1. Install Systemd Service

```bash
# Copy service file
mkdir -p ~/.config/systemd/user
cp systemd/murmur-daemon.service ~/.config/systemd/user/

# Edit service file to update paths if needed
nano ~/.config/systemd/user/murmur-daemon.service

# If you used a virtual environment, update ExecStart path:
# ExecStart=/home/yourusername/Downloads/Whisper/venv/bin/murmur-daemon
```

### 2. Enable and Start Service

```bash
# Reload systemd
systemctl --user daemon-reload

# Enable service (auto-start on login)
systemctl --user enable murmur-daemon

# Start service now
systemctl --user start murmur-daemon

# Check status
systemctl --user status murmur-daemon
```

### 3. Verify Daemon is Running

```bash
whi status
```

Expected output:
```json
{
  "daemon_running": true,
  "recording": false,
  "model_loaded": true,
  ...
}
```

---

## Configure Hyprland Keybindings

### 1. Edit Hyprland Configuration

```bash
nano ~/.config/hypr/hyprland.conf
```

### 2. Add Keybindings

Add these lines to your keybindings section:

```conf
# Murmur
bind = SUPER SHIFT, Space, exec, murmur start
bind = SUPER SHIFT, R, exec, murmur stop

# Alternative: use function keys
# bind = , F9, exec, murmur start
# bind = , F10, exec, murmur stop
```

**Recommended Keybindings**:
- `Super+Shift+Space`: Start recording
- `Super+Shift+R`: Stop recording and insert text

### 3. Reload Hyprland Configuration

```bash
# Reload Hyprland
hyprctl reload
```

---

## Verify Installation

### 1. Test CLI Commands

```bash
# Check status
whi status

# Start recording
whi start

# Speak: "This is a test of the murmur system"

# Stop recording
whi stop

# Text should appear in the active application or be copied to clipboard
```

### 2. Test Keybindings

1. Open any text editor (e.g., `nano`, VSCode, browser)
2. Press `Super+Shift+Space` to start recording
3. GUI window should appear at center of screen
4. Speak clearly into microphone
5. Watch transcription appear in real-time
6. Press `Super+Shift+R` to stop
7. Text should be inserted at cursor position

### 3. Check Logs

```bash
# View recent logs
journalctl --user -u murmur-daemon -n 50

# Follow logs in real-time
journalctl --user -u murmur-daemon -f
```

---

## Troubleshooting

### Daemon Won't Start

**Check logs**:
```bash
journalctl --user -u murmur-daemon --no-pager
```

**Common issues**:

1. **ROCm not detected**
   ```bash
   # Check ROCm installation
   rocminfo

   # Check if GPU is visible
   rocm-smi

   # May need to set environment variable
   export HSA_OVERRIDE_GFX_VERSION=10.3.0  # For RX 6000 series
   ```

2. **Python module not found**
   ```bash
   # Check if whisper is installed
   pip list | grep whisper

   # Reinstall if needed
   pip install --user -e /path/to/Whisper
   ```

3. **Permission denied for socket**
   ```bash
   # Check socket permissions
   ls -l /tmp/murmur-daemon.sock

   # Should be owned by your user
   ```

### Model Loading Fails

**Symptom**: "Failed to load Whisper model" error

**Solutions**:

1. **Download model manually**:
   ```bash
   # Models are auto-downloaded on first use
   # But you can pre-download:
   python3 -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cuda')"
   ```

2. **Try CPU fallback**:
   ```yaml
   # Edit config.yaml
   model:
     device: "cpu"
     compute_type: "int8"
   ```

3. **Check disk space**:
   ```bash
   df -h ~/.cache/huggingface
   # Models are ~1-3GB
   ```

### No Audio Input

**Check microphone**:
```bash
# List devices
arecord -l

# Test recording
arecord -d 5 test.wav && aplay test.wav
```

**Check permissions**:
```bash
# User should be in audio group
groups | grep audio

# Add if missing
sudo usermod -aG audio $USER
```

**Select specific device**:
```yaml
# Edit config.yaml
audio:
  device_index: 5  # Your microphone index from sd.query_devices()
```

### Text Not Inserting

**Check ydotool**:
```bash
# Check service status
systemctl --user status ydotool

# Check if user is in input group
groups | grep input

# Verify /dev/uinput access
ls -l /dev/uinput
```

**Test manually**:
```bash
# Should type "hello"
ydotool type hello
```

**Fallback to clipboard**:
```yaml
# Edit config.yaml - use clipboard only
text_insertion:
  method: "clipboard"
```

### GUI Window Not Appearing

**Check Qt platform**:
```bash
# Should use Wayland
echo $QT_QPA_PLATFORM
# Should output: wayland or be empty

# Force Wayland if needed
export QT_QPA_PLATFORM=wayland
```

**Check compositor**:
```bash
# Hyprland should be running
ps aux | grep Hyprland

# Check if layer-shell is supported
# (Some compositors may not support floating overlays)
```

### High GPU Usage / Temperature

**Use smaller model**:
```yaml
model:
  size: "small"  # Instead of "medium"
```

**Limit GPU power**:
```bash
# Set power limit (example: 150W)
sudo rocm-smi -d 0 --setpoweroverdrive 150
```

---

## Performance Tuning

### For Faster Transcription

1. **Use smaller model**: `tiny` or `base` (less accurate)
2. **Shorter chunks**:
   ```yaml
   audio:
     chunk_duration: 1.5  # Faster but may cut words
   ```
3. **Reduce VAD aggressiveness**:
   ```yaml
   audio:
     vad_aggressiveness: 2  # Less filtering
   ```

### For Better Accuracy

1. **Use larger model**: `large` (slower)
2. **Longer chunks**:
   ```yaml
   audio:
     chunk_duration: 3.0  # More context
   ```
3. **Increase VAD aggressiveness**:
   ```yaml
   audio:
     vad_aggressiveness: 3  # More filtering
   ```

### For Lower Resource Usage

1. **CPU mode**:
   ```yaml
   model:
     device: "cpu"
     compute_type: "int8"  # Quantized
   ```

2. **Smaller model**:
   ```yaml
   model:
     size: "tiny"
   ```

---

## Uninstallation

```bash
# Stop and disable daemon
systemctl --user stop murmur-daemon
systemctl --user disable murmur-daemon

# Remove service file
rm ~/.config/systemd/user/murmur-daemon.service
systemctl --user daemon-reload

# Uninstall Python package
pip uninstall murmur-voice

# Remove configuration
rm -rf ~/.config/whisper

# Remove models (optional - saves ~2GB)
rm -rf ~/.cache/huggingface/hub/models--guillaumekln--faster-whisper*

# Remove user from input group (optional)
sudo deluser $USER input
```

---

## Updates

### Updating to Latest Version

```bash
# Navigate to repo
cd ~/Downloads/Whisper

# Pull latest changes
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Reinstall
pip install --user -e .

# Restart daemon
systemctl --user restart murmur-daemon
```

---

## Getting Help

### Check Logs
```bash
# Daemon logs
journalctl --user -u murmur-daemon -f

# Application logs
tail -f ~/.local/share/murmur/whisper.log
```

### Report Issues
- GitHub Issues: https://github.com/Abrahamvdl/murmur/issues
- Include:
  - OS and distribution
  - AMD GPU model
  - ROCm version
  - Error logs
  - Configuration file (remove sensitive info)

### Community
- Discussions: https://github.com/Abrahamvdl/murmur/discussions
- Matrix/Discord: (TODO)

---

## Advanced Configuration

### Custom Model Path

```yaml
model:
  model_path: "/path/to/custom/model"
```

### Multiple Audio Profiles

Create separate config files:

```bash
# Work setup (headset)
~/.config/murmur/work.yaml

# Home setup (desk mic)
~/.config/murmur/home.yaml
```

Run daemon with specific config:
```bash
murmur-daemon --config ~/.config/murmur/work.yaml
```

### Hyprland Window Rules

Add rules to control GUI window behavior:

```conf
# Keep window floating
windowrulev2 = float, class:^(whisper-gui)$

# Center window
windowrulev2 = center, class:^(whisper-gui)$

# Make window sticky (show on all workspaces)
windowrulev2 = pin, class:^(whisper-gui)$

# No shadow
windowrulev2 = noshadow, class:^(whisper-gui)$
```

---

## Security Considerations

### Permissions

Whisper requires:
- ✅ Microphone access (audio group)
- ✅ Input injection (input group, /dev/uinput)
- ✅ Clipboard access (standard)
- ❌ Network access (NOT required - all processing is local)
- ❌ Root access (NOT required)

### Privacy

- **All processing is local** - no data sent to external servers
- **No data retention** - transcriptions are not saved (unless you configure logging)
- **Microphone only active during recording** - controlled by you

### Logs

Logs may contain partial transcriptions. To disable:

```yaml
logging:
  level: "ERROR"  # Only log errors
```

Or disable file logging entirely by commenting out the log file in daemon code.

---

## Next Steps

1. ✅ Complete installation
2. ✅ Configure Hyprland keybindings
3. ✅ Test voice input in various applications
4. 📖 Read [API Documentation](API.md) for advanced usage
5. 🛠️  Read [Development Guide](DEVELOPMENT.md) to contribute

---

**Enjoy hands-free text input! 🎤**
