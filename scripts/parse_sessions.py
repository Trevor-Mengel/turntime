#!/usr/bin/env python3
"""turntime - Parse Claude Code session logs and extract turn duration metrics.

Reads JSONL session files from ~/.claude/projects/ and calculates the time
between a user prompt and Claude's final response (before the next user message).
"""
from __future__ import annotations

import json
import os
import sys
import glob
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Turn:
    """A single user→assistant turn with timing data."""
    session_id: str
    project: str
    user_timestamp: str
    assistant_timestamp: str
    duration_seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    tool_uses: int = 0


@dataclass
class TurnStats:
    """Aggregated turn statistics for a time period."""
    period: str  # "day", "week", "month", "quarter", "year", "all"
    label: str   # e.g. "2025-02-19", "2025-W08", "2025-02", "2025-Q1", "2025"
    count: int = 0
    total_seconds: float = 0.0
    min_seconds: float = float('inf')
    max_seconds: float = 0.0
    avg_seconds: float = 0.0
    median_seconds: float = 0.0
    p90_seconds: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_uses: int = 0
    durations: list = field(default_factory=list)

    def finalize(self):
        """Calculate derived stats from collected durations."""
        if not self.durations:
            self.avg_seconds = 0
            self.min_seconds = 0
            self.median_seconds = 0
            self.p90_seconds = 0
            return
        self.count = len(self.durations)
        self.total_seconds = sum(self.durations)
        self.avg_seconds = self.total_seconds / self.count
        self.min_seconds = min(self.durations)
        self.max_seconds = max(self.durations)
        sorted_d = sorted(self.durations)
        mid = self.count // 2
        self.median_seconds = (
            sorted_d[mid] if self.count % 2 == 1
            else (sorted_d[mid - 1] + sorted_d[mid]) / 2
        )
        p90_idx = int(self.count * 0.9)
        self.p90_seconds = sorted_d[min(p90_idx, self.count - 1)]

    def to_dict(self):
        """Serialize to dict, excluding raw durations list."""
        d = asdict(self)
        del d['durations']
        return d


def find_claude_dir() -> Path:
    """Locate the Claude Code projects directory."""
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        # Check common alternative locations
        alt = Path.home() / ".config" / "claude" / "projects"
        if alt.exists():
            return alt
        print(f"⚠️  Claude Code projects directory not found at {claude_dir}")
        print("   Make sure Claude Code is installed and you've had at least one session.")
        sys.exit(1)
    return claude_dir


def find_session_files(claude_dir: Path, project_filter: Optional[str] = None) -> list[Path]:
    """Find all JSONL session files, optionally filtered by project."""
    pattern = "**/*.jsonl" if not project_filter else f"*{project_filter}*/**/*.jsonl"
    files = sorted(claude_dir.glob(pattern))
    # Exclude non-session files
    session_files = [f for f in files if f.stem.startswith("session-") or f.stem != "sessions-index"]
    return session_files


