#!/usr/bin/env python3
"""Start-Checkliste: die Fragen vor dem Einrichten des Repositorys und vor dem Grundgerüst des Projekts.

    python3 .github/blueprint/start.py                      Fragen nacheinander stellen (Terminal)
    python3 .github/blueprint/start.py --antworten a.toml   Antworten aus einer Datei (z. B. von Claude ausgefüllt)
    python3 .github/blueprint/start.py --vorlage            leere Antwortdatei ausgeben
    python3 .github/blueprint/start.py --markdown           Fragen als Markdown ausgeben (START-CHECKLISTE.md)
    … --probelauf                                           nur zeigen, was in die Konfiguration käme

Aus den Antworten entstehen:
- die Werte in .github/blueprint.toml (art, Sichtbarkeit, Lizenz, Prüfbefehl, Ökosysteme, Release-Dateien …),
  dazu [start] erledigt = true – erst dann richtet apply.py das Repository ein;
- docs/PROJEKTSTART.md: der Steckbrief des Projekts mit allen Antworten. Er ist die Grundlage für das Grundgerüst;
  dieses wird erst nach Bestätigung durch die/den Projektverantwortliche:n erstellt.
Bestehende Werte, nach denen nicht gefragt wird, bleiben. Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".github" / "blueprint.toml"
STECKBRIEF = ROOT / "docs" / "PROJEKTSTART.md"

TECH = ["Python", "PHP", "JavaScript / TypeScript", "C# / .NET", "Java / Kotlin", "Rust", "Go", "Swift", "andere"]
ECOSYSTEM = {"Python": "pip", "PHP": "composer", "JavaScript / TypeScript": "npm", "C# / .NET": "nuget",
             "Java / Kotlin": "maven", "Rust": "cargo", "Go": "gomod", "Swift": "swift"}
CHECK_CMD = {"Python": "python3 -m unittest discover -s tests", "PHP": "composer test", "JavaScript / TypeScript": "npm test",
             "C# / .NET": "dotnet test", "Java / Kotlin": "mvn -B verify", "Rust": "cargo test", "Go": "go test ./...",
             "Swift": "swift test"}
PREPARE = {"PHP": "composer install --no-interaction --no-progress", "JavaScript / TypeScript": "npm ci"}
CI_VERSION = {"Python": ("python", "3.x"), "JavaScript / TypeScript": ("node", "lts/*"), "Java / Kotlin": ("java", "21"),
              "C# / .NET": ("dotnet", "10.0.x")}
DELIVERY = ["Server (Deployment per SSH, Docker o. Ä.)", "GitHub Pages (statische Seite)", "Installer über GitHub-Releases",
            "App-Store (Microsoft Store, Mac App Store …)", "nur als Quellcode"]
OS_RUNNER = {"Windows": "windows-latest", "macOS": "macos-latest", "Linux": "ubuntu-latest"}

# Jede Frage: id, Teil, Frage, Hilfe, Typ (text, wahl, mehrfach, liste, janein), Optionen, Vorgabe, Pflicht, Bedingung
FRAGEN = [
    # --- A · Projekt ---------------------------------------------------------------------------------------------
    dict(id="name", teil="A · Projekt", frage="Wie heisst das Projekt (voller Name)?", typ="text", pflicht=True,
         hilfe="z. B. «SekBülach Intranet» oder «MarKusSXCH TagStudio»"),
    dict(id="kurz", teil="A · Projekt", frage="Kurzname für Release-Titel?", typ="text",
         vorgabe=lambda a: a.get("name", "").split()[-1] if a.get("name") else "", hilfe="erscheint als «Kurzname 0.2.0»"),
    dict(id="zweck", teil="A · Projekt", frage="Was soll das Projekt leisten, und für wen? (ein bis zwei Sätze)", typ="text",
         pflicht=True, hilfe="wird zur Beschreibung bei «About» und zum Ziel im Steckbrief"),
    dict(id="nichtziele", teil="A · Projekt", frage="Was gehört ausdrücklich nicht dazu (Nichtziele)?", typ="liste",
         hilfe="schützt vor schleichender Ausweitung, z. B. «keine DJ-Mixing-Software»"),
    dict(id="art", teil="A · Projekt", frage="Ist es eine Web-Anwendung, eine Desktop-Anwendung oder beides?", typ="wahl",
         optionen=["web", "desktop", "beides"], pflicht=True,
         hilfe="bestimmt Fehlerformular, Zielsysteme der Tests, Release-Dateien und Regeln für Agenten"),
    dict(id="repo", teil="A · Projekt", frage="Neues oder bestehendes Repository?", typ="wahl", optionen=["neu", "bestehend"],
         vorgabe="neu", hilfe="bestehend: danach Teil C der CHECKLISTE.md (Labels, Tags, vorhandene Workflows)"),
    # --- B · Verantwortung und Sichtbarkeit -------------------------------------------------------------------------
    dict(id="verantwortlich", teil="B · Verantwortung und Sichtbarkeit", frage="Wer gibt Issues und Releases frei (Rolle genügt)?",
         typ="text", vorgabe="Projektverantwortliche:r"),
    dict(id="team", teil="B · Verantwortung und Sichtbarkeit", frage="Arbeitest du allein oder im Team?", typ="wahl",
         optionen=["allein", "team"], vorgabe="allein", hilfe="allein: direkte Pushes; Team: Änderungen über Pull Requests"),
    dict(id="sichtbarkeit", teil="B · Verantwortung und Sichtbarkeit", frage="Ist das Repository öffentlich oder privat?",
         typ="wahl", optionen=["privat", "oeffentlich"], vorgabe="privat",
         hilfe="öffentlich erst ohne Geheimnisse und echte Daten im Verlauf; geändert wird nur mit apply.py --sichtbarkeit"),
    dict(id="lizenz", teil="B · Verantwortung und Sichtbarkeit", frage="Unter welcher Lizenz steht der Code (SPDX)?", typ="text",
         pflicht=lambda a: a.get("sichtbarkeit") == "oeffentlich",
         hilfe="z. B. MIT, Apache-2.0, GPL-3.0-or-later; leer bei privaten Projekten ohne Weitergabe"),
    dict(id="lizenz_inhaber", teil="B · Verantwortung und Sichtbarkeit", frage="Auf wen lautet die Lizenz?", typ="text",
         wenn=lambda a: bool(a.get("lizenz")), wenn_text="nur mit Lizenz", vorgabe=lambda a: a.get("name", "")),
    # --- C · Technik und Grundgerüst --------------------------------------------------------------------------------
    dict(id="technik", teil="C · Technik und Grundgerüst", frage="In welchen Programmiersprachen wird entwickelt?", typ="mehrfach",
         optionen=TECH, pflicht=True, hilfe="bestimmt Dependabot, Vorgaben für Prüfbefehl, CodeQL und die Liste der Fremdkomponenten"),
    dict(id="framework", teil="C · Technik und Grundgerüst", frage="Welches Framework bzw. welche Grundlage?", typ="text",
         vorgabe="offen", hilfe="Web z. B. Laravel, Django, Vite + React; Desktop z. B. Python + pywebview, Electron, Tauri, "
                                "WPF; «offen» = im Konzept klären"),
    dict(id="abhaengigkeiten", teil="C · Technik und Grundgerüst", frage="Welcher Grundsatz gilt für Abhängigkeiten?", typ="wahl",
         optionen=["nur Standardbibliothek im Kern, Pakete nur optional bzw. in Plugins",
                   "bewährte Pakete erlaubt, neue nur nach Prüfung von Lizenz und Pflege", "frei"],
         vorgabe="bewährte Pakete erlaubt, neue nur nach Prüfung von Lizenz und Pflege"),
    dict(id="betriebssysteme", teil="C · Technik und Grundgerüst", frage="Für welche Betriebssysteme?", typ="mehrfach",
         optionen=["Windows", "macOS", "Linux"], vorgabe=["Windows", "macOS"], wenn=lambda a: a.get("art") in ("desktop", "beides"), wenn_text="nur Desktop bzw. beides",
         hilfe="darauf laufen die Tests im Workflow «pruefungen»"),
    dict(id="hosting", teil="C · Technik und Grundgerüst", frage="Wo läuft die Web-Anwendung (Hosting, Server, Datenbank)?",
         typ="text", wenn=lambda a: a.get("art") in ("web", "beides"), wenn_text="nur Web bzw. beides", hilfe="z. B. «Hostinger, PHP 8.4, MySQL» oder «Azure App Service»"),
    dict(id="auslieferung", teil="C · Technik und Grundgerüst", frage="Wie kommt die Anwendung zu den Nutzer:innen?", typ="mehrfach",
         optionen=DELIVERY,
         vorgabe=lambda a: [DELIVERY[2]] if a.get("art") == "desktop" else [DELIVERY[0]],
         hilfe="Installer → Dateien am Release mit Prüfsummen; Pages → Workflow pages.yml"),
    dict(id="daten", teil="C · Technik und Grundgerüst", frage="Welche Daten verarbeitet die Anwendung?", typ="wahl",
         optionen=["keine Personendaten", "Personendaten (DSG bzw. IDG beachten)", "besonders schützenswerte Personendaten"],
         pflicht=True, hilfe="bestimmt Datenschutz-Hinweis in allen Formularen und Grundsätze in SECURITY.md"),
    dict(id="anmeldung", teil="C · Technik und Grundgerüst", frage="Welche Anmeldungen und Zugänge braucht es?", typ="mehrfach",
         optionen=["keine", "eigene Benutzerkonten", "Microsoft Entra ID / SSO", "externe Dienste mit API-Schlüssel oder OAuth"],
         vorgabe=["keine"]),
    dict(id="sprachen", teil="C · Technik und Grundgerüst", frage="In welchen Sprachen wird die Oberfläche ausgeliefert?",
         typ="liste", vorgabe=["de-CH"], hilfe="erste = Ausgangssprache, z. B. de-CH, en, fr; ab zwei Sprachen gilt die Übersetzungsregel"),
    dict(id="plugins", teil="C · Technik und Grundgerüst", frage="Gibt es Plugins oder Module mit eigener Version?", typ="janein",
         vorgabe=False, hilfe="dann muss deren Version bei jeder Änderung steigen (Prüfung in release.py)"),
    # --- D · Ablauf -------------------------------------------------------------------------------------------------
    dict(id="pruefbefehl", teil="D · Ablauf", frage="Mit welchem Befehl laufen alle Prüfungen?", typ="text",
         vorgabe=lambda a: CHECK_CMD.get((a.get("technik") or ["?"])[0], "make check"),
         hilfe="läuft vor jedem Commit und im Workflow «pruefungen»"),
    dict(id="versionsdatei", teil="D · Ablauf", frage="In welcher Datei steht die Versionsnummer?", typ="wahl",
         optionen=["VERSION", "version.py", "package.json", "composer.json", "pyproject.toml"],
         vorgabe=lambda a: "package.json" if (a.get("technik") or [""])[0] == "JavaScript / TypeScript" else "VERSION"),
    dict(id="startversion", teil="D · Ablauf", frage="Mit welcher Version startet das Projekt?", typ="text", vorgabe="0.1.0",
         hilfe="0.x = Prototyp, 1.0.0 = erster produktiver Stand"),
    dict(id="meilenstein", teil="D · Ablauf", frage="Wie heisst der erste Meilenstein?", typ="text",
         vorgabe=lambda a: f"{a.get('startversion') or '0.1.0'} – Grundgerüst"),
    dict(id="funktionen", teil="D · Ablauf", frage="Welche ersten Funktionen gehören in diesen Meilenstein?", typ="liste",
         hilfe="werden nach Bestätigung als Issues (mit Testliste) angelegt"),
    dict(id="agenten", teil="D · Ablauf", frage="Mit welchen KI-Agenten wird gearbeitet?", typ="mehrfach",
         optionen=["Claude", "GitHub Copilot", "keine"], vorgabe=["Claude"]),
    dict(id="projekt_kopie", teil="D · Ablauf", frage="Übergabe und Projektstand auch als Kopie im Claude-Projekt führen?",
         typ="janein", vorgabe=False, wenn=lambda a: "Claude" in (a.get("agenten") or []), wenn_text="nur mit Claude"),
]


# --- Fragen stellen -----------------------------------------------------------------------------------------------

def _val(x, answers):
    return x(answers) if callable(x) else x


def active(q: dict, answers: dict) -> bool:
    return q.get("wenn") is None or q["wenn"](answers)


def required(q: dict, answers: dict) -> bool:
    return bool(_val(q.get("pflicht", False), answers))


def ask(q: dict, answers: dict):
    default = _val(q.get("vorgabe"), answers)
    print(f"\n{q['frage']}" + (" *" if required(q, answers) else ""))
    if q.get("hilfe"):
        print(f"  ({q['hilfe']})")
    opts = q.get("optionen", [])
    for n, o in enumerate(opts, 1):
        print(f"  {n}. {o}")
    shown = ", ".join(default) if isinstance(default, list) else ("ja" if default is True else "nein" if default is False else default or "")
    while True:
        raw = input(f"> [{shown}] " if shown else "> ").strip()
        value = parse(q, raw) if raw else default
        problem = check(q, value, answers)
        if not problem:
            return value
        print(f"  ✗ {problem}")


def parse(q: dict, raw: str):
    opts, typ = q.get("optionen", []), q["typ"]
    pick = lambda s: opts[int(s) - 1] if s.isdigit() and 0 < int(s) <= len(opts) else s
    if typ == "wahl":
        return pick(raw)
    if typ == "mehrfach":
        return [pick(x.strip()) for x in raw.split(",") if x.strip()]
    if typ == "liste":
        return [x.strip() for x in raw.split(",") if x.strip()]
    if typ == "janein":
        return raw.lower() in ("j", "ja", "y", "yes", "1", "true")
    return raw


def check(q: dict, value, answers: dict) -> str:
    if required(q, answers) and value in (None, "", []):
        return "Pflichtangabe"
    opts = q.get("optionen", [])
    if q["typ"] == "wahl" and value and value not in opts:
        return f"bitte eine der Optionen wählen ({', '.join(opts)})"
    if q["typ"] == "mehrfach" and value:
        bad = [v for v in value if v not in opts]
        if bad:
            return f"unbekannt: {', '.join(bad)}"
    if q["id"] == "startversion" and value and not re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?", value):
        return "Version im Format MAJOR.MINOR.PATCH, z. B. 0.1.0"
    return ""


def collect(given: dict | None) -> tuple[dict, list[str]]:
    """Antworten interaktiv (given=None) oder aus einer Datei; fehlende Werte erhalten ihre Vorgabe."""
    answers, problems = {}, []
    for q in FRAGEN:
        if not active(q, answers):
            continue
        if given is None:
            answers[q["id"]] = ask(q, answers)
            continue
        value = given.get(q["id"])
        if value in (None, "", []):                                 # leer in der Vorlage = Vorschlag übernehmen
            value = _val(q.get("vorgabe"), answers)
        if isinstance(value, str) and q["typ"] in ("mehrfach", "liste"):
            value = [x.strip() for x in value.split(",") if x.strip()]
        problem = check(q, value, answers)
        if problem:
            problems.append(f"{q['id']}: {problem} – {q['frage']}")
        answers[q["id"]] = value
    return answers, problems


# --- Antworten → Konfiguration --------------------------------------------------------------------------------------

def settings_from(a: dict) -> list[tuple[str, str, object]]:
    tech = list(a.get("technik") or [])
    delivery = list(a.get("auslieferung") or [])
    langs = list(a.get("sprachen") or ["de-CH"])
    out = [
        ("projekt", "name", a["name"]), ("projekt", "kurz", a.get("kurz") or a["name"]), ("projekt", "art", a["art"]),
        ("projekt", "verantwortlich", a.get("verantwortlich") or "Projektverantwortliche:r"),
        ("projekt", "pruefbefehl", a.get("pruefbefehl") or "make check"),
        ("projekt", "sprachen_auslieferung", langs if len(langs) > 1 else []),
        ("projekt", "lizenz", a.get("lizenz") or ""), ("projekt", "lizenz_inhaber", a.get("lizenz_inhaber") or ""),
        ("repository", "sichtbarkeit", a.get("sichtbarkeit") or "privat"),
        ("repository", "beschreibung", a.get("zweck") or ""),
        ("repository", "pr_profil", "team" if a.get("team") == "team" else "solo"),
        ("versionierung", "datei", a.get("versionsdatei") or "VERSION"),
        ("versionierung", "startversion", a.get("startversion") or "0.1.0"),
        ("meilensteine", "erster_release", a.get("meilenstein") or ""),
        ("dependabot", "oekosysteme", ["github-actions"] + [ECOSYSTEM[t] for t in tech if t in ECOSYSTEM]),
        ("ci", "aktiv", bool(a.get("pruefbefehl"))),
    ]
    if langs and langs[0].lower().startswith("de"):
        out.append(("projekt", "sprache", langs[0]))
    for t in tech:
        if t in CI_VERSION:
            out.append(("ci", CI_VERSION[t][0], CI_VERSION[t][1]))
    prep = [PREPARE[t] for t in tech if t in PREPARE]
    if prep:
        out.append(("ci", "vorbereiten", " && ".join(prep)))
    if a.get("betriebssysteme"):
        systems = [OS_RUNNER[x] for x in a["betriebssysteme"]]
        if a["art"] == "beides" and "ubuntu-latest" not in systems:
            systems.insert(0, "ubuntu-latest")
        out.append(("ci", "betriebssysteme", systems))
    # Daten und Zugänge
    data = a.get("daten", "")
    rules = []
    if data.startswith("besonders"):
        out.append(("projekt", "datenschutz", "Keine echten Personendaten, Zugangsdaten oder Bildschirmfotos mit Personendaten anhängen – "
                                               "auch nicht teilweise oder verpixelt."))
        rules += ["Besonders schützenswerte Personendaten nur verschlüsselt speichern und übertragen",
                  "Zugriffe auf Personendaten protokollieren; Testdaten immer erfunden"]
    elif data.startswith("Personendaten"):
        rules.append("Personendaten nur so weit wie nötig speichern; Testdaten immer erfunden")
    else:
        out.append(("projekt", "datenschutz", "Keine Zugangsdaten anhängen."))
    access = list(a.get("anmeldung") or [])
    if any(x != "keine" for x in access):
        rules.append("Zugangsdaten, Tokens und Schlüssel nie im Repository; nur verschlüsselt bzw. im Schlüsselbund speichern")
    if "Microsoft Entra ID / SSO" in access:
        rules.append("Anmeldung über Microsoft Entra ID; Rechte über Gruppen, nicht über einzelne Konten")
    out.append(("projekt", "sicherheit_grundsaetze", rules))
    # Auslieferung
    release_after = ["pruefungen"] if a.get("pruefbefehl") else []
    if DELIVERY[2] in delivery:
        out += [("release_dateien", "artefakte", ["installer-*"]), ("release_dateien", "pruefsummen", True)]
        release_after.append("installer")
    out.append(("versionierung", "release_nach", release_after))
    if DELIVERY[1] in delivery:
        out.append(("pages", "aktiv", True))
    # Vorlagen und Pflege
    extras = []
    if len(langs) > 1:
        extras.append("uebersetzung")
    if a.get("plugins"):
        extras.append("plugin")
        out.append(("versionierung", "plugin_manifeste", ["plugins/*/plugin.json"]))
    out.append(("issues", "zusatzvorlagen", extras))
    dep = a.get("abhaengigkeiten", "")
    out.append(("fremdkomponenten", "aktiv", not dep.startswith("frei")))
    agent_rules = []
    if dep.startswith("nur Standardbibliothek"):
        agent_rules.append("Kern nur mit der Standardbibliothek; Pakete nur optional bzw. in Plugins mit eigener Umgebung")
    for n in a.get("nichtziele") or []:
        agent_rules.append(f"Nichtziel: {n}")
    out.append(("agenten", "regeln", agent_rules))
    agents = list(a.get("agenten") or [])
    out += [("copilot", "aktiv", "GitHub Copilot" in agents), ("agenten", "uebergabe", "Claude" in agents),
            ("agenten", "projekt_kopie", bool(a.get("projekt_kopie")))]
    out += [("start", "erledigt", True), ("start", "datum", datetime.date.today().isoformat())]
    return out


def toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)


def set_value(text: str, section: str, key: str, value) -> str:
    """Einen Wert in der Konfiguration setzen; Kommentare und Reihenfolge bleiben."""
    lines = text.splitlines(keepends=True)
    current, last_in_section = None, None
    for i, line in enumerate(lines):
        head = re.match(r"^\[([^\[\]]+)\]\s*(#.*)?$", line)
        if head:
            current = head.group(1).strip()
            if current == section:
                last_in_section = i
            continue
        if line.startswith("[["):
            current = None
            continue
        if current != section:
            continue
        if line.strip() and not line.lstrip().startswith("#"):
            last_in_section = i
        m = re.match(rf"^({re.escape(key)}\s*=\s*)(.*?)(\s+#.*)?(\r?\n)?$", line)
        if m:
            lines[i] = m.group(1) + toml_value(value) + (m.group(3) or "") + (m.group(4) or "\n")
            return "".join(lines)
    entry = f"{key} = {toml_value(value)}\n"
    if last_in_section is None:
        return text.rstrip("\n") + f"\n\n[{section}]\n{entry}"
    lines.insert(last_in_section + 1, entry)
    return "".join(lines)


def steckbrief(a: dict) -> str:
    def show(v):
        if isinstance(v, list):
            return ", ".join(v) if v else "–"
        if isinstance(v, bool):
            return "ja" if v else "nein"
        return str(v) if v else "–"
    today = datetime.date.today().isoformat()
    rows = "\n".join(f"| {q['frage']} | {show(a.get(q['id']))} |" for q in FRAGEN if q["id"] in a)
    funcs = "\n".join(f"- [ ] {f}" for f in a.get("funktionen") or []) or "- (noch keine)"
    non = "\n".join(f"- {n}" for n in a.get("nichtziele") or []) or "- (keine genannt)"
    return f"""# Projektstart – {a['name']}

