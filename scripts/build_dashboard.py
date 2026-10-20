"""SVG dashboard renderer adapted from shashanthnetha/shashanthnetha."""
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape


def esc(text) -> str:
    if text is None:
        return ""
    return xml_escape(str(text), entities={'"': "&quot;", "'": "&#39;"})


def relative_time(iso_date: str) -> str:
    if not iso_date:
        return "recently"
    try:
        then = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        seconds = int((now - then).total_seconds())
        if seconds < 0:
            return "just now"
        if seconds < 3600:
            return f"{max(seconds // 60, 1)}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        if seconds < 86400 * 30:
            return f"{seconds // 86400}d ago"
        return then.strftime("%b %Y")
    except Exception:
        return "recently"


def compute_streaks(days: list) -> tuple:
    longest = run = 0
    for d in days:
        if d.get("contributionCount", 0) > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    current = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx].get("contributionCount", 0) == 0:
        idx -= 1
    while idx >= 0 and days[idx].get("contributionCount", 0) > 0:
        current += 1
        idx -= 1
    return current, longest


def fmt_num(val, suffix="") -> str:
    if val is None:
        return "—"
    if isinstance(val, int):
        return f"{val:,}{suffix}"
    return str(val)


def render_svg(data: dict) -> str:
    sans = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    mono = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
    now_utc = datetime.now(timezone.utc).strftime("%b %d, %Y · %H:%M UTC")

    card_w = 880
    card_h = 360

    # Format languages progress bar
    langs = data["languages"]
    bar_segments = []
    legend_items = []
    current_x = 0
    total_bar_w = 776

    for name, count, color, pct_str in langs:
        pct_float = float(pct_str.rstrip("%"))
        seg_w = (pct_float / 100.0) * total_bar_w
        if seg_w > 0:
            bar_segments.append(
                f'<rect x="{52 + current_x}" y="242" width="{seg_w}" height="10" fill="{color}" opacity="0.9"/>'
            )
            current_x += seg_w

        legend_items.append(
            f'<g>'
            f'<circle cx="{0}" cy="0" r="4" fill="{color}"/>'
            f'<text x="10" y="4" font-family="{sans}" font-size="11" font-weight="600" fill="#E2E8F0">{esc(name)} <tspan fill="#64748B" font-weight="400">({pct_str})</tspan></text>'
            f'</g>'
        )

    # Render Legend Group
    legend_svg = []
    leg_x = 52
    for item in legend_items:
        legend_svg.append(f'<g transform="translate({leg_x}, 268)">{item}</g>')
        leg_x += 150

    svg = f'''<svg width="{card_w}" height="{card_h}" viewBox="0 0 {card_w} {card_h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Live Telemetry Dashboard for {esc(data['username'])}">
  <defs>
    <linearGradient id="dbBg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#161b22"/>
      <stop offset="100%" stop-color="#0d1117"/>
    </linearGradient>

    <linearGradient id="topBorder" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#8B5CF6"/>
      <stop offset="35%" stop-color="#38BDF8"/>
      <stop offset="70%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#F472B6"/>
    </linearGradient>

    <linearGradient id="cardGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8B5CF6" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#8B5CF6" stop-opacity="0.02"/>
    </linearGradient>

    <linearGradient id="cardGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F59E0B" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.02"/>
    </linearGradient>

    <linearGradient id="cardGrad3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10B981" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#10B981" stop-opacity="0.02"/>
    </linearGradient>

    <linearGradient id="cardGrad4" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#38BDF8" stop-opacity="0.02"/>
    </linearGradient>

    <filter id="glowGreen" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Container Base -->
  <rect width="{card_w}" height="{card_h}" rx="16" fill="url(#dbBg)"/>
  <rect width="{card_w}" height="{card_h}" rx="16" fill="none" stroke="#30363d" stroke-width="1"/>

  <!-- Glowing Top Border Accent -->
  <path d="M 0 16 A 16 16 0 0 1 16 0 L {card_w - 16} 0 A 16 16 0 0 1 {card_w} 16" fill="none" stroke="url(#topBorder)" stroke-width="3"/>

  <!-- Header Row -->
  <g transform="translate(52, 38)">
    <circle cx="0" cy="0" r="5" fill="#10B981" filter="url(#glowGreen)"/>
    <circle cx="0" cy="0" r="5" fill="#10B981"/>
    <text x="14" y="4" font-family="{mono}" font-size="12" font-weight="700" fill="#E2E8F0" letter-spacing="1">LIVE TELEMETRY &amp; METRICS ENGINE</text>
    <text x="776" y="4" text-anchor="end" font-family="{mono}" font-size="11" fill="#64748B">Verified: {esc(now_utc)}</text>
  </g>

  <!-- Divider Line -->
  <line x1="52" y1="56" x2="828" y2="56" stroke="#21262d" stroke-width="1"/>

  <!-- 4 Stat Block Cards Grid (Row 1) -->
  <!-- Block 1: Codebase & Repos (Purple) -->
  <g transform="translate(52, 72)">
    <rect width="180" height="135" rx="12" fill="url(#cardGrad1)" stroke="#8B5CF6" stroke-opacity="0.3" stroke-width="1"/>
    <text x="16" y="24" font-family="{mono}" font-size="10" font-weight="700" fill="#C4B5FD" letter-spacing="0.5">CODEBASE SCOPE</text>
    <text x="16" y="60" font-family="{sans}" font-size="28" font-weight="800" fill="#F3E8FF">{fmt_num(data['repos'])}</text>
    <text x="16" y="78" font-family="{sans}" font-size="11" fill="#94A3B8">Public Repositories</text>
    <line x1="16" y1="92" x2="164" y2="92" stroke="#8B5CF6" stroke-opacity="0.2" stroke-width="1"/>
    <text x="16" y="114" font-family="{mono}" font-size="11" fill="#DDD6FE">⭐ {fmt_num(data['stars'])} stars · 🍴 {fmt_num(data['forks'])} forks</text>
  </g>

  <!-- Block 2: Development Velocity (Amber) -->
  <g transform="translate(248, 72)">
    <rect width="180" height="135" rx="12" fill="url(#cardGrad2)" stroke="#F59E0B" stroke-opacity="0.3" stroke-width="1"/>
    <text x="16" y="24" font-family="{mono}" font-size="10" font-weight="700" fill="#FDE68A" letter-spacing="0.5">DEV VELOCITY</text>
    <text x="16" y="60" font-family="{sans}" font-size="28" font-weight="800" fill="#FEF3C7">{fmt_num(data['contributions'])}</text>
    <text x="16" y="78" font-family="{sans}" font-size="11" fill="#94A3B8">Yearly Contributions</text>
    <line x1="16" y1="92" x2="164" y2="92" stroke="#F59E0B" stroke-opacity="0.2" stroke-width="1"/>
    <text x="16" y="114" font-family="{mono}" font-size="11" fill="#FDE68A">💻 {fmt_num(data['commits'])} total commits</text>
  </g>

  <!-- Block 3: Consistency & Streaks (Emerald) -->
  <g transform="translate(444, 72)">
    <rect width="180" height="135" rx="12" fill="url(#cardGrad3)" stroke="#10B981" stroke-opacity="0.3" stroke-width="1"/>
    <text x="16" y="24" font-family="{mono}" font-size="10" font-weight="700" fill="#A7F3D0" letter-spacing="0.5">CONSISTENCY</text>
    <text x="16" y="60" font-family="{sans}" font-size="28" font-weight="800" fill="#ECFDF5">{fmt_num(data['streak'], 'd')}</text>
    <text x="16" y="78" font-family="{sans}" font-size="11" fill="#94A3B8">Current Streak 🔥</text>
    <line x1="16" y1="92" x2="164" y2="92" stroke="#10B981" stroke-opacity="0.2" stroke-width="1"/>
    <text x="16" y="114" font-family="{mono}" font-size="11" fill="#A7F3D0">🏆 Best: {fmt_num(data['longest_streak'], 'd')} streak</text>
  </g>

  <!-- Block 4: Open Source Activity (Sky Blue) -->
  <g transform="translate(640, 72)">
    <rect width="188" height="135" rx="12" fill="url(#cardGrad4)" stroke="#38BDF8" stroke-opacity="0.3" stroke-width="1"/>
    <text x="16" y="24" font-family="{mono}" font-size="10" font-weight="700" fill="#BAE6FD" letter-spacing="0.5">OPEN SOURCE</text>
    <text x="16" y="60" font-family="{sans}" font-size="28" font-weight="800" fill="#E0F2FE">{fmt_num(data['prs'])}</text>
    <text x="16" y="78" font-family="{sans}" font-size="11" fill="#94A3B8">Pull Requests Opened</text>
    <line x1="16" y1="92" x2="172" y2="92" stroke="#38BDF8" stroke-opacity="0.2" stroke-width="1"/>
    <text x="16" y="114" font-family="{mono}" font-size="11" fill="#BAE6FD">👥 {fmt_num(data['followers'])} followers · {fmt_num(data['issues'])} issues</text>
  </g>

  <!-- Row 2: Top Languages Progress Bar -->
  <g transform="translate(52, 224)">
    <text x="0" y="0" font-family="{mono}" font-size="10" font-weight="700" fill="#94A3B8" letter-spacing="0.5">MOST USED LANGUAGES</text>
  </g>

  <!-- Progress Bar Base Container -->
  <rect x="52" y="242" width="776" height="10" rx="5" fill="#21262d"/>
  <g clip-path="url(#barClip)">
    <clipPath id="barClip">
      <rect x="52" y="242" width="776" height="10" rx="5"/>
    </clipPath>
    {"".join(bar_segments)}
  </g>

  <!-- Language Legend Below Bar -->
  {"".join(legend_svg)}

  <!-- Row 3: Latest Commit Dispatch Line (Bottom) -->
  <line x1="52" y1="304" x2="828" y2="304" stroke="#21262d" stroke-width="1"/>
  <g transform="translate(52, 328)">
    <circle cx="0" cy="0" r="4" fill="#38BDF8"/>
    <text x="12" y="4" font-family="{mono}" font-size="11" fill="#64748B">
      LATEST DISPATCH: <tspan fill="#38BDF8" font-weight="600">{esc(data['active_repo'])}</tspan> <tspan fill="#94A3B8">"{esc(data['commit_msg'])}"</tspan> <tspan fill="#64748B">({esc(data['active_when'])})</tspan>
    </text>
  </g>
</svg>
'''
    return svg
