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
    """Pick a badge color based on average turn duration."""
    if seconds == 0:
        return "lightgrey"
    if seconds < 10:
        return "brightgreen"
    if seconds < 30:
        return "green"
    if seconds < 60:
        return "yellowgreen"
    if seconds < 120:
        return "yellow"
    if seconds < 300:
        return "orange"
    return "red"


def generate_static_badge(label: str, value: str, color: str, logo: str = "") -> str:
    """Generate a shields.io static badge URL."""
    base = "https://img.shields.io/badge"
    label_enc = quote(label.replace('-', '--').replace('_', '__'))
    value_enc = quote(value.replace('-', '--').replace('_', '__'))
    url = f"{base}/{label_enc}-{value_enc}-{color}?style=flat-square"
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
        "style": "flat-square",
    }


def generate_all_badges(data: dict) -> dict:
    """Generate badge data for all periods."""
    stats = data.get('stats', {})
    badges = {}

    for period, period_stats in stats.items():
        avg = period_stats.get('avg_seconds', 0)
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

        badges[period] = {
            'url': generate_static_badge(label, format_duration(avg), duration_color(avg)),
            'markdown': f'![{label}]({generate_static_badge(label, format_duration(avg), duration_color(avg))})',
            'avg': format_duration(avg),
            'count': count,
            'color': duration_color(avg),
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