Stand: {today} · Status: **OFFEN** – Grundgerüst erst nach Bestätigung durch {a.get('verantwortlich') or 'die Projektverantwortlichen'}

Steckbrief aus der Start-Checkliste (`python3 .github/blueprint/start.py`). Er ist die Grundlage für das Grundgerüst
und für die Konfiguration in `.github/blueprint.toml`. Änderungen hier festhalten und `start.py` erneut ausführen.

## Ziel

{a.get('zweck') or '–'}

**Nichtziele:**

{non}

## Antworten

| Frage | Antwort |
|---|---|
{rows}

## Grundgerüst

Vorschlag für Aufbau, Ordner und erste Dateien – wird vor dem Anlegen mit {a.get('verantwortlich') or 'den Projektverantwortlichen'}
abgestimmt (Status je Punkt: BESCHLOSSEN, EMPFOHLEN, OFFEN, ZU PRÜFEN):

| Punkt | Vorschlag | Status |
|---|---|---|
| Technik | {show(a.get('technik'))} · {show(a.get('framework'))} | OFFEN |
| Ordner | Quellcode, `tests/`, `docs/` | OFFEN |
| Prüfungen | `{a.get('pruefbefehl') or 'make check'}` (Workflow «pruefungen») | OFFEN |
| Version | `{a.get('versionsdatei') or 'VERSION'}` mit {a.get('startversion') or '0.1.0'} | OFFEN |
| Auslieferung | {show(a.get('auslieferung'))}{' – Workflow «installer» lädt Artefakte «installer-*» hoch' if DELIVERY[2] in (a.get('auslieferung') or []) else ''} | OFFEN |

