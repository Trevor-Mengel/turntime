# Changelog

## [Unreleased]

### Changed
- Histogram redesigned from duration-distribution bins to a 12-week time-series chart showing average turn duration per week
- Duration formatting changed from "m" to "mins" (e.g., "6.8mins" instead of "6.8m")
- Badge section now includes "Avg. Turn Duration (Claude Code)" title, a link to the TurnTime repo, and a link to Anthropic's research on agent autonomy
- `build_histogram_data()` now accepts `num_weeks` parameter instead of `period`
- Stats header in histogram uses all-time stats instead of period-specific stats

### Added
- `sync-cron.sh` — reusable cron/launchd wrapper script for automated syncing
- Beginner-friendly setup guide for creating and configuring a GitHub profile repo
- Troubleshooting section in README
- Gist pinning instructions
- Windows manual install instructions
- launchd plist template inline in README

### Removed
- `--period` flag from `turntime sync` (histogram always shows last 12 weeks)
- `--histogram-period` flag from `parse_sessions.py` (replaced by `--num-weeks`)
- `histogram_period`, `exclude_projects`, `max_turn_duration_seconds`, `min_turn_duration_seconds` config keys (were never implemented)

## [1.0.0] - 2025-02-19

### Added
- Initial release
- Parse Claude Code JSONL session logs into turn duration metrics
- Generate shields.io badges with Tailwind-inspired color scale
- Generate SVG histogram with dark/light theme support
- Push stats to GitHub Gist for dynamic badges
- Update profile README with badge and histogram injection
- CLI with `init`, `sync`, and `stats` subcommands
- `setup.sh` one-liner installer
- GitHub Actions workflow for daily automated updates
