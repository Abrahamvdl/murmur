#!/bin/bash

# Whisper Voice Input Installation Script
# This script automates the installation process for Arch Linux and derivatives

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
 __        ___     _
 \ \      / / |__ (_)___ _ __   ___ _ __
  \ \ /\ / /| '_ \| / __| '_ \ / _ \ '__|
   \ V  V / | | | | \__ \ |_) |  __/ |
    \_/\_/  |_| |_|_|___/ .__/ \___|_|
                        |_|
    Voice Input for Linux
EOF
echo -e "${NC}"

info "Starting installation..."

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "This script is designed for Linux systems only"
fi

# Detect distribution
if [ -f /etc/arch-release ]; then
    DISTRO="arch"
elif [ -f /etc/debian_version ]; then
    DISTRO="debian"
elif [ -f /etc/fedora-release ]; then
    DISTRO="fedora"
else
    warning "Unknown distribution. Proceeding with manual installation..."
    DISTRO="unknown"
fi

info "Detected distribution: $DISTRO"

# Check for required system dependencies
info "Checking system dependencies..."

MISSING_DEPS=()

if ! check_command python3; then
    MISSING_DEPS+=("python3")
fi

if ! check_command pip; then
    MISSING_DEPS+=("python-pip")
fi

if ! check_command git; then
    MISSING_DEPS+=("git")
fi

if ! check_command ydotool; then
    MISSING_DEPS+=("ydotool")
fi

# Install missing dependencies based on distro
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    info "Missing dependencies: ${MISSING_DEPS[*]}"

    if [ "$DISTRO" = "arch" ]; then
        info "Installing dependencies with pacman..."
        sudo pacman -S --needed python python-pip git ydotool portaudio qt6-base qt6-wayland

        # Check for ROCm
        if ! check_command rocminfo; then
            warning "ROCm not found. Installing rocm-hip-sdk..."
            sudo pacman -S --needed rocm-hip-sdk
        fi

    elif [ "$DISTRO" = "debian" ]; then
        info "Installing dependencies with apt..."
        sudo apt update
        sudo apt install -y python3 python3-pip git portaudio19-dev qt6-base-dev qt6-wayland

        warning "ydotool may need to be built from source on Debian/Ubuntu"

    else
        error "Please install the following dependencies manually: ${MISSING_DEPS[*]}"
    fi
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    error "Python 3.10+ required. Found: $PYTHON_VERSION"
fi

success "Python $PYTHON_VERSION found"

# Create virtual environment (optional but recommended)
if [ ! -d "venv" ]; then
    info "Creating virtual environment..."
    python3 -m venv venv
    success "Virtual environment created"
fi

info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
info "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
info "Installing Python dependencies..."
pip install -r requirements.txt

# Install ROCm-optimized ctranslate2
info "Installing ctranslate2-rocm..."
pip install ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/

# Install whisper package
info "Installing whisper-voice-input..."
pip install -e .

success "Python packages installed"

# Configure ydotool
info "Configuring ydotool..."

# Check if user is in input group
if ! groups | grep -q input; then
    warning "Adding user to 'input' group (required for ydotool)..."
    sudo usermod -aG input $USER
    warning "You will need to log out and back in for group changes to take effect"
fi

# Enable ydotool service
info "Enabling ydotool service..."
systemctl --user enable --now ydotool.service || warning "Could not enable ydotool service"

# Create config directory
info "Setting up configuration..."
CONFIG_DIR="$HOME/.config/whisper"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cp config.example.yaml "$CONFIG_DIR/config.yaml"
    success "Configuration file created at $CONFIG_DIR/config.yaml"
else
    info "Configuration file already exists"
fi

# Install systemd service
info "Installing systemd service..."
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

# Update service file with correct path
WHISPER_DAEMON_PATH="$(pwd)/venv/bin/whisper-daemon"
sed "s|%h/.local/bin/whisper-daemon|$WHISPER_DAEMON_PATH|g" systemd/whisper-daemon.service > "$SYSTEMD_USER_DIR/whisper-daemon.service"

# Reload systemd
systemctl --user daemon-reload

success "Systemd service installed"

# Enable and start service
info "Enabling whisper-daemon service..."
systemctl --user enable whisper-daemon

info "Starting whisper-daemon service..."
systemctl --user start whisper-daemon

# Wait a moment for daemon to start
sleep 2

# Check if daemon is running
if systemctl --user is-active --quiet whisper-daemon; then
    success "Daemon is running!"
else
    warning "Daemon may have failed to start. Check logs with: journalctl --user -u whisper-daemon"
fi

# Create logs directory
mkdir -p "$HOME/.local/share/whisper"

# Print next steps
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
info "Next steps:"
echo ""
echo "1. Add keybindings to Hyprland config (~/.config/hypr/hyprland.conf):"
echo -e "   ${YELLOW}bind = SUPER SHIFT, Space, exec, $(pwd)/venv/bin/whi start${NC}"
echo -e "   ${YELLOW}bind = SUPER SHIFT, R, exec, $(pwd)/venv/bin/whi stop${NC}"
echo ""
echo "2. Reload Hyprland:"
echo -e "   ${YELLOW}hyprctl reload${NC}"
echo ""
echo "3. Test the installation:"
echo -e "   ${YELLOW}$(pwd)/venv/bin/whi status${NC}"
echo ""
echo "4. Check daemon logs:"
echo -e "   ${YELLOW}journalctl --user -u whisper-daemon -f${NC}"
echo ""
echo "5. (Optional) If you were added to the input group, log out and back in"
echo ""
echo "For more information, see: docs/INSTALLATION.md"
echo ""

success "Installation completed successfully!"