def parse_session_file(filepath: Path) -> list[Turn]:
    """Parse a single JSONL session file and extract turns."""
    turns = []
    messages = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract core fields
                timestamp = entry.get('timestamp')
                message = entry.get('message', {})
                role = message.get('role', '')
                session_id = entry.get('sessionId', filepath.stem)

                if not timestamp or not role:
                    continue

                # Collect token usage from assistant messages
                usage = message.get('usage', {})
                content = message.get('content', [])
                tool_use_count = 0
                if isinstance(content, list):
                    tool_use_count = sum(
                        1 for c in content
                        if isinstance(c, dict) and c.get('type') == 'tool_use'
                    )

                messages.append({
                    'timestamp': timestamp,
                    'role': role,
                    'session_id': session_id,
                    'input_tokens': usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                    'cache_read': usage.get('cache_read_input_tokens', 0),
                    'tool_uses': tool_use_count,
                })
    except (IOError, PermissionError) as e:
        print(f"⚠️  Could not read {filepath}: {e}")
        return []

    if not messages:
        return []

    # Extract project name from directory structure
    project = filepath.parent.name

    # Build turns: find user→assistant pairs
    # A turn starts at a user message and ends at the last assistant message
    # before the next user message
    i = 0
    while i < len(messages):
        msg = messages[i]

        if msg['role'] == 'user':
            user_ts = msg['timestamp']
            user_dt = _parse_ts(user_ts)
            if user_dt is None:
                i += 1
                continue

            # Collect all assistant messages until next user message
            last_assistant_ts = None
            total_input = 0
            total_output = 0
            total_cache = 0
            total_tools = 0
            j = i + 1

            while j < len(messages):
                next_msg = messages[j]
                if next_msg['role'] == 'user':
                    break
                if next_msg['role'] == 'assistant':
                    last_assistant_ts = next_msg['timestamp']
                    total_input += next_msg.get('input_tokens', 0)
                    total_output += next_msg.get('output_tokens', 0)
                    total_cache += next_msg.get('cache_read', 0)
                    total_tools += next_msg.get('tool_uses', 0)
                j += 1

            if last_assistant_ts:
                assistant_dt = _parse_ts(last_assistant_ts)
                if assistant_dt and assistant_dt > user_dt:
                    duration = (assistant_dt - user_dt).total_seconds()

                    # Filter out unreasonable durations
                    # < 0.5s is likely a system message, > 30min is likely idle
                    if 0.5 <= duration <= 1800:
                        turns.append(Turn(
                            session_id=msg['session_id'],
                            project=project,
                            user_timestamp=user_ts,
                            assistant_timestamp=last_assistant_ts,
                            duration_seconds=round(duration, 2),
                            input_tokens=total_input,
                            output_tokens=total_output,
                            cache_read_tokens=total_cache,
                            tool_uses=total_tools,
                        ))

            i = j
        else:
            i += 1

    return turns


def _parse_ts(ts: str) -> Optional[datetime]:
    """Parse ISO-8601 timestamp string to datetime."""
    if not ts:
        return None
    try:
        # Handle various ISO formats
        ts = ts.replace('Z', '+00:00')
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        try:
            # Fallback: try strptime for edge cases
            return datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None


