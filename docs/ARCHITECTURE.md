# Murmur - Architecture Documentation

## Overview

Murmur is a real-time voice-to-text transcription tool designed for Linux Wayland systems. It provides system-wide speech-to-text capability through keyboard shortcuts configured in the window manager (Hyprland).

## System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                            │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │   Hyprland   │────────▶│  CLI Tool    │                  │
│  │  Keybinding  │         │  (whisper)   │                  │
│  └──────────────┘         └───────┬──────┘                  │
└────────────────────────────────────┼───────────────────────┘
                                     │ Unix Socket (IPC)
┌────────────────────────────────────┼───────────────────────┐
│                  Daemon Layer      │                        │
│                            ┌───────▼────────┐               │
│                            │  IPC Server    │               │
│                            └───────┬────────┘               │
│                                    │                        │
│            ┌───────────────────────┼──────────────────┐     │
│            │                       │                  │     │
│    ┌───────▼────────┐   ┌─────────▼───────┐  ┌──────▼───┐ │
│    │     Audio      │   │   Transcriber   │  │   Text   │ │
│    │    Capture     │   │   (Whisper)     │  │ Injector │ │
│    │  + VAD         │──▶│   ROCm GPU      │─▶│ 3-tier   │ │
│    └────────────────┘   └─────────────────┘  └──────────┘ │
│                                    │                        │
│                            ┌───────▼────────┐               │
│                            │  GUI Window    │               │
│                            │  (PyQt6)       │               │
│                            │  Waveform +    │               │
│                            │  Transcription │               │
│                            └────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. CLI Tool (`whisper`)
**Purpose**: User-facing command-line interface

**Responsibilities**:
- Accept user commands (`start`, `stop`, `status`)
- Communicate with daemon via Unix socket
- Display results and errors to user

**Technologies**: Python, argparse

#### 2. Background Daemon (`murmur-daemon`)
**Purpose**: Persistent service that manages transcription pipeline

**Responsibilities**:
- Keep Whisper model loaded in memory (avoid startup delay)
- Manage transcription sessions
- Coordinate between audio capture, transcription, and text insertion
- Control GUI window lifecycle

**Technologies**: Python, systemd user service

**Key Features**:
- Auto-starts on system boot
- Low idle memory footprint (<2GB)
- Fast response to commands (<100ms)

#### 3. IPC Server
**Purpose**: Inter-process communication between CLI and daemon

**Protocol**:
```json
Request:
{
  "command": "start|stop|status",
  "args": {}
}

Response:
{
  "status": "success|error",
  "message": "...",
  "result": {}
}
```

**Technologies**: Unix domain sockets (fast, local, secure)

**Socket Location**: `/tmp/murmur-daemon.sock`

#### 4. Audio Capture Module
**Purpose**: Capture and process audio input

**Responsibilities**:
- Capture audio from default/specified microphone
- Perform Voice Activity Detection (VAD)
- Split audio into chunks for streaming transcription
- Provide audio levels for waveform visualization

**Technologies**:
- `sounddevice`: Audio capture
- `webrtcvad`: Voice Activity Detection
- `numpy`: Audio buffer management

**Audio Pipeline**:
```
Microphone → sounddevice → VAD Filter → Chunks → Transcriber
                 ↓
             Waveform Data → GUI
```

**Configuration**:
- Sample rate: 16kHz (Whisper requirement)
- Channels: Mono
- Chunk duration: 2-3 seconds (balance latency vs accuracy)
- VAD aggressiveness: 3 (scale 0-3)

#### 5. Transcriber Module
**Purpose**: Convert audio to text using Whisper

**Responsibilities**:
- Load and manage Whisper model
- Process audio chunks in real-time
- Stream transcription results to GUI
- Handle errors and retries

**Technologies**:
- `faster-whisper`: Optimized Whisper implementation
- `ctranslate2-rocm`: AMD GPU acceleration (RX 6000/7000 series)

