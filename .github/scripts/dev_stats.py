import os
import requests
from datetime import datetime, timedelta
from collections import defaultdict

USER = "shibang-das"
TOKEN = os.environ["GITHUB_TOKEN"]

S = requests.Session()
S.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
})

def get(url, params=None):
    r = S.get(url, params=params)
    r.raise_for_status()
    return r.json()

def paginated(url, params=None):
    page = 1
    out = []
    while True:
        p = dict(params or {})
        p.update({"per_page": 100, "page": page})
        data = get(url, p)
        if not data:
            break
        out.extend(data)
        page += 1
    return out

def repos():
    return paginated(
        f"https://api.github.com/users/{USER}/repos",
        {"type": "owner", "sort": "updated"}
    )

def languages(repo):
    data = get(repo["languages_url"])
    total = sum(data.values())
    if not total:
        return {}
    return {k: v / total for k, v in data.items()}

def commits(repo):
    return paginated(
        f"https://api.github.com/repos/{USER}/{repo['name']}/commits",
        {"author": USER}
    )

def parse_time(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00"))

def estimate(commits):
    if not commits:
        return 0

    times = sorted(
        parse_time(c["commit"]["author"]["date"])
        for c in commits
    )

    sessions = []
    start = times[0]
    prev = times[0]

    for t in times[1:]:
        gap = t - prev

        if gap <= timedelta(hours=2):
            prev = t
        else:
            duration = (prev - start).total_seconds() / 3600
            sessions.append(max(0.5, min(duration + 0.5, 4)))
            start = t
            prev = t

    duration = (prev - start).total_seconds() / 3600
    sessions.append(max(0.5, min(duration + 0.5, 4)))

    return sum(sessions)

def fmt(hours):
    if hours < 1:
        return "<1h"
    return f"{round(hours)}h"

repos_data = repos()

total = defaultdict(float)
repo_count = 0
commit_count = 0

for repo in repos_data:
    if repo["fork"] or repo["archived"]:
        continue

    cs = commits(repo)

    if not cs:
        continue

    ls = languages(repo)

    if not ls:
        continue

    hours = estimate(cs)

    if hours <= 0:
        continue

    commit_count += len(cs)
    repo_count += 1

    for lang, share in ls.items():
        total[lang] += hours * share

total_hours = sum(total.values())

items = sorted(
    total.items(),
    key=lambda x: x[1],
    reverse=True
)[:8]

if not items:
    raise RuntimeError("No GitHub activity found.")

max_hours = items[0][1]

rows = []

for lang, hours in items:
    width = max(5, int((hours / max_hours) * 220))

    rows.append(f"""
    <text x="30" y="{100 + len(rows) * 42}"
          fill="#e6edf3"
          font-family="Arial"
          font-size="16">{lang}</text>

    <rect x="140" y="{84 + len(rows) * 42}"
          width="{width}"
          height="22"
          rx="5"
          fill="#58a6ff"/>

    <text x="{155 + width}" y="{100 + len(rows) * 42}"
          fill="#8b949e"
          font-family="Arial"
          font-size="14">{fmt(hours)}</text>
    """)

height = 130 + len(items) * 42

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
width="520"
height="{height}"
viewBox="0 0 520 {height}">

<rect width="100%" height="100%"
rx="12"
fill="#0d1117"
stroke="#30363d"/>

<text x="30" y="35"
fill="#ffffff"
font-family="Arial"
font-size="20"
font-weight="bold">
⏱ Estimated Development Time
</text>

<text x="30" y="60"
fill="#8b949e"
font-family="Arial"
font-size="12">
Based on historical GitHub activity
</text>

{''.join(rows)}

<text x="30" y="{height - 18}"
fill="#6e7681"
font-family="Arial"
font-size="11">
{fmt(total_hours)} estimated · {commit_count} commits · {repo_count} repositories
</text>

</svg>
"""

os.makedirs("generated", exist_ok=True)

with open("generated/development-time.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print("Generated development-time.svg")
