# Whisper Voice Input - API Reference

## CLI Commands

### `whi start`

Start a new recording session.

**Behavior**:
- Opens GUI window at center of screen
- Begins audio capture
- Starts real-time transcription
- Returns immediately (non-blocking)

**Exit Codes**:
- `0`: Success
- `1`: Daemon not running
- `2`: Recording already in progress
- `3`: Error starting recording

**Example**:
```bash
whi start
```

**Hyprland Keybinding**:
```
bind = SUPER_SHIFT, Space, exec, whi start
```

---

### `whi stop`

Stop the current recording session and insert transcribed text.

**Behavior**:
- Stops audio capture
- Finalizes transcription
- Inserts text using 3-tier fallback system
- Keeps GUI window open for review
- Returns when text insertion completes

**Exit Codes**:
- `0`: Success, text inserted
- `1`: Daemon not running
- `2`: No recording in progress
- `3`: Error during transcription/insertion

**Example**:
```bash
whi stop
```

**Hyprland Keybinding**:
```
bind = SUPER_SHIFT, R, exec, whi stop
```

---

### `whi status`

Check daemon and recording status.

**Output**:
```json
{
  "daemon_running": true,
  "recording": false,
  "model_loaded": true,
  "last_transcription": "Hello world",
  "text_insertion_methods": ["direct", "auto_paste", "clipboard"]
}
```

**Exit Codes**:
- `0`: Daemon running
- `1`: Daemon not running

**Example**:
```bash
whi status
```

---

### `whisper-daemon`

Start the background daemon (usually managed by systemd).

**Arguments**:
- `--config PATH`: Path to configuration file
- `--log-level LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR)

**Example**:
```bash
whisper-daemon --config ~/.config/whisper/config.yaml
```

**Systemd Management**:
```bash
# Start daemon
systemctl --user start whisper-daemon

# Stop daemon
systemctl --user stop whisper-daemon

# Enable auto-start
systemctl --user enable whisper-daemon

# Check status
systemctl --user status whisper-daemon

# View logs
journalctl --user -u whisper-daemon -f
```

---

## IPC Protocol

### Overview

Communication between CLI and daemon uses JSON messages over Unix domain socket.

**Socket Location**: `/tmp/whisper-daemon.sock`

**Transport**: Stream-based Unix socket

**Format**: JSON

### Message Structure

#### Request
```json
{
  "command": "string",
  "args": {
    "key": "value"
  }
}
```

#### Response
```json
{
  "status": "success|error",
  "message": "Human-readable message",
  "result": {
    "key": "value"
  }
}
```

### Commands

#### `start`

Start recording session.

**Request**:
```json
{
  "command": "start",
  "args": {}
}
```

**Response (Success)**:
```json
{
  "status": "success",
  "message": "Recording started",
  "result": {
    "session_id": "uuid-string",
    "start_time": "2025-01-15T10:30:00Z"
  }
}
```

**Response (Error)**:
```json
{
  "status": "error",
  "message": "Recording already in progress",
  "result": null
}
```

---

#### `stop`

Stop recording session and insert text.

**Request**:
```json
{
  "command": "stop",
  "args": {}
}
```

**Response (Success)**:
```json
{
  "status": "success",
  "message": "Recording stopped, text inserted",
  "result": {
    "transcription": "The transcribed text",
    "duration": 5.2,
    "insertion_method": "auto_paste",
    "word_count": 15
  }
}
```

**Response (Error)**:
```json
{
  "status": "error",
  "message": "No recording in progress",
  "result": null
}
```

---

#### `status`

Get daemon status.

**Request**:
```json
{
  "command": "status",
  "args": {}
}
```

**Response**:
```json
{
  "status": "success",
  "result": {
    "recording": false,
    "model_loaded": true,
    "model_name": "medium.en",
    "audio_device": "Default Microphone",
    "uptime": 3600,
    "memory_usage_mb": 1850,
    "sessions_count": 5,
    "text_injection_available": {
      "direct": true,
      "auto_paste": true,
      "clipboard": true
    }
  }
}
```

---

#### `shutdown`

Gracefully shut down daemon.

**Request**:
```json
{
  "command": "shutdown",
  "args": {}
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Daemon shutting down"
}
```

---

## Configuration API

### Configuration File Format

**Location**: `~/.config/whisper/config.yaml`

**Format**: YAML

### Configuration Schema

```yaml
model:
  size: string                    # "tiny" | "base" | "small" | "medium" | "large"
  language: string                # "en" for English only
  device: string                  # "cuda" for ROCm
  compute_type: string            # "float16" | "int8"
  model_path: string | null       # Optional custom model path