**Model Configuration**:
- Size: Medium (balanced accuracy/speed)
- Language: Auto-detect (99+ languages supported)
- Compute type: float16 (GPU)
- Device: CUDA (ROCm backend)

**Streaming Strategy**:
1. Receive 2-3 second audio chunks from VAD
2. Process chunk with Whisper (~0.5-1s on GPU)
3. Emit partial transcription to GUI
4. Accumulate full transcription for final insertion

#### 6. Text Injector Module
**Purpose**: Insert transcribed text into active application

**3-Tier Fallback System**:

1. **Direct Injection** (Primary)
   - Tool: `ydotool`
   - Method: Type text character-by-character
   - Pros: Works in most applications, feels natural
   - Cons: Requires /dev/uinput access, slower for long text

2. **Auto-Paste** (Secondary)
   - Tool: `ydotool`
   - Method: Copy to clipboard + simulate Ctrl+V
   - Pros: Fast, widely compatible
   - Cons: Overwrites clipboard temporarily

3. **Clipboard Only** (Tertiary)
   - Tool: `pyperclip`
   - Method: Copy to clipboard only
   - Pros: Always works, no permissions needed
   - Cons: Requires manual paste (Ctrl+V)

**Selection Logic**:
- Try methods in order until one succeeds
- Log which method was used
- Provide user feedback

#### 7. GUI Window Module
**Purpose**: Visual feedback during transcription

**Features**:
- Fixed center-screen positioning
- Real-time waveform visualization
- Timer (recording duration)
- Scrolling transcription text
- Minimal, non-intrusive design

**Technologies**:
- PyQt6 (Wayland support via layer-shell)
- Qt stylesheets for theming

**Window Behavior**:
- Opens on `murmur start`
- Shows real-time transcription as user speaks
- Stays open after recording stops (until `murmur stop` or user closes)
- Frameless, floating overlay

**UI Layout**:
```
┌─────────────────────────────────┐
│     🎤  Recording  [00:05]      │
├─────────────────────────────────┤
│   ╱╲   ╱╲╱╲  ╱╲   ╱╲           │ ← Waveform
│  ╱  ╲ ╱    ╲╱  ╲ ╱  ╲          │
├─────────────────────────────────┤
│ The quick brown fox jumps over │ ← Transcription
│ the lazy dog. This is a test   │
│ of the real-time...             │
└─────────────────────────────────┘
```

#### 8. Configuration System
**Purpose**: Manage user preferences

**Format**: YAML

**Locations** (checked in order):
1. `~/.config/murmur/config.yaml`
2. `~/.whisper/config.yaml`
3. `/etc/whisper/config.yaml`

**Structure**: See `config.example.yaml`

## Data Flow

### Starting a Recording Session

```
User presses keybinding
        ↓
Hyprland executes: whi start
        ↓
CLI sends "start" command to daemon (Unix socket)
        ↓
Daemon receives command via IPC server
        ↓
┌───────────────────────────────────────────────┐
│ Daemon launches three parallel threads:        │
│                                                 │
│ 1. Audio Capture Thread                        │
│    - Start capturing audio                     │
│    - Apply VAD                                 │
│    - Emit chunks + waveform data              │
│                                                 │
│ 2. Transcription Thread                        │
│    - Receive audio chunks                      │
│    - Process with Whisper                      │
│    - Emit partial transcriptions              │
│                                                 │
│ 3. GUI Thread (Qt event loop)                  │
│    - Create and show window                    │
│    - Update waveform visualization            │
│    - Display transcription text                │
│    - Update timer                              │
└───────────────────────────────────────────────┘
        ↓
CLI returns success to user
```

### Stopping a Recording Session

```
User presses keybinding
        ↓
Hyprland executes: whi stop
        ↓
CLI sends "stop" command to daemon
        ↓
Daemon receives command
        ↓
┌───────────────────────────────────────────────┐
│ Daemon stops threads and finalizes:            │
│                                                 │
│ 1. Stop audio capture                          │
│ 2. Process remaining audio chunks              │
│ 3. Get final transcription text                │
│ 4. Insert text using Text Injector            │
│    (try direct → auto-paste → clipboard)       │
│ 5. Keep GUI window open (user can review)     │
└───────────────────────────────────────────────┘
        ↓
CLI returns success/error to user
        ↓
Text appears in application
```

