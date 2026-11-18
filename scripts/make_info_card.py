"""neofetch-style info card -> info-card.svg (stdlib only).

Edit HOST and ROWS below, then:  python scripts/make_info_card.py
Rows type themselves in one after another (SMIL, runs inside GitHub's <img>).
Size matches the portrait: shown at width 490 next to the portrait at 370.
"""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "info-card.svg")

HOST = "riku@github"
ROWS = [
    ("Role", "Software Developer & Entrepreneur"),
    ("Company", "Tmi Riku Kaartoaho"),
    ("Study", "Engineering · Metropolia UAS"),
    ("Location", "Helsinki, Finland"),
    ("Focus", "Building with AI"),
    None,
    ("Frontend", "TypeScript · React · Next.js · Svelte"),
    ("Backend", "Node.js · Python · FastAPI · C#"),
    ("Data", "PostgreSQL · MongoDB"),
    ("Ops", "Docker · AWS · Vercel · Cloudflare"),
    ("3D", "three.js · Blender · Unity"),
    None,
    ("Featured", "Hakkapeliitta 01 · 3D web demo"),
    ("", "tyredemo.rikukaartoaho.workers.dev"),
]

W, H = 980, 771          # 490 x 385 on the profile, same height as the portrait (370 x 385)
PAD = 40
TITLEBAR_H = 60
BG, BG2, FRAME = "#0d1117", "#111722", "#30363d"
MUTED, INK, KEY = "#7d8590", "#c9d1d9", "#e6edf3"
FS = 25                  # font size (12.5 px on the profile)
LINE = 38
KEY_W = 170
ROW_DUR, STAGGER, START = 0.35, 0.16, 0.6
CHAR_W = FS * 0.6        # monospace advance

p = []
p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">')
p.append(f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
         f'<stop offset="1" stop-color="{BG}"/></linearGradient></defs>')
p.append(f'<rect width="{W}" height="{H}" rx="24" fill="url(#bg)"/>')
p.append(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="24" fill="none" stroke="{FRAME}" stroke-width="2"/>')
p.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}" stroke-width="2"/>')
for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    p.append(f'<circle cx="{PAD + i*32}" cy="{TITLEBAR_H/2}" r="10" fill="{c}"/>')
p.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 8}" fill="{MUTED}" font-size="24" text-anchor="middle">'
         f'{HOST}: ~$ neofetch</text>')


def typed(i, y, inner, width):
    """One row, revealed left-to-right by a clip wipe."""
    d = START + i * STAGGER
    p.append(f'<clipPath id="c{i}"><rect x="{PAD}" y="{y - LINE + 10}" height="{LINE}" width="0">'
             f'<animate attributeName="width" from="0" to="{width:.0f}" begin="{d:.2f}s" dur="{ROW_DUR}s" '
             f'fill="freeze"/></rect></clipPath>')
    p.append(f'<g clip-path="url(#c{i})">{inner}</g>')


y = TITLEBAR_H + 60
typed(0, y, f'<text x="{PAD}" y="{y}" font-size="{FS}" fill="{KEY}" font-weight="700">{HOST}</text>',
      CHAR_W * len(HOST) + 10)
y += LINE * 0.75
typed(1, y, f'<text x="{PAD}" y="{y}" font-size="{FS}" fill="{FRAME}">{"─" * len(HOST)}</text>',
      CHAR_W * len(HOST) + 10)
y += LINE

i = 2
for row in ROWS:
    if row is None:
        y += LINE * 0.45
        continue
    k, v = row
    key = f'<tspan fill="{KEY}" font-weight="700">{html.escape(k)}</tspan>' if k else ""
    inner = (f'<text x="{PAD}" y="{y}" font-size="{FS}">{key}</text>'
             f'<text x="{PAD + KEY_W}" y="{y}" font-size="{FS}" fill="{INK}">{html.escape(v)}</text>')
    typed(i, y, inner, KEY_W + CHAR_W * len(v) + 10)
    y += LINE
    i += 1

# neofetch colour blocks, in greys to keep the card monochrome
y += 10
d = START + i * STAGGER
for j, c in enumerate(["#21262d", "#30363d", "#484f58", "#6e7681", "#8b949e", "#b1bac4", "#c9d1d9", "#f0f6fc"]):
    p.append(f'<rect x="{PAD + j*44}" y="{y}" width="38" height="22" rx="3" fill="{c}" opacity="0">'
             f'<set attributeName="opacity" to="1" begin="{d + j*0.05:.2f}s"/></rect>')

p.append("</svg>")
with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(p))
print("wrote", os.path.normpath(OUT), "rows end at y =", round(y + 22), "of", H)
