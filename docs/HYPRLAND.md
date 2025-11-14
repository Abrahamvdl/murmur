# Murmur - Hyprland Integration Guide

This guide covers integrating Murmur with the Hyprland compositor.

---

## Prerequisites

- Hyprland compositor installed and running
- Murmur installed (see [INSTALLATION.md](INSTALLATION.md))
- Daemon running: `systemctl --user status murmur-daemon`

---

## Basic Keybindings

Add these lines to your Hyprland configuration file (`~/.config/hypr/hyprland.conf`):

```conf
# Murmur
bind = SUPER SHIFT, Space, exec, murmur start
bind = SUPER SHIFT, R, exec, murmur stop
```

### Explanation

- **`SUPER SHIFT + Space`**: Starts recording
  - Opens GUI window at center of screen
  - Begins capturing audio and real-time transcription

- **`SUPER SHIFT + R`**: Stops recording
  - Finalizes transcription
  - Inserts text at cursor position
  - Keeps GUI window open for review

### Reload Configuration

After adding keybindings:

```bash
hyprctl reload
```

---

## Alternative Keybindings

### Function Keys

If you prefer function keys:

```conf
bind = , F9, exec, murmur start
bind = , F10, exec, murmur stop
```

### Control-based

For Ctrl combinations:

```conf
bind = CTRL ALT, V, exec, murmur start
bind = CTRL ALT, B, exec, murmur stop
```

### Custom Modifiers

You can use any combination:
- `SUPER` (Windows/Meta key)
- `SHIFT`
- `CTRL`
- `ALT`

Example:
```conf
bind = SUPER CTRL, Space, exec, murmur start
bind = SUPER CTRL, Return, exec, murmur stop
```

---

## Window Rules

### Make GUI Window Float

The GUI window is already configured to float, but you can add explicit rules:

```conf
# Whisper window rules
windowrulev2 = float, title:^(Murmur)$
windowrulev2 = center, title:^(Murmur)$
```

### Pin to All Workspaces

Make the window sticky (visible on all workspaces):

```conf
windowrulev2 = pin, title:^(Murmur)$
```

### Disable Shadows

For a cleaner look:

```conf
windowrulev2 = noshadow, title:^(Murmur)$
```

### Size and Position

Override default size:

```conf
windowrulev2 = size 700 350, title:^(Murmur)$
windowrulev2 = move center, title:^(Murmur)$
```

### Opacity

Make window semi-transparent:

```conf
windowrulev2 = opacity 0.95, title:^(Murmur)$
```

### Complete Window Rules Example

```conf
# Murmur Window Rules
windowrulev2 = float, title:^(Murmur)$
windowrulev2 = center, title:^(Murmur)$
windowrulev2 = pin, title:^(Murmur)$
windowrulev2 = noshadow, title:^(Murmur)$
windowrulev2 = opacity 0.95, title:^(Murmur)$
```

---

## Advanced Usage

### Submaps for Voice Input

Create a dedicated submap for voice input:

```conf
# Voice input submap
bind = SUPER, V, submap, voice

submap = voice

bind = , S, exec, murmur start
bind = , S, submap, reset

bind = , E, exec, murmur stop
bind = , E, submap, reset

bind = , escape, submap, reset

submap = reset
```

Usage:
1. Press `Super + V` to enter voice mode
2. Press `S` to start recording
3. Press `E` to stop and insert text
4. Press `Escape` to exit voice mode

### Status Check Keybinding

Add a keybinding to check daemon status:

```conf
bind = SUPER SHIFT, I, exec, notify-send "Whisper Status" "$(whi status)"
```

---

## Integration with Other Tools

### With Rofi/Wofi

Create a launcher menu:

```bash
#!/bin/bash
# ~/.config/hypr/scripts/whisper-menu.sh

choice=$(echo -e "Start Recording\nStop Recording\nCheck Status\nRestart Daemon" | wofi --dmenu)

case "$choice" in
    "Start Recording")
        whi start
        ;;
    "Stop Recording")
        whi stop
        ;;
    "Check Status")
        whi status | wofi --dmenu
        ;;
    "Restart Daemon")
        systemctl --user restart murmur-daemon
        ;;
esac
```

Then add to Hyprland config:

```conf
bind = SUPER SHIFT, W, exec, ~/.config/hypr/scripts/whisper-menu.sh
```

### With Waybar

Add a Waybar module to show recording status:

