# ⏱ turntime

**Track and display your Claude Code turn duration on your GitHub profile.**

turntime parses your local Claude Code session logs, calculates how long each prompt→response turn takes, and generates beautiful badges and histogram charts you can embed in your GitHub profile README — updated automatically on a schedule.

<picture>
  <img src="assets/example-histogram.svg" alt="Example turn duration histogram" />
</picture>

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Trevor-Mengel/turntime/main/setup.sh | bash
```

This clones turntime to `~/.local/share/turntime` and adds a `turntime` command to your PATH.

Or clone manually:

```bash
git clone https://github.com/Trevor-Mengel/turntime.git
cd turntime
python3 scripts/turntime_cli.py stats
```

## What it measures

**Turn duration** = the time from when you send a prompt to when Claude finishes its complete response (including all tool uses).

A "turn" starts when a `user` message is logged and ends at the final `assistant` message before the next `user` message. Turns shorter than 0.5s (system messages) and longer than 30min (idle sessions) are automatically filtered out.

## Quick start

```bash
# View your stats immediately (no setup needed)
turntime stats
```

You'll see a table like this:

```
⏱  turntime stats (12849 turns from 505 sessions)

Period                Avg   Median      P90      Min      Max    Count
────────────────────────────────────────────────────────────────────────
Today               7.1s     3.7s    12.2s     0.5s    65.5s       58
This Week           8.3s     4.6s    16.0s     0.5s   199.3s     3617
This Month          7.8s     3.9s    13.7s     0.5s  1205.5s    11442
All Time            8.0s     3.9s    14.3s     0.5s  1205.5s    12849
```

## Setup for GitHub profile

### 1. Initialize

```bash
turntime init
```

This will:
- Verify Claude Code logs exist on your machine
- Authenticate with GitHub (via `gh` CLI or `GITHUB_TOKEN`)
- Create a public Gist to host your stats
- Save config to `~/.config/turntime/config.json`

### 2. Sync your stats

```bash
turntime sync
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

Then run `turntime sync` — it will fill these in with your actual badges and histogram.

### 4. Automate updates

**macOS (launchd):**

Create `~/Library/LaunchAgents/com.turntime.sync.plist` to sync every 6 hours. See the repo wiki for a ready-to-use plist template.

**Any platform (cron):**

```bash
crontab -e
```

```cron
0 */6 * * * cd /path/to/turntime && python3 scripts/turntime_cli.py sync 2>/dev/null
```

> **Note:** For cron/launchd, store your GitHub token in `~/.config/turntime/.env` as `GH_TOKEN=<token>` and source it in your wrapper script. The `gh auth token` command may not work in non-interactive shells due to keychain access.

### 5. Automate with GitHub Actions (optional)

If you commit `turntime-stats.json` to your profile repo, you can add a GitHub Action to regenerate the histogram and update badges daily — even when your machine is off:

1. Copy `.github/workflows/update-stats.yml` to your profile repo
2. Add these repository secrets:
   - `TURNTIME_GIST_ID` — your Gist ID (from `~/.config/turntime/config.json`)
   - `TURNTIME_GIST_TOKEN` — a [fine-grained PAT](https://github.com/settings/personal-access-tokens/new) with **Gists** (read/write) and **Contents** (read/write) permissions
3. The action runs daily at 6am UTC and supports manual dispatch

## CLI reference

```bash
# Show stats in terminal
turntime stats
turntime stats --project myproject    # filter by project name

# Generate files locally without pushing
turntime sync --local-only
turntime sync --local-only --period week --theme dark

# Full sync: parse → generate → push to Gist → update README
turntime sync

# Initialize configuration
turntime init
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
  "theme": "auto"
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `gist_id` | GitHub Gist ID for hosting stats | Set by `init` |
| `profile_repo` | Local path to your profile repo | Optional |
| `histogram_period` | Period for histogram chart | `"month"` |
| `badge_periods` | Which periods to show as badges | `["month", "all"]` |
| `theme` | SVG theme: `auto`, `dark`, `light` | `"auto"` |

## How it works

1. **Reads** Claude Code session logs from `~/.claude/projects/**/*.jsonl`
2. **Parses** each JSONL file to extract timestamped user/assistant message pairs
3. **Calculates** turn duration as `last_assistant_timestamp - user_timestamp`
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

Use the Gist endpoint for auto-updating badges:

```markdown
![Turn Duration](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/YOUR_USER/GIST_ID/raw/turntime-badge.json)
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

- [ ] Global and regional leaderboards
- [ ] Public website for leaderboard display
- [ ] `pip install turntime` package distribution
- [ ] Additional metrics (tokens/turn, tool uses/turn, complexity score)
- [ ] Claude Code hook integration for real-time tracking
- [ ] Trend lines and rolling averages
- [ ] Per-project breakdown charts

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE).
