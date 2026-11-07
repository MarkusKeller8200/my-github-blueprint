#!/usr/bin/env python3
"""GitHub-Blueprint auf ein Ziel-Repository anwenden – läuft immer vom Blueprint aus (nur Standardbibliothek, 3.11+).

    python3 .github/blueprint/start.py --ziel ../projekt                   zuerst: Start-Checkliste
    python3 .github/blueprint/apply.py --ziel ../projekt --probelauf       zeigen, was passieren würde
    python3 .github/blueprint/apply.py --ziel ../projekt                   anwenden (Dateien + GitHub)
    … --nur-dateien | --nur-github                                         nur einen Teil
    … --aufraeumen [--ja]                                                  Ballast entfernen (nach Rückfrage)
    … --aktualisieren                                                      Laufzeitdateien auf den Stand des Blueprints

Ins Ziel kommt nur, was das Projekt braucht (manifest.toml): die Laufzeitdateien der eingeschalteten Funktionen
und die aus .github/blueprint/templates erzeugten Dateien. Werkzeuge für die Einrichtung (apply.py, start.py,
Vorlagen …) und Dateien des Blueprints selbst bleiben hier. Ballast im Ziel – etwa nach «Use this template» – wird
gemeldet und mit --aufraeumen nach ausdrücklicher Bestätigung entfernt (git rm, über den Verlauf wiederherstellbar).
Bestehende Dateien werden NIE überschrieben (ausser --ueberschreiben bzw. --aktualisieren für Laufzeitdateien).
AGENTS.md erhält den Abschnitt «GitHub-Ablauf» zwischen Markierungen (wird beim erneuten Anwenden aktualisiert).
GitHub (über die gh-CLI): Labels, Meilensteine, Admin-Issue, Repository-Einstellungen; GitHub-Standard-Labels nur
entfernen, wenn eingeschaltet (es werden nie Issues gelöscht).

Für das Blueprint-Repository selbst (nur GitHub-Einstellungen):
    python3 .github/blueprint/apply.py --config .github/blueprint-repo.toml --nur-github
"""
from __future__ import annotations

import argparse
import difflib
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
import release  # noqa: E402  (Versionsdatei, Tabelle «Unterstützte Versionen»)
import third_party  # noqa: E402  (Liste der Fremdkomponenten)
import manifest  # noqa: E402  (was ins Ziel gehört, was Ballast ist)

SOURCE = HERE.parents[1]

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
    ("abhaengigkeiten", "0366d6", "Aktualisierung von Abhängigkeiten (Dependabot)"),
    ("wird nicht umgesetzt", "ffffff", "Bewusst abgelehnt"),
]
OPTIONAL_LABELS = {
    "plugin": ("plugin", "5319e7", "Anbindung über ein Plugin"),
    "gui": ("gui", "1d76db", "Oberfläche, GUI-Bausteine, Farbkonzept"),
    "uebersetzung": ("uebersetzung", "c5def5", "Texte und Übersetzungen der Oberfläche"),
}
CODEQL_LABEL = ("codeql", "5319e7", "Fund aus dem Code Scanning (CodeQL), automatisch angelegt")

