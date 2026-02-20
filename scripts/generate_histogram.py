#!/usr/bin/env python3
"""Generate an SVG histogram chart of Claude Code turn durations.
Designed to embed in GitHub profile READMEs with dark/light theme support.
"""
from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

# GitHub-friendly colors
THEMES = {
    'dark': {
        'bg': '#0d1117',
        'text': '#c9d1d9',
        'text_secondary': '#8b949e',
        'bar': '#58a6ff',
        'bar_hover': '#79c0ff',
        'grid': '#21262d',
        'border': '#30363d',
        'accent': '#f78166',
        'title': '#f0f6fc',
    },
    'light': {
        'bg': '#ffffff',
        'text': '#24292f',
        'text_secondary': '#57606a',
        'bar': '#0969da',
        'bar_hover': '#218bff',
        'grid': '#d0d7de',
        'border': '#d0d7de',
        'accent': '#cf222e',
        'title': '#24292f',
    },
    'auto': None,  # Will generate both with prefers-color-scheme
}


def format_duration(seconds: float) -> str:
    """Format seconds into a readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


def _xml_escape(text: str) -> str:
    """Escape special XML characters in text content."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def generate_histogram_svg(
    histogram_data: list[dict],
    stats: dict,
    period_label: str = "This Month",
    theme: str = "auto",
    width: int = 840,
    height: int = 320,
) -> str:
    """Generate an SVG histogram chart."""

    # Chart dimensions
    margin_top = 60
    margin_right = 30
    margin_bottom = 60
    margin_left = 50
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom

    # Filter out empty trailing bins
    while histogram_data and histogram_data[-1]['count'] == 0:
        histogram_data = histogram_data[:-1]

    if not histogram_data:
        histogram_data = [{'bin': 'No data', 'count': 0, 'lo': 0, 'hi': 0}]

    max_count = max(d['count'] for d in histogram_data) or 1
    n_bins = len(histogram_data)
    bar_gap = 4
    bar_width = max(12, (chart_w - bar_gap * (n_bins - 1)) / n_bins)
    total_bar_width = bar_width * n_bins + bar_gap * (n_bins - 1)
    offset_x = (chart_w - total_bar_width) / 2

    # Stats for header
    avg = stats.get('avg_seconds', 0)
    median = stats.get('median_seconds', 0)
    count = stats.get('count', 0)
    p90 = stats.get('p90_seconds', 0)

    def make_chart(colors: dict, scheme_id: str = "") -> str:
        """Generate chart SVG content for a specific theme."""
        prefix = f"{scheme_id}-" if scheme_id else ""

        bars = []
        labels = []
        for i, d in enumerate(histogram_data):
            x = margin_left + offset_x + i * (bar_width + bar_gap)
            bar_h = (d['count'] / max_count) * chart_h if max_count > 0 else 0
            # Ensure non-zero counts get a minimum visible bar height
            if d['count'] > 0 and bar_h < 2:
                bar_h = 2
            y = margin_top + chart_h - bar_h
            radius = min(4, bar_width / 4)

            # Bar with rounded top corners
            if bar_h > 0:
                bars.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                    f'height="{bar_h:.1f}" rx="{radius}" fill="{colors["bar"]}" '
                    f'opacity="0.9">'
                    f'<title>{_xml_escape(d["bin"])}: {d["count"]} turns</title>'
                    f'</rect>'
                )
                # Count label above bar
                if d['count'] > 0:
                    bars.append(
                        f'<text x="{x + bar_width / 2:.1f}" y="{y - 6:.1f}" '
                        f'text-anchor="middle" fill="{colors["text_secondary"]}" '
                        f'font-size="11" font-family="ui-monospace,monospace">'
                        f'{d["count"]}</text>'
                    )

            # X-axis label
            labels.append(
                f'<text x="{x + bar_width / 2:.1f}" '
                f'y="{margin_top + chart_h + 20:.1f}" '
                f'text-anchor="middle" fill="{colors["text_secondary"]}" '
                f'font-size="11" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">'
                f'{_xml_escape(d["bin"])}</text>'
            )

        # Y-axis grid lines
        grid_lines = []
        n_grid = 4
        for i in range(n_grid + 1):
            y = margin_top + chart_h - (i / n_grid) * chart_h
            val = int(max_count * i / n_grid)
            grid_lines.append(
                f'<line x1="{margin_left}" y1="{y:.1f}" '
                f'x2="{width - margin_right}" y2="{y:.1f}" '
                f'stroke="{colors["grid"]}" stroke-width="1" stroke-dasharray="4,4"/>'
            )
            if i > 0:
                grid_lines.append(
                    f'<text x="{margin_left - 8}" y="{y + 4:.1f}" '
                    f'text-anchor="end" fill="{colors["text_secondary"]}" '
                    f'font-size="11" font-family="ui-monospace,monospace">{val}</text>'
                )

        # Stats header
        stats_items = [
            ("Avg", format_duration(avg)),
            ("Median", format_duration(median)),
            ("P90", format_duration(p90)),
            ("Turns", str(count)),
        ]

        stats_x = margin_left
        stat_elements = []
        for label, value in stats_items:
            stat_elements.append(
                f'<text x="{stats_x}" y="42" fill="{colors["text_secondary"]}" '
                f'font-size="11" '
                f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">'
                f'{label}</text>'
                f'<text x="{stats_x}" y="55" fill="{colors["text"]}" '
                f'font-size="13" font-weight="600" '
                f'font-family="ui-monospace,monospace">{value}</text>'
            )
            stats_x += 120

        return f"""
        {''.join(grid_lines)}
        {''.join(bars)}
        {''.join(labels)}
        <text x="{margin_left}" y="22" fill="{colors['title']}" font-size="16" font-weight="600"
              font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
            ⏱ Turn Duration · {period_label}
        </text>
        {''.join(stat_elements)}
        <text x="{width - margin_right}" y="{height - 8}" text-anchor="end"
              fill="{colors['text_secondary']}" font-size="10"
              font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
            generated by turntime
        </text>
        """

    if theme == 'auto':
        # Generate with CSS media query for auto dark/light
        dark = THEMES['dark']
        light = THEMES['light']
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <style>
      .light {{ display: block; }}
      .dark {{ display: none; }}
      @media (prefers-color-scheme: dark) {{
        .light {{ display: none; }}
        .dark {{ display: block; }}
      }}
    </style>
  </defs>
  <g class="light">
    <rect width="{width}" height="{height}" rx="6" fill="{light['bg']}" stroke="{light['border']}" stroke-width="1"/>
    {make_chart(light, 'light')}
  </g>
  <g class="dark">
    <rect width="{width}" height="{height}" rx="6" fill="{dark['bg']}" stroke="{dark['border']}" stroke-width="1"/>
    {make_chart(dark, 'dark')}
  </g>