audio:
  sample_rate: integer            # 16000 (required for Whisper)
  channels: integer               # 1 (mono)
  chunk_duration: float           # Seconds per chunk (1.0 - 5.0)
  vad_aggressiveness: integer     # 0-3, higher = more aggressive
  device_index: integer | null    # null = default, or device index

gui:
  window_width: integer           # Pixels
  window_height: integer          # Pixels
  theme: string                   # "dark" | "light"
  font_size: integer              # Points
  show_waveform: boolean          # Show audio visualization
  show_timer: boolean             # Show recording timer

text_insertion:
  method: string                  # "auto" | "direct" | "auto_paste" | "clipboard"
  fallback_enabled: boolean       # Enable fallback to next method

ipc:
  socket_path: string             # Path to Unix socket

logging:
  level: string                   # "DEBUG" | "INFO" | "WARNING" | "ERROR"
  file: string                    # Path to log file (~ expanded)
```

### Example Configuration

```yaml
model:
  size: "medium"
  language: "en"
  device: "cuda"
  compute_type: "float16"

audio:
  chunk_duration: 2.5
  vad_aggressiveness: 3

gui:
  theme: "dark"
  font_size: 14
```

---

## Python API

For developers wanting to integrate Whisper Voice Input into other Python applications.

### IPCClient

```python
from whisper_daemon.ipc_server import IPCClient

client = IPCClient()

# Start recording
response = client.send_command("start")
if response["status"] == "success":
    print("Recording started")

# Stop recording
response = client.send_command("stop")
if response["status"] == "success":
    transcription = response["result"]["transcription"]
    print(f"Transcribed: {transcription}")

# Get status
response = client.send_command("status")
print(response["result"])
```

### TextInjector

```python
from whisper_daemon.text_injector import TextInjector, InsertionMethod

injector = TextInjector(preferred_method="auto")

# Insert text
try:
    method = injector.insert_text("Hello, world!")
    print(f"Text inserted using: {method.value}")
except Exception as e:
    print(f"Failed to insert text: {e}")

# Check status
status = injector.get_status()
print(f"Available methods: {status['available_methods']}")
```

### Config

```python
from whisper_daemon.config import Config

config = Config()

# Get configuration values
model_size = config.get("model", "size")
chunk_duration = config.get("audio", "chunk_duration")

# Set configuration values
config.set("gui", "theme", value="light")

# Save configuration
config.save()
```

---

## GUI Window Events

The GUI window emits events that can be captured by the daemon.

### Event Types

**transcription_updated**
- Emitted when new transcription text is available
- Payload: `{"text": "partial transcription"}`

**recording_started**
- Emitted when recording begins
- Payload: `{"timestamp": "2025-01-15T10:30:00Z"}`

**recording_stopped**
- Emitted when recording stops
- Payload: `{"duration": 5.2, "timestamp": "..."}`

**window_closed**
- Emitted when user closes window
- Payload: `{}`

**error**
- Emitted on error
- Payload: `{"error": "Error message"}`

---

## Error Codes

### CLI Exit Codes
- `0`: Success
- `1`: Daemon not running / not accessible
- `2`: Invalid command or state
- `3`: Execution error
- `4`: Configuration error

### IPC Error Types

**DaemonNotRunning**
```json
{
  "status": "error",
  "message": "Daemon is not running"
}
```

**AlreadyRecording**
```json
{
  "status": "error",
  "message": "Recording already in progress"
}
```

**NotRecording**
```json
{
  "status": "error",
  "message": "No recording in progress"
}
```

**ModelLoadError**
```json
{
  "status": "error",
  "message": "Failed to load Whisper model: ..."
}
```

**AudioCaptureError**
```json
{
  "status": "error",
  "message": "Failed to capture audio: ..."
}
```

**TextInsertionError**
```json
{
  "status": "error",
  "message": "Failed to insert text: ..."
}
```

---

## Logging

### Log Format

```
YYYY-MM-DD HH:MM:SS - module_name - LEVEL - Message
```

**Example**:
```
2025-01-15 10:30:45 - whisper_daemon.transcriber - INFO - Model loaded successfully
2025-01-15 10:30:50 - whisper_daemon.audio_capture - DEBUG - Audio chunk received: 2.0s
2025-01-15 10:30:52 - whisper_daemon.transcriber - INFO - Transcription: "Hello world"
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for serious problems

### Log Location

Default: `~/.local/share/whisper/whisper.log`

Configurable in `config.yaml`:
```yaml
logging:
  file: "~/.local/share/whisper/whisper.log"
```

### Log Rotation

- Maximum size: 10MB per file
- Keep last 5 rotated files
- Automatic rotation when limit reached