# Vorgaben je nach projekt.art für «Fehler melden» (issues.plattformen / issues.varianten = "auto")
ART_FIELDS = {
    "desktop": {
        "plattform": ("Betriebssystem", ["Windows 11", "Windows 10", "macOS (Apple Silicon)", "macOS (Intel)", "Linux", "anderes"]),
        "variante": ("Variante", ["Installer", "Portable / ZIP", "aus dem Quellcode", "anderes"]),
        "hinweis": "Bildschirmfoto, Häufigkeit, Protokolldatei",
    },
    "web": {
        "plattform": ("Browser / Gerät", ["Chrome", "Edge", "Firefox", "Safari", "Smartphone / Tablet", "anderes"]),
        "variante": ("Umgebung", ["Produktion", "Test", "lokal / Entwicklung"]),
        "hinweis": "Bildschirmfoto, Häufigkeit, ungefähre Uhrzeit (hilft beim Finden im Server-Protokoll)",
    },
    "beides": {
        "plattform": ("Plattform", ["Windows", "macOS", "Linux", "Browser (Chrome, Edge, Firefox)", "Browser (Safari)",
                                    "Smartphone / Tablet", "anderes"]),
        "variante": ("Variante", ["Installer / App", "Web – Produktion", "Web – Test", "aus dem Quellcode"]),
        "hinweis": "Bildschirmfoto, Häufigkeit, Protokolldatei bzw. ungefähre Uhrzeit",
    },
}
LANG_NAMES = {"de": "Deutsch", "en": "Englisch", "fr": "Französisch", "it": "Italienisch", "rm": "Rätoromanisch", "es": "Spanisch"}
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
    ("ISSUE_TEMPLATE/translation.yml", ".github/ISSUE_TEMPLATE/translation.yml", "uebersetzung"),
    ("ISSUE_TEMPLATE/config.yml", ".github/ISSUE_TEMPLATE/config.yml", None),
    ("pull_request_template.md", ".github/pull_request_template.md", None),
    ("CONTRIBUTING.md", "CONTRIBUTING.md", None),
    ("SECURITY.md", "SECURITY.md", None),
    ("CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.md", "verhaltenskodex"),
    ("CHANGELOG.md", "CHANGELOG.md", None),
    ("docs/GITHUB-ABLAUF.md", "docs/GITHUB-ABLAUF.md", None),
    ("CLAUDE.md", "CLAUDE.md", "uebergabe"),
    ("docs/UEBERGABE.md", "docs/UEBERGABE.md", "uebergabe"),
    ("docs/PROJEKTSTAND.md", "docs/PROJEKTSTAND.md", "uebergabe"),
    ("docs/KONZEPT-VORLAGE.md", "docs/KONZEPT-VORLAGE.md", "konzepte"),
    ("copilot-instructions.md", ".github/copilot-instructions.md", None),
    ("devcontainer/devcontainer.json", ".devcontainer/devcontainer.json", "codespaces"),
    ("workflows/pages.yml", ".github/workflows/pages.yml", "pages"),
    ("workflows/installer.yml", ".github/workflows/installer.yml", "installer"),
    ("README.md", "README.md", None),
]
# Versionsdateien, die angelegt werden, wenn sie fehlen ({name}, {slug}, {version})
VERSION_FILES = {
    "VERSION": "{version}\n",
    "version.py": '"""Version des Projekts (GitHub-Blueprint: release.py set X.Y.Z)."""\nVERSION = "{version}"\n',
    "package.json": '{{\n  "name": "{slug}",\n  "version": "{version}",\n  "private": true\n}}\n',
    "composer.json": '{{\n  "name": "projekt/{slug}",\n  "description": "{name}",\n  "version": "{version}",\n  "type": "project"\n}}\n',
    "pyproject.toml": '[project]\nname = "{slug}"\nversion = "{version}"\ndescription = "{name}"\nrequires-python = ">=3.11"\n',
}


def dependabot_yml(cfg: dict) -> str:
    d = cfg.get("dependabot", {})
    lines = ["# Dependabot (GitHub-Blueprint, [dependabot] in .github/blueprint.toml)", "version: 2", "updates:"]
    for eco in d.get("oekosysteme", ["github-actions"]):
        lines += [f'  - package-ecosystem: "{eco}"', '    directory: "/"', "    schedule:", f'      interval: "{d.get("intervall", "weekly")}"',
                  "    labels:", '      - "abhaengigkeiten"']
        if int(d.get("cooldown_tage", 0)) > 0:
            lines += ["    cooldown:", f"      default-days: {int(d['cooldown_tage'])}"]
        lines += ["    groups:", f"      {eco.replace('-', '_')}:", '        patterns: ["*"]']
        if d.get("commit_praefix"):
            lines += ["    commit-message:", f'      prefix: "{d["commit_praefix"]}"']
    return "\n".join(lines) + "\n"
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


def art(cfg: dict) -> str:
    a = cfg.get("projekt", {}).get("art", "web")
    return a if a in ART_FIELDS else "web"


def is_public(cfg: dict) -> bool:
    return cfg.get("repository", {}).get("sichtbarkeit") == "oeffentlich"


def features(cfg: dict) -> set[str]:
    """Bedingungen für die Vorlagen in FILES (zusatzvorlagen und Schalter aus der Konfiguration)."""
    p, ag = cfg.get("projekt", {}), cfg.get("agenten", {})
    on = set(cfg.get("issues", {}).get("zusatzvorlagen", []))
    if cfg.get("codespaces", {}).get("devcontainer"):
        on.add("codespaces")
    if cfg.get("pages", {}).get("aktiv"):
        on.add("pages")
    if settings._auto(p.get("verhaltenskodex", "auto"), is_public(cfg), True, False):
        on.add("verhaltenskodex")
    if ag.get("uebergabe", True):
        on.add("uebergabe")
    if ag.get("konzepte", True):
        on.add("konzepte")
    if manifest.BEDINGUNGEN["installer"](cfg):
        on.add("installer")
    return on


def dropdown(field_id: str, label: str, options: list[str], required: bool) -> str:
    opts = "\n".join(f"        - {o}" for o in options)
    return (f"\n  - type: dropdown\n    id: {field_id}\n    attributes:\n      label: {label}\n      options:\n{opts}\n"
            f"    validations:\n      required: {'true' if required else 'false'}")


def bug_fields(cfg: dict) -> str:
    i, defaults = cfg.get("issues", {}), ART_FIELDS[art(cfg)]
    out = ""
    for key, plural, field_id, required in (("plattform", "plattformen", "platform", True), ("variante", "varianten", "variant", False)):
        options = i.get(plural, "auto")
        title = i.get(f"{key}_titel", "auto")
        if options == "auto":
            options = defaults[key][1]
        if title == "auto":
            title = defaults[key][0]
        if options:
            out += dropdown(field_id, title, list(options), required)
    return out


