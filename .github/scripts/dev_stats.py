import os
import requests
from datetime import datetime, timedelta
from collections import defaultdict

USER = "shibang-das"
TOKEN = os.environ["GITHUB_TOKEN"]

s = requests.Session()
s.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
})

def get(url, params=None):
    r = s.get(url, params=params)
    r.raise_for_status()
    return r.json()

def commits():
    out = []
    page = 1

    while page <= 10:
        data = get(
            "https://api.github.com/search/commits",
            {
                "q": f"author:{USER}",
                "per_page": 100,
                "page": page
            }
        )

        items = data.get("items", [])

        if not items:
            break

        out.extend(items)

        if len(items) < 100:
            break

        page += 1

    return out

def repo_languages(repo):
    try:
        return get(
            f"https://api.github.com/repos/{repo}/languages"
        )
    except:
        return {}

def parse_time(x):
    return datetime.fromisoformat(
        x.replace("Z", "+00:00")
    )

def estimate(times):
    if not times:
        return 0

    times = sorted(times)

    total = 0
    start = times[0]
    prev = times[0]

    for t in times[1:]:
        gap = t - prev

        if gap <= timedelta(hours=2):
            prev = t
        else:
            duration = (prev - start).total_seconds() / 3600
            total += max(0.5, min(duration + 0.5, 4))

            start = t
            prev = t

    duration = (prev - start).total_seconds() / 3600
    total += max(0.5, min(duration + 0.5, 4))

    return total

cs = commits()

print(f"Found {len(cs)} commits")

if not cs:
    raise RuntimeError(
        "No public GitHub commits found for this username."
    )

repo_commits = defaultdict(list)

for c in cs:
    repo = c["repository"]["full_name"]

    date = c["commit"]["author"]["date"]

    repo_commits[repo].append(
        parse_time(date)
    )

total = defaultdict(float)
commit_count = 0
repo_count = 0

for repo, times in repo_commits.items():

    ls = repo_languages(repo)

    if not ls:
        continue

    total_bytes = sum(ls.values())

    if total_bytes == 0:
        continue

    hours = estimate(times)

    if hours <= 0:
        continue

    commit_count += len(times)
    repo_count += 1

    for lang, size in ls.items():
        share = size / total_bytes
        total[lang] += hours * share

items = sorted(
    total.items(),
    key=lambda x: x[1],
    reverse=True
)[:8]

if not items:
    raise RuntimeError(
        "Commits were found, but no language statistics could be calculated."
    )

total_hours = sum(total.values())
max_hours = items[0][1]

rows = []

for i, (lang, hours) in enumerate(items):

    y = 100 + i * 42
    width = max(5, int((hours / max_hours) * 220))

    rows.append(f"""
    <text x="30" y="{y}"
          fill="#e6edf3"
          font-family="Arial"
          font-size="16">{lang}</text>

    <rect x="140" y="{y - 16}"
          width="{width}"
          height="22"
          rx="5"
          fill="#58a6ff"/>

    <text x="{155 + width}" y="{y}"
          fill="#8b949e"
          font-family="Arial"
          font-size="14">{round(hours)}h</text>
    """)

height = 130 + len(items) * 42

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
width="520"
height="{height}"
viewBox="0 0 520 {height}">

<rect width="100%"
height="100%"
rx="12"
fill="#0d1117"
stroke="#30363d"/>

<text x="30"
y="35"
fill="#ffffff"
font-family="Arial"
font-size="20"
font-weight="bold">
⏱ Estimated Development Time
</text>

<text x="30"
y="60"
fill="#8b949e"
font-family="Arial"
font-size="12">
Based on historical GitHub activity
</text>

{''.join(rows)}

<text x="30"
y="{height - 18}"
fill="#6e7681"
font-family="Arial"
font-size="11">
{round(total_hours)}h estimated · {commit_count} commits · {repo_count} repositories
</text>

</svg>
"""

os.makedirs("generated", exist_ok=True)

with open(
    "generated/development-time.svg",
    "w",
    encoding="utf-8"
) as f:
    f.write(svg)

print("Generated development-time.svg")
