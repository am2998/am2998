import requests
import re
from datetime import datetime, timedelta

# === CONFIG ===
USERNAME = "am2998"           # ← Replace with your GitHub username
REPO_LIMIT = 20                     # Number of repos to check
COMMITS_LIMIT = 5                   # Number of commits to show
PROFILE_REPO = USERNAME.lower()    # Skip the profile README repo

# === FETCH REPOS ===
headers = {"Accept": "application/vnd.github.v3+json"}
repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page={REPO_LIMIT}&sort=updated"
repos = requests.get(repos_url, headers=headers).json()

commits_data = []

for repo in repos:
    repo_name = repo["name"]

    # Skip profile repo, forks, and archived repos
    if repo_name.lower() == PROFILE_REPO or repo.get("fork") or repo.get("archived"):
        continue

    commits_url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits"
    commits = requests.get(commits_url, headers=headers).json()

    if isinstance(commits, list) and len(commits) > 0:
        commit = commits[0]
        sha = commit["sha"][:7]
        message = commit["commit"]["message"].split("\n")[0].strip()
        date = commit["commit"]["committer"]["date"][:10]
        url = commit["html_url"]

        commits_data.append((repo_name, message, sha, url, date))

# Sort by date descending
commits_data.sort(key=lambda x: x[4], reverse=True)
commits_data = commits_data[:COMMITS_LIMIT]

# === BUILD MARKDOWN TABLE ===
table_header = "| Repo | Message | Commit | Date |\n|------|---------|--------|------|"
table_rows = [
    f"| `{repo}` | {msg} | [`{sha}`]({url}) | {date} |"
    for repo, msg, sha, url, date in commits_data
]
table_markdown = table_header + "\n" + "\n".join(table_rows)

# === UPDATE README ===
with open("README.md", "r") as f:
    readme = f.read()

# Update commits section
start_tag = "<!-- LATEST_COMMITS_START -->"
end_tag = "<!-- LATEST_COMMITS_END -->"

start_index = readme.find(start_tag)
end_index = readme.find(end_tag) + len(end_tag)

if start_index == -1 or end_index == -1:
    raise ValueError("Missing commit section markers in README.md")

new_section = f"{start_tag}\n{table_markdown}\n{end_tag}"
new_readme = readme[:start_index] + new_section + readme[end_index:]

# Update uptime
uptime_pattern = r"Uptime: (\d+)y (\d+)m (\d+)d"
# Calculate uptime based on time since September 29, 1998
birth_date = datetime(1998, 9, 29).date()
today = datetime.now().date()

# Get the last update date from README to check if we need to update
last_update_pattern = r"<!-- LAST_UPDATED: (\d{4}-\d{2}-\d{2}) -->"
last_update_match = re.search(last_update_pattern, readme)
last_update_date = None

if last_update_match:
    last_update_str = last_update_match.group(1)
    last_update_date = datetime.strptime(last_update_str, '%Y-%m-%d').date()

# Only update if it's a new day or no previous update exists
if not last_update_date or today > last_update_date:
    # Calculate the difference
    delta = today - birth_date
    total_days = delta.days

    # Convert to years, months, days
    years = total_days // 365
    remaining_days = total_days % 365
    months = remaining_days // 30
    days = remaining_days % 30

    # Update the uptime in README
    new_uptime = f"Uptime: {years}y {months}m {days}d"
    new_readme = re.sub(uptime_pattern, new_uptime, new_readme)

    # Update the last updated date tag
    if last_update_match:
        new_last_update = f"<!-- LAST_UPDATED: {today.strftime('%Y-%m-%d')} -->"
        new_readme = re.sub(last_update_pattern, new_last_update, new_readme)
    else:
        # Add the tag if it doesn't exist (right after commits section)
        new_last_update = f"\n<!-- LAST_UPDATED: {today.strftime('%Y-%m-%d')} -->"
        new_readme = new_readme.replace(end_tag, end_tag + new_last_update)

    with open("README.md", "w") as f:
        f.write(new_readme)
else:
    # No need to update if it's the same day
    print("No update needed - same day as last execution.")