def aggregate_turns(turns: list[Turn], now: Optional[datetime] = None) -> dict:
    """Aggregate turns into time-period buckets."""
    if now is None:
        now = datetime.now(timezone.utc)

    periods = {
        'today': TurnStats(period='day', label=now.strftime('%Y-%m-%d')),
        'week': TurnStats(period='week', label=now.strftime('%Y-W%V')),
        'month': TurnStats(period='month', label=now.strftime('%Y-%m')),
        'quarter': TurnStats(period='quarter', label=f"{now.year}-Q{(now.month - 1) // 3 + 1}"),
        'year': TurnStats(period='year', label=str(now.year)),
        'all': TurnStats(period='all', label='all-time'),
    }

    # Calculate time boundaries
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    quarter_month = ((now.month - 1) // 3) * 3 + 1
    quarter_start = today_start.replace(month=quarter_month, day=1)
    year_start = today_start.replace(month=1, day=1)

    for turn in turns:
        ts = _parse_ts(turn.user_timestamp)
        if ts is None:
            continue

        # Make timezone-aware if needed
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        d = turn.duration_seconds

        # All-time always gets it
        periods['all'].durations.append(d)
        periods['all'].total_input_tokens += turn.input_tokens
        periods['all'].total_output_tokens += turn.output_tokens
        periods['all'].total_tool_uses += turn.tool_uses

        if ts >= year_start:
            periods['year'].durations.append(d)
            periods['year'].total_input_tokens += turn.input_tokens
            periods['year'].total_output_tokens += turn.output_tokens
            periods['year'].total_tool_uses += turn.tool_uses

        if ts >= quarter_start:
            periods['quarter'].durations.append(d)
            periods['quarter'].total_input_tokens += turn.input_tokens
            periods['quarter'].total_output_tokens += turn.output_tokens
            periods['quarter'].total_tool_uses += turn.tool_uses

        if ts >= month_start:
            periods['month'].durations.append(d)
            periods['month'].total_input_tokens += turn.input_tokens
            periods['month'].total_output_tokens += turn.output_tokens
            periods['month'].total_tool_uses += turn.tool_uses

        if ts >= week_start:
            periods['week'].durations.append(d)
            periods['week'].total_input_tokens += turn.input_tokens
            periods['week'].total_output_tokens += turn.output_tokens
            periods['week'].total_tool_uses += turn.tool_uses

        if ts >= today_start:
            periods['today'].durations.append(d)
            periods['today'].total_input_tokens += turn.input_tokens
            periods['today'].total_output_tokens += turn.output_tokens
            periods['today'].total_tool_uses += turn.tool_uses

    for stats in periods.values():
        stats.finalize()

    return {k: v.to_dict() for k, v in periods.items()}


def build_histogram_data(turns: list[Turn], period: str = 'month',
                         now: Optional[datetime] = None) -> list[dict]:
    """Build histogram bucket data for chart generation."""
    if now is None:
        now = datetime.now(timezone.utc)

    # Define bins (in seconds)
    bins = [
        (0, 5, "0-5s"),
        (5, 10, "5-10s"),
        (10, 20, "10-20s"),
        (20, 30, "20-30s"),
        (30, 60, "30-60s"),
        (60, 120, "1-2m"),
        (120, 300, "2-5m"),
        (300, 600, "5-10m"),
        (600, 1800, "10-30m"),
    ]

    # Filter turns by period
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    boundaries = {
        'day': today_start,
        'week': today_start - timedelta(days=now.weekday()),
        'month': today_start.replace(day=1),
        'quarter': today_start.replace(month=((now.month - 1) // 3) * 3 + 1, day=1),
        'year': today_start.replace(month=1, day=1),
        'all': datetime.min.replace(tzinfo=timezone.utc),
    }
    cutoff = boundaries.get(period, boundaries['month'])

    filtered = []
    for t in turns:
        ts = _parse_ts(t.user_timestamp)
        if ts and (ts.tzinfo is None and ts.replace(tzinfo=timezone.utc) >= cutoff
                   or ts.tzinfo and ts >= cutoff):
            filtered.append(t.duration_seconds)

    # Count per bin
    result = []
    for lo, hi, label in bins:
        count = sum(1 for d in filtered if lo <= d < hi)
        result.append({
            'bin': label,
            'lo': lo,
            'hi': hi,
            'count': count,
        })

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Parse Claude Code session logs and extract turn duration metrics.'
    )
    parser.add_argument(
        '--claude-dir', type=str, default=None,
        help='Path to Claude projects directory (default: ~/.claude/projects)'
    )
    parser.add_argument(
        '--project', type=str, default=None,
        help='Filter by project name (substring match)'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='Output JSON file path (default: stdout)'
    )
    parser.add_argument(
        '--format', choices=['stats', 'turns', 'histogram', 'full'],
        default='full',
        help='Output format: stats, turns, histogram, or full (default: full)'
    )
    parser.add_argument(
        '--histogram-period', choices=['day', 'week', 'month', 'quarter', 'year', 'all'],
        default='month',
        help='Time period for histogram data (default: month)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Show progress info'
    )
    args = parser.parse_args()

    # Find session files
    claude_dir = Path(args.claude_dir) if args.claude_dir else find_claude_dir()
    session_files = find_session_files(claude_dir, args.project)

    if args.verbose:
        print(f"📂 Found {len(session_files)} session files in {claude_dir}", file=sys.stderr)

    # Parse all sessions
    all_turns = []
    for i, filepath in enumerate(session_files):
        if args.verbose and (i + 1) % 10 == 0:
            print(f"   Parsing {i + 1}/{len(session_files)}...", file=sys.stderr)
        turns = parse_session_file(filepath)
        all_turns.extend(turns)

    if args.verbose:
        print(f"✅ Extracted {len(all_turns)} turns from {len(session_files)} sessions",
              file=sys.stderr)

    # Build output
    now = datetime.now(timezone.utc)
    output = {'generated_at': now.isoformat(), 'version': '1.0.0'}

    if args.format in ('stats', 'full'):
        output['stats'] = aggregate_turns(all_turns, now)

    if args.format in ('turns', 'full'):
        # Include recent turns (last 100) for detailed inspection
        recent = sorted(all_turns, key=lambda t: t.user_timestamp, reverse=True)[:100]
        output['recent_turns'] = [asdict(t) for t in recent]

    if args.format in ('histogram', 'full'):
        output['histogram'] = build_histogram_data(all_turns, args.histogram_period, now)

    # Output
    json_str = json.dumps(output, indent=2, default=str)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_str)
        if args.verbose:
            print(f"💾 Wrote output to {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == '__main__':
    main()
