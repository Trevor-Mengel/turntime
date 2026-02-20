#!/usr/bin/env python3
"""
turntime sync - Push stats to GitHub Gist and update profile README.

This script:
1. Parses Claude Code session logs
2. Generates stats JSON, badge data, and histogram SVG
3. Pushes everything to a GitHub Gist (for dynamic badges)
4. Optionally commits histogram SVG to your profile repo
"""
from __future__ import annotations

import json
import os
import re
import sys
import subprocess
import argparse
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from parse_sessions import find_claude_dir, find_session_files, parse_session_file, aggregate_turns, build_histogram_data
from generate_histogram import generate_histogram_svg
from generate_badges import generate_all_badges, generate_badge_json, format_duration


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def get_github_token() -> str:
    """Get GitHub token from environment or gh CLI."""
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        return token

    # Try gh CLI
    try:
        result = run_cmd(['gh', 'auth', 'token'])
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    print("❌ No GitHub token found. Set GITHUB_TOKEN or install gh CLI and run `gh auth login`.")
    sys.exit(1)


def get_github_username(token: str) -> str:
    """Get the authenticated GitHub username."""
    import urllib.request

    req = urllib.request.Request(
        'https://api.github.com/user',
        headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['login']
    except (urllib.error.HTTPError, KeyError):
        return ''


def create_or_update_gist(token: str, gist_id: str | None, files: dict[str, str | None],
                          description: str = "turntime stats") -> str:
    """Create or update a GitHub Gist. Returns the Gist ID.

    Files with None values are deleted from the Gist (only applies to updates).
    """
    import urllib.request

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
    }

    gist_files: dict[str, dict[str, str] | None] = {}
    for name, content in files.items():
        if content is None:
            gist_files[name] = None
        else:
            gist_files[name] = {'content': content}

    payload = {
        'description': description,
        'files': gist_files,
    }

    if gist_id:
        # Update existing
        url = f'https://api.github.com/gists/{gist_id}'
        method = 'PATCH'
    else:
        # Create new
        url = 'https://api.github.com/gists'
        method = 'POST'
        payload['public'] = True

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['id']
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        print(f"❌ GitHub API error ({e.code}): {body}")
        sys.exit(1)


def update_profile_readme(
    readme_path: Path,
    badges_md: str,
    histogram_path: str | None = None,
    gist_raw_url: str | None = None,
):
    """Update a profile README with turntime badges and histogram."""
    if not readme_path.exists():
        print(f"⚠️  README not found at {readme_path}")
        return False

    content = readme_path.read_text()

    # Replace badge section
    badge_pattern = r'<!-- turntime badges -->.*?<!-- /turntime badges -->'
    if re.search(badge_pattern, content, re.DOTALL):
        content = re.sub(badge_pattern, badges_md, content, flags=re.DOTALL)
    else:
        # Append if not found
        content += f'\n\n{badges_md}\n'

    # Replace histogram section
    if histogram_path or gist_raw_url:
        img_src = histogram_path or gist_raw_url
        histogram_md = (
            f'<!-- turntime histogram -->\n'
            f'<picture>\n'
            f'  <img src="{img_src}" alt="Claude Code Turn Duration Histogram" />\n'
            f'</picture>\n'
            f'<!-- /turntime histogram -->'
        )
        hist_pattern = r'<!-- turntime histogram -->.*?<!-- /turntime histogram -->'
        if re.search(hist_pattern, content, re.DOTALL):
            content = re.sub(hist_pattern, histogram_md, content, flags=re.DOTALL)
        else:
            content += f'\n\n{histogram_md}\n'

    readme_path.write_text(content)
    return True


def load_config(config_path: Path | None = None) -> dict:
    """Load turntime config file."""
    paths_to_try = [
        config_path,
        Path.cwd() / '.turntime.json',
        Path.home() / '.config' / 'turntime' / 'config.json',
        Path.home() / '.turntime.json',
    ]

    for p in paths_to_try:
        if p and p.exists():
            with open(p) as f:
                return json.load(f)

    return {}


def save_config(config: dict, config_path: Path | None = None):
    """Save turntime config."""
    path = config_path or Path.home() / '.config' / 'turntime' / 'config.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"💾 Config saved to {path}")


