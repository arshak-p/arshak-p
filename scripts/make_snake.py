"""Draws snake.svg: a snake that eats your last year of GitHub contributions, square by square.
Needs GH_TOKEN and GH_USER. Pure SVG (SMIL) animation, no third-party service."""
import os, json, urllib.request

USER = os.environ.get('GH_USER', 'arshak-p')
TOKEN = os.environ.get('GH_TOKEN', '')
OUT = os.environ.get('OUT_DIR', '.')

def call(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
        headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-art'})
    with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read().decode())

q = 'query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}'
cal = call('https://api.github.com/graphql', {'query': q, 'variables': {'l': USER}})['data']['user']['contributionsCollection']['contributionCalendar']
weeks = [[(d['date'], d['contributionCount']) for d in w['contributionDays']] for w in cal['weeks']]
total = cal['totalContributions']

CS, GAP, X0, Y0 = 12, 3, 24, 46
STEP = CS + GAP
W = X0 + len(weeks) * STEP + 22
H = Y0 + 7 * STEP + 40
EMPTY = '#15251c'
SHADES = ['#15251c', '#1d5a35', '#19a34a', '#19C652', '#7BE8A0']
mx = max([c for w in weeks for _, c in w] + [1])
lvl = lambda c: 0 if c <= 0 else 1 if c / mx <= .25 else 2 if c / mx <= .5 else 3 if c / mx <= .75 else 4

# the snake walks up and down every week column, with a run-in before and a run-out after the grid
L = 7                                                    # snake length (squares)
grid = []                                                # (week, day) in the order the snake passes them
for wi in range(len(weeks)):
    days = range(7) if wi % 2 == 0 else range(6, -1, -1)
    grid += [(wi, di) for di in days]
cx = lambda wi: X0 + wi * STEP + CS / 2
cy = lambda di: Y0 + di * STEP + CS / 2
pre = [(cx(0) - (L - i) * STEP, cy(0)) for i in range(L)]
last_wi, last_di = grid[-1]
post = [(cx(last_wi) + (i + 1) * STEP, cy(last_di)) for i in range(L)]
pts = pre + [(cx(w), cy(d)) for w, d in grid] + post
SPEED = 0.055                                             # seconds per square
DUR = len(pts) * SPEED
path = 'M' + ' L'.join('%.1f %.1f' % p for p in pts)

cells = ''
for g, (wi, di) in enumerate(grid):
    date, c = weeks[wi][di]
    x, y = X0 + wi * STEP, Y0 + di * STEP
    if c > 0:
        eaten = (L + g) * SPEED                           # the head reaches this square at this time
        frac = min(max(eaten / DUR, 0.001), 0.999)
        cells += '<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="%s"><title>%s: %d</title><animate attributeName="fill" calcMode="discrete" values="%s;%s" keyTimes="0;%.4f" dur="%.1fs" repeatCount="indefinite"/></rect>' % (
            x, y, CS, CS, SHADES[lvl(c)], date, c, SHADES[lvl(c)], EMPTY, frac, DUR)
    else:
        cells += '<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="%s"/>' % (x, y, CS, CS, EMPTY)

body = ''
for k in range(L):                                        # k = 0 is the head, then the body behind it
    size = CS if k == 0 else max(6, CS - k)
    colour = '#19C652' if k == 0 else '#%02x%02x%02x' % (int(25 + (10 - 25) * k / L), int(198 - 100 * k / L), int(82 - 30 * k / L))
    hide = '<set attributeName="visibility" to="hidden" begin="0s" dur="%.2fs"/>' % (k * SPEED) if k else ''
    eyes = '<circle cx="2" cy="-2" r="1.4" fill="#01190E"/><circle cx="2" cy="2" r="1.4" fill="#01190E"/>' if k == 0 else ''
    body = '<g><rect x="%.1f" y="%.1f" width="%d" height="%d" rx="%.1f" fill="%s"/>%s%s<animateMotion path="%s" dur="%.1fs" begin="%.3fs" repeatCount="indefinite" rotate="auto"/></g>' % (
        -size / 2, -size / 2, size, size, size * .38, colour, eyes, hide, path, DUR, k * SPEED) + body   # head is drawn last, on top

svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="A snake eating %d GitHub contributions from the last year">
<rect width="%d" height="%d" rx="14" fill="#0d1117" stroke="#1f3a2b"/>
<text x="24" y="30" font-family="Consolas,Menlo,'Courier New',monospace" font-size="14" fill="#19C652">%s@github ~ $ ./snake.sh</text>
<text x="%d" y="30" text-anchor="end" font-family="'Segoe UI',Helvetica,Arial,sans-serif" font-size="12" fill="#86a393">%s contributions in the last year</text>
%s%s
</svg>
""" % (W, H, W, H, total, W, H, USER.split('-')[0], W - 24, format(total, ','), cells, body)
open(os.path.join(OUT, 'snake.svg'), 'w', encoding='utf-8').write(svg)
print('snake.svg: %d squares, loop %.0fs, %d KB' % (len(grid), DUR, len(svg) // 1024))
