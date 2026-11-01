#!/usr/bin/env python3
"""Neue Issues ohne Meilenstein nach Label der passenden Sammlung zuordnen (GitHub-Blueprint).

Liest nur die Labels des Ereignisses – keinen Text aus dem Issue. Zuordnung aus .github/blueprint.toml
([meilensteine] zuordnung = { fehler = "Fehler", … }), sonst die Vorgabe unten.
"""
import json
import os
import subprocess
import tomllib
from pathlib import Path

DEFAULT = {"fehler": "Fehler", "verbesserung": "Verbesserungen", "funktion": "Funktionen"}


def main() -> int:
    with open(Path(__file__).resolve().parents[1] / "blueprint.toml", "rb") as fh:
        cfg = tomllib.load(fh).get("meilensteine", {})
    if not cfg.get("sammlungen", True):
        print("Sammlungen ausgeschaltet.")
        return 0
    mapping = cfg.get("zuordnung", DEFAULT)
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
        issue = json.load(fh).get("issue") or {}
    if issue.get("milestone"):
        return 0
    labels = [l.get("name") for l in issue.get("labels") or []]
    title = next((mapping[l] for l in mapping if l in labels), None)
    if not title:
        print(f"Keine passende Art ({', '.join(labels)})")
        return 0
    repo = os.environ["GITHUB_REPOSITORY"]
    out = subprocess.run(["gh", "api", f"repos/{repo}/milestones?state=open&per_page=100"], capture_output=True, text=True, check=True).stdout
    number = next((m["number"] for m in json.loads(out) if m["title"] == title), None)
    if number is None:
        print(f"::warning::Meilenstein «{title}» nicht gefunden")
        return 0
    subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{repo}/issues/{issue['number']}", "-F", f"milestone={number}", "--silent"], check=True)
    print(f"Issue #{issue['number']} → {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
