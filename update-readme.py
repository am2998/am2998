#!/usr/bin/env python3
import html
import re
import subprocess
from pathlib import Path

README_PATH = Path("README.md")
SECTION_TITLE = "## Recent Commits"
START_MARKER = "<!-- RECENT_COMMITS_START -->"
END_MARKER = "<!-- RECENT_COMMITS_END -->"
DISPLAY_COLUMNS = 3


def get_recent_commits(limit: int = 3) -> list[tuple[str, str, str]]:
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

    commits: list[tuple[str, str, str]] = []
    for line in output.splitlines():
        commit_hash, message, date = line.split("\t", maxsplit=2)
        commits.append((commit_hash, message, date))
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


def shorten_message(message: str, max_chars: int = 72) -> str:
    if len(message) <= max_chars:
        return message
    return message[: max_chars - 3].rstrip() + "..."


def build_commits_section(commits: list[tuple[str, str, str]]) -> str:
    repo_url = get_repo_web_url()

    if not commits:
        body = "_No commits found._"
    else:
        cells = []
        for index, (commit_hash, message, date) in enumerate(commits[:DISPLAY_COLUMNS], start=1):
            safe_hash = html.escape(commit_hash)
            safe_message = html.escape(shorten_message(message))
            safe_date = html.escape(date)
            if repo_url:
                hash_block = (
                    f"<a href=\"{repo_url}/commit/{safe_hash}\"><code>{safe_hash}</code></a>"
                )
            else:
                hash_block = f"<code>{safe_hash}</code>"

            cells.append(
                "    <td align=\"left\" valign=\"top\" width=\"33%\">\n"
                f"      <b>Commit {index}</b><br/>\n"
                f"      {hash_block}<br/>\n"
                f"      <sub>{safe_date}</sub><br/><br/>\n"
                f"      <sub>{safe_message}</sub>\n"
                "    </td>"
            )

        while len(cells) < DISPLAY_COLUMNS:
            cells.append(
                "    <td align=\"left\" valign=\"top\" width=\"33%\">\n"
                "      <b>Commit</b><br/>\n"
                "      <code>-</code><br/>\n"
                "      <sub>-</sub><br/><br/>\n"
                "      <sub>No data</sub>\n"
                "    </td>"
            )

        body = "<table>\n  <tr>\n" + "\n".join(cells) + "\n  </tr>\n</table>"

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