## Threading Model

### Daemon Process Threads

1. **Main Thread**
   - Runs IPC server
   - Handles commands
   - Coordinates other threads

2. **Audio Thread**
   - Continuous audio capture loop
   - VAD processing
   - Thread-safe queue for audio chunks

3. **Transcription Thread**
   - Consumes audio chunks from queue
   - Runs Whisper inference
   - Emits results via signals/callbacks

4. **GUI Thread** (Qt)
   - Qt event loop
   - UI updates
   - User interactions

**Synchronization**:
- Thread-safe queues for audio chunks
- Qt signals/slots for GUI updates
- Locks for shared state (recording status, transcription buffer)

## Performance Considerations

### Latency Targets
- CLI command to daemon response: <100ms
- Audio chunk to transcription: <1s
- Total speech to text display: <3s

### Memory Usage
- Idle daemon: <2GB (model loaded)
- Active transcription: <3GB
- GUI window: <100MB

### GPU Utilization
- Whisper inference: 30-50% GPU usage
- ROCm overhead: ~500MB VRAM
- Medium model: ~2GB VRAM

## Security Considerations

### Permissions Required
- **Audio capture**: Access to microphone
- **ydotool**: Access to `/dev/uinput` (requires user to be in `input` group)
- **Wayland**: Some compositors may restrict window positioning

### Data Privacy
- All processing is local (no network calls)
- No audio/transcription data is stored permanently
- Logs may contain partial transcriptions (configurable)

### Socket Security
- Unix socket with 0o600 permissions (owner-only)
- Socket in /tmp (system cleans on reboot)

## Error Handling

### Recovery Strategies

1. **Model Loading Failure**
   - Retry with CPU fallback
   - Log detailed error
   - Notify user via CLI

2. **Audio Capture Failure**
   - Try alternative audio backend
   - List available devices
   - Prompt user to check configuration

3. **Text Insertion Failure**
   - Fall back through 3-tier system
   - Always guarantee clipboard copy
   - Notify user of method used

4. **GPU Failure**
   - Automatically fall back to CPU
   - Warn user of performance impact
   - Suggest ROCm troubleshooting

### Logging Strategy
- All components log to `~/.local/share/murmur/whisper.log`
- Configurable log level (DEBUG, INFO, WARNING, ERROR)
- Log rotation (keep last 5 files, 10MB each)

## Future Enhancements

### Planned Features
- [x] Multi-language support (99+ languages with auto-detection)
- [ ] Custom model selection
- [ ] Punctuation and capitalization commands
- [ ] History of transcriptions
- [ ] In-window editing before insertion
- [ ] Configuration GUI
- [ ] Multiple audio device profiles

### Technical Debt
- [ ] Add comprehensive unit tests
- [ ] Performance profiling and optimization
- [ ] Better error messages and user guidance
- [ ] Automated installation script
- [ ] Package for AUR

## Dependencies

### System Requirements
- Linux with Wayland compositor
- AMD GPU (RX 6000/7000 series recommended)
- ROCm 5.x+ installed
- Python 3.10+
- ydotool package

### Python Dependencies
See `pyproject.toml` and `requirements.txt`

### External Tools
- `ydotool`: Wayland input injection
- `systemd`: Daemon management

## Development Setup

See `docs/DEVELOPMENT.md` for detailed setup instructions.

## References

- [faster-whisper documentation](https://github.com/guillaumekln/faster-whisper)
- [ydotool documentation](https://github.com/ReimuNotMoe/ydotool)
- [PyQt6 Wayland support](https://doc.qt.io/qt-6/wayland.html)
- [Hyprland keybindings](https://wiki.hyprland.org/Configuring/Binds/)
