"""Turns the GitHub avatar into an ASCII-art portrait (ascii-portrait.svg, 420 x 380). Run once; run again if the profile photo changes."""
import os, io, json, urllib.request
from PIL import Image, ImageOps, ImageEnhance

USER = os.environ.get('GH_USER', 'arshak-p')
OUT = os.environ.get('OUT_DIR', '.')
req = urllib.request.Request('https://api.github.com/users/' + USER, headers={'User-Agent': 'profile-art'})
avatar = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())['avatar_url']
img = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(avatar + ('&' if '?' in avatar else '?') + 's=460', headers={'User-Agent': 'profile-art'}), timeout=30).read())).convert('L')
COLS = 84
ROWS = int(COLS * img.height / img.width * 0.5)          # characters are about twice as tall as wide
img = ImageOps.autocontrast(img.resize((COLS, ROWS), Image.LANCZOS), cutoff=2)
img = ImageEnhance.Contrast(img).enhance(1.35)
RAMP = ' .\'`^",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$'
px = img.load()
lines = []
for y in range(ROWS):
    lines.append(''.join(RAMP[min(len(RAMP) - 1, int((255 - px[x, y]) / 255 * (len(RAMP) - 1)))] if False else RAMP[int(px[x, y] / 255 * (len(RAMP) - 1))] for x in range(COLS)))
# dark pixels (hair, outline) get the dense characters, so invert the ramp
lines = [''.join(RAMP[len(RAMP) - 1 - int(px[x, y] / 255 * (len(RAMP) - 1))] for x in range(COLS)) for y in range(ROWS)]
FS, LH = 7.2, 7.6
W, H = 420, 380
x0 = (W - COLS * FS * 0.6) / 2
y0 = (H - ROWS * LH) / 2 + LH
import html
rows = ''.join('<tspan x="%.1f" y="%.1f">%s</tspan>' % (x0, y0 + i * LH, html.escape(l)) for i, l in enumerate(lines))
svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="ASCII-art portrait of %s">
<style>
  :root{--bg:#ffffff;--ink:#0b6b34;--line:#d5e3da}
  @media (prefers-color-scheme: dark){:root{--bg:#0d1117;--ink:#19C652;--line:#1f3a2b}}
  .ascii{font-family:Consolas,Menlo,'Courier New',monospace;font-size:%.1fpx;fill:var(--ink);white-space:pre;animation:glow 6s ease-in-out infinite}
  @keyframes glow{0%%,100%%{opacity:.88}50%%{opacity:1}}
  @media (prefers-reduced-motion: reduce){.ascii{animation:none}}
</style>
<rect width="%d" height="%d" rx="14" fill="var(--bg)" stroke="var(--line)"/>
<text class="ascii" xml:space="preserve">%s</text>
</svg>
""" % (W, H, W, H, USER, FS, W, H, rows)
open(os.path.join(OUT, 'ascii-portrait.svg'), 'w', encoding='utf-8').write(svg)
print('ascii portrait: %d x %d characters, %d KB' % (COLS, ROWS, len(svg) // 1024))