</svg>"""
    else:
        colors = THEMES.get(theme, THEMES['dark'])
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="6" fill="{colors['bg']}" stroke="{colors['border']}" stroke-width="1"/>
  {make_chart(colors)}
</svg>"""

    return svg


def main():
    parser = argparse.ArgumentParser(description='Generate SVG histogram from turntime stats.')
    parser.add_argument(
        'input', type=str,
        help='Path to turntime JSON stats file (output of parse_sessions.py)'
    )
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='Output SVG file path (default: stdout)'
    )
    parser.add_argument(
        '--theme', choices=['auto', 'dark', 'light'], default='auto',
        help='Color theme (default: auto, respects prefers-color-scheme)'
    )
    parser.add_argument(
        '--period', type=str, default=None,
        help='Stats period key to display (default: month). Options: today, week, month, quarter, year, all'
    )
    parser.add_argument(
        '--width', type=int, default=840,
        help='SVG width in pixels (default: 840)'
    )
    parser.add_argument(
        '--height', type=int, default=320,
        help='SVG height in pixels (default: 320)'
    )
    args = parser.parse_args()

    # Load stats
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

    histogram = data.get('histogram', [])
    stats_all = data.get('stats', {})

    # Pick the stats period
    period_key = args.period or 'month'
    stats = stats_all.get(period_key, stats_all.get('all', {}))
    period_labels = {
        'today': 'Today',
        'week': 'This Week',
        'month': 'This Month',
        'quarter': 'This Quarter',
        'year': 'This Year',
        'all': 'All Time',
    }
    period_label = period_labels.get(period_key, period_key)

    svg = generate_histogram_svg(
        histogram_data=histogram,
        stats=stats,
        period_label=period_label,
        theme=args.theme,
        width=args.width,
        height=args.height,
    )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(svg)
        print(f"✅ Wrote histogram to {args.output}", file=sys.stderr)
    else:
        print(svg)


if __name__ == '__main__':
    main()
