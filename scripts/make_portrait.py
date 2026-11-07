"""Makes ascii-portrait.svg from the GitHub avatar: (1) cut the subject out, (2) smooth + sharpen the tones, (3) turn it into
high-detail ASCII art inside a terminal window that "types" itself in. Run once; run again if the profile photo changes.
    python scripts/make_portrait.py [photo.png]
Needs: pip install pillow numpy opencv-python-headless"""
import os, sys, io, json, html, urllib.request
import numpy as np, cv2
from PIL import Image

USER = os.environ.get('GH_USER', 'arshak-p')
OUT = os.environ.get('OUT_DIR', '.')
NAME = os.environ.get('DISPLAY_NAME', 'Arshak P')
COLS = int(os.environ.get('COLS', 170))

# ---------- 1) the photo ----------
if len(sys.argv) > 1:
    img = Image.open(sys.argv[1]).convert('RGB')
else:
    av = json.loads(urllib.request.urlopen(urllib.request.Request('https://api.github.com/users/' + USER, headers={'User-Agent': 'profile-art'})).read().decode())['avatar_url']
    img = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(av + ('&' if '?' in av else '?') + 's=1024', headers={'User-Agent': 'profile-art'})).read())).convert('RGB')
side = 900
img = img.resize((side, side), Image.LANCZOS)
bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

# ---------- 2) cut the subject out (hand-placed outline of head, hand, arm and shirt, softened) ----------
POLY = [(62,170),(78,105),(130,66),(200,62),(250,85),(272,150),(282,205),(270,245),(300,262),(360,282),(395,290),(430,300),(460,320),(460,460),(0,460),(0,330),(60,300),(105,268),(95,225)]
k = side / 460.0
fg = np.zeros((side, side), np.uint8)
cv2.fillPoly(fg, [np.array([(int(x * k), int(y * k)) for x, y in POLY], np.int32)], 255)
alpha = cv2.GaussianBlur(fg, (0, 0), 6).astype(np.float32) / 255.0

