"""Portrait photo -> monochrome ASCII portrait that types itself in (avi-ascii.svg).

No installs: runs inside Blender's bundled Python (numpy + image loading):

    blender --background --factory-startup --python scripts/make_ascii_svg.py -- photo.jpg [out.svg]

Set STATIC=1 to write the final frame without animation (for previews).
Works best with a head-and-shoulders photo on a plain background: the
background is flood-filled from the image border and becomes blank space.
"""
import html
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    sys.exit("usage: blender -b -P make_ascii_svg.py -- photo.jpg [out.svg]")
SRC = os.path.abspath(argv[0])
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, "..", "avi-ascii.svg")

# ---- tuning ---------------------------------------------------------------
COLS, ROWS = 100, 53          # cells are 8 x 15 px, so the art is ~square
CELL_W, CELL_H = 8, 15
RAMP = " .`:-=+*cs#%@"        # light (sparse) -> dark (dense); bg maps to blank
GAMMA = float(os.environ.get("GAMMA", 1.7))  # >1 pushes mid-tones into denser characters
WHITE_FLOOR = float(os.environ.get("WHITE_FLOOR", 0.97))  # luminance above this becomes a space
BG_TOL = float(os.environ.get("BG_TOL", 0.24))  # colour distance still counted as background
CROP_TOP = float(os.environ.get("CROP_TOP", 0.0))  # 0..1, shift the square crop up/down
ZOOM = float(os.environ.get("ZOOM", 0.85))        # >1 crops tighter, <1 zooms out (pads the edges)
DARK_BG = float(os.environ.get("DARK_BG", 0.2))    # e.g. 0.18: border-touching near-black areas count as bg
HANDLE, NAME = "riku", "Riku Kaartoaho"

# ---- 1. load ---------------------------------------------------------------
img = bpy.data.images.load(SRC)
w, h = img.size
# 8-bit images come back as raw display values / 255 (no colour management)
px = np.clip(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3], 0, 1)

# crop to the art's aspect ratio, centred (tweak with CROP_TOP / ZOOM)
aspect = (COLS * CELL_W) / (ROWS * CELL_H)
if ZOOM < 1:  # zoom out: pad with the border colour so the whole head fits
    py, pxw = int(h * (1 / ZOOM - 1) / 2), int(w * (1 / ZOOM - 1) / 2)
    canvas = np.pad(px, ((py, py), (pxw, pxw), (0, 0)), mode="edge")  # continue wall and shoulders
    px, ZOOM = canvas, 1.0
    h, w = px.shape[:2]
cw = min(w, h * aspect) / ZOOM
ch = cw / aspect
x0 = int((w - cw) / 2)
y0 = int((h - ch) * (0.5 if not CROP_TOP else CROP_TOP))
px = px[y0:y0 + int(ch), x0:x0 + int(cw)]

# work at a modest resolution
def resize(a, nw, nh):
    """Box-average resize via summed-area table."""
    yb = np.linspace(0, a.shape[0], nh + 1).astype(int)
    xb = np.linspace(0, a.shape[1], nw + 1).astype(int)
    s = np.pad(a.cumsum(0).cumsum(1), ((1, 0), (1, 0)) + ((0, 0),) * (a.ndim - 2))
    tot = s[yb[1:]][:, xb[1:]] - s[yb[:-1]][:, xb[1:]] - s[yb[1:]][:, xb[:-1]] + s[yb[:-1]][:, xb[:-1]]
    area = np.outer(np.diff(yb), np.diff(xb))
    return tot / (area[..., None] if a.ndim == 3 else area)

WW, WH = 400, int(400 / aspect)
small = resize(px, WW, WH)

# ---- 2. background: flood fill from the border over bg-coloured pixels ------
border = np.concatenate([small[0], small[-1], small[:, 0], small[:, -1]])
bg_col = np.median(border, axis=0)
near = np.linalg.norm(small - bg_col, axis=2) < BG_TOL * np.sqrt(3)
if DARK_BG:  # also clear near-black objects touching the border (chair, dark clothes)
    near |= small.mean(axis=2) < DARK_BG
bg = np.zeros_like(near)
bg[0], bg[-1], bg[:, 0], bg[:, -1] = near[0], near[-1], near[:, 0], near[:, -1]
for _ in range(WW + WH):
    grown = bg.copy()
    grown[1:] |= bg[:-1]; grown[:-1] |= bg[1:]; grown[:, 1:] |= bg[:, :-1]; grown[:, :-1] |= bg[:, 1:]
    grown &= near
    if (grown == bg).all():
        break
    bg = grown
