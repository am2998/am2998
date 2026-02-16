#!/usr/bin/env python3
import html
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib import error, parse, request

README_PATH = Path("README.md")
SECTION_TITLE = "## Recent Commits"
START_MARKER = "<!-- RECENT_COMMITS_START -->"
END_MARKER = "<!-- RECENT_COMMITS_END -->"
DISPLAY_COLUMNS = 3
API_TIMEOUT_SECONDS = 10


@dataclass
class CommitEntry:
    short_hash: str
    message: str
    date: str
    commit_url: str | None = None
    repo_name: str | None = None


def get_recent_commits(limit: int = 3) -> list[CommitEntry]:
    username = detect_github_username()
    if username:
        api_commits = get_recent_commits_from_github(username=username, limit=limit)
        if api_commits:
            return api_commits

    return get_recent_commits_from_local_repo(limit=limit)


def detect_github_username() -> str | None:
    env_username = os.getenv("GH_USERNAME") or os.getenv("GITHUB_REPOSITORY_OWNER")
    if env_username:
        return env_username.strip()

    repo_url = get_repo_web_url()
    if not repo_url:
        return None

    # https://github.com/<owner>/<repo>
    owner = repo_url.rstrip("/").split("/")[-2]
    return owner or None


def get_recent_commits_from_github(username: str, limit: int = 3) -> list[CommitEntry]:
    query = parse.quote(f"author:{username}", safe="")
    url = (
        "https://api.github.com/search/commits"
        f"?q={query}&sort=author-date&order=desc&per_page={limit}"
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []

    items = payload.get("items", [])
    commits: list[CommitEntry] = []
    seen_hashes: set[str] = set()
    for item in items:
        sha = str(item.get("sha", "")).strip()
        short_hash = sha[:7]
        if not short_hash or short_hash in seen_hashes:
            continue

        commit_obj = item.get("commit", {}) or {}
        message = str(commit_obj.get("message", "")).splitlines()[0].strip()
        author_obj = commit_obj.get("author", {}) or {}
        date = str(author_obj.get("date", ""))[:10]
        repo_name = str((item.get("repository", {}) or {}).get("full_name", "")).strip() or None
        commit_url = str(item.get("html_url", "")).strip() or None

        if not message or not date:
            continue

        commits.append(
            CommitEntry(
                short_hash=short_hash,
                message=message,
                date=date,
                commit_url=commit_url,
                repo_name=repo_name,
            )
        )
        seen_hashes.add(short_hash)
        if len(commits) >= limit:
            break

    return commits


def get_recent_commits_from_local_repo(limit: int = 3) -> list[CommitEntry]:
    output = subprocess.check_output(
        [
            "git",
            "log",
            f"-n{limit}",
            "--pretty=format:%h%x09%s%x09%ad",
            "--date=short",
        ],
        text=True,
    ).strip()

    if not output:
        return []

    repo_url = get_repo_web_url()
    repo_name = get_repo_name_from_url(repo_url) if repo_url else None
    commits: list[CommitEntry] = []
    for line in output.splitlines():
        commit_hash, message, date = line.split("\t", maxsplit=2)
        commit_url = f"{repo_url}/commit/{commit_hash}" if repo_url else None
        commits.append(
            CommitEntry(
                short_hash=commit_hash,
                message=message,
                date=date,
                commit_url=commit_url,
                repo_name=repo_name,
            )
        )
    return commits


def get_repo_web_url() -> str | None:
    try:
        origin = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return None

    if not origin:
        return None

    repo_path: str | None = None
    if origin.startswith("git@github.com:"):
        repo_path = origin.split(":", maxsplit=1)[1]
    elif origin.startswith("ssh://git@github.com/"):
        repo_path = origin.split("ssh://git@github.com/", maxsplit=1)[1]
    elif origin.startswith("https://github.com/"):
        repo_path = origin.split("https://github.com/", maxsplit=1)[1]
    elif origin.startswith("http://github.com/"):
        repo_path = origin.split("http://github.com/", maxsplit=1)[1]

    if not repo_path:
        return None

    repo_path = repo_path.removesuffix(".git").strip("/")
    if "/" not in repo_path:
        return None

    return f"https://github.com/{repo_path}"


def get_repo_name_from_url(repo_url: str) -> str | None:
    # https://github.com/<owner>/<repo>
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return None
    owner = parts[-2]
    repo = parts[-1]
    if not owner or not repo:
        return None
    return f"{owner}/{repo}"


def shorten_message(message: str, max_chars: int = 72) -> str:
    if len(message) <= max_chars:
        return message
    return message[: max_chars - 3].rstrip() + "..."


def build_commits_section(commits: list[CommitEntry]) -> str:
    if not commits:
        body = "_No commits found._"
    else:
        cells = []
        for index, commit in enumerate(commits[:DISPLAY_COLUMNS], start=1):
            safe_hash = html.escape(commit.short_hash)
            safe_message = html.escape(shorten_message(commit.message))
            safe_date = html.escape(commit.date)
            safe_repo = html.escape(commit.repo_name) if commit.repo_name else None
            if commit.commit_url:
                safe_commit_url = html.escape(commit.commit_url, quote=True)
                hash_block = f"<a href=\"{safe_commit_url}\"><code>{safe_hash}</code></a>"
            else:
                hash_block = f"<code>{safe_hash}</code>"

            cells.append(
                "    <td align=\"left\" valign=\"top\" width=\"33%\">\n"
                f"      <b>Commit {index}</b><br/>\n"
                f"      {hash_block}<br/>\n"
                f"      <sub>{safe_date}</sub><br/>\n"
                f"      <sub>{safe_repo if safe_repo else '-'}</sub><br/><br/>\n"
                f"      {safe_message}\n"
                "    </td>"
            )

        while len(cells) < DISPLAY_COLUMNS:
            cells.append(
                "    <td align=\"left\" valign=\"top\" width=\"33%\">\n"
                "      <b>Commit</b><br/>\n"
                "      <code>-</code><br/>\n"
                "      <sub>-</sub><br/><br/>\n"
                "      No data\n"
                "    </td>"
            )

        body = "<table width=\"100%\">\n  <tr>\n" + "\n".join(cells) + "\n  </tr>\n</table>"

    return (
        f"{SECTION_TITLE}\n\n"
        f"{START_MARKER}\n"
        f"{body}\n"
        f"{END_MARKER}\n"
    )


def upsert_commits_section(readme: str, section: str) -> str:
    replace_pattern = re.compile(
        rf"{re.escape(SECTION_TITLE)}\n\n{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}\n?",
        re.DOTALL,
    )
    if replace_pattern.search(readme):
        return replace_pattern.sub(section, readme, count=1)

    certifications_heading = "## Certifications"
    heading_pos = readme.find(certifications_heading)
    if heading_pos == -1:
        raise RuntimeError("Sezione '## Certifications' non trovata nel README.")

    certifications_end = readme.find("</div>", heading_pos)
    if certifications_end == -1:
        raise RuntimeError("Chiusura </div> della sezione certifications non trovata.")

    insert_pos = certifications_end + len("</div>")
    return f"{readme[:insert_pos]}\n\n{section}{readme[insert_pos:]}"


def main() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    commits = get_recent_commits(limit=3)
    section = build_commits_section(commits)
    updated_readme = upsert_commits_section(readme, section)
    README_PATH.write_text(updated_readme, encoding="utf-8")


if __name__ == "__main__":
    main()