def cmd_init(args):
    """Initialize turntime configuration."""
    config = load_config()

    print("🚀 turntime setup\n")

    # Check for Claude Code
    claude_dir = find_claude_dir()
    session_files = find_session_files(claude_dir)
    print(f"✅ Found Claude Code with {len(session_files)} session files\n")

    # GitHub token
    token = get_github_token()
    print("✅ GitHub authentication OK\n")

    # Get and store GitHub username (needed for Gist raw URLs)
    username = get_github_username(token)
    if username:
        config['github_username'] = username
        print(f"✅ GitHub user: {username}\n")
    else:
        print("⚠️  Could not determine GitHub username. Gist raw URLs may not work.\n")

    # Create initial Gist
    print("📌 Creating stats Gist...")
    gist_id = create_or_update_gist(
        token=token,
        gist_id=config.get('gist_id'),
        files={
            'turntime-stats.json': json.dumps({'status': 'initializing', 'version': '1.0.0'}),
        },
        description='turntime - Claude Code turn duration stats',
    )
    config['gist_id'] = gist_id
    print(f"✅ Gist ready: https://gist.github.com/{gist_id}\n")

    # Profile repo
    profile_repo = input("📂 Path to your GitHub profile repo (or press Enter to skip): ").strip()
    if profile_repo:
        config['profile_repo'] = str(Path(profile_repo).expanduser().resolve())

    # Histogram period preference
    config.setdefault('histogram_period', 'month')
    config.setdefault('badge_periods', ['week', 'all'])

    save_config(config)

    print("\n✅ Setup complete! Run `turntime sync` to generate your first stats.\n")
    print("Add this to your profile README:\n")
    print("```markdown")
    print("<!-- turntime badges -->")
    print("<!-- /turntime badges -->")
    print("")
    print("<!-- turntime histogram -->")
    print("<!-- /turntime histogram -->")
    print("```")


def cmd_sync(args):
    """Parse logs, generate assets, and push to GitHub."""
    config = load_config(Path(args.config) if args.config else None)

    if not config.get('gist_id') and not args.local_only:
        print("❌ No Gist configured. Run `turntime init` first or use --local-only.")
        sys.exit(1)

    # Parse sessions
    claude_dir = Path(args.claude_dir) if args.claude_dir else find_claude_dir()
    session_files = find_session_files(claude_dir, args.project)
    if not session_files:
        print("❌ No session files found.")
        if args.project:
            print(f"   No sessions matched project filter '{args.project}'.")
        else:
            print("   Make sure Claude Code is installed and you've had at least one session.")
        sys.exit(1)
    print(f"📂 Parsing {len(session_files)} session files...")

    all_turns = []
    for filepath in session_files:
        turns = parse_session_file(filepath)
        all_turns.extend(turns)

    if not all_turns:
        print("⚠️  No turns extracted from session files.")
        print("   Your session files may not contain complete user→assistant message pairs.")
        sys.exit(1)

    print(f"✅ Extracted {len(all_turns)} turns")

    # Generate stats
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    stats = aggregate_turns(all_turns, now)
    histogram_period = args.period or config.get('histogram_period', 'month')
    histogram_data = build_histogram_data(all_turns, histogram_period, now)

    # Build full output
    output = {
        'generated_at': now.isoformat(),
        'version': '1.0.0',
        'stats': stats,
        'histogram': histogram_data,
    }

    # Generate SVG
    period_labels = {
        'today': 'Today', 'week': 'This Week', 'month': 'This Month',
        'quarter': 'This Quarter', 'year': 'This Year', 'all': 'All Time',
    }
    period_stats = stats.get(histogram_period, stats.get('all', {}))
    svg = generate_histogram_svg(
        histogram_data=histogram_data,
        stats=period_stats,
        period_label=period_labels.get(histogram_period, histogram_period),
        theme=args.theme or 'auto',
    )

    # Generate badges (pass config for customization)
    badges = generate_all_badges(output, config)
    badge_periods = args.badge_periods or config.get('badge_periods', ['week', 'all'])
    badge_md_lines = ["<!-- turntime badges -->"]
    for p in badge_periods:
        if p in badges:
            badge_md_lines.append(badges[p]['markdown'])
    badge_md_lines.append("<!-- /turntime badges -->")
    badges_md = '\n'.join(badge_md_lines)

    # Generate endpoint JSON (for shields.io dynamic badges)
    endpoint_json = generate_badge_json(period_stats)

    # Build text dashboard for pinned Gist display (plain text, no markdown)
    # Shows weekly average vs the 45s global median across all Claude Code users
    GLOBAL_MEDIAN_SECONDS = 45
    week_stats = stats.get('week', {})
    week_avg = week_stats.get('avg_seconds', 0)
    week_avg_fmt = format_duration(week_avg)
    if week_avg > 0:
        pct = ((week_avg - GLOBAL_MEDIAN_SECONDS) / GLOBAL_MEDIAN_SECONDS) * 100
        arrow = '\u2191' if pct > 0 else '\u2193'
        gist_dashboard = f"{week_avg_fmt} avg  {arrow}{abs(pct):.0f}%\n"
    else:
        gist_dashboard = "no data\n"

    # Save locally
    output_dir = Path(args.output_dir or '.turntime-output')
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / 'turntime-stats.json').write_text(json.dumps(output, indent=2))
    (output_dir / 'turntime-histogram.svg').write_text(svg)
    (output_dir / 'turntime-shield.json').write_text(json.dumps(endpoint_json, indent=2))
    (output_dir / 'turntime-badges.md').write_text(badges_md)
    print(f"💾 Local output saved to {output_dir}/")

    if args.local_only:
        print("\n✅ Done (local only mode).")
        return

    # Push to Gist
    token = get_github_token()
    gist_id = config.get('gist_id')
    github_user = config.get('github_username') or get_github_username(token)
    print(f"🔄 Pushing to Gist {gist_id}...")

    gist_files: dict[str, str | None] = {
        'dashboard': gist_dashboard,
        'turntime-stats.json': json.dumps(output, indent=2),
        'turntime-histogram.svg': svg,
        'turntime-shield.json': json.dumps(endpoint_json, indent=2),
    }

    gist_id = create_or_update_gist(
        token=token,
        gist_id=gist_id,
        files=gist_files,
        description='turntime - Claude Code turn duration stats',
    )
    print(f"✅ Gist updated: https://gist.github.com/{gist_id}")

    # Update profile README if configured
    profile_repo = config.get('profile_repo')
    if profile_repo:
        readme_path = Path(profile_repo) / 'README.md'
        if github_user:
            gist_raw = f"https://gist.githubusercontent.com/{github_user}/{gist_id}/raw/turntime-histogram.svg"
        else:
            print("⚠️  GitHub username not configured. Run `turntime init` to fix.")
            gist_raw = f"https://gist.githubusercontent.com/raw/{gist_id}/turntime-histogram.svg"
        if update_profile_readme(readme_path, badges_md, gist_raw_url=gist_raw):
            print(f"📝 Updated {readme_path}")
            # Git commit & push
            try:
                run_cmd(['git', '-C', profile_repo, 'add', 'README.md'])
                run_cmd(['git', '-C', profile_repo, 'commit', '-m',
                         f'chore: update turntime stats ({now.strftime("%Y-%m-%d")})'],
                        check=False)
                run_cmd(['git', '-C', profile_repo, 'push'], check=False)
                print("🚀 Pushed to profile repo")
            except Exception as e:
                print(f"⚠️  Could not push: {e}")

    # Print summary
    print(f"\n📊 Summary:")
    for p in badge_periods:
        if p in stats:
            s = stats[p]
            print(f"   {period_labels.get(p, p)}: avg {s['avg_seconds']:.1f}s "
                  f"(median {s['median_seconds']:.1f}s, {s['count']} turns)")


