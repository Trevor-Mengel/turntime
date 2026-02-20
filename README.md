# ⏱ turntime

**Track and display your Claude Code turn duration on your GitHub profile.**

turntime parses your local Claude Code session logs, calculates how long each prompt→response turn takes, and generates beautiful badges and histogram charts you can embed in your GitHub profile README — updated automatically on a schedule.

<picture>
  <img src="assets/example-histogram.svg" alt="Example turn duration histogram" />
</picture>

<!-- turntime badges -->
![⏱ This Month](https://img.shields.io/badge/%E2%8F%B1%20This%20Month-1.3m-yellow?style=flat-square)
![⏱ All Time](https://img.shields.io/badge/%E2%8F%B1%20All%20Time-1.3m-yellow?style=flat-square)
<!-- /turntime badges -->

## What it measures

**Turn duration** = the time from when you send a prompt to when Claude finishes its complete response (including all tool uses).

A "turn" starts when a `user` message is logged and ends at the final `assistant` message before the next `user` message. Turns shorter than 0.5s (system messages) and longer than 30min (idle sessions) are automatically filtered out.

## Quick start

```bash
# Clone the repo
git clone https://github.com/Trevor-Mengel/turntime.git
cd turntime

# View your stats immediately (no setup needed)
python3 scripts/turntime_cli.py stats
```

That's it — you'll see a table like this:

```
⏱  turntime stats (847 turns from 93 sessions)

Period                Avg   Median      P90      Min      Max    Count
────────────────────────────────────────────────────────────────────────
Today               18.3s    12.1s    45.2s     2.1s    62.0s       23
This Week           24.7s    15.8s    58.3s     1.2s   185.0s      142
This Month          22.1s    14.2s    52.0s     0.8s   210.5s      387
All Time            26.4s    16.5s    61.2s     0.5s   450.3s      847
```

## Setup for GitHub profile

### 1. Initialize

```bash
python3 scripts/turntime_cli.py init
```

This will:
- Verify Claude Code logs exist on your machine
- Authenticate with GitHub (via `gh` CLI or `GITHUB_TOKEN`)
- Create a public Gist to host your stats
- Save config to `~/.config/turntime/config.json`

### 2. Sync your stats

```bash
python3 scripts/turntime_cli.py sync
```

This parses your logs, generates a histogram SVG and badge data, and pushes everything to your Gist.

### 3. Add to your profile README

Add these placeholder comments to your GitHub profile `README.md`:

```markdown
<!-- turntime badges -->
<!-- /turntime badges -->

<!-- turntime histogram -->
<!-- /turntime histogram -->
```

The `sync` command will fill these in with your actual stats.

### 4. Automate with cron (local)

Add to your crontab to sync every 6 hours:

```bash
crontab -e
```

```cron
0 */6 * * * cd /path/to/turntime && python3 scripts/turntime_cli.py sync 2>/dev/null
```

### 5. Automate with GitHub Actions (optional)

If you commit your `turntime-stats.json` to your profile repo, you can use the included GitHub Action to regenerate the histogram and update your README daily:

1. Copy `.github/workflows/update-stats.yml` to your profile repo
2. Add `TURNTIME_GIST_ID` as a repository secret
3. The action runs daily at 6am UTC (customizable)

## CLI reference

```bash
# Show stats in terminal
python3 turntime.py stats
python3 turntime.py stats --project myproject    # filter by project name

# Generate files locally without pushing
python3 turntime.py sync --local-only
python3 turntime.py sync --local-only --period week --theme dark

# Full sync: parse → generate → push to Gist → update README
python3 turntime.py sync

# Initialize configuration
python3 turntime.py init
```

### Individual scripts

The scripts can also be used independently:

```bash
# Parse sessions to JSON
python3 scripts/parse_sessions.py --output stats.json --verbose

# Generate histogram SVG
python3 scripts/generate_histogram.py stats.json --output histogram.svg --theme auto

# Generate badge markdown
python3 scripts/generate_badges.py stats.json --format markdown
```

## Configuration

Config is stored at `~/.config/turntime/config.json`:

```json
{
  "gist_id": "abc123...",
  "profile_repo": "/Users/you/you",
  "histogram_period": "month",
  "badge_periods": ["month", "all"],
  "theme": "auto",
  "exclude_projects": [],
  "max_turn_duration_seconds": 1800,
  "min_turn_duration_seconds": 0.5
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `gist_id` | GitHub Gist ID for hosting stats | Set by `init` |
| `profile_repo` | Local path to your profile repo | Optional |
| `histogram_period` | Period for histogram chart | `"month"` |
| `badge_periods` | Which periods to show as badges | `["month", "all"]` |
| `theme` | SVG theme: `auto`, `dark`, `light` | `"auto"` |
| `exclude_projects` | Project names to skip | `[]` |
| `max_turn_duration_seconds` | Max turn duration to include | `1800` |
| `min_turn_duration_seconds` | Min turn duration to include | `0.5` |

## How it works

1. **Reads** Claude Code session logs from `~/.claude/projects/**/*.jsonl`
2. **Parses** each JSONL file to extract timestamped user/assistant message pairs
3. **Calculates** turn duration as `assistant_final_timestamp - user_timestamp`
4. **Aggregates** into time periods (day, week, month, quarter, year, all-time)
5. **Generates** shields.io badge URLs and an SVG histogram chart
6. **Pushes** to a GitHub Gist (for dynamic badge endpoints)
7. **Updates** your profile README with badge images and the histogram

### Privacy

turntime **never** reads your prompts or code. It only extracts:
- Timestamps (to calculate duration)
- Message roles (to identify user vs assistant turns)
- Token counts (for optional usage stats)
- Tool use counts (for optional complexity metrics)
- Session IDs and project directory names

No prompt content, code, or file paths from your sessions are ever included in the output.

## Badge customization

Badges use [shields.io](https://shields.io) and are color-coded by average duration:

| Duration | Color |
|----------|-------|
| < 10s | 🟢 brightgreen |
| 10-30s | 🟢 green |
| 30-60s | 🟡 yellowgreen |
| 1-2m | 🟡 yellow |
| 2-5m | 🟠 orange |
| > 5m | 🔴 red |

### Dynamic badges (recommended)

If you use the Gist-based setup, your badges update automatically:

```markdown
![Turn Duration](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/Trevor-Mengel/GIST_ID/raw/turntime-badge.json)
```

### Static badges

Or use direct shields.io URLs (generated by the badge script):

```markdown
![⏱ This Month](https://img.shields.io/badge/⏱%20This%20Month-22.1s-green?style=flat-square)
```

## Histogram themes

The SVG histogram supports GitHub's automatic dark/light theme via `prefers-color-scheme`:

- **`auto`** (default) — adapts to the viewer's GitHub theme
- **`dark`** — always dark background
- **`light`** — always light background

## Requirements

- Python 3.9+
- Claude Code installed (with at least one session in `~/.claude/projects/`)
- `gh` CLI or `GITHUB_TOKEN` environment variable (for Gist sync)
- No external Python dependencies — uses only the standard library

## Roadmap

- [ ] 🏆 Global and regional leaderboards
- [ ] 🌐 Public website for leaderboard display
- [ ] 📦 `pip install turntime` package distribution
- [ ] 📊 Additional metrics (tokens/turn, tool uses/turn, complexity score)
- [ ] 🔌 Claude Code hook integration for real-time tracking
- [ ] 📈 Trend lines and rolling averages
- [ ] 🏷️ Per-project breakdown charts

## Contributing

Contributions welcome! Areas where help is especially appreciated:
- Leaderboard backend and frontend
- Additional chart types and visualizations
- Platform testing (Windows, Linux)
- pip packaging

## License

MIT — see [LICENSE](LICENSE).
