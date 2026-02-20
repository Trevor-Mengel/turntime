```
     ████████╗██╗   ██╗██████╗ ███╗   ██╗
     ╚══██╔══╝██║   ██║██╔══██╗████╗  ██║
        ██║   ██║   ██║██████╔╝██╔██╗ ██║
        ██║   ██║   ██║██╔══██╗██║╚██╗██║
        ██║   ╚██████╔╝██║  ██║██║ ╚████║
        ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝
                ████████╗██╗███╗   ███╗███████╗
╔══════════╗    ╚══██╔══╝██║████╗ ████║██╔════╝
║    │     ║       ██║   ██║██╔████╔██║█████╗
║    ·──   ║       ██║   ██║██║╚██╔╝██║██╔══╝
║          ║       ██║   ██║██║ ╚═╝ ██║███████╗
╚══════════╝      ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝
```

**Track and display your Claude Code turn duration on your GitHub profile.**

Anthropic's research shows that the top 0.1% of Claude Code users have average turn durations [nearly double](https://www.anthropic.com/research/agent-autonomy) everyone else's — and climbing. These are the power users tackling the most complex, ambitious work: the kind where Claude reads dozens of files, orchestrates multi-step tool chains, runs tests, refactors, and delivers — all in a single turn. Turn duration is one of the clearest signals of how much autonomy you're granting your agent, and how hard the problems you're throwing at it actually are.

turntime makes that visible. It parses your local Claude Code session logs, calculates your turn durations, and generates badges and histogram charts you can display on your GitHub profile — because if you're going to let an AI work unsupervised for 20 minutes, you might as well get credit for it.

<picture>
  <img src="assets/example-histogram.svg" alt="Example turn duration histogram" />
</picture>

## Why turn duration matters

Most Claude Code turns are short. The median across all users is around 45 seconds. Nearly every percentile below the 99th has held steady for months — that's what happens when a product is growing fast and new users are still learning the tool.

The interesting signal is in the tail. Between October 2025 and January 2026, the 99.9th percentile turn duration nearly doubled, from under 25 minutes to over 45 minutes. This wasn't driven by model releases — it was a smooth trend, suggesting that power users are building trust over time, attempting more ambitious tasks, and letting Claude work independently for longer.

Internally at Anthropic, Claude Code's success rate on the hardest tasks doubled between August and December, while human interventions per session dropped from 5.4 to 3.3. Users are granting more autonomy *and* getting better outcomes.

**Where do you fall on that curve?** turntime lets you find out. Whether you should *tell* people is between you and your conscience.

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

**Turn duration** = the wall-clock time from when you send a prompt to when Claude finishes its complete response — including every intermediate tool call in between.

When Claude reads 14 files, edits 3, runs the test suite, and refactors based on the results — that's one turn. You were probably making coffee. turntime captures the full duration of that autonomous work, not just the final response.

Technical details:
- Tool results (`user` messages with `tool_result` content blocks) are correctly identified and skipped — multi-step tool chains count as a single turn, not dozens of micro-turns
- Subagent processes (background Task tool spawns) are excluded — only your direct Claude Code sessions are measured
- Turns under 5 seconds are filtered out (quick confirmations and short terminal commands)
- No upper cap — if Claude wants to work for an hour, who are we to stop it

## Quick start

```bash
turntime stats
```

```
⏱  turntime stats (712 turns from 108 sessions)

Period                Avg   Median      P90      Min      Max    Count
────────────────────────────────────────────────────────────────────────
Today              605.7s   222.6s  2596.4s     4.2s  2900.9s       27
This Week          503.2s    99.6s  1251.3s     4.2s 12395.8s      210
This Month         376.4s    52.4s   645.5s     0.6s 22822.4s      648
All Time           412.1s    53.4s   661.5s     0.6s 24853.5s      712
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

Then run `turntime sync` — it will inject your badges and histogram automatically.

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
  "badge_periods": ["week", "all"],
  "badge_metric": "avg",
  "badge_style": "for-the-badge",
  "badge_delta": true,
  "badge_delta_baseline": "all",
  "theme": "auto"
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `gist_id` | GitHub Gist ID for hosting stats | Set by `init` |
| `profile_repo` | Local path to your profile repo | Optional |
| `histogram_period` | Period for histogram chart | `"month"` |
| `badge_periods` | Which periods to show as badges | `["week", "all"]` |
| `badge_metric` | Metric to display: `"avg"`, `"median"`, `"p90"`, `"count"` | `"avg"` |
| `badge_style` | shields.io badge style: `"flat"`, `"flat-square"`, `"plastic"`, `"for-the-badge"` | `"for-the-badge"` |
| `badge_delta` | Show ▲/▼ percentage vs baseline period | `true` |
| `badge_delta_baseline` | Period to compare against for delta | `"all"` |
| `theme` | SVG theme: `"auto"`, `"dark"`, `"light"` | `"auto"` |

### Badge examples

**Default** — weekly average with delta vs all-time:
```json
{ "badge_periods": ["week", "all"], "badge_metric": "avg", "badge_delta": true }
```
> ![⏱ This Week](https://img.shields.io/badge/⏱%20This%20Week-8.2m%20▲15%25-6366f1?style=for-the-badge) ![⏱ All Time](https://img.shields.io/badge/⏱%20All%20Time-7.2m-6366f1?style=for-the-badge)

**Median-focused** — useful if your distribution is skewed:
```json
{ "badge_periods": ["week", "all"], "badge_metric": "median" }
```

**No delta** — just the raw durations:
```json
{ "badge_periods": ["today", "month", "all"], "badge_delta": false }
```

**Flat-square style** — compact alternative:
```json
{ "badge_style": "flat-square" }
```

## How it works

1. **Reads** Claude Code session logs from `~/.claude/projects/**/*.jsonl`
2. **Parses** each JSONL file to extract timestamped messages, distinguishing genuine human prompts from tool_result messages (which share `role: "user"` in the Claude API)
3. **Calculates** turn duration from your prompt to Claude's final response, spanning all intermediate tool-use cycles
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

Your prompts, code, and questionable variable names stay between you and Claude.

## Badge colors

Badges use [shields.io](https://shields.io) with a Tailwind-inspired color palette. The progression reflects the research — longer turns correlate with more complex, more autonomous work:

| Duration | Tier | Color | Hex |
|----------|------|-------|-----|
| < 2m | Routine | ⚫ Slate | `#475569` |
| 2–5m | Engaged | 🟡 Amber | `#f59e0b` |
| 5–10m | Deep Work | 🟢 Teal | `#14b8a6` |
| 10–20m | Power User | 🔵 Indigo | `#6366f1` |
| 20–40m | Top 1% | 🟣 Fuchsia | `#d946ef` |
| ≥ 40m | 99.9th Percentile | ⚪ White | `#ffffff` |

### Dynamic badges (recommended)

Use the Gist endpoint for auto-updating badges:

```markdown
![Turn Duration](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/YOUR_USER/GIST_ID/raw/turntime-badge.json)
```

### Static badges

Or use direct shields.io URLs (generated by the badge script):

```markdown
![⏱ This Month](https://img.shields.io/badge/⏱%20This%20Month-3.4m-green?style=flat-square)
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
- A willingness to quantify your relationship with an AI (you're already here)

## Roadmap

- [ ] Global and regional leaderboards (we know you want this)
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
