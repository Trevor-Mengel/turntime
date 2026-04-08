# Changelog

## [Unreleased]

### Fixed
- Sync now runs `git pull --rebase --autostash` before pushing to the profile repo, preventing silent push failures when the remote has diverged

### Removed
- GitHub Actions workflow recommendation from README (the Action operated on stale data and caused push divergence that silently broke syncing)

### Changed
- Histogram redesigned from duration-distribution bins to a 12-week time-series chart showing average turn duration per week
- Duration formatting changed from "m" to "mins" (e.g., "6.8mins" instead of "6.8m")
- Badge section now includes "Avg. Turn Duration (Claude Code)" title, a link to the TurnTime repo, and a link to Anthropic's research on agent autonomy
- `build_histogram_data()` now accepts `num_weeks` parameter instead of `period`
- Stats header in histogram uses all-time stats instead of period-specific stats

### Added
- Frequency distribution chart type showing turn counts bucketed by duration range (<1 min, 1–2 min, 2–5 min, 5–10 min, 10–20 min, 20+ min)
- `--chart-type` flag for `turntime sync` (`timeseries`, `distribution`, `both`) and `generate_histogram.py`
- `chart_type` config option (defaults to `timeseries` for backward compatibility)
- `build_distribution_data()` function in `parse_sessions.py`
- `generate_distribution_svg()` function in `generate_histogram.py`
- `<!-- turntime distribution -->` comment markers for profile README injection
- `distribution` key in JSON stats output
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
