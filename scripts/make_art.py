"""Builds contrib-heatmap.svg and stats.svg for the GitHub profile from live GitHub data.
Run by .github/workflows/update-profile-art.yml every day. Needs GH_TOKEN (the workflow's built-in token) and GH_USER.
No third-party services: everything is drawn here as SVG."""
import os, json, datetime, urllib.request, html

USER = os.environ.get('GH_USER', 'arshak-p')
TOKEN = os.environ.get('GH_TOKEN', '')
OUT = os.environ.get('OUT_DIR', '.')

def call(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
        headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-art'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())

# ---------- data ----------
q = '''query($l:String!){user(login:$l){contributionsCollection{
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}
  commitContributionsByRepository(maxRepositories:100){repository{nameWithOwner}}
  pullRequestContributionsByRepository(maxRepositories:100){repository{nameWithOwner}}
  issueContributionsByRepository(maxRepositories:100){repository{nameWithOwner}}}}}'''
cc = call('https://api.github.com/graphql', {'query': q, 'variables': {'l': USER}})['data']['user']['contributionsCollection']
cal = cc['contributionCalendar']
worked_on = {x['repository']['nameWithOwner'] for k in ('commitContributionsByRepository', 'pullRequestContributionsByRepository', 'issueContributionsByRepository') for x in cc[k]}
weeks = [[(d['date'], d['contributionCount']) for d in w['contributionDays']] for w in cal['weeks']]
days = [d for w in weeks for d in w]
total = cal['totalContributions']

def streaks(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    cur = 0; i = len(counts) - 1
    if i >= 0 and counts[i] == 0: i -= 1            # today may not have a contribution yet
    while i >= 0 and counts[i] > 0: cur += 1; i -= 1
    return cur, longest
cur, longest = streaks(days)

u = call('https://api.github.com/users/' + USER)
repos, page = [], 1
while True:
    r = call('https://api.github.com/users/%s/repos?per_page=100&type=owner&page=%d' % (USER, page))
    repos += r
    if len(r) < 100: break
    page += 1
own = [r for r in repos if not r['fork']]
stars = sum(r['stargazers_count'] for r in own)
langs = {}
for r in own:
    if r['language']: langs[r['language']] = langs.get(r['language'], 0) + 1
top = sorted(langs.items(), key=lambda x: -x[1])[:5]
best_day = max(days, key=lambda d: d[1]) if days else ('', 0)
total_prs = call('https://api.github.com/search/issues?q=author:%s+type:pr&per_page=1' % USER)['total_count']
total_issues = call('https://api.github.com/search/issues?q=author:%s+type:issue&per_page=1' % USER)['total_count']
lang_bytes = {}
for r in own:
    try:
        for k, v in call('https://api.github.com/repos/%s/%s/languages' % (USER, r['name'])).items(): lang_bytes[k] = lang_bytes.get(k, 0) + v
    except Exception: pass
LCOL = {'JavaScript': '#f1e05a', 'TypeScript': '#3178c6', 'Python': '#3572A5', 'HTML': '#e34c26', 'CSS': '#7c5cbf', 'PHP': '#8892bf', 'SCSS': '#c6538c', 'Dart': '#00B4AB', 'Jupyter Notebook': '#DA5B0B', 'PowerShell': '#3a6ea5', 'Shell': '#89e051'}
lt = sum(lang_bytes.values()) or 1
top_langs = sorted(lang_bytes.items(), key=lambda x: -x[1])[:6]

# ---------- shared look (dark and light) ----------
STYLE = """
<style>
  :root{--bg:#ffffff;--card:#f3f8f5;--ink:#10231a;--mute:#5b7266;--accent:#0f9d46;--l0:#e3ece6;--l1:#b9e9cb;--l2:#6fd297;--l3:#19a34a;--l4:#0b6b34;--line:#d5e3da}
  @media (prefers-color-scheme: dark){:root{--bg:#0d1117;--card:#0f1d16;--ink:#e7f3ea;--mute:#86a393;--accent:#19C652;--l0:#15251c;--l1:#1d5a35;--l2:#19a34a;--l3:#19C652;--l4:#7BE8A0;--line:#1f3a2b}}
  text{font-family:'Segoe UI',Helvetica,Arial,sans-serif;fill:var(--ink)}
  .mono{font-family:Consolas,Menlo,'Courier New',monospace}
  .mute{fill:var(--mute)}
  .cell{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .5s ease-out forwards}
  @keyframes pop{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:scale(1)}}
  .bar{transform-box:fill-box;transform-origin:left center;animation:grow 1.1s ease-out both}
  @keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
  .fade{opacity:0;animation:fade .8s ease-out forwards}
  @keyframes fade{to{opacity:1}}
  @media (prefers-reduced-motion: reduce){.cell,.bar,.fade{animation:none;opacity:1}}
</style>"""

def level(c, mx):
    if c <= 0: return 0
    r = c / mx
    return 1 if r <= .25 else 2 if r <= .5 else 3 if r <= .75 else 4

# ---------- heatmap ----------
mx = max([c for _, c in days] + [1])
CS, GAP, X0, Y0 = 12, 3, 38, 30
W = X0 + len(weeks) * (CS + GAP) + 20
H = Y0 + 7 * (CS + GAP) + 44
cells, months, last_m = [], [], None
for wi, w in enumerate(weeks):
    first = w[0][0]
    m = datetime.date.fromisoformat(first).strftime('%b')
    if m != last_m and wi > 0 or (wi == 0):
        months.append('<text x="%d" y="20" class="mute" font-size="11">%s</text>' % (X0 + wi * (CS + GAP), m)); last_m = m
    for di, (date, c) in enumerate(w):
        cells.append('<rect class="cell" x="%d" y="%d" width="%d" height="%d" rx="3" fill="var(--l%d)" style="animation-delay:%.2fs"><title>%s: %d contributions</title></rect>' % (
            X0 + wi * (CS + GAP), Y0 + di * (CS + GAP), CS, CS, level(c, mx), wi * 0.025 + di * 0.01, date, c))
labels = ''.join('<text x="8" y="%d" class="mute" font-size="10">%s</text>' % (Y0 + i * (CS + GAP) + 10, d) for i, d in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')))
legend = '<text x="%d" y="%d" class="mute" font-size="11">less</text>' % (W - 190, H - 12) + ''.join('<rect x="%d" y="%d" width="12" height="12" rx="3" fill="var(--l%d)"/>' % (W - 160 + i * 18, H - 22, i) for i in range(5)) + '<text x="%d" y="%d" class="mute" font-size="11">more</text>' % (W - 62, H - 12)
foot = '<text x="%d" y="%d" class="mute" font-size="12">%s contributions in the last year · busiest day: %d on %s</text>' % (X0, H - 12, format(total, ','), best_day[1], best_day[0])
heat = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Contribution heatmap: %d contributions in the last year">%s<rect width="%d" height="%d" rx="14" fill="var(--bg)" stroke="var(--line)"/>%s%s%s%s%s</svg>\n' % (
    W, H, W, H, total, STYLE, W, H, ''.join(months), labels, ''.join(cells), legend, foot)
open(os.path.join(OUT, 'contrib-heatmap.svg'), 'w', encoding='utf-8').write(heat)

# ---------- stats card (420 x 380, same height as the portrait next to it) ----------
rows = [('Contributions (last year)', format(total, ',')), ('Total pull requests', total_prs), ('Total issues', total_issues),
        ('Repositories worked on (last year)', len(worked_on)), ('Public repositories', u['public_repos']), ('Stars earned', stars),
        ('Streak: current / longest', '%d / %d days' % (cur, longest))]
lines = ''
for i, (k, v) in enumerate(rows):
    y = 86 + i * 25
    lines += '<g class="fade" style="animation-delay:%.2fs"><circle cx="34" cy="%d" r="3.5" style="fill:var(--accent)"/><text x="46" y="%d" font-size="13" class="mute">%s</text><text x="392" y="%d" font-size="14" font-weight="700" text-anchor="end">%s</text></g>' % (.15 + i * .1, y - 4, y, html.escape(k), y, html.escape(str(v)))
langs_svg = '<text x="28" y="288" font-size="12" font-weight="700" class="mute">TOP LANGUAGES</text>'
for i, (name, nbytes) in enumerate(top_langs):
    col, row = i % 2, i // 2
    x, y = 28 + col * 196, 312 + row * 24
    langs_svg += '<g class="fade" style="animation-delay:%.2fs"><circle cx="%d" cy="%d" r="5" fill="%s"/><text x="%d" y="%d" font-size="12.5">%s <tspan class="mute">%.1f%%</tspan></text></g>' % (1.0 + i * .12, x + 5, y - 4, LCOL.get(name, '#8b949e'), x + 18, y, html.escape(name), 100 * nbytes / lt)
stats = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 380" width="420" height="380" role="img" aria-label="GitHub stats for %s">%s<rect width="420" height="380" rx="14" fill="var(--bg)" stroke="var(--line)"/><text x="28" y="40" class="mono" font-size="15" style="fill:var(--accent)">%s@github ~ $ ./stats.sh</text><line x1="28" y1="54" x2="392" y2="54" stroke="var(--line)"/>%s<line x1="28" y1="268" x2="392" y2="268" stroke="var(--line)"/>%s</svg>\n' % (
    USER, STYLE, USER.split('-')[0], lines, langs_svg)
open(os.path.join(OUT, 'stats.svg'), 'w', encoding='utf-8').write(stats)
print('ok: %d contributions, %d PRs, %d issues, %d repos worked on, streak %d/%d, languages %s' % (total, total_prs, total_issues, len(worked_on), cur, longest, [(n, round(100*b/lt,1)) for n, b in top_langs]))
