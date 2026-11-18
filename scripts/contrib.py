"""Public contribution calendar -> animated monochrome contrib-heatmap.svg (stdlib only).

    python scripts/contrib.py [username]

Reads github.com/users/<user>/contributions (the same public page the profile
uses, no token). Runs daily from .github/workflows/update-graph.yml.
"""
import datetime as dt
import html
import os
import re
import sys
import urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_PROFILE_USER", "rikudi")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "contrib-heatmap.svg")

req = urllib.request.Request(f"https://github.com/users/{USER}/contributions",
                             headers={"User-Agent": "profile-graph-script"})
page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

days = {}  # id -> [date, level, count]
for m in re.finditer(r"<td\b[^>]*ContributionCalendar-day[^>]*>", page):
    tag = m.group(0)
    a = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
    if "data-date" in a:
        days[a["id"]] = [dt.date.fromisoformat(a["data-date"]), int(a.get("data-level", 0)), 0]
for m in re.finditer(r'<tool-tip\b[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
    if m.group(1) in days:
        n = re.match(r"\s*([\d,]+) contribution", m.group(2))
        days[m.group(1)][2] = int(n.group(1).replace(",", "")) if n else 0
if len(days) < 300:
    sys.exit(f"only {len(days)} days parsed, GitHub's markup may have changed")

cells = sorted(days.values())
first = cells[0][0]
start = first - dt.timedelta(days=(first.weekday() + 1) % 7)   # back to Sunday
total_m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", page)
total = total_m.group(1) if total_m else f"{sum(c[2] for c in cells):,}"
best = max(cells, key=lambda c: c[2])

# --- layout -----------------------------------------------------------------
CELL, GAP = 15, 4
STEP = CELL + GAP
weeks = (cells[-1][0] - start).days // 7 + 1
PAD, LEFT, TITLEBAR_H, MONTH_H = 24, 44, 30, 26
W = LEFT + weeks * STEP - GAP + PAD
GRID_TOP = TITLEBAR_H + 18 + MONTH_H
H = GRID_TOP + 7 * STEP - GAP + 58
BG, BG2, FRAME, MUTED, INK = "#0d1117", "#111722", "#30363d", "#7d8590", "#c9d1d9"
LEVEL = ["#161b22", "#2d333b", "#545d68", "#8b949e", "#e6edf3"]   # monochrome ramp
COL_STAGGER = 0.025

p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
     f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
     f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
     f'<stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
     f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
     f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
     f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>']
for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    p.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{c}"/>')
p.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" text-anchor="middle">'
         f'{html.escape(USER)}@github: ~$ git log --since="1 year ago" --graph</text>')

# month labels where a month starts
last_w = -9
for w in range(weeks):
    week = [start + dt.timedelta(days=7 * w + k) for k in range(7)]
    firsts = [d for d in week if d.day == 1]
    if firsts and w - last_w >= 3:
        p.append(f'<text x="{LEFT + w*STEP}" y="{GRID_TOP - 9}" fill="{MUTED}" font-size="11">'
                 f'{firsts[0].strftime("%b")}</text>')
        last_w = w
for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
    p.append(f'<text x="{PAD}" y="{GRID_TOP + r*STEP + CELL - 3}" fill="{MUTED}" font-size="11">{name}</text>')

# cells: each week column pops in, sweeping left -> right
for date, level, count in cells:
    w = (date - start).days // 7
    r = (date - start).days % 7
    x, y = LEFT + w * STEP, GRID_TOP + r * STEP
    title = f"{count} on {date.isoformat()}"
    p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{LEVEL[min(level, 4)]}" '
             f'opacity="0"><title>{title}</title><set attributeName="opacity" to="1" '
             f'begin="{0.3 + w*COL_STAGGER:.3f}s"/></rect>')

# status line
sy = H - 22
p.append(f'<line x1="0" y1="{H-44}" x2="{W}" y2="{H-44}" stroke="{FRAME}"/>')
p.append(f'<text x="{PAD}" y="{sy}" fill="{MUTED}" font-size="13"><tspan fill="{INK}">{total}</tspan> '
         f'contributions in the last year · best day <tspan fill="{INK}">{best[2]}</tspan></text>')
lx = W - PAD - 5 * (CELL - 3 + 4) - 76
p.append(f'<text x="{lx}" y="{sy}" fill="{MUTED}" font-size="11">Less</text>')
for i, c in enumerate(LEVEL):
    p.append(f'<rect x="{lx + 34 + i*(CELL+1)}" y="{sy-11}" width="{CELL-3}" height="{CELL-3}" rx="2" fill="{c}"/>')
p.append(f'<text x="{lx + 34 + 5*(CELL+1) + 4}" y="{sy}" fill="{MUTED}" font-size="11">More</text>')
p.append("</svg>")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(p))
print(f"wrote {os.path.normpath(OUT)}: {len(cells)} days, {total} contributions, {W}x{H}")