```json
{
    "custom/whisper": {
        "exec": "systemctl --user is-active murmur-daemon && echo '🎤' || echo '❌'",
        "interval": 5,
        "on-click": "whi start",
        "on-click-right": "whi stop",
        "tooltip": true,
        "tooltip-format": "Murmur"
    }
}
```

### With dunst/mako (Notifications)

Show notifications on start/stop:

```bash
# In your Hyprland config
bind = SUPER SHIFT, Space, exec, murmur start && notify-send "Whisper" "Recording started"
bind = SUPER SHIFT, R, exec, murmur stop && notify-send "Whisper" "Recording stopped"
```

---

## Workspace-Specific Behavior

### Only Allow on Certain Workspaces

```conf
# Example: Only allow voice input on workspace 1 and 2
bind = SUPER SHIFT, Space, exec, [[ $(hyprctl activeworkspace -j | jq -r '.id') -le 2 ]] && whi start
```

### Different Keybindings per Workspace

```conf
# Workspace 1: Standard keybindings
workspace = 1, bind = SUPER SHIFT, Space, exec, murmur start

# Workspace 2: Different keybindings
workspace = 2, bind = CTRL, Space, exec, murmur start
```

---

## Troubleshooting

### Window Not Appearing

1. Check if daemon is running:
   ```bash
   systemctl --user status murmur-daemon
   ```

2. Check Hyprland logs:
   ```bash
   hyprctl clients | grep -i whisper
   ```

3. Try launching window directly:
   ```bash
   python -m murmur_gui.window
   ```

### Keybindings Not Working

1. Test keybinding:
   ```bash
   # In terminal
   whi start
   ```

2. Check if keybinding is registered:
   ```bash
   hyprctl binds | grep whisper
   ```

3. Ensure no conflicts:
   ```bash
   hyprctl binds | grep "SUPER SHIFT Space"
   ```

### Text Not Inserting

1. Check text injection status:
   ```bash
   whi status
   ```

2. Verify ydotool is running:
   ```bash
   systemctl --user status ydotool
   ```

3. Check you're in input group:
   ```bash
   groups | grep input
   ```

---

## Performance Tips

### Reduce Latency

In `~/.config/murmur/config.yaml`:

```yaml
audio:
  chunk_duration: 1.5  # Faster chunks (less accurate)
```

### Improve Accuracy

```yaml
audio:
  chunk_duration: 3.0  # Longer chunks (slower but more accurate)
  vad_aggressiveness: 3  # Maximum voice detection
```

### Disable GUI Animation

If GUI feels slow:

```yaml
gui:
  show_waveform: false  # Disable waveform visualization
```

---

## Example Complete Configuration

Here's a complete Hyprland configuration snippet for Whisper:

```conf
# ~/.config/hypr/hyprland.conf

# Murmur Configuration

# Basic keybindings
bind = SUPER SHIFT, Space, exec, murmur start && notify-send "🎤 Recording"
bind = SUPER SHIFT, R, exec, murmur stop && notify-send "✓ Transcribed"

# Utility bindings
bind = SUPER SHIFT, I, exec, notify-send "Whisper Status" "$(whi status)"
bind = SUPER SHIFT, W, exec, ~/.config/hypr/scripts/whisper-menu.sh

# Window rules
windowrulev2 = float, title:^(Murmur)$
windowrulev2 = center, title:^(Murmur)$
windowrulev2 = pin, title:^(Murmur)$
windowrulev2 = noshadow, title:^(Murmur)$
windowrulev2 = opacity 0.95 0.95, title:^(Murmur)$

# Startup
exec-once = systemctl --user start murmur-daemon
```

---

## Tips and Best Practices

1. **Speak Clearly**: For best results, speak clearly and at a normal pace
2. **Minimize Background Noise**: Use in a quiet environment when possible
3. **Wait for Transcription**: Give the system a moment to process after speaking
4. **Review Before Inserting**: The GUI shows transcription in real-time
5. **Use Punctuation Commands**: Say "period", "comma", etc. (future feature)

---

## Uninstalling

To remove Whisper integration from Hyprland:

1. Remove keybindings from `hyprland.conf`
2. Remove window rules
3. Reload Hyprland: `hyprctl reload`
4. Stop daemon: `systemctl --user stop murmur-daemon`

---

## Further Reading

- [Hyprland Documentation](https://wiki.hyprland.org/)
- [Hyprland Keybindings](https://wiki.hyprland.org/Configuring/Binds/)
- [Hyprland Window Rules](https://wiki.hyprland.org/Configuring/Window-Rules/)

---

**Happy voice typing!** 🎤