def context(cfg: dict, repo: str, root: Path | None = None) -> dict[str, str]:
    p, v, i = cfg.get("projekt", {}), cfg.get("versionierung", {}), cfg.get("issues", {})
    privacy = p.get("datenschutz", "").strip()
    ablauf = (
        "  - type: markdown\n    attributes:\n      value: |\n"
        "        **Ablauf:** Neue Meldungen erhalten das Label `triage` und werden geprüft. Erst die ausdrückliche\n"
        f"        Freigabe (Label `_1 bereit`, {p.get('verantwortlich', 'Projektverantwortliche:r')}) macht daraus einen Entwicklungsauftrag."
    )
    if privacy:
        ablauf += f"\n\n        **Datenschutz:** {privacy}"
    extras = set(i.get("zusatzvorlagen", []))
    vorlagen = [("Fehler melden", "`fehler`, `triage`", "Fehler"),
                ("Verbesserung", "`verbesserung`, `triage`", "Verbesserungen"),
                ("Neue Funktion / Idee", "`funktion`, `triage`", "Funktionen")]
    if "plugin" in extras:
        vorlagen.append(("Plugin-Idee", "`funktion`, `plugin`, `triage`", "Funktionen"))
    if "gui" in extras:
        vorlagen.append(("GUI-Baustein", "`verbesserung`, `gui`, `triage`", "Verbesserungen"))
    if "uebersetzung" in extras:
        vorlagen.append(("Übersetzung", "`funktion`, `uebersetzung`, `triage`", "Funktionen"))
    kinds = [l for k, l in (("plugin", "Plugin"), ("gui", "GUI-Baustein"), ("uebersetzung", "Übersetzung")) if k in extras]
    manifeste = v.get("plugin_manifeste", [])
    langs = [x for x in p.get("sprachen_auslieferung", []) if x]
    tp = cfg.get("fremdkomponenten", {})
    tp_file = tp.get("datei", "docs/third-party.json")
    checks = (["Bei Änderung an Plugins bzw. Modulen `version` im Manifest erhöht"] if manifeste else [])
    if len(langs) > 1:
        checks.append(f"Neue bzw. geänderte Oberflächentexte in allen Sprachen ({', '.join(langs)})")
    if tp.get("aktiv", False):
        checks.append(f"Neue Abhängigkeiten in `{tp_file}` eingetragen (Lizenz geprüft)")
    checks += list(p.get("pr_checkliste", []))
    grundsaetze = list(p.get("sicherheit_grundsaetze", []))
    entwicklung = p.get("entwicklung", "").strip()
    doku_url = p.get("doku_url", "").strip()
    oeffentlich = cfg.get("repository", {}).get("sichtbarkeit") == "oeffentlich"
    return {
        "vorlagen_tabelle": "\n".join(f"| {a:<20} | {b:<31} | {c:<25} |" for a, b, c in vorlagen),
        "pr_art_zusatz": "".join(f"\n- [ ] {a}" for a in kinds),
        "pr_checks_zusatz": "".join(f"\n- [ ] {c}" for c in checks),
        "entwicklung": f"\n\n## Entwicklungsumgebung\n\n{entwicklung}" if entwicklung else "",
        "sicherheit_grundsaetze": ("\n\n## Grundsätze\n\n" + "\n".join(f"- {g}" for g in grundsaetze)) if grundsaetze else "",
        "sicherheit_privat_hinweis": "" if oeffentlich else ("\n\nPrivate Sicherheitsmeldungen über GitHub («Report a vulnerability») gibt es nur bei öffentlichen "
                                                              "Repositorys."),
        "doku_link": (f"\n  - name: {p.get('doku_titel', 'Dokumentation')}\n    url: {doku_url}\n    about: {p.get('doku_beschreibung', 'Konzepte, Anleitungen und Betrieb.')}") if doku_url else "",
        "release_befehl": v.get("release_befehl", "python3 .github/blueprint/release.py set X.Y.Z --commit"),
        "release_befehl_beispiel": v.get("release_befehl", "python3 .github/blueprint/release.py set X.Y.Z --commit").replace("X.Y.Z", "0.2.0"),
        "release_check_befehl": v.get("release_check_befehl", "python3 .github/blueprint/release.py check"),
        "name": p.get("name", "Projekt"),
        "kurz": p.get("kurz", "Projekt"),
        "beschreibung": cfg.get("repository", {}).get("beschreibung", "").strip() or "(Beschreibung folgt)",
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
        "pages_ordner": cfg.get("pages", {}).get("ordner", "docs"),
        **extra_context(cfg, repo, root, langs, tp, tp_file, manifeste, extras),
        "sicherheit_github": (f"Am einfachsten über **Security → Report a vulnerability** "
                              f"(https://github.com/{repo}/security/advisories/new) – privat, nur für die Betreuer:innen sichtbar. Alternativ"
                              if cfg.get("repository", {}).get("sichtbarkeit") == "oeffentlich" else "Melden"),
    }