# soften the mask edge a little
mask = 1.0 - resize(bg.astype(np.float32), WW, WH)
for _ in range(2):
    m = np.pad(mask, 1, mode="edge")
    mask = (m[:-2, 1:-1] + m[2:, 1:-1] + m[1:-1, :-2] + m[1:-1, 2:] + 4 * mask) / 8

# ---- 3. luminance + local contrast on the subject only ----------------------
lum = small @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
subj = lum[mask > 0.5]
if subj.size:
    lo, hi = np.percentile(subj, [2, 98])
    lum = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
# unsharp mask with a wide box blur ~ cheap local contrast
k = 15
c = np.pad(lum, k, mode="edge").cumsum(0).cumsum(1)
c = np.pad(c, ((1, 0), (1, 0)))
blur = (c[2*k+1:, 2*k+1:] - c[:-2*k-1, 2*k+1:] - c[2*k+1:, :-2*k-1] + c[:-2*k-1, :-2*k-1]) / (2*k+1) ** 2
lum = np.clip(lum + 0.6 * (lum - blur), 0, 1)
lum = lum * mask + 1.0 * (1 - mask)          # background -> white -> blank

grid = np.clip(resize(lum, COLS, ROWS), 0, 1)  # float32 summed areas can dip below 0
rows_txt = []
for y in range(ROWS):
    line = []
    for x in range(COLS):
        v = grid[y, x] ** GAMMA
        if v >= WHITE_FLOOR:
            line.append(" ")
        else:
            line.append(RAMP[max(0, min(len(RAMP) - 1, int((1 - v) * (len(RAMP) - 1) + 0.5)))])
    rows_txt.append("".join(line).rstrip().ljust(COLS))

# ---- 4. SVG (terminal window, rows wipe in top -> bottom) --------------------
PAD, TITLEBAR_H, STATUS_H = 20, 30, 30
ART_W, ART_H = COLS * CELL_W, ROWS * CELL_H
W, H = ART_W + 2 * PAD, TITLEBAR_H + ART_H + STATUS_H + PAD
BG, BG2, FRAME, MUTED, INK = "#0d1117", "#111722", "#30363d", "#7d8590", "#c9d1d9"
ROW_DUR = STAGGER = 0.11
STATIC = bool(os.environ.get("STATIC"))

p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
     f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
     f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG2}"/>'
     f'<stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
     f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
     f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
     f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>']
for i, col in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    p.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{col}"/>')
p.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" text-anchor="middle">'
         f'{HANDLE}@github: ~$ ./portrait.sh</text>')

top = TITLEBAR_H + PAD * 0.35
fs = CELL_H * 0.86
for r, line in enumerate(rows_txt):
    if not line.strip():
        continue
    ry = top + r * CELL_H
    text = (f'<text xml:space="preserve" x="{PAD}" y="{ry + CELL_H*0.74:.1f}" fill="{INK}" font-size="{fs:.1f}" '
            f'textLength="{ART_W}" lengthAdjust="spacing">{html.escape(line)}</text>')
    if STATIC:
        p.append(text)
        continue
    d = r * STAGGER
    p.append(f'<clipPath id="r{r}"><rect x="{PAD}" y="{ry:.1f}" height="{CELL_H}" width="0">'
             f'<animate attributeName="width" from="0" to="{ART_W}" begin="{d:.2f}s" dur="{ROW_DUR}s" '
             f'fill="freeze"/></rect></clipPath><g clip-path="url(#r{r})">{text}</g>')
    p.append(f'<rect y="{ry+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{INK}" opacity="0">'
             f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{d:.2f}s" dur="{ROW_DUR}s" '
             f'fill="freeze"/><set attributeName="opacity" to="0.85" begin="{d:.2f}s"/>'
             f'<set attributeName="opacity" to="0" begin="{d+ROW_DUR:.2f}s"/></rect>')

sl = TITLEBAR_H + ART_H + PAD * 0.35
sy = sl + 19
prompt = f"{HANDLE}@github:~$ whoami "
p.append(f'<line x1="0" y1="{sl:.1f}" x2="{W}" y2="{sl:.1f}" stroke="{FRAME}"/>')
p.append(f'<text x="{PAD}" y="{sy:.1f}" fill="{MUTED}" font-size="13">{prompt}<tspan fill="{INK}">{NAME}</tspan></text>')
cx = PAD + (len(prompt) + len(NAME)) * 13 * 0.6 + 4
p.append(f'<rect x="{cx:.0f}" y="{sy-12:.1f}" width="8" height="14" fill="{INK}"><animate attributeName="opacity" '
         f'values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>')
p.append("</svg>")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(p))
print(f"wrote {OUT}: {W}x{H}, background {bg.mean()*100:.0f}% of the crop")
