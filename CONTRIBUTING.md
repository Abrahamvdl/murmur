# Contributing to Whisper Voice Input

Thank you for your interest in contributing to Whisper Voice Input! This document provides guidelines and information for contributors.

---

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions. We're building this together!

---

## How to Contribute

### Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, GPU, ROCm version, Python version)
   - Relevant logs (`journalctl --user -u whisper-daemon`)

### Suggesting Features

1. **Check the roadmap** in README.md
2. **Open an issue** labeled "enhancement" with:
   - Clear description of the feature
   - Use cases and benefits
   - Possible implementation approach (optional)

### Contributing Code

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following our style guide
4. **Test your changes** thoroughly
5. **Commit with conventional commits**:
   ```
   feat: add support for custom models
   fix: resolve VAD false positives
   docs: update installation guide
   ```
6. **Push and create a Pull Request**

---

## Development Setup

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.

**Quick Start**:

```bash
# Clone your fork
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
```

---

## Code Style

### Python

We follow PEP 8 with these tools:

**Formatting**:
```bash
black .
```

**Linting**:
```bash
flake8 whisper_daemon/ whisper_gui/ whisper_cli/
```

**Type Hints** (encouraged but not required):
```python
def process_audio(audio_data: np.ndarray, sample_rate: int = 16000) -> str:
    """Process audio and return transcription."""
    ...
```

### Documentation

**Docstrings** (Google style):
```python
def my_function(param1: str, param2: int) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When this happens
    """
    ...
```

**Comments**:
- Explain WHY, not WHAT
- Keep comments up-to-date with code changes

---

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Build, dependencies

**Examples**:
```
feat(transcriber): add support for large-v3 model
fix(audio): resolve microphone permission issues on Ubuntu
docs(api): update IPC protocol examples
refactor(daemon): simplify session state management
```

---

## Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new features (when test suite exists)
3. **Update CHANGELOG.md** with your changes
4. **Ensure all checks pass**:
   - Code formatting (black)
   - Linting (flake8)
   - Tests (pytest, when available)

5. **Request review** from maintainers
6. **Address feedback** promptly
7. **Squash commits** if requested

### PR Title Format

Use conventional commit format:
```
feat: add multi-language support
fix: resolve clipboard paste issues
```

---

## Areas for Contribution

### High Priority

- [ ] **Unit Tests**: Add comprehensive test coverage
- [ ] **Multi-language Support**: Extend beyond English
- [ ] **Custom Model Support**: Allow user-provided models
- [ ] **Performance Optimization**: Reduce latency, improve GPU usage
- [ ] **Error Handling**: Improve error messages and recovery

### Medium Priority

- [ ] **GUI Improvements**: Better styling, animations
- [ ] **Configuration GUI**: Visual config editor
- [ ] **Transcription History**: Save past transcriptions
- [ ] **Voice Commands**: Punctuation, formatting commands
- [ ] **Better Documentation**: More examples, tutorials

### Low Priority

- [ ] **AUR Package**: Package for Arch User Repository
- [ ] **Flatpak Support**: Distribution via Flatpak
- [ ] **Alternative Compositors**: Test on Sway, GNOME, KDE
- [ ] **Internationalization**: Translate UI to other languages

---

## Testing Guidelines

### Manual Testing Checklist

Before submitting a PR:

- [ ] Daemon starts without errors
- [ ] CLI commands work (`start`, `stop`, `status`)
- [ ] GUI window appears and displays correctly
- [ ] Audio capture works
- [ ] Transcription is accurate
- [ ] Text insertion works (all 3 methods)
- [ ] Configuration changes are respected
- [ ] No regressions in existing features

### Writing Tests (Future)

When the test suite is available:

```python
# tests/test_ipc_server.py
def test_start_command():
    """Test that start command initializes recording."""
    client = IPCClient()
    response = client.send_command("start")
    assert response["status"] == "success"
```

---

## Getting Help

- **GitHub Discussions**: Ask questions, share ideas
- **GitHub Issues**: Report bugs, request features
- **Documentation**: Check docs/ folder
- **Development Guide**: See docs/DEVELOPMENT.md

---

## Recognition

Contributors will be:
- Listed in README.md (if significant contributions)
- Credited in release notes
- Mentioned in commit messages

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you're unsure about anything, don't hesitate to ask! Open an issue or discussion, and we'll help you get started.

**Thank you for contributing!** 🎉
