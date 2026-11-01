#!/usr/bin/env python3
"""GitHub-Blueprint anwenden – auf ein neues oder ein bestehendes Repository (nur Standardbibliothek, Python 3.11+).

    python3 .github/blueprint/apply.py --probelauf               zeigen, was passieren würde (empfohlen zuerst)
    python3 .github/blueprint/apply.py                           Dateien erzeugen + GitHub einrichten
    python3 .github/blueprint/apply.py --nur-dateien | --nur-github
    python3 .github/blueprint/apply.py --ziel ../anderes-repo --repo owner/name   auf ein anderes Repository

Dateien: aus .github/blueprint/templates mit den Werten aus .github/blueprint.toml. Bestehende Dateien werden
NIE überschrieben (ausser --ueberschreiben); abweichende werden gemeldet. AGENTS.md erhält den Abschnitt
«GitHub-Ablauf» zwischen Markierungen (wird beim erneuten Anwenden aktualisiert).
GitHub (über die gh-CLI, in Actions mit dem Repository-Token): Labels, Meilensteine, Admin-Issue; GitHub-Standard-
Labels nur entfernen, wenn in der Konfiguration eingeschaltet (es werden nie Issues oder Dateien gelöscht).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
sys.path.insert(0, str(HERE))
import settings  # noqa: E402  (Repository-Einstellungen, FUNDING.yml)

STATUS_LABELS = [
    ("triage", "fbca04", "Neu gemeldet – noch nicht freigegeben, kein Entwicklungsauftrag"),
    ("_1 bereit", "0e8a16", "Zur Umsetzung freigegeben (nur Projektverantwortliche:r)"),
    ("_2 in Arbeit", "0052cc", "Wird gerade umgesetzt"),
    ("_3 Beta-Test", "f9d0c4", "In einer Beta, wartet auf deinen Test (oder einfach nur Test)"),
]
KIND_LABELS = [
    ("fehler", "d73a4a", "Etwas funktioniert nicht wie erwartet"),
    ("verbesserung", "a2eeef", "Bestehende Funktion besser machen"),
    ("funktion", "0e8a16", "Neue Funktion"),
    ("doku", "0075ca", "Dokumentation"),
    ("sicherheit", "b60205", "Sicherheit und Datenschutz"),
    ("duplikat", "cfd3d7", "Gibt es schon"),
    ("wird nicht umgesetzt", "ffffff", "Bewusst abgelehnt"),
]
OPTIONAL_LABELS = {
    "plugin": ("plugin", "5319e7", "Anbindung über ein Plugin"),
    "gui": ("gui", "1d76db", "Oberfläche, GUI-Bausteine, Farbkonzept"),
}
GITHUB_DEFAULT_LABELS = ["bug", "documentation", "duplicate", "enhancement", "good first issue", "help wanted",
                         "invalid", "question", "wontfix"]
COLLECTIONS = {
    "Fehler": "Sammlung: Fehler ohne festen Release-Termin (Zuordnung automatisch über das Label)",
    "Verbesserungen": "Sammlung: Verbesserungen ohne festen Release-Termin (Zuordnung automatisch über das Label)",
    "Funktionen": "Sammlung: neue Funktionen ohne festen Release-Termin (Zuordnung automatisch über das Label)",
}

# Vorlage → Ziel (relativ zum Repository); Bedingung über zusatzvorlagen
FILES = [
    ("ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/bug_report.yml", None),
    ("ISSUE_TEMPLATE/improvement.yml", ".github/ISSUE_TEMPLATE/improvement.yml", None),
    ("ISSUE_TEMPLATE/feature_request.yml", ".github/ISSUE_TEMPLATE/feature_request.yml", None),
    ("ISSUE_TEMPLATE/plugin_idea.yml", ".github/ISSUE_TEMPLATE/plugin_idea.yml", "plugin"),
    ("ISSUE_TEMPLATE/gui_component.yml", ".github/ISSUE_TEMPLATE/gui_component.yml", "gui"),
    ("ISSUE_TEMPLATE/config.yml", ".github/ISSUE_TEMPLATE/config.yml", None),
    ("pull_request_template.md", ".github/pull_request_template.md", None),
    ("CONTRIBUTING.md", "CONTRIBUTING.md", None),
    ("SECURITY.md", "SECURITY.md", None),
    ("CHANGELOG.md", "CHANGELOG.md", None),
    ("docs/GITHUB-ABLAUF.md", "docs/GITHUB-ABLAUF.md", None),
]
# Teile des Blueprints, die in ein anderes Repository kopiert werden (--ziel)
BLUEPRINT_PARTS = [
    ".github/blueprint",
    ".github/workflows/issue-milestone.yml",
    ".github/workflows/milestone-admin.yml",
    ".github/workflows/release.yml",
    ".github/workflows/blueprint-anwenden.yml",
]
AGENTS_START, AGENTS_END = "<!-- blueprint:github-ablauf -->", "<!-- /blueprint:github-ablauf -->"


class Report:
    def __init__(self, dry: bool):
        self.dry = dry
        self.lines: list[str] = []
        self.warnings: list[str] = []

    def do(self, text: str) -> None:
        self.lines.append(("(Probelauf) " if self.dry else "") + text)
        print(self.lines[-1])

    def warn(self, text: str) -> None:
        self.warnings.append(text)
        print("⚠ " + text)


def load_config(path: Path) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def context(cfg: dict, repo: str) -> dict[str, str]:
    p, v, i = cfg.get("projekt", {}), cfg.get("versionierung", {}), cfg.get("issues", {})
    privacy = p.get("datenschutz", "").strip()
    ablauf = (
        "  - type: markdown\n    attributes:\n      value: |\n"
        "        **Ablauf:** Neue Meldungen erhalten das Label `triage` und werden geprüft. Erst die ausdrückliche\n"
        f"        Freigabe (Label `_1 bereit`, {p.get('verantwortlich', 'Projektverantwortliche:r')}) macht daraus einen Entwicklungsauftrag."
    )
    if privacy:
        ablauf += f"\n\n        **Datenschutz:** {privacy}"
    return {
        "name": p.get("name", "Projekt"),
        "kurz": p.get("kurz", "Projekt"),
        "repo": repo,
        "verantwortlich": p.get("verantwortlich", "Projektverantwortliche:r"),
        "sicherheit_kontakt": p.get("sicherheit_kontakt", "direkt an den Eigentümer dieses Repositorys"),
        "version_ort": p.get("version_ort", "in der Anwendung"),
        "pruefbefehl": p.get("pruefbefehl", "make check"),
        "versionsdatei": v.get("datei", "VERSION"),
        "release_beispiel": v.get("release_titel", "{kurz} {version}").format(kurz=p.get("kurz", "Projekt"), name=p.get("name", ""), version="0.2.0"),
        "datenschutz_satz": f" **Datenschutz:** {privacy}" if privacy else "",
        "ablauf": ablauf,
        "bereiche": "\n".join(f"        - {b}" for b in i.get("bereiche", ["Allgemein", "anderes"])),
    }


def render(text: str, ctx: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        if m.group(1) not in ctx:
            raise KeyError(f"Platzhalter {{{{{m.group(1)}}}}} unbekannt")
        return ctx[m.group(1)]
    return re.sub(r"\{\{(\w+)\}\}", repl, text)


# --- Dateien -------------------------------------------------------------------------------------------------

def apply_files(cfg: dict, root: Path, ctx: dict[str, str], rep: Report, force: bool) -> None:
    extras = set(cfg.get("issues", {}).get("zusatzvorlagen", []))
    for src, dst, cond in FILES:
        if cond and cond not in extras:
            continue
        content = render((TEMPLATES / src).read_text(encoding="utf-8"), ctx)
        target = root / dst
        if target.exists():
            if target.read_text(encoding="utf-8") == content:
                continue
            if not force:
                hint = " – Abschnitt «## [Unveröffentlicht]» fehlt" if dst == "CHANGELOG.md" and "## [Unveröffentlicht]" not in target.read_text(encoding="utf-8") else ""
                rep.warn(f"{dst} gibt es schon und weicht ab – nicht überschrieben{hint} (Vorlage: .github/blueprint/templates/{src})")
                continue
        rep.do(f"Datei {dst} {'überschrieben' if target.exists() else 'angelegt'}")
        if not rep.dry:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    # Unterstützung (nur öffentliche Repositorys)
    if cfg.get("repository", {}).get("sichtbarkeit") == "oeffentlich":
        fund = settings.funding(cfg)
        for dst, content in ((".github/FUNDING.yml", fund), ("docs/UNTERSTUETZEN.md", render((TEMPLATES / "docs/UNTERSTUETZEN.md").read_text(encoding="utf-8"), ctx) if fund else "")):
            if not content:
                continue
            target = root / dst
            if target.exists() and target.read_text(encoding="utf-8") != content and not force:
                rep.warn(f"{dst} gibt es schon und weicht ab – nicht überschrieben")
                continue
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                rep.do(f"Datei {dst} {'überschrieben' if target.exists() else 'angelegt'}")
                if not rep.dry:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")

    # AGENTS.md: Abschnitt zwischen Markierungen
    section = render((TEMPLATES / "AGENTS-github.md").read_text(encoding="utf-8"), ctx).strip() + "\n"
    agents = root / "AGENTS.md"
    if agents.exists():
        text = agents.read_text(encoding="utf-8")
        if AGENTS_START in text and AGENTS_END in text:
            new = re.sub(re.escape(AGENTS_START) + r".*?" + re.escape(AGENTS_END) + r"\n?", lambda _m: section, text, flags=re.S)
        else:
            new = text.rstrip() + "\n\n" + section
        if new != text:
            rep.do("AGENTS.md: Abschnitt «GitHub-Ablauf und Releases» " + ("aktualisiert" if AGENTS_START in text else "ergänzt"))
            if not rep.dry:
                agents.write_text(new, encoding="utf-8")
    else:
        rep.do("Datei AGENTS.md angelegt (Abschnitt «GitHub-Ablauf und Releases»)")
        if not rep.dry:
            agents.write_text(f"# AGENTS.md – Hinweise für KI-Agenten\n\nProjekt: {ctx['name']}.\n\n" + section, encoding="utf-8")

    # Versionsdatei
    v = cfg.get("versionierung", {})
    vfile = root / v.get("datei", "VERSION")
    if not vfile.exists():
        if v.get("datei", "VERSION") == "VERSION":
            rep.do(f"Datei VERSION angelegt ({v.get('startversion', '0.1.0')})")
            if not rep.dry:
                vfile.write_text(v.get("startversion", "0.1.0") + "\n", encoding="utf-8")
        else:
            rep.warn(f"Versionsdatei {v.get('datei')} fehlt – bitte anlegen oder [versionierung] datei anpassen.")


def copy_blueprint(target_root: Path, rep: Report, force: bool) -> None:
    """Blueprint-Dateien in ein anderes Repository kopieren (Workflows, Skripte, Vorlagen)."""
    source_root = HERE.parents[1]
    for part in BLUEPRINT_PARTS:
        src, dst = source_root / part, target_root / part
        if src.is_dir():
            if dst.exists() and not force:
                rep.warn(f"{part}/ gibt es schon – nicht überschrieben (--ueberschreiben zum Aktualisieren)")
                continue
            rep.do(f"Ordner {part}/ kopiert")
            if not rep.dry:
                shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            if dst.exists() and dst.read_bytes() != src.read_bytes() and not force:
                rep.warn(f"{part} gibt es schon und weicht ab – nicht überschrieben")
                continue
            if not dst.exists() or force:
                rep.do(f"Datei {part} kopiert")
                if not rep.dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
    cfg_dst = target_root / ".github" / "blueprint.toml"
    if not cfg_dst.exists():
        rep.do("Datei .github/blueprint.toml angelegt (bitte anhand CHECKLISTE.md ausfüllen)")
        if not rep.dry:
            text = (source_root / ".github" / "blueprint.toml").read_text(encoding="utf-8")
            cfg_dst.write_text(re.sub(r"^admin_issue = \d+", "admin_issue = 0", text, flags=re.M), encoding="utf-8")


# --- GitHub --------------------------------------------------------------------------------------------------

def gh_json(*args: str):
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh api {args[0]}: {r.stderr.strip() or r.stdout.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def apply_github(cfg: dict, repo: str, root: Path, config_path: Path, rep: Report) -> None:
    from urllib.parse import quote
    issues_cfg = cfg.get("issues", {})
    existing = {l["name"]: l for l in gh_json(f"repos/{repo}/labels?per_page=100")}
    wanted = STATUS_LABELS + KIND_LABELS
    wanted += [OPTIONAL_LABELS[x] for x in issues_cfg.get("zusatzvorlagen", []) if x in OPTIONAL_LABELS]
    wanted += [(l["name"], l.get("farbe", "ededed"), l.get("beschreibung", "")) for l in issues_cfg.get("zusatzlabels", [])]
    for name, color, desc in wanted:
        if name in existing:
            continue
        rep.do(f"Label «{name}» angelegt")
        if not rep.dry:
            gh_json("-X", "POST", f"repos/{repo}/labels", "-f", f"name={name}", "-f", f"color={color}", "-f", f"description={desc}")
    if issues_cfg.get("standard_labels_entfernen", False):
        for name in GITHUB_DEFAULT_LABELS:
            if name in existing:
                count = len(gh_json(f"repos/{repo}/issues?labels={quote(name)}&state=all&per_page=1"))
                if count:
                    rep.warn(f"Standard-Label «{name}» wird noch von {count} Issue(s) verwendet – nicht entfernt (bitte zuerst umstellen)")
                    continue
                rep.do(f"Standard-Label «{name}» entfernt (unbenutzt)")
                if not rep.dry:
                    gh_json("-X", "DELETE", f"repos/{repo}/labels/{quote(name)}")

    ms = cfg.get("meilensteine", {})
    titles = {m["title"] for m in gh_json(f"repos/{repo}/milestones?state=all&per_page=100")}
    wanted_ms = dict(COLLECTIONS) if ms.get("sammlungen", True) else {}
    if ms.get("erster_release"):
        wanted_ms[ms["erster_release"]] = "Erster Release-Meilenstein"
    for title, desc in wanted_ms.items():
        if title in titles:
            continue
        rep.do(f"Meilenstein «{title}» angelegt")
        if not rep.dry:
            gh_json("-X", "POST", f"repos/{repo}/milestones", "-f", f"title={title}", "-f", f"description={desc}")

    wf = cfg.get("workflows", {})
    if wf.get("milestone_admin", True) and int(wf.get("admin_issue", 0)) == 0:
        rep.do("Admin-Issue «Administration: Meilensteine» angelegt und geschlossen, Nummer in .github/blueprint.toml eingetragen")
        if not rep.dry:
            body = ("**Administrationskanal für Meilensteine** – nur Kommentare des Repository-Eigentümers werden ausgeführt "
                    "(`.github/workflows/milestone-admin.yml`, Anleitung `.github/blueprint/MILESTONE-ADMIN.md`).\n\n"
                    "Bewusst geschlossen; Kommentare sind trotzdem möglich. Ein Befehl pro Kommentar:\n\n"
                    "```\n/milestone list\n/milestone create 0.2.0 – Titel\n/milestone close NUMMER\n/milestone reopen NUMMER\n```\n")
            issue = gh_json("-X", "POST", f"repos/{repo}/issues", "-f", "title=Administration: Meilensteine", "-f", f"body={body}")
            gh_json("-X", "PATCH", f"repos/{repo}/issues/{issue['number']}", "-f", "state=closed", "-f", "state_reason=completed")
            text = config_path.read_text(encoding="utf-8")
            config_path.write_text(re.sub(r"^admin_issue = \d+", f"admin_issue = {issue['number']}", text, flags=re.M), encoding="utf-8")


def detect_repo(root: Path) -> str:
    if os.environ.get("GITHUB_REPOSITORY"):
        return os.environ["GITHUB_REPOSITORY"]
    r = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", r.stdout.strip())
    return m.group(1) if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description="GitHub-Blueprint anwenden")
    ap.add_argument("--ziel", default=str(HERE.parents[1]), help="Repository-Ordner (Standard: dieses Repository)")
    ap.add_argument("--repo", default="", help="owner/name auf GitHub (Standard: aus GITHUB_REPOSITORY bzw. git remote)")
    ap.add_argument("--probelauf", action="store_true", help="nichts ändern, nur anzeigen")
    ap.add_argument("--nur-dateien", action="store_true")
    ap.add_argument("--nur-github", action="store_true")
    ap.add_argument("--ueberschreiben", action="store_true", help="bestehende Dateien durch die Vorlagen ersetzen")
    ap.add_argument("--sichtbarkeit", action="store_true", help="Sichtbarkeit (öffentlich/privat) gemäss Konfiguration ändern")
    ap.add_argument("--ohne-einstellungen", action="store_true", help="Repository-Einstellungen nicht prüfen/ändern")
    args = ap.parse_args()

    root = Path(args.ziel).resolve()
    rep = Report(args.probelauf)
    config_path = root / ".github" / "blueprint.toml"
    if root != HERE.parents[1].resolve():
        fresh = not config_path.exists()
        copy_blueprint(root, rep, args.ueberschreiben)
        if fresh and not args.probelauf:
            print(f"\nBlueprint nach {root} kopiert. Jetzt .github/blueprint.toml anhand CHECKLISTE.md ausfüllen und "
                  "danach dort «python3 .github/blueprint/apply.py --probelauf» bzw. den Workflow «Blueprint anwenden» starten.")
            return 0
    if not config_path.exists():
        config_path = HERE.parent / "blueprint.toml"  # Probelauf auf ein Repository ohne Konfiguration
    cfg = load_config(config_path)
    repo = args.repo or detect_repo(root)
    if not repo and not args.nur_dateien:
        print("✗ GitHub-Repository unbekannt – bitte --repo owner/name angeben.", file=sys.stderr)
        return 1
    try:
        if not args.nur_github:
            apply_files(cfg, root, context(cfg, repo or "OWNER/REPO"), rep, args.ueberschreiben)
        manual: list[str] = []
        if not args.nur_dateien:
            apply_github(cfg, repo, root, root / ".github" / "blueprint.toml", rep)
            if not args.ohne_einstellungen:
                manual = settings.apply_settings(cfg, repo, rep, args.sichtbarkeit)
    except (RuntimeError, KeyError, OSError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    if manual:
        print("\nVon Hand (GitHub bietet dafür keine API):")
        for step in manual:
            print(f"  ☐ {step}")
    print(f"\n{len(rep.lines)} Schritt(e), {len(rep.warnings)} Hinweis(e).")
    if rep.dry:
        print("Probelauf – nichts geändert. Ohne --probelauf ausführen, um anzuwenden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
