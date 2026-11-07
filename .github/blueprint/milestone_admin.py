"""GitHub Actions: Meilensteine per Kommentar auf dem Admin-Issue verwalten (GitHub-Blueprint).

Erlaubte Befehle (ein Befehl pro Kommentar, eine Zeile):
  /milestone list
  /milestone create VERSION – Titel
  /milestone close NUMMER
  /milestone reopen NUMMER

Berechtigt: die Eigentümerin bzw. der Eigentümer (author_association OWNER – bei Organisationen deren Owner) und
die Konten in [workflows] milestone_admins der .github/blueprint.toml (Mitglieder bzw. Mitwirkende).
Kommentartext nie in Shell-Befehle einsetzen. Nur der kurzlebige GITHUB_TOKEN (issues:write), kein persönlicher Token.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import tomllib
import urllib.request
from pathlib import Path

# Repository und Admin-Issue aus der Umgebung bzw. .github/blueprint.toml (GitHub-Blueprint)
EXPECTED_REPO = os.environ.get("GITHUB_REPOSITORY", "")


TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}


def workflow_config() -> dict:
    with open(Path(__file__).resolve().parents[1] / "blueprint.toml", "rb") as fh:
        return tomllib.load(fh).get("workflows", {})


def admin_issue_number() -> int:
    return int(workflow_config().get("admin_issue", 0))


def authorized(comment: dict, extra: list[str]) -> bool:
    """OWNER immer; weitere Konten nur, wenn eingetragen UND Mitglied bzw. Mitwirkende:r des Repositorys."""
    association = str(comment.get("author_association") or "")
    login = str((comment.get("user") or {}).get("login") or "").casefold()
    if association == "OWNER":
        return True
    return association in TRUSTED and login in {x.casefold() for x in extra}
COMMAND_PATTERN = re.compile(r"^/milestone (list|create|close|reopen)(?: (.+))?$")


def api(method: str, endpoint: str, data: dict | None = None) -> object:
    token = os.environ["GH_TOKEN"]
    url = "https://api.github.com" + endpoint
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "User-Agent": "github-blueprint-milestone-admin",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc


def parse_command(raw: str) -> tuple[str, str | None]:
    if len(raw) > 180 or "\n" in raw or "\r" in raw:
        raise ValueError("Bitte genau einen einzeiligen Befehl (höchstens 180 Zeichen).")
    match = COMMAND_PATTERN.fullmatch(raw.strip())
    if not match:
        raise ValueError("Befehle: /milestone list | create TITEL | close NUMMER | reopen NUMMER")
    operation, argument = match.groups()
    if operation == "list" and argument is not None:
        raise ValueError("Aufruf: /milestone list")
    if operation == "create":
        if not argument or not 3 <= len(argument) <= 120:
            raise ValueError("Aufruf: /milestone create TITEL (3–120 Zeichen)")
        return operation, argument
    if operation in ("close", "reopen"):
        if not argument or not re.fullmatch(r"[1-9][0-9]{0,7}", argument):
            raise ValueError("Aufruf: /milestone close NUMMER bzw. /milestone reopen NUMMER")
        return operation, argument
    return operation, None


def execute(operation: str, argument: str | None, repo: str) -> str:
    base = f"/repos/{repo}/milestones"
    if operation == "list":
        found = []
        page = 1
        while True:
            data = api("GET", f"{base}?state=all&per_page=100&page={page}")
            if not isinstance(data, list):
                raise RuntimeError("Unerwartete Antwort der GitHub-API (Meilensteine).")
            found.extend(data)
            if len(data) < 100:
                break
            page += 1
            if page > 10:
                raise RuntimeError("Zu viele Meilensteine für die Liste.")
        lines = [
            f"- [#{m['number']} – {m['title']}]({m['html_url']}) · {'offen' if m['state'] == 'open' else 'geschlossen'} · {m['open_issues']} offene Issues"
            for m in sorted(found, key=lambda m: m["number"], reverse=True)
        ]
        return "**Meilensteine:**\n" + ("\n".join(lines) if lines else "(keine)")
    if operation == "create":
        title = str(argument)
        existing = api("GET", f"{base}?state=all&per_page=100")
        for item in existing:
            if item["title"].casefold() == title.casefold():
                return f"Gibt es schon: [#{item['number']} – {item['title']}]({item['html_url']})."
        created = api("POST", base, {"title": title})
        return f"Angelegt: [#{created['number']} – {created['title']}]({created['html_url']})."
    number = int(str(argument))
    milestone = api("GET", f"{base}/{number}")
    target = "closed" if operation == "close" else "open"
    word = "geschlossen" if target == "closed" else "offen"
    if milestone["state"] == target:
        return f"Ist schon {word}: [#{number} – {milestone['title']}]({milestone['html_url']})."
    updated = api("PATCH", f"{base}/{number}", {"state": target})
    return f"Jetzt **{word}**: [#{number} – {updated['title']}]({updated['html_url']})."


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as fp:
        event = json.load(fp)
    issue = event.get("issue") or {}
    comment = event.get("comment") or {}
    repository = event.get("repository") or {}
    repo = repository.get("full_name") or ""
    wf = workflow_config()
    issue_number = int(wf.get("admin_issue", 0))
    # WICHTIG: die Prüfungen des Workflows hier wiederholen, bevor etwas geschieht.
    if (
        event.get("action") != "created"
        or not EXPECTED_REPO
        or issue_number <= 0
        or repo != EXPECTED_REPO
        or os.environ.get("GITHUB_REPOSITORY") != EXPECTED_REPO
        or not authorized(comment, list(wf.get("milestone_admins", [])))
        or issue.get("number") != issue_number
        or "pull_request" in issue
    ):
        print("Kein berechtigter Befehl auf dem Admin-Issue – nichts ausgeführt.")
        return 0
    body = str(comment.get("body") or "")
    if not body.startswith("/milestone "):
        return 0
    print("Berechtigter Befehl auf dem Admin-Issue wird ausgeführt.")
    try:
        operation, argument = parse_command(body)
        result = execute(operation, argument, repo)
        message = "✅ **Meilensteine:** " + result
    except (ValueError, RuntimeError, KeyError) as exc:
        message = "⚠️ **Meilensteine – nicht ausgeführt:** " + str(exc)
        print(message, file=sys.stderr)
    api("POST", f"/repos/{repo}/issues/{issue_number}/comments", {"body": message})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
