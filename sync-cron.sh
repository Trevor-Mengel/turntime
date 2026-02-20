#!/bin/bash
# turntime sync - cron/launchd wrapper
# Syncs Claude Code turn stats to GitHub Gist and profile README
#
# Usage:
#   1. Copy this script somewhere convenient (e.g., ~/.local/share/turntime/)
#   2. Create ~/.config/turntime/.env with: GH_TOKEN=your_github_token
#   3. Add to crontab: 0 */6 * * * /path/to/sync-cron.sh >> ~/.config/turntime/logs/sync.log 2>&1

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

TURNTIME_DIR="${HOME}/.local/share/turntime"
ENV_FILE="${HOME}/.config/turntime/.env"

# Load GitHub token from env file (avoids keychain prompts in non-interactive shells)
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "ERROR: $ENV_FILE not found"
    echo "Create it with: echo 'GH_TOKEN=your_token' > $ENV_FILE"
    exit 1
fi

# Create log directory if needed
mkdir -p "${HOME}/.config/turntime/logs"

cd "$TURNTIME_DIR" || { echo "ERROR: turntime not found at $TURNTIME_DIR"; exit 1; }

echo "$(date '+%Y-%m-%d %H:%M:%S') — turntime sync starting"
python3 scripts/turntime_cli.py sync 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') — turntime sync finished (exit $?)"
