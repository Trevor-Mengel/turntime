#!/usr/bin/env python3
"""Generate shields.io badge URLs and markdown from turntime stats.
Supports both static badges and dynamic badges via GitHub Gist.
"""
from __future__ import annotations

import json
import sys
import argparse
from urllib.parse import quote


def format_duration(seconds: float) -> str:
    """Format seconds into a clean badge-friendly string."""
    if seconds == 0:
        return "no data"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


def duration_color(seconds: float) -> str:
    """Pick a badge color based on average turn duration.

    Longer turns signal deeper, more complex AI-assisted work — the color
    palette progresses from neutral to increasingly vibrant, rewarding
    sustained sessions.  Hex values are Tailwind-inspired:

      < 2 min  = slate-400   (#94a3b8)  — quick / routine
      < 5 min  = amber-500   (#f59e0b)  — warming up
      < 10 min = teal-500    (#14b8a6)  — solid session
      < 20 min = indigo-500  (#6366f1)  — deep work
      < 40 min = fuchsia-500 (#d946ef)  — marathon
      ≥ 40 min = white       (#ffffff)  — legendary
    """
    if seconds == 0:
        return "lightgrey"
    if seconds < 120:
        return "94a3b8"
    if seconds < 300:
        return "f59e0b"
    if seconds < 600:
        return "14b8a6"
    if seconds < 1200:
        return "6366f1"
    if seconds < 2400:
        return "d946ef"
    return "ffffff"


def generate_static_badge(label: str, value: str, color: str, logo: str = "") -> str:
    """Generate a shields.io static badge URL."""
    base = "https://img.shields.io/badge"
    label_enc = quote(label.replace('-', '--').replace('_', '__'))
    value_enc = quote(value.replace('-', '--').replace('_', '__'))
    url = f"{base}/{label_enc}-{value_enc}-{color}?style=for-the-badge"
    if logo:
        url += f"&logo={quote(logo)}&logoColor=white"
    return url


def generate_dynamic_badge(gist_id: str, filename: str, period: str = "month") -> str:
    """Generate a shields.io dynamic badge URL pointing to a Gist."""
    gist_url = f"https://gist.githubusercontent.com/{gist_id}/raw/{filename}"
    label = quote(f"Turn Duration ({period})")
    query = quote(f"$.stats.{period}.avg_seconds")
    return (
        f"https://img.shields.io/badge/dynamic/json"
        f"?url={quote(gist_url)}"
        f"&label={label}"
        f"&query={query}"
        f"&suffix=s"
        f"&color=blue"
        f"&style=flat-square"
        f"&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxjaXJjbGUgY3g9IjEyIiBjeT0iMTIiIHI9IjEwIi8+PHBvbHlsaW5lIHBvaW50cz0iMTIgNiAxMiAxMiAxNiAxNCIvPjwvc3ZnPg=="
    )


def generate_badge_json(stats: dict) -> dict:
    """Generate a shields.io endpoint badge JSON."""
    avg = stats.get('avg_seconds', 0)
    return {
        "schemaVersion": 1,
        "label": "Avg Turn Duration",
        "message": format_duration(avg),
        "color": duration_color(avg),
        "namedLogo": "claude",
        "style": "for-the-badge",
    }


def format_delta(period_avg: float, baseline_avg: float) -> str:
    """Format the percentage change from baseline as a badge-friendly string.

    Returns e.g. " ▲15%" or " ▼8%" or "" if no meaningful delta.
    """
    if baseline_avg <= 0 or period_avg <= 0:
        return ""
    pct = ((period_avg - baseline_avg) / baseline_avg) * 100
    if abs(pct) < 1:
        return ""
    arrow = "▲" if pct > 0 else "▼"
    return f" {arrow}{abs(pct):.0f}%"


def _get_metric_value(period_stats: dict, metric: str) -> float:
    """Extract a metric value from period stats."""
    metric_map = {
        'avg': 'avg_seconds',
        'median': 'median_seconds',
        'p90': 'p90_seconds',
        'count': 'count',
    }
    return period_stats.get(metric_map.get(metric, 'avg_seconds'), 0)


def _format_metric(value: float, metric: str) -> str:
    """Format a metric value for display."""
    if metric == 'count':
        return str(int(value))
    return format_duration(value)


def generate_all_badges(data: dict, config: dict | None = None) -> dict:
    """Generate badge data for all periods.

    Configurable via the config dict:
      badge_metric:         "avg" | "median" | "p90" | "count" (default: "avg")
      badge_style:          shields.io style string (default: "flat-square")
      badge_delta:          true | false — show % delta vs baseline (default: true)
      badge_delta_baseline: period key to compare against (default: "all")
    """
    if config is None:
        config = {}

    stats = data.get('stats', {})
    badges = {}

    metric = config.get('badge_metric', 'avg')
    style = config.get('badge_style', 'for-the-badge')
    show_delta = config.get('badge_delta', True)
    baseline_key = config.get('badge_delta_baseline', 'all')

    baseline_val = _get_metric_value(stats.get(baseline_key, {}), metric)

    for period, period_stats in stats.items():
        val = _get_metric_value(period_stats, metric)
        count = period_stats.get('count', 0)

        period_labels = {
            'today': 'Today',
            'week': 'This Week',
            'month': 'This Month',
            'quarter': 'This Quarter',
            'year': 'This Year',
            'all': 'All Time',
        }
        label = f"⏱ {period_labels.get(period, period)}"

        # Add delta vs baseline for non-baseline periods
        delta = ""
        if show_delta and period != baseline_key and metric != 'count':
            delta = format_delta(val, baseline_val)
        formatted = _format_metric(val, metric)
        value = f"{formatted}{delta}"

        color = duration_color(val) if metric != 'count' else 'blue'
        url = generate_static_badge(label, value, color)
        if style != 'for-the-badge':
            url = url.replace('style=for-the-badge', f'style={quote(style)}')

        badges[period] = {
            'url': url,
            'markdown': f'![{label}]({url})',
            'avg': format_duration(period_stats.get('avg_seconds', 0)),
            'metric': metric,
            'metric_value': formatted,
            'delta': delta.strip(),
            'count': count,
            'color': color,
            'endpoint_json': generate_badge_json(period_stats),
        }

    return badges


def main():
    parser = argparse.ArgumentParser(description='Generate badge URLs from turntime stats.')
    parser.add_argument(
        'input', type=str,
        help='Path to turntime JSON stats file'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--format', choices=['markdown', 'json', 'urls'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--period', type=str, default=None,
        help='Specific period (default: all periods)'
    )
    parser.add_argument(
        '--gist-id', type=str, default=None,
        help='GitHub Gist ID for dynamic badges (format: username/gist_hash)'
    )
    args = parser.parse_args()

    try:
        with open(args.input, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Stats file not found: {args.input}", file=sys.stderr)
        print("   Run `turntime sync --local-only` first to generate stats.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    badges = generate_all_badges(data)

    if args.period:
        badges = {args.period: badges[args.period]} if args.period in badges else {}

    if args.format == 'markdown':
        lines = ["<!-- turntime badges -->"]
        for period, badge in badges.items():
            lines.append(badge['markdown'])
        lines.append("<!-- /turntime badges -->")
        output = '\n'.join(lines)
    elif args.format == 'urls':
        output = '\n'.join(b['url'] for b in badges.values())
    else:
        output = json.dumps(badges, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
    else:
        print(output)


if __name__ == '__main__':
    main()