## Erster Meilenstein: {a.get('meilenstein') or '–'}

{funcs}

Diese Punkte werden nach Bestätigung als Issues mit Testliste angelegt.
"""


def markdown() -> str:
    out = ["# Start-Checkliste", "",
           "Diese Fragen werden **vor** dem Einrichten des Repositorys (`apply.py`) und **vor** dem Grundgerüst des Projekts",
           "beantwortet – im Terminal mit `python3 .github/blueprint/start.py` oder im Gespräch mit Claude. Aus den Antworten",
           "entstehen die Werte in `.github/blueprint.toml` und der Steckbrief `docs/PROJEKTSTART.md`. Solange",
           "`[start] erledigt = false` gilt, richtet `apply.py` nichts ein (nur Probelauf). Pflichtfragen sind mit * markiert.",
           "Die ausführliche [CHECKLISTE.md](CHECKLISTE.md) bleibt für Feineinstellungen.", "",
           "<!-- erzeugt mit: python3 .github/blueprint/start.py --markdown > START-CHECKLISTE.md -->"]
    part, n = None, 0
    for q in FRAGEN:
        if q["teil"] != part:
            part = q["teil"]
            out += ["", f"## {part}", ""]
        n += 1
        star = " *" if q.get("pflicht") is True else (" (* wenn öffentlich)" if callable(q.get("pflicht")) else "")
        line = f"{n}. **{q['frage']}**{star}"
        if q.get("optionen"):
            line += f" – {' · '.join(q['optionen'])}" + (" (mehrere möglich)" if q["typ"] == "mehrfach" else "")
        if q.get("wenn"):
            line += f" _({q.get('wenn_text', 'nur wenn zutreffend')})_"
        out.append(line)
        if q.get("hilfe"):
            out.append(f"   <br>{q['hilfe']}")
    return "\n".join(out) + "\n"


def template() -> str:
    lines = ["# Antworten für die Start-Checkliste: python3 .github/blueprint/start.py --antworten DATEI"]
    for q in FRAGEN:
        hint = f"  # {' | '.join(q['optionen'])}" if q.get("optionen") else ""
        empty = {"mehrfach": "[]", "liste": "[]", "janein": "false"}.get(q["typ"], '""')
        lines.append(f"{q['id']} = {empty}{hint}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Start-Checkliste")
    ap.add_argument("--antworten", default="")
    ap.add_argument("--probelauf", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--vorlage", action="store_true")
    ap.add_argument("--ueberschreiben", action="store_true", help="docs/PROJEKTSTART.md ersetzen, falls vorhanden")
    args = ap.parse_args(argv)
    if args.markdown:
        print(markdown(), end="")
        return 0
    if args.vorlage:
        print(template(), end="")
        return 0
    given = None
    if args.antworten:
        with open(args.antworten, "rb") as fh:
            given = tomllib.load(fh)
    else:
        print("Start-Checkliste – Enter übernimmt den Vorschlag in [Klammern], * = Pflicht. Mehrere Antworten mit Komma.")
    answers, problems = collect(given)
    if problems:
        for p in problems:
            print(f"✗ {p}", file=sys.stderr)
        return 1
    text = CONFIG.read_text(encoding="utf-8")
    new = text
    for section, key, value in settings_from(answers):
        new = set_value(new, section, key, value)
    tomllib.loads(new)                                          # muss gültig bleiben
    prefix = "(Probelauf) " if args.probelauf else ""
    for section, key, value in settings_from(answers):
        print(f"{prefix}{section}.{key} = {toml_value(value)}")
    if args.probelauf:
        return 0
    CONFIG.write_text(new, encoding="utf-8")
    print(f"✓ {CONFIG.relative_to(ROOT)} aktualisiert")
    if STECKBRIEF.exists() and not args.ueberschreiben:
        print(f"⚠ {STECKBRIEF.relative_to(ROOT)} gibt es schon – nicht überschrieben (--ueberschreiben)")
    else:
        STECKBRIEF.parent.mkdir(parents=True, exist_ok=True)
        STECKBRIEF.write_text(steckbrief(answers), encoding="utf-8")
        print(f"✓ {STECKBRIEF.relative_to(ROOT)} angelegt")
    print("\nNächste Schritte: python3 .github/blueprint/apply.py --probelauf, danach ohne Probelauf; "
          "das Grundgerüst erst nach Bestätigung des Steckbriefs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
