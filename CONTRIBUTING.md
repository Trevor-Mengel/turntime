# Contributing to turntime

Thanks for your interest in contributing! Here's how to get started.

## Development setup

```bash
git clone https://github.com/Trevor-Mengel/turntime.git
cd turntime

# Run against your own Claude Code logs
python3 scripts/turntime_cli.py stats

# Run against test fixtures
python3 scripts/parse_sessions.py --claude-dir tests/fixtures --verbose
```

No external dependencies are required — turntime uses only the Python standard library.

## Project structure

```
scripts/
  turntime_cli.py         # CLI entry point (init, sync, stats commands)
  parse_sessions.py       # JSONL log parser and stats aggregation
  generate_histogram.py   # SVG histogram chart generator
  generate_badges.py      # shields.io badge URL generator
tests/
  fixtures/               # Test JSONL session files
assets/
  example-histogram.svg   # Example output for README
turntime.py               # Wrapper entry point
setup.sh                  # One-liner install script
```

## Guidelines

- **Python 3.9+** — use `from __future__ import annotations` in every file for `X | Y` type hint compatibility
- **No external dependencies** — standard library only
- **Error messages** — use friendly `❌`/`⚠️` prefixed messages, not raw tracebacks
- **Test with real logs** — run `python3 scripts/turntime_cli.py stats` to verify changes work against real Claude Code session data
- **Test with fixtures** — use `tests/fixtures/` for automated testing

## Areas where help is appreciated

- Additional chart types and visualizations
- Platform testing (Windows, Linux)
- `pip install turntime` packaging
- Leaderboard backend and frontend
- Test coverage

## Submitting changes

1. Fork the repo
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes and test them
4. Commit with a descriptive message
5. Open a pull request

## Code style

- Follow existing patterns in the codebase
- Use type hints where practical
- Keep functions focused and well-documented with docstrings
