# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

turntime is a Python CLI tool that parses Claude Code session logs, calculates turn-duration metrics, generates SVG histograms and shields.io badges, and syncs them to GitHub Gists for profile display. It uses **only the Python standard library** (no external dependencies). Requires Python 3.9+.

## Commands

```bash
# View stats in terminal
python3 scripts/turntime_cli.py stats
python3 scripts/turntime_cli.py stats --project myproject

# First-time setup (GitHub auth, Gist creation)
python3 scripts/turntime_cli.py init

# Generate stats locally without pushing
python3 scripts/turntime_cli.py sync --local-only

# Full sync (parse → generate → push to Gist → update profile README)
python3 scripts/turntime_cli.py sync

# Run individual scripts directly
python3 scripts/parse_sessions.py --output stats.json --verbose
python3 scripts/generate_histogram.py stats.json --output histogram.svg --theme auto
python3 scripts/generate_badges.py stats.json --format markdown

# Test against fixture data (no real Claude logs needed)
python3 scripts/parse_sessions.py --claude-dir tests/fixtures --verbose
```

There is no linter, formatter, or test runner configured.

## Architecture

**Data flow**: Parse JSONL → Aggregate stats → Generate SVG/badges/JSON → Push to Gist → Update profile README

### Key modules (all in `scripts/`)

- **turntime_cli.py** — CLI entry point with three subcommands: `init`, `sync`, `stats`. Handles GitHub auth (via `gh` CLI or `GITHUB_TOKEN`/`GH_TOKEN` env vars), Gist CRUD, and profile README injection between comment markers.
- **parse_sessions.py** — Parses JSONL session files from `~/.claude/projects/`. Core data structures are `Turn` and `TurnStats` dataclasses. A "turn" spans from a genuine user prompt to the final assistant response, including intermediate tool-use cycles. Tool results (role=user with tool_result content) are NOT turn boundaries. Turns under 5 seconds are filtered out. Aggregates into periods: today, week, month, quarter, year, all-time.
- **generate_histogram.py** — Produces responsive SVG with `prefers-color-scheme` media query for GitHub dark/light themes. Uses 11 duration bins from <15s to >2h.
- **generate_badges.py** — Generates shields.io URLs with a Tailwind-inspired color scale based on duration tiers. Supports dynamic badges via Gist endpoints.

### Entry points

- `turntime.py` — wrapper that imports `scripts/turntime_cli.py`
- Installed as symlink at `~/.local/bin/turntime` via `setup.sh`

### Configuration

Stored at `~/.config/turntime/config.json`. See `config.example.json` for the schema. Key options: `gist_id`, `profile_repo`, `histogram_period`, `badge_periods`, `theme`, `exclude_projects`.

## Conventions

- Every Python file must use `from __future__ import annotations` for `X | Y` type hint compatibility with Python 3.9
- Zero external dependencies — standard library only
- User-facing error messages use emoji prefixes (`✅`, `❌`, `⚠️`) instead of raw tracebacks
- Data structures use `dataclasses`; paths use `pathlib.Path`
- GitHub API calls use `urllib.request` (not requests); subprocess calls run `gh` CLI commands
