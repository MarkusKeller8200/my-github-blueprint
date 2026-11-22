#!/usr/bin/env python3
"""Repository-Einstellungen aus .github/blueprint.toml per Action setzen (GitHub-Blueprint, Workflow einstellungen.yml).

Holt den Blueprint im Stand aus .github/blueprint/VERSION («0.1.0 abc1234») und führt dessen
«apply.py --ziel . --nur-github» aus: Labels, Meilensteine und Repository-Einstellungen, keine Dateien.
Braucht in GH_TOKEN ein Token mit Admin-Rechten (Secret BLUEPRINT_ADMIN_TOKEN); ohne Token nur ein Hinweis.
PROBELAUF=1 zeigt nur an, was geändert würde. Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BLUEPRINT = "MarkusKeller8200/my-github-blueprint"
ZUGANG_NAME = "BLUEPRINT_ADMIN_TOKEN"   # nur der Name für Hinweise, nie der Wert


def summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def load_config() -> dict:
    path = ROOT / ".github" / "blueprint.toml"
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def blueprint_ref(text: str) -> tuple[str, str]:
    """Version und Commit aus .github/blueprint/VERSION; ohne Commit «main»."""
    parts = text.split()
    version = parts[0] if parts else ""
    commit = parts[1] if len(parts) > 1 and re.fullmatch(r"[0-9a-f]{7,40}", parts[1]) else ""
    return version, commit or "main"


def problems(cfg: dict) -> list[str]:
    """Gründe, warum der Lauf nicht starten darf (sonst entstünden Doppel)."""
    out = []
    if not cfg.get("start", {}).get("erledigt", False):
        out.append("Start-Checkliste noch nicht beantwortet ([start] erledigt = false) – zuerst lokal start.py/apply.py")
    wf = cfg.get("workflows", {})
    if wf.get("milestone_admin", True) and int(wf.get("admin_issue", 0) or 0) == 0:
        out.append("[workflows] admin_issue = 0 – das Admin-Issue zuerst lokal mit apply.py anlegen "
                   "(die Action könnte die Nummer nicht zurückschreiben und würde es bei jedem Lauf neu anlegen)")
    return out


def main() -> int:
    dry = bool(os.environ.get("PROBELAUF"))
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if (ROOT / ".github" / "blueprint-repo.toml").exists():
        print("Blueprint selbst – nichts zu tun.")
        return 0
    cfg = load_config()
    if not os.environ.get("GH_TOKEN"):
        msg = (f"Secret {ZUGANG_NAME} fehlt – Einstellungen nicht gesetzt. Fine-grained PAT nur für dieses Repository mit "
               "«Administration: Read and write» und «Issues: Read and write» erzeugen und unter Settings → Secrets and "
               f"variables → Actions als {ZUGANG_NAME} eintragen; danach den Workflow von Hand starten.")
        print(f"::warning title=Einstellungen anwenden::{msg}")
        summary(f"### Einstellungen anwenden\n\n⚠ {msg}")
        return 0
    blocked = problems(cfg)
    if blocked:
        for p in blocked:
            print(f"::error title=Einstellungen anwenden::{p}")
        summary("### Einstellungen anwenden\n\n" + "\n".join(f"- ✗ {p}" for p in blocked))
        return 1
    source = cfg.get("einstellungen", {}).get("blueprint", "") or DEFAULT_BLUEPRINT
    version_file = ROOT / ".github" / "blueprint" / "VERSION"
    version, ref = blueprint_ref(version_file.read_text(encoding="utf-8") if version_file.exists() else "")
    if ref == "main":
        print("::warning::.github/blueprint/VERSION nennt keinen Commit – verwende den aktuellen Blueprint (main)")
    with tempfile.TemporaryDirectory() as tmp:
        bp = Path(tmp) / "blueprint"
        env = {k: v for k, v in os.environ.items() if k != "GH_TOKEN"}   # Blueprint ist öffentlich: ohne Token klonen
        subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                        f"https://github.com/{source}.git", str(bp)], check=True, env=env)
        subprocess.run(["git", "-C", str(bp), "checkout", "--quiet", ref], check=True, env=env)
        cmd = [sys.executable, str(bp / ".github" / "blueprint" / "apply.py"), "--ziel", str(ROOT), "--nur-github"]
        if repo:
            cmd += ["--repo", repo]
        if dry:
            cmd.append("--probelauf")
        print(f"Blueprint {source} @ {ref} (Stand {version or '–'}){' – Probelauf' if dry else ''}")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout + r.stderr).strip()
    print(out)
    title = "Einstellungen anwenden" + (" (Probelauf)" if dry else "")
    summary(f"### {title}\n\nBlueprint `{source}` @ `{ref}`\n\n```\n{out}\n```")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
