#!/usr/bin/env python3
"""turntime - Track and display your Claude Code turn duration stats."""

import sys
from pathlib import Path

# Ensure scripts directory is importable
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from scripts.turntime_cli import main

if __name__ == '__main__':
    main()
