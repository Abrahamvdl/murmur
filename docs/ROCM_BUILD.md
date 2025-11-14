# Building CTranslate2 with ROCm Support

This guide explains how to build CTranslate2 with ROCm support for AMD GPUs when pre-built wheels are unavailable.

## Prerequisites

### System Requirements
- AMD GPU (RDNA 2/3 recommended: RX 6000/7000 series)
- ROCm 6.0+ installed
- Arch Linux, Ubuntu 22.04+, or similar

### Build Dependencies

**Arch Linux:**
```bash
sudo pacman -S cmake clang hip-runtime-amd rocm-hip-sdk base-devel
```

**Ubuntu:**
```bash
sudo apt install cmake clang libhip-dev rocm-dev build-essential
```

### Python Dependencies
```bash
pip install pybind11 numpy pyyaml
```

## Build Steps

### 1. Identify Your GPU Architecture

Check your GPU model and architecture:
```bash
rocminfo | grep -E "(Marketing Name|gfx)"
```

Common architectures:
- **RX 6000 series**: gfx1030, gfx1031, gfx1032
- **RX 7000 series**: gfx1100, gfx1101, gfx1102

### 2. Clone the Repository

```bash
cd ~/Workspace/Linux/Whisper  # Or your preferred location
git clone https://github.com/arlo-phoenix/CTranslate2-rocm.git --recurse-submodules --depth 1
cd CTranslate2-rocm
```

### 3. Configure the Build

```bash
mkdir build && cd build

# Set your GPU architecture (replace gfx1030 with your arch)
export PYTORCH_ROCM_ARCH=gfx1030

# Set compilers
export CXX=clang++
export HIPCXX=/opt/rocm/lib/llvm/bin/clang
export HIP_PATH=/opt/rocm

# Configure with CMake
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=$HOME/.local \
      -DWITH_MKL=OFF \
      -DWITH_HIP=ON \
      -DWITH_CUDNN=ON \
      -DBUILD_TESTS=OFF \
      -DOPENMP_RUNTIME=COMP \
      ..
```

**Configuration Options:**
- `CMAKE_INSTALL_PREFIX`: Installation directory (default: `$HOME/.local`)
- `WITH_HIP=ON`: Enable ROCm/HIP support
- `WITH_MKL=OFF`: Disable Intel MKL (not needed for AMD)
- `DOPENMP_RUNTIME=COMP`: Use compiler OpenMP runtime
- `DBUILD_TESTS=OFF`: Skip building tests (faster)

### 4. Build the Library

```bash
# Build with parallel jobs (adjust -j based on your CPU cores)
make -j$(nproc)
```

**Build Time:**
- 6 cores: ~10-15 minutes
- 4 cores: ~15-20 minutes
- 2 cores: ~30-40 minutes

**Note:** The build may show warnings about deprecated operators. These are harmless.

### 5. Install C++ Library and Headers

```bash
# Copy library files
cp libctranslate2.so* ~/.local/lib/

# Copy headers
mkdir -p ~/.local/include
cp -r ../include/ctranslate2 ~/.local/include/
cp -r ../include/half_float ~/.local/include/
cp -r ../include/nlohmann ~/.local/include/
```

### 6. Build Python Package

```bash
cd ../python

# Activate your virtual environment
source /path/to/your/venv/bin/activate

# Set library and include paths
export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH
export CFLAGS="-I$HOME/.local/include"
export CXXFLAGS="-I$HOME/.local/include"
export LDFLAGS="-L$HOME/.local/lib -Wl,-rpath,$HOME/.local/lib"

# Install without build isolation (to use system pybind11)
pip install --no-build-isolation .
```

### 7. Verify Installation

```bash
python -c "import ctranslate2; print(f'CTranslate2 version: {ctranslate2.__version__}')"
```

Expected output:
```
CTranslate2 version: 4.1.0
```

## Usage

### Set Library Path

The daemon needs to find the ROCm-enabled library. Add this to your daemon startup:

**Option 1: Export before running**
```bash
export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH
python -m murmur_daemon.daemon
```

**Option 2: Add to systemd service**

Edit `~/.config/systemd/user/murmur-daemon.service`:
```ini
[Service]
Environment="LD_LIBRARY_PATH=/home/YOUR_USERNAME/.local/lib"
ExecStart=/home/YOUR_USERNAME/.local/bin/murmur-daemon
```

**Option 3: Add to shell profile**

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH
```

### Verify GPU Usage

```bash
# Start the daemon
whi status

# Check GPU usage
rocm-smi --showuse

# Check logs for "Model loaded successfully on cuda"
journalctl --user -u murmur-daemon -f
```

## Troubleshooting

### Build Fails with "HIP_PATH not found"

Make sure ROCm is installed and HIP_PATH is set:
```bash
export HIP_PATH=/opt/rocm
```

### Python Build Can't Find Headers

Ensure all headers are copied:
```bash
ls ~/.local/include/ctranslate2  # Should show header files
ls ~/.local/include/half_float   # Should show half.hpp
```

### Library Not Found at Runtime

Add library path permanently:
```bash
echo 'export LD_LIBRARY_PATH=$HOME/.local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### Model Still Loads on CPU

Check daemon logs for errors:
```bash
journalctl --user -u murmur-daemon -n 50
```

Common causes:
- LD_LIBRARY_PATH not set
- Wrong GPU architecture compiled
- ROCm drivers not properly installed

### GPU Architecture Mismatch

If you see "unsupported architecture" errors:
1. Verify your GPU arch with `rocminfo`
2. Clean and rebuild with correct `PYTORCH_ROCM_ARCH`:
   ```bash
   rm -rf build
   mkdir build && cd build
   export PYTORCH_ROCM_ARCH=gfx1031  # Your actual arch
   # ... repeat configure and build steps
   ```

## Performance Verification

After successful build:

**Check Model Load Time:**
```bash
# Watch daemon startup
journalctl --user -u murmur-daemon -f
```

Expected: "Model loaded successfully on cuda" with ~15-20 second load time for medium model.

**Check GPU Utilization:**
```bash
# During transcription
watch -n 1 rocm-smi --showuse
```

Expected: GPU usage spikes to 30-80% during transcription.

**Check Transcription Speed:**

The daemon logs show Real-Time Factor (RTF):
- RTF < 1.0: Faster than real-time (good!)
- RTF = 1.0: Real-time speed
- RTF > 1.0: Slower than real-time (investigate)

## Cleanup

To remove build artifacts:
```bash
cd ~/Workspace/Linux/Whisper
rm -rf CTranslate2-rocm
```

The installed files in `~/.local/` should remain.

## Alternative: Pre-built Wheels

If `wheels.arlo-phoenix.com` becomes available again, you can install directly:
```bash
pip install ctranslate2-rocm --extra-index-url https://wheels.arlo-phoenix.com/
```

However, building from source ensures compatibility with your specific GPU architecture and ROCm version.

## References

- [CTranslate2-rocm GitHub](https://github.com/arlo-phoenix/CTranslate2-rocm)
- [AMD ROCm Documentation](https://rocm.docs.amd.com/)
- [CTranslate2 Official Docs](https://opennmt.net/CTranslate2/)