def cmd_stats(args):
    """Show stats without syncing."""
    claude_dir = Path(args.claude_dir) if args.claude_dir else find_claude_dir()
    session_files = find_session_files(claude_dir, args.project)

    if not session_files:
        print("❌ No session files found.")
        if args.project:
            print(f"   No sessions matched project filter '{args.project}'.")
        else:
            print("   Make sure Claude Code is installed and you've had at least one session.")
        sys.exit(1)

    all_turns = []
    for filepath in session_files:
        turns = parse_session_file(filepath)
        all_turns.extend(turns)

    from datetime import datetime, timezone
    stats = aggregate_turns(all_turns, datetime.now(timezone.utc))

    period_labels = {
        'today': 'Today', 'week': 'This Week', 'month': 'This Month',
        'quarter': 'This Quarter', 'year': 'This Year', 'all': 'All Time',
    }

    print(f"\n⏱  turntime stats ({len(all_turns)} turns from {len(session_files)} sessions)\n")
    print(f"{'Period':<16} {'Avg':>8} {'Median':>8} {'P90':>8} {'Min':>8} {'Max':>8} {'Count':>8}")
    print(f"{'─' * 72}")
    for key in ['today', 'week', 'month', 'quarter', 'year', 'all']:
        s = stats.get(key, {})
        if s.get('count', 0) > 0:
            print(f"{period_labels[key]:<16} "
                  f"{s['avg_seconds']:>7.1f}s "
                  f"{s['median_seconds']:>7.1f}s "
                  f"{s['p90_seconds']:>7.1f}s "
                  f"{s['min_seconds']:>7.1f}s "
                  f"{s['max_seconds']:>7.1f}s "
                  f"{s['count']:>8}")
        else:
            print(f"{period_labels[key]:<16} {'—':>8} {'—':>8} {'—':>8} {'—':>8} {'—':>8} {'0':>8}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog='turntime',
        description='⏱  Track and display your Claude Code turn duration stats.',
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init
    init_parser = subparsers.add_parser('init', help='Set up turntime configuration')

    # sync
    sync_parser = subparsers.add_parser('sync', help='Parse logs and push stats')
    sync_parser.add_argument('--claude-dir', type=str, default=None)
    sync_parser.add_argument('--project', type=str, default=None)
    sync_parser.add_argument('--config', type=str, default=None)
    sync_parser.add_argument('--output-dir', type=str, default=None)
    sync_parser.add_argument('--period', type=str, default=None)
    sync_parser.add_argument('--theme', choices=['auto', 'dark', 'light'], default=None)
    sync_parser.add_argument('--badge-periods', nargs='+', default=None)
    sync_parser.add_argument('--local-only', action='store_true',
                             help='Generate files locally without pushing to GitHub')

    # stats
    stats_parser = subparsers.add_parser('stats', help='Show stats in terminal')
    stats_parser.add_argument('--claude-dir', type=str, default=None)
    stats_parser.add_argument('--project', type=str, default=None)

    args = parser.parse_args()

    if args.command == 'init':
        cmd_init(args)
    elif args.command == 'sync':
        cmd_sync(args)
    elif args.command == 'stats':
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
