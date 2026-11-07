#!/usr/bin/env python3
"""Aufräumen auf GitHub (aus TagStudio) – Workflow «Aufräumen» bzw. release.py nach einer finalen Version.

    python3 .github/blueprint/cleanup.py laeufe [--tage N] [--probelauf]
        Abgeschlossene Workflow-Durchläufe löschen, die älter als N Tage sind (Standard: [aufraeumen]
        actions_verlauf_tage; 0 = aus). Der neueste Durchlauf jedes Workflows und laufende bleiben.
    python3 .github/blueprint/cleanup.py betas [--probelauf]
        Release-Einträge von Vorabversionen (vX.Y.Z-beta.N) entfernen, sobald es die finale Version vX.Y.Z oder eine
        höhere gibt. Die Git-Tags bleiben – nur die Einträge samt Dateien verschwinden von der Releases-Seite.

Gelöscht werden nur Protokolle von Workflow-Läufen bzw. Release-Einträge, nie Code, Tags, Issues oder Dateien.
Braucht gh mit GH_TOKEN und GH_REPO (in Actions gesetzt). Nur Standardbibliothek.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "blueprint.toml"


def config() -> dict:
    try:
        with open(CONFIG, "rb") as fh:
            return tomllib.load(fh)
    except OSError:
        return {}


def gh(*args: str):
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return json.loads(r.stdout) if r.stdout.strip() else None


def repo() -> str:
    return os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY", "")


def runs(days: int, dry: bool) -> int:
    if days <= 0:
        print("Actions-Verlauf: aus ([aufraeumen] actions_verlauf_tage = 0)")
        return 0
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    items, page = [], 1
    while True:
        batch = (gh(f"/repos/{repo()}/actions/runs?per_page=100&page={page}") or {}).get("workflow_runs") or []
        items += batch
        if len(batch) < 100:
            break
        page += 1
    newest = {}
    for r in items:                                   # neuester Durchlauf je Workflow bleibt
        if r["workflow_id"] not in newest or r["created_at"] > newest[r["workflow_id"]]["created_at"]:
            newest[r["workflow_id"]] = r
    keep = {r["id"] for r in newest.values()}
    gone = 0
    for r in items:
        when = datetime.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        if r["id"] in keep or r["status"] != "completed" or when > cutoff:
            continue
        if not dry:
            try:
                gh("-X", "DELETE", f"/repos/{repo()}/actions/runs/{r['id']}")
            except RuntimeError as ex:
                print(f"nicht gelöscht {r['id']}: {ex}")
                continue
        gone += 1
    print(f"{'würde löschen' if dry else 'gelöscht'}: {gone} von {len(items)} Durchläufen "
          f"(behalten: neuester je Workflow, laufende, jünger als {days} Tage)")
    return 0


def _ver(tag: str) -> tuple:
    try:
        return tuple(int(x) for x in tag.lstrip("v").split("-", 1)[0].split("."))
    except ValueError:
        return ()


def betas(dry: bool) -> int:
    out = subprocess.run(["gh", "api", "--paginate", f"repos/{repo()}/releases?per_page=100",
                          "--jq", ".[] | [.id, .tag_name, .prerelease] | @json"], capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr.strip())
    rels = [json.loads(line) for line in out.stdout.splitlines() if line.strip()]
    finals = {tag for _id, tag, pre in rels if not pre and "-" not in tag}
    top = max((_ver(t) for t in finals if _ver(t)), default=())
    gone = []
    for rid, tag, pre in rels:
        if (pre or "-" in tag) and (tag.split("-", 1)[0] in finals or (_ver(tag) and _ver(tag) < top)):
            print(("würde entfernen: " if dry else "entferne: ") + tag)
            if not dry:                               # nur der Release-Eintrag, der Git-Tag bleibt
                gh("-X", "DELETE", f"repos/{repo()}/releases/{rid}")
            gone.append(tag)
    print(f"{len(gone)} Vorabversion(en) {'gefunden' if dry else 'entfernt'}, {len(finals)} finale Version(en) bleiben.")
    return 0


def main(argv: list[str]) -> int:
    dry = "--probelauf" in argv or "--dry-run" in argv
    cfg = config()
    try:
        if argv[:1] == ["laeufe"]:
            days = cfg.get("aufraeumen", {}).get("actions_verlauf_tage", 0)
            if "--tage" in argv and argv[argv.index("--tage") + 1:]:
                value = argv[argv.index("--tage") + 1]
                days = int(value) if value.strip() else days
            return runs(int(days), dry)
        if argv[:1] == ["betas"]:
            return betas(dry)
    except (RuntimeError, ValueError) as e:
        print(f"::warning title=Aufräumen::{e}")
        return 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