def extra_context(cfg: dict, repo: str, root: Path | None, langs: list[str], tp: dict, tp_file: str,
                  manifeste: list, extras: set[str]) -> dict[str, str]:
    """Platzhalter für Desktop/Web-Felder, Sicherheit, Verhaltenskodex, Übersetzungen, Übergabe und Leitplanken."""
    p, i, ag = cfg.get("projekt", {}), cfg.get("issues", {}), cfg.get("agenten", {})
    v = cfg.get("versionierung", {})
    feat = features(cfg)
    a = art(cfg)
    hint = ART_FIELDS[a]["hinweis"]
    if i.get("protokoll_ort"):
        hint += f" ({i['protokoll_ort']})"
    table = p.get("sicherheit_versionstabelle", "auto")
    table = (a != "web") if table == "auto" else bool(table)
    version = (release.read_version(cfg, root) if root else "") or v.get("startversion", "0.1.0")
    if not release.SEMVER.match(version):
        version = v.get("startversion", "0.1.0")
    outside = list(p.get("sicherheit_nicht_im_bereich", []))
    scope = ("\n\n## Geltungsbereich\n\nIm Geltungsbereich: der Code in diesem Repository"
             + (" (Anwendung, Installer und Workflows)." if a != "web" else " (Anwendung, Konfiguration und Workflows).")
             + "\n\nNicht im Geltungsbereich:\n" + "\n".join(f"- {x}" for x in outside)) if outside else ""
    contrib = []
    if len(langs) > 1:
        ablage = f" in `{i['uebersetzung_ablage']}`" if i.get("uebersetzung_ablage") else ""
        contrib.append(f"**Übersetzungen:** Neue oder geänderte Oberflächentexte kommen im selben Pull Request in allen "
                       f"Sprachen ({', '.join(langs)}){ablage}.")
    if tp.get("aktiv", False):
        contrib.append(f"**Abhängigkeiten:** Neue Bibliotheken, Werkzeuge oder Dienste in `{tp_file}` eintragen (mit Lizenz; "
                       "`python3 .github/blueprint/third_party.py --erfassen` übernimmt sie aus den Paketdateien).")
    if manifeste:
        contrib.append("**Plugins/Module:** Bei Änderungen die `version` im Manifest erhöhen.")
    agents = []
    if len(langs) > 1:
        agents.append(f"- **Mehrsprachigkeit:** Jeder neue oder geänderte Oberflächentext kommt im selben Commit in allen "
                      f"Auslieferungssprachen ({', '.join(langs)})"
                      + (f", abgelegt in `{i['uebersetzung_ablage']}`" if i.get("uebersetzung_ablage") else "") + ".")
    if manifeste:
        agents.append("- **Plugin-/Modul-Versionen:** Wer ein Plugin bzw. Modul ändert, erhöht dessen `version` im Manifest; "
                      f"`{v.get('release_check_befehl', 'python3 .github/blueprint/release.py check')}` weist auf vergessene Erhöhungen hin.")
    if "uebergabe" in feat:
        agents.append("- **Übergabe:** `docs/UEBERGABE.md` und `docs/PROJEKTSTAND.md` am Ende jeder Sitzung bzw. vor einem "
                      "Chatwechsel nachführen (neueste Einträge oben, Älteres nach `docs/PROJEKTSTAND-ARCHIV.md`)."
                      + (" Kopien im Claude-Projekt (`claude/uebergabe.md`, `claude/projektstand.md`) mitführen." if ag.get("projekt_kopie", False) else ""))
    if a in ("desktop", "beides"):
        agents.append("- **Desktop:** Installer, Signatur und Build-Workflows nur nach Freigabe ändern; Tests müssen auf allen "
                      "Zielsystemen laufen (Workflow «pruefungen»).")
    if a in ("web", "beides"):
        agents.append("- **Web:** Ausrollen auf «produktion» nur über die Umgebung mit Freigabe; keine echten Personendaten in "
                      "Tests, Protokollen oder Bildschirmfotos.")
    agents += [f"- {x}" for x in ag.get("regeln", [])]
    trans_langs = i.get("uebersetzung_sprachen") or [LANG_NAMES.get(x.split("-")[0], x) for x in langs[1:]] or ["Englisch", "Französisch", "Italienisch"]
    sprache = p.get("sprache", "de-CH")
    return {
        "plattform_feld": bug_fields(cfg),
        "extra_hinweis": hint,
        "versionstabelle": ("\n\n" + release.security_table(version)) if table else "",
        "sicherheit_antwortzeit": p.get("sicherheit_antwortzeit", "5 Arbeitstagen"),
        "sicherheit_bereich": scope,
        "verhaltenskodex_satz": " Bitte halte dich an den [Verhaltenskodex](CODE_OF_CONDUCT.md)." if "verhaltenskodex" in feat else "",
        "verhaltenskodex_kontakt": p.get("verhaltenskodex_kontakt") or p.get("sicherheit_kontakt", "die Projektverantwortlichen"),
        "contrib_regeln": "".join(f"\n{5 + n}. {c}" for n, c in enumerate(contrib)),
        "fremdkomponenten_regel": f"; neue Komponenten in `{tp_file}` eintragen" if tp.get("aktiv", False) else "",
        "agents_zusatz": ("\n" + "\n".join(agents)) if agents else "",
        "uebersetzung_sprachen": "\n".join(f"        - {x}" for x in [*trans_langs, "anderes"]),
        "uebersetzung_ablage": f" (`{i['uebersetzung_ablage']}`)" if i.get("uebersetzung_ablage") else "",
        "uebergabe_projekt": ("\nKopien im Claude-Projekt: `claude/uebergabe.md` und `claude/projektstand.md` – bei jeder Übergabe beide "
                              "Orte nachführen.") if ag.get("projekt_kopie", False) else "",
        "sprache_name": LANG_NAMES.get(sprache.split("-")[0], sprache),
    }


