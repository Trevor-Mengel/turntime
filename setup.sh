#!/bin/bash
# turntime - Quick setup script
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USER/turntime/main/setup.sh | bash

set -e

TURNTIME_DIR="${HOME}/.local/share/turntime"
BIN_DIR="${HOME}/.local/bin"

echo "⏱  Installing turntime..."
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required. Install it first."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python ${PY_VERSION} found"

# Check for Claude Code
CLAUDE_DIR="${HOME}/.claude/projects"
if [ -d "$CLAUDE_DIR" ]; then
    SESSION_COUNT=$(find "$CLAUDE_DIR" -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
    echo "✅ Claude Code found (${SESSION_COUNT} session files)"
else
    echo "⚠️  Claude Code projects directory not found at ${CLAUDE_DIR}"
    echo "   turntime will work once you run Claude Code at least once."
fi

# Clone or update
if [ -d "$TURNTIME_DIR" ]; then
    echo "🔄 Updating turntime..."
    cd "$TURNTIME_DIR"
    git pull --quiet
else
    echo "📦 Cloning turntime..."
    mkdir -p "$(dirname "$TURNTIME_DIR")"
    git clone --quiet https://github.com/YOUR_USER/turntime.git "$TURNTIME_DIR"
fi

# Create symlink
mkdir -p "$BIN_DIR"
cat > "${BIN_DIR}/turntime" << 'EOF'
#!/bin/bash
exec python3 "${HOME}/.local/share/turntime/turntime.py" "$@"
EOF
chmod +x "${BIN_DIR}/turntime"

# Ensure ~/.local/bin is in PATH
if ! echo "$PATH" | grep -q "${BIN_DIR}"; then
    SHELL_RC=""
    if [ -f "${HOME}/.zshrc" ]; then
        SHELL_RC="${HOME}/.zshrc"
    elif [ -f "${HOME}/.bashrc" ]; then
        SHELL_RC="${HOME}/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        echo "" >> "$SHELL_RC"
        echo '# turntime' >> "$SHELL_RC"
        echo "export PATH=\"${BIN_DIR}:\$PATH\"" >> "$SHELL_RC"
        echo "✅ Added ${BIN_DIR} to PATH in ${SHELL_RC}"
    else
        echo "⚠️  Add ${BIN_DIR} to your PATH manually"
    fi
fi

echo ""
echo "✅ turntime installed!"
echo ""
echo "Getting started:"
echo "  turntime stats     # View your stats in the terminal"
echo "  turntime init      # Set up GitHub Gist for badges/charts"
echo "  turntime sync      # Parse logs and push to GitHub"
echo ""
echo "For automated updates, see: ${TURNTIME_DIR}/README.md"
