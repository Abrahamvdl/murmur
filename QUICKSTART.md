# Whisper Voice Input - Quick Start Guide

Get up and running in 5 minutes!

---

## Prerequisites

- Arch Linux (or compatible)
- AMD RX 6000/7000 series GPU
- Hyprland compositor
- Working microphone

---

## Installation (3 steps)

### 1. Run Installation Script

```bash
cd ~/Workspace/Linux/Whisper
./install.sh
```

The script will:
- Install system dependencies
- Create Python virtual environment
- Install Whisper and dependencies
- Setup ydotool
- Configure systemd service
- Start the daemon

### 2. Log Out and Back In

If you were added to the `input` group, log out and back in for changes to take effect.

### 3. Add Hyprland Keybindings

Edit `~/.config/hypr/hyprland.conf`:

```conf
# Whisper Voice Input
bind = SUPER SHIFT, Space, exec, ~/.local/bin/whisper start
bind = SUPER SHIFT, R, exec, ~/.local/bin/whisper stop
```

Reload Hyprland:
```bash
hyprctl reload
```

---

## Usage

### Start Recording
Press `Super + Shift + Space`

### Speak
Speak clearly into your microphone. You'll see:
- Real-time waveform visualization
- Live transcription as you speak
- Recording timer

### Stop Recording
Press `Super + Shift + R`

Text will be inserted at your cursor position!

---

## Verify Installation

```bash
# Check daemon status
whisper status

# Should show:
# ✓ Daemon running
# ✓ Model loaded
# ✓ Text injection available
```

---

## Troubleshooting

### Daemon not starting?

```bash
# Check logs
journalctl --user -u whisper-daemon -n 50

# Restart daemon
systemctl --user restart whisper-daemon
```

### Text not inserting?

```bash
# Check ydotool
systemctl --user status ydotool

# Check you're in input group
groups | grep input
```

### No audio?

```bash
# List audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"
```

---

## Configuration

Edit `~/.config/whisper/config.yaml`:

```yaml
model:
  size: "medium"  # tiny, base, small, medium, large

audio:
  chunk_duration: 2.0  # Lower = faster, higher = more accurate

gui:
  theme: "dark"  # or "light"
```

Restart daemon after changes:
```bash
systemctl --user restart whisper-daemon
```

---

## Tips for Best Results

1. **Speak clearly** at a normal pace
2. **Minimize background noise**
3. **Wait ~2 seconds** after speaking before stopping
4. **Review transcription** in the GUI before stopping
5. **Use in quiet environments** for best accuracy

---

## Next Steps

- Read [docs/HYPRLAND.md](docs/HYPRLAND.md) for advanced keybindings
- Read [docs/INSTALLATION.md](docs/INSTALLATION.md) for detailed setup
- Read [docs/API.md](docs/API.md) for CLI commands
- Read [CONTRIBUTING.md](CONTRIBUTING.md) to contribute

---

## Uninstall

```bash
systemctl --user stop whisper-daemon
systemctl --user disable whisper-daemon
rm ~/.config/systemd/user/whisper-daemon.service
rm -rf ~/.config/whisper
pip uninstall whisper-voice-input
```

---

**Happy voice typing!** 🎤
