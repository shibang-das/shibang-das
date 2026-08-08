import os
import requests
from collections import defaultdict
from datetime import datetime, timedelta

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

def get_all(url, params=None):
    result = []
    page = 1

    while True:
        p = dict(params or {})
        p["per_page"] = 100
        p["page"] = page

        data = get(url, p)

        if not data:
            break

        result.extend(data)

        if len(data) < 100:
            break

        page += 1

    return result

repos = get_all(
    f"https://api.github.com/users/{USER}/repos",
    {
        "type": "owner",
        "sort": "created",
        "direction": "asc"
    }
)

daily = defaultdict(list)

repo_count = 0
commit_count = 0

for repo in repos:
    if repo["fork"] or repo["archived"] or not repo["has_issues"] and False:
        continue

    name = repo["full_name"]

    try:
        commits = get_all(
            f"https://api.github.com/repos/{name}/commits",
            {
                "author": USER
            }
        )
    except Exception as e:
        print(f"Skipping {name}: {e}")
        continue

    if not commits:
        continue

    repo_count += 1

    for commit in commits:
        try:
            date = commit["commit"]["author"]["date"]
            dt = datetime.fromisoformat(
                date.replace("Z", "+00:00")
            )

            day = dt.date()
            daily[day].append(dt)
            commit_count += 1

        except Exception:
            continue

print(f"Repositories analyzed: {repo_count}")
print(f"Commits found: {commit_count}")

if not daily:
    raise RuntimeError("No public GitHub activity found.")

# Estimate coding sessions.
#
# Commits within 2 hours are considered the same session.
# Each session has a minimum estimate of 30 minutes
# and a maximum estimate of 4 hours.

hours = {}

for day, times in daily.items():
    times.sort()

    total = 0
    start = times[0]
    previous = times[0]

    for current in times[1:]:
        gap = current - previous

        if gap <= timedelta(hours=2):
            previous = current
        else:
            duration = (
                previous - start
            ).total_seconds() / 3600

            total += max(
                0.5,
                min(duration + 0.5, 4)
            )

            start = current
            previous = current

    duration = (
        previous - start
    ).total_seconds() / 3600

    total += max(
        0.5,
        min(duration + 0.5, 4)
    )

    hours[day] = total

start_date = min(hours)
end_date = max(hours)

days = (end_date - start_date).days + 1

values = []

for i in range(days):
    d = start_date + timedelta(days=i)
    values.append((d, hours.get(d, 0)))

total_hours = sum(hours.values())

# SVG dimensions

width = 1100
height = 360

left = 70
right = 25
top = 45
bottom = 55

graph_width = width - left - right
graph_height = height - top - bottom

max_value = max(v for _, v in values)

if max_value == 0:
    max_value = 1

points = []

for i, (date, value) in enumerate(values):

    if len(values) == 1:
        x = left
    else:
        x = left + (
            i / (len(values) - 1)
        ) * graph_width

    y = top + graph_height - (
        value / max_value
    ) * graph_height

    points.append(f"{x:.2f},{y:.2f}")

polyline = " ".join(points)

# X-axis labels

labels = []

label_count = min(8, max(2, len(values) // 30))

for i in range(label_count):
    idx = round(
        i * (len(values) - 1) /
        (label_count - 1)
    )

    date, _ = values[idx]

    x = left + (
        idx / max(1, len(values) - 1)
    ) * graph_width

    labels.append(
        f"""
        <text x="{x:.2f}"
              y="{height - 20}"
              fill="#8b949e"
              font-size="12"
              text-anchor="middle"
              font-family="Arial">
            {date.strftime("%b %Y")}
        </text>
        """
    )

# Y-axis labels

y_labels = []

for i in range(5):
    value = max_value * i / 4

    y = (
        top +
        graph_height -
        (i / 4) * graph_height
    )

    y_labels.append(
        f"""
        <text x="{left - 10}"
              y="{y + 4:.2f}"
              fill="#8b949e"
              font-size="11"
              text-anchor="end"
              font-family="Arial">
            {value:.1f}h
        </text>
        """
    )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
width="{width}"
height="{height}"
viewBox="0 0 {width} {height}">

<rect width="100%"
      height="100%"
      rx="12"
      fill="#0d1117"
      stroke="#30363d"/>

<text x="{left}"
      y="27"
      fill="#ffffff"
      font-size="18"
      font-weight="bold"
      font-family="Arial">
    Coding Activity
</text>

<line x1="{left}"
      y1="{top + graph_height}"
      x2="{width - right}"
      y2="{top + graph_height}"
      stroke="#30363d"/>

<line x1="{left}"
      y1="{top}"
      x2="{left}"
      y2="{top + graph_height}"
      stroke="#30363d"/>

{''.join(y_labels)}

<polyline
    points="{polyline}"
    fill="none"
    stroke="#58a6ff"
    stroke-width="2"/>

<polyline
    points="{left},{top + graph_height} {polyline} {width - right},{top + graph_height}"
    fill="#58a6ff"
    fill-opacity="0.08"
    stroke="none"/>

{''.join(labels)}

<text x="{width - right}"
      y="27"
      fill="#8b949e"
      font-size="11"
      text-anchor="end"
      font-family="Arial">
    {total_hours:.1f}h estimated · {commit_count} commits
</text>

</svg>
"""

os.makedirs("generated", exist_ok=True)

with open(
    "generated/coding-activity.svg",
    "w",
    encoding="utf-8"
) as f:
    f.write(svg)

print("Generated coding-activity.svg")