def render(text: str, ctx: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        if m.group(1) not in ctx:
            raise KeyError(f"Platzhalter {{{{{m.group(1)}}}}} unbekannt")
        return ctx[m.group(1)]
    return re.sub(r"\{\{(\w+)\}\}", repl, text)


# --- Dateien -------------------------------------------------------------------------------------------------

def apply_files(cfg: dict, root: Path, ctx: dict[str, str], rep: Report, force: bool, gone: set[str] | None = None) -> None:
    """Dateien aus den Vorlagen erzeugen. «gone» = Pfade, die gerade als Ballast entfernt werden (gelten als fehlend)."""
    gone = gone or set()
    exists = lambda rel: (root / rel).exists() and rel not in gone
    extras = features(cfg)
    items = [(src, dst, cond, None) for src, dst, cond in FILES]
    if cfg.get("dependabot", {}).get("oekosysteme", ["github-actions"]):
        items.append(("(erzeugt)", ".github/dependabot.yml", None, dependabot_yml(cfg)))
    for src, dst, cond, generated in items:
        if cond and cond not in extras:
            continue
        if dst.startswith(".github/workflows/") and os.environ.get("GITHUB_ACTIONS"):
            if not exists(dst):
                rep.warn(f"{dst} kann in Actions nicht angelegt werden (GITHUB_TOKEN darf keine Workflows schreiben) – lokal ausführen")
            continue
        content = generated if generated is not None else render((TEMPLATES / src).read_text(encoding="utf-8"), ctx)
        target = root / dst
        if exists(dst):
            if target.read_text(encoding="utf-8") == content:
                continue
            if not force:
                hint = " – Abschnitt «## [Unveröffentlicht]» fehlt" if dst == "CHANGELOG.md" and "## [Unveröffentlicht]" not in target.read_text(encoding="utf-8") else ""
                rep.warn(f"{dst} gibt es schon und weicht ab – nicht überschrieben{hint} (Vorlage: .github/blueprint/templates/{src})")
                continue
        rep.do(f"Datei {dst} {'überschrieben' if exists(dst) else 'angelegt'}")
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
            if exists(dst) and target.read_text(encoding="utf-8") != content and not force:
                rep.warn(f"{dst} gibt es schon und weicht ab – nicht überschrieben")
                continue
            if not exists(dst) or target.read_text(encoding="utf-8") != content:
                rep.do(f"Datei {dst} {'überschrieben' if exists(dst) else 'angelegt'}")
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

    # Versionsdatei (minimal anlegen, wenn sie fehlt)
    v = cfg.get("versionierung", {})
    vname = v.get("datei", "VERSION")
    vfile = root / vname
    if not vfile.exists():
        start_v = v.get("startversion", "0.1.0")
        tmpl = VERSION_FILES.get(Path(vname).name)
        if tmpl:
            slug = re.sub(r"[^a-z0-9]+", "-", ctx["name"].lower()).strip("-") or "projekt"
            rep.do(f"Datei {vname} angelegt ({start_v})")
            if not rep.dry:
                vfile.parent.mkdir(parents=True, exist_ok=True)
                vfile.write_text(tmpl.format(name=ctx["name"], slug=slug, version=start_v), encoding="utf-8")
        else:
            rep.warn(f"Versionsdatei {vname} fehlt – bitte anlegen oder [versionierung] datei anpassen.")

    license_file(cfg, root, rep)

    # Liste der Fremdkomponenten (nur anlegen, nie überschreiben)
    tp = cfg.get("fremdkomponenten", {})
    if tp.get("aktiv", False):
        target = root / tp.get("datei", "docs/third-party.json")
        if not target.exists():
            data = third_party.empty(ctx["name"], ctx["repo"], cfg.get("projekt", {}).get("lizenz", ""))
            deps = third_party.manifest_deps(root)
            data["items"] += [{"id": d["id"], "group": d["group"], "name": d["name"], "use": "", "license": "", "url": "",
                               "check": d["check"]} for d in deps]
            rep.do(f"Datei {target.relative_to(root)} angelegt ({len(deps)} Abhängigkeit(en) aus den Paketdateien)")
            if not rep.dry:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(third_party.dump(data), encoding="utf-8")
    if is_public(cfg) and not cfg.get("projekt", {}).get("lizenz") and not any((root / n).exists() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt")):
        rep.warn("Öffentliches Repository ohne LICENSE – projekt.lizenz setzen (z. B. \"MIT\" oder \"GPL-3.0-or-later\").")


def license_file(cfg: dict, root: Path, rep: Report) -> None:
    """LICENSE aus der Lizenzvorlage von GitHub (gh api licenses/…), nur wenn sie fehlt."""
    p = cfg.get("projekt", {})
    spdx = (p.get("lizenz") or "").strip()
    target = root / "LICENSE"
    if not spdx or target.exists() or (root / "LICENSE.md").exists():
        return
    key = re.sub(r"-(or-later|only)$", "", spdx.lower())
    holder = p.get("lizenz_inhaber") or p.get("name", "")
    r = subprocess.run(["gh", "api", f"licenses/{key}", "--jq", ".body"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        rep.warn(f"LICENSE: Vorlage «{key}» bei GitHub nicht abrufbar ({(r.stderr or '').strip()[:100]}) – von Hand anlegen.")
        return
    import datetime
    text = r.stdout.replace("[year]", str(datetime.date.today().year)).replace("[fullname]", holder)
    rep.do(f"Datei LICENSE angelegt ({spdx}" + (f", {holder}" if holder else "") + ")")
    if not rep.dry:
        target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def _diffstat(old: Path, new: Path) -> str:
    try:
        a = old.read_text(encoding="utf-8").splitlines()
        b = new.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return "Binärdatei"
    plus = minus = 0
    for line in difflib.unified_diff(a, b, lineterm="", n=0):
        if line.startswith("+") and not line.startswith("+++"):
            plus += 1
        elif line.startswith("-") and not line.startswith("---"):
            minus += 1
    return f"+{plus} −{minus} Zeilen"


def sync_runtime(cfg: dict, root: Path, rep: Report, update: bool, gone: set[str]) -> None:
    """Laufzeitdateien der eingeschalteten Funktionen aus dem Blueprint ins Ziel kopieren (manifest.toml).
    Abweichende Dateien nur mit --aktualisieren (bzw. --ueberschreiben) ersetzen."""
    for rel in manifest.runtime_files(cfg):
        src, dst = SOURCE / rel, root / rel
        if os.environ.get("GITHUB_ACTIONS") and rel.startswith(".github/workflows/"):
            if not dst.exists():
                rep.warn(f"{rel} kann in Actions nicht angelegt werden (GITHUB_TOKEN darf keine Workflows schreiben) – lokal ausführen")
            continue
        if dst.exists() and rel not in gone:
            if dst.read_bytes() == src.read_bytes():
                continue
            if not update:
                rep.warn(f"{rel} weicht vom Blueprint ab ({_diffstat(dst, src)}) – nicht ersetzt (--aktualisieren)")
                continue
            rep.do(f"Datei {rel} aktualisiert ({_diffstat(dst, src)})")
        else:
            rep.do(f"Datei {rel} kopiert")
        if not rep.dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def ensure_config(root: Path, rep: Report) -> Path:
    """.github/blueprint.toml im Ziel; fehlt sie, aus der Vorlage des Blueprints anlegen (Start-Checkliste offen)."""
    cfg_dst = root / ".github" / "blueprint.toml"
    if not cfg_dst.exists():
        rep.do("Datei .github/blueprint.toml angelegt (Vorlage – zuerst Start-Checkliste: start.py --ziel …)")
        if not rep.dry:
            cfg_dst.parent.mkdir(parents=True, exist_ok=True)
            cfg_dst.write_text(config_template(), encoding="utf-8")
    return cfg_dst


def config_template() -> str:
    text = (SOURCE / ".github" / "blueprint.toml").read_text(encoding="utf-8")
    text = re.sub(r"^admin_issue = \d+", "admin_issue = 0", text, flags=re.M)
    return re.sub(r"^erledigt = true", "erledigt = false", text, flags=re.M)


def remove_ballast(cfg: dict, root: Path, rep: Report, do_it: bool, confirmed: bool) -> set[str]:
    """Ballast im Ziel melden; mit --aufraeumen nach Bestätigung entfernen (git rm). → entfernte Pfade."""
    found = manifest.ballast(root, cfg)
    if not found:
        return set()
    if not do_it:
        rep.warn(f"{len(found)} Datei(en) gehören nicht ins Projekt (Ballast) – anzeigen und entfernen mit --aufraeumen:")
        for rel, why in found:
            print(f"    {rel} – {why}")
        return set()
    print(f"\nBallast im Ziel ({len(found)} Datei(en)):")
    for rel, why in found:
        print(f"  {rel} – {why}")
    if rep.dry:
        for rel, _ in found:
            rep.do(f"Datei {rel} entfernt (Ballast)")
        return {rel for rel, _ in found}
    if not confirmed:
        if not sys.stdin.isatty():
            rep.warn("Ballast nicht entfernt: Bestätigung fehlt (im Terminal nachfragen lassen oder --ja nach Rückfrage)")
            return set()
        answer = input("Diese Dateien entfernen? Sie bleiben über den Git-Verlauf wiederherstellbar. [ja/nein] ").strip().lower()
        if answer not in ("j", "ja", "y", "yes"):
            rep.warn("Ballast nicht entfernt (abgelehnt)")
            return set()
    tracked = set(subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True).stdout.splitlines())
    for rel, _ in found:
        if rel in tracked:
            subprocess.run(["git", "-C", str(root), "rm", "-q", "--", rel], check=True)
        else:
            (root / rel).unlink()
        rep.do(f"Datei {rel} entfernt (Ballast)")
    for rel, _ in found:                                       # leere Ordner wegräumen
        parent = (root / rel).parent
        while parent != root and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    return {rel for rel, _ in found}


def workflow_info(text: str) -> tuple[str, set[str]]:
    """Name eines Workflows und die Namen seiner Status-Checks (Job-Name bzw. Job-ID; dynamische Namen fehlen)."""
    m = re.search(r"^name:\s*(.+?)\s*$", text, re.M)
    name = m.group(1).strip("'\"") if m else ""
    checks: set[str] = set()
    body = text.split("\njobs:\n", 1)[1] if "\njobs:\n" in text else ""
    for block in re.split(r"(?m)^(?=  [A-Za-z0-9_-]+:\s*$)", body):
        head = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", block, re.M)
        if not head:
            continue
        job_name = re.search(r"^    name:\s*(.+?)\s*$", block, re.M)
        label = job_name.group(1).strip("'\"") if job_name else head.group(1)
        if "${{" not in label:
            checks.add(label)
    return name, checks


def target_workflows(cfg: dict, root: Path, gone: set[str]) -> dict[str, set[str]]:
    """Workflows, die im Ziel nach dem Anwenden liegen: vorhandene, kopierte und aus Vorlagen erzeugte."""
    texts: dict[str, str] = {}
    folder = root / ".github" / "workflows"
    for f in sorted(folder.glob("*.y*ml")) if folder.exists() else []:
        rel = f.relative_to(root).as_posix()
        if rel not in gone:
            texts[rel] = f.read_text(encoding="utf-8", errors="replace")
    for rel in manifest.runtime_files(cfg):
        if rel.startswith(".github/workflows/"):
            texts.setdefault(rel, (SOURCE / rel).read_text(encoding="utf-8"))
    extras = features(cfg)
    for src, dst, cond in FILES:
        if dst.startswith(".github/workflows/") and (not cond or cond in extras):
            texts.setdefault(dst, (TEMPLATES / src).read_text(encoding="utf-8"))
    return dict(workflow_info(t) for t in texts.values())


def check_gates(cfg: dict, root: Path, rep: Report, gone: set[str]) -> None:
    """Release-Gate und Pflichtprüfungen: gibt es die genannten Workflows bzw. Jobs im Ziel?"""
    state, message = release.release_gate(cfg)
    if state == "warnung":
        rep.warn(message)
    workflows = target_workflows(cfg, root, gone)
    for name in cfg.get("versionierung", {}).get("release_nach", []):
        if name not in workflows:
            hint = " – [ci] aktiv = true setzen" if name == "pruefungen" else ""
            rep.warn(f"versionierung.release_nach nennt «{name}», diesen Workflow gibt es im Ziel nicht – so entsteht nie ein Release{hint}")
    if "installer" in cfg.get("versionierung", {}).get("release_nach", []) and not cfg.get("installer", {}).get("befehl", "").strip():
        rep.warn("[installer] befehl fehlt – ohne Bau-Befehl schlägt «installer» fehl und es entsteht kein Release")
    checks = set().union(*workflows.values()) if workflows else set()
    for name in cfg.get("repository", {}).get("pflicht_pruefungen", []):
        if name not in checks:
            rep.warn(f"repository.pflicht_pruefungen nennt «{name}», diesen Job gibt es im Ziel nicht – Pull Requests liessen sich nie mergen")


def write_blueprint_version(root: Path, rep: Report) -> None:
    """Stand des Blueprints im Ziel festhalten (.github/blueprint/VERSION: Version und Commit)."""
    version = (SOURCE / ".github" / "blueprint" / "VERSION").read_text(encoding="utf-8").split()[0]
    r = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    text = f"{version} {r.stdout.strip()}\n" if r.returncode == 0 and r.stdout.strip() else f"{version}\n"
    dst = root / ".github" / "blueprint" / "VERSION"
    if dst.exists() and dst.read_text(encoding="utf-8") == text:
        return
    rep.do(f"Blueprint-Stand {text.strip()} in .github/blueprint/VERSION")
    if not rep.dry:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")


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
    if cfg.get("codeql", {}).get("workflow", "auto") is not False and cfg.get("codeql", {}).get("issues", True):
        wanted.append(CODEQL_LABEL)
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
            body = ("**Administrationskanal für Meilensteine** – ausgeführt werden nur Kommentare der Eigentümerin bzw. des "
                    "Eigentümers und der Konten in `[workflows] milestone_admins` "
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
    ap = argparse.ArgumentParser(description="GitHub-Blueprint auf ein Ziel-Repository anwenden (läuft vom Blueprint aus)")
    ap.add_argument("--ziel", default="", help="Ordner des Ziel-Repositorys, z. B. ../mein-projekt")
    ap.add_argument("--repo", default="", help="owner/name auf GitHub (Standard: aus git remote des Ziels)")
    ap.add_argument("--probelauf", action="store_true", help="nichts ändern, nur anzeigen")
    ap.add_argument("--nur-dateien", action="store_true")
    ap.add_argument("--nur-github", action="store_true")
    ap.add_argument("--ueberschreiben", action="store_true", help="bestehende Dateien durch die Vorlagen ersetzen")
    ap.add_argument("--aktualisieren", action="store_true", help="Laufzeitdateien (Workflows, Skripte) auf den Stand des Blueprints bringen")
    ap.add_argument("--aufraeumen", action="store_true", help="Ballast im Ziel entfernen (fragt nach; git rm)")
    ap.add_argument("--ja", action="store_true", help="Entfernen ist bereits bestätigt (nur nach ausdrücklicher Rückfrage)")
    ap.add_argument("--sichtbarkeit", action="store_true", help="Sichtbarkeit (öffentlich/privat) gemäss Konfiguration ändern")
    ap.add_argument("--ohne-einstellungen", action="store_true", help="Repository-Einstellungen nicht prüfen/ändern")
    ap.add_argument("--config", default="", help="andere Konfigurationsdatei (nur mit --nur-github, z. B. .github/blueprint-repo.toml für den Blueprint selbst)")
    args = ap.parse_args()
    rep = Report(args.probelauf)

    # Blueprint-Repository selbst: nur GitHub-Einstellungen aus einer eigenen Konfiguration
    if not args.ziel:
        if not (args.config and args.nur_github):
            print("✗ Ziel fehlt: apply.py läuft vom Blueprint aus gegen ein anderes Repository, z. B.\n"
                  "    python3 .github/blueprint/apply.py --ziel ../mein-projekt --probelauf\n"
                  "  (für den Blueprint selbst: --config .github/blueprint-repo.toml --nur-github)", file=sys.stderr)
            return 1
        root, config_path, self_mode = SOURCE, Path(args.config).resolve(), True
    else:
        root, self_mode = Path(args.ziel).resolve(), False
        if root == SOURCE.resolve() or manifest.is_blueprint(root):
            print("✗ Das Ziel ist der Blueprint selbst. Bitte ein anderes Repository angeben (--ziel ../projekt).", file=sys.stderr)
            return 1
        if not root.is_dir():
            print(f"✗ Ziel {root} gibt es nicht (zuerst das Repository klonen).", file=sys.stderr)
            return 1
        config_path = Path(args.config).resolve() if args.config else ensure_config(root, rep)

    cfg = load_config(config_path if config_path.exists() else SOURCE / ".github" / "blueprint.toml")
    start = cfg.get("start")
    if not self_mode and start is not None and not start.get("erledigt", False):
        msg = ("Die Start-Checkliste ist noch nicht beantwortet ([start] erledigt = false). Zuerst "
               f"«python3 .github/blueprint/start.py --ziel {args.ziel}» (bzw. mit Claude die Fragen aus START-CHECKLISTE.md).")
        if not args.probelauf:
            print(f"✗ {msg}", file=sys.stderr)
            return 1
        print(f"⚠ {msg}\n")
    repo = args.repo or detect_repo(root)
    if not repo and not args.nur_dateien:
        print("✗ GitHub-Repository unbekannt – bitte --repo owner/name angeben.", file=sys.stderr)
        return 1
    try:
        if not args.nur_github and not self_mode:
            gone = remove_ballast(cfg, root, rep, args.aufraeumen, args.ja)
            sync_runtime(cfg, root, rep, args.aktualisieren or args.ueberschreiben, gone)
            apply_files(cfg, root, context(cfg, repo or "OWNER/REPO", root), rep, args.ueberschreiben, gone)
            write_blueprint_version(root, rep)
            check_gates(cfg, root, rep, gone)
        manual: list[str] = []
        if not args.nur_dateien:
            apply_github(cfg, repo, root, config_path, rep)
            if not args.ohne_einstellungen:
                manual = settings.apply_settings(cfg, repo, rep, args.sichtbarkeit, root)
    except (RuntimeError, KeyError, OSError, subprocess.CalledProcessError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    if manual:
        print("\nOffen bzw. von Hand (GitHub bietet dafür keine API oder es braucht einen geheimen Wert):")
        for step in manual:
            print(f"  ☐ {step}")
    print(f"\n{len(rep.lines)} Schritt(e), {len(rep.warnings)} Hinweis(e).")
    if rep.dry:
        print("Probelauf – nichts geändert. Ohne --probelauf ausführen, um anzuwenden.")
    elif not self_mode and not args.nur_github:
        print(f"Danach im Ziel die Änderungen prüfen und committen: git -C {args.ziel} status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