# ---------- 3) tones: smooth the texture, stretch the contrast, darken the fine lines ----------
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
smooth = gray
for _ in range(2): smooth = cv2.bilateralFilter(smooth, 9, 38, 9)
smooth = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6)).apply(smooth)
sub = smooth[fg > 128]
lo, hi = np.percentile(sub, [2, 97])
tone = np.clip((smooth.astype(np.float32) - lo) / (hi - lo + 1e-6), 0, 1)
tone = np.power(tone, 0.85)                                        # lift the shadows so the face keeps its shape
fine = cv2.GaussianBlur(smooth, (0, 0), 1.3).astype(np.float32)
coarse = cv2.GaussianBlur(smooth, (0, 0), 5).astype(np.float32)
lines = np.clip((coarse - fine) / 34.0, 0, 1)                      # eyes, brows, beard edge, glasses
out = np.clip(tone - 0.55 * lines, 0, 1) * 255
out = out * alpha + 255.0 * (1 - alpha)                            # subject on white, background becomes blank
ys, xs = np.where(fg > 128)
x0, x1, y0, y1 = max(xs.min() - 20, 0), min(xs.max() + 20, side), max(ys.min() - 20, 0), min(ys.max() + 20, side)
crop = out[y0:y1, x0:x1].astype(np.uint8)
h, w = crop.shape
sq = max(h, w)
canvas = np.full((sq, sq), 255, np.uint8); canvas[(sq - h) // 2:(sq - h) // 2 + h, (sq - w) // 2:(sq - w) // 2 + w] = crop
prepped = Image.fromarray(canvas, 'L')
prepped.save(os.path.join(OUT, 'portrait-prepped.png'))

# ---------- 4) ASCII ----------
ROWS = round(COLS * 8 / 15)                                        # a character is about 1:1.875, so this keeps the picture square
RAMP = " .`:-=+*cs#%@"
im = prepped.resize((COLS, ROWS), Image.LANCZOS); px = im.load()
GAMMA, WHITE = 1.35, 0.90
grid = []
for y in range(ROWS):
    row = ''
    for x in range(COLS):
        lum = (px[x, y] / 255.0) ** GAMMA
        row += ' ' if lum >= WHITE else RAMP[max(0, min(len(RAMP) - 1, int((1 - lum) * (len(RAMP) - 1) + .5)))]
    grid.append(row)
json.dump(grid, open(os.path.join(OUT, 'portrait-grid.json'), 'w'))

# ---------- 5) the terminal window ----------
ART_W_T = 800; CW = ART_W_T / COLS; CH = CW * 15 / 8
PAD, TB, SB = 20, 30, 30
AW, AH = COLS * CW, ROWS * CH
CW_, CH_ = AW + PAD * 2, TB + AH + SB + PAD
BG, BG2, FRAME, MUTE, INK = '#0d1117', '#111722', '#1f3a2b', '#86a393', '#19C652'
ROW_DUR = 5.5 / ROWS
p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" role="img" aria-label="ASCII-art portrait of %s">' % (CW_, CH_, CW_, CH_, NAME)]
p.append('<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient></defs>' % (BG2, BG))
p.append('<rect width="%d" height="%d" rx="12" fill="url(#bg)"/><rect x=".5" y=".5" width="%d" height="%d" rx="12" fill="none" stroke="%s"/>' % (CW_, CH_, CW_ - 1, CH_ - 1, FRAME))
p.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (TB, CW_, TB, FRAME))
for i, c in enumerate(['#ff5f56', '#ffbd2e', '#27c93f']): p.append('<circle cx="%d" cy="%d" r="5" fill="%s"/>' % (PAD + i * 16, TB / 2, c))
p.append('<text x="%.0f" y="%.0f" fill="%s" font-size="12" text-anchor="middle">%s@github: ~$ ./portrait.sh</text>' % (CW_ / 2, TB / 2 + 4, MUTE, USER.split('-')[0]))
top = TB + PAD * .35
fs = CH * .86
for ry, line in enumerate(grid):
    y = top + ry * CH + CH * .74; ry_top = top + ry * CH; delay = ry * ROW_DUR
    t = '<text xml:space="preserve" x="%d" y="%.1f" fill="%s" font-size="%.1f" textLength="%.1f" lengthAdjust="spacing">%s</text>' % (PAD, y, INK, fs, AW, html.escape(line))
    p.append('<clipPath id="r%d"><rect x="%d" y="%.1f" height="%.2f" width="0"><animate attributeName="width" from="0" to="%.1f" begin="%.3fs" dur="%.2fs" fill="freeze"/></rect></clipPath><g clip-path="url(#r%d)">%s</g>' % (ry, PAD, ry_top, CH, AW, delay, ROW_DUR, ry, t))
    p.append('<rect y="%.1f" width="%.2f" height="%.2f" fill="%s" opacity="0"><animate attributeName="x" from="%d" to="%.1f" begin="%.3fs" dur="%.2fs" fill="freeze"/><set attributeName="opacity" to=".85" begin="%.3fs"/><set attributeName="opacity" to="0" begin="%.3fs"/></rect>' % (ry_top + 1, CW, CH - 2, INK, PAD, PAD + AW, delay, ROW_DUR, delay, delay + ROW_DUR))
ly = TB + AH + PAD * .35
p.append('<line x1="0" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>' % (ly, CW_, ly, FRAME))
p.append('<text x="%d" y="%.1f" fill="%s" font-size="13">%s@github:~$ whoami <tspan fill="%s">%s</tspan></text>' % (PAD, ly + 19, MUTE, USER.split('-')[0], INK, html.escape(NAME)))
cx = PAD + len('%s@github:~$ whoami %s ' % (USER.split('-')[0], NAME)) * 13 * .6
p.append('<rect x="%.1f" y="%.1f" width="8" height="14" fill="%s"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.51;1" dur="1s" repeatCount="indefinite"/></rect></svg>' % (cx, ly + 7, INK))
svg = ''.join(p)
open(os.path.join(OUT, 'ascii-portrait.svg'), 'w', encoding='utf-8').write(svg)
print('portrait: %d x %d characters, svg %d KB, canvas %d x %d' % (COLS, ROWS, len(svg) // 1024, CW_, CH_))
