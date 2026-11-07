#!/usr/bin/env python3
"""Start-Checkliste: die Fragen vor dem Einrichten des Repositorys und vor dem Grundgerüst des Projekts.

    python3 .github/blueprint/start.py --ziel ../projekt    Fragen nacheinander stellen (Terminal)
    … --ziel ../projekt --antworten a.toml                  Antworten aus einer Datei (z. B. von Claude ausgefüllt)
    python3 .github/blueprint/start.py --vorlage            leere Antwortdatei ausgeben
    python3 .github/blueprint/start.py --markdown           Fragen als Markdown ausgeben (START-CHECKLISTE.md)
    python3 .github/blueprint/start.py --runde [--antworten a.toml]
                                                            nächste Fragerunde als JSON: bis zu 4 Fragen mit
                                                            Antworten zum Anklicken (für Claude, AskUserQuestion)
    … --probelauf                                           nur zeigen, was in die Konfiguration käme

Aus den Antworten entstehen:
- die Werte in .github/blueprint.toml (art, Sichtbarkeit, Lizenz, Prüfbefehl, Ökosysteme, Release-Dateien …),
  dazu [start] erledigt = true – erst dann richtet apply.py das Repository ein;
- docs/PROJEKTSTART.md: der Steckbrief des Projekts mit allen Antworten. Er ist die Grundlage für das Grundgerüst;
  dieses wird erst nach Bestätigung durch die/den Projektverantwortliche:n erstellt.
Bestehende Werte, nach denen nicht gefragt wird, bleiben. Fehlt die Konfiguration im Ziel, wird sie aus der Vorlage
des Blueprints angelegt. Läuft vom Blueprint aus (--ziel); im Blueprint selbst ändert start.py nichts.
Nur Python-Standardbibliothek.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import tomllib
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2]       # Blueprint-Repository
ROOT = SOURCE                                      # Ziel; wird in main() aus --ziel gesetzt
CONFIG = ROOT / ".github" / "blueprint.toml"
STECKBRIEF = ROOT / "docs" / "PROJEKTSTART.md"


def set_target(root: Path) -> None:
    global ROOT, CONFIG, STECKBRIEF
    ROOT = root
    CONFIG = root / ".github" / "blueprint.toml"
    STECKBRIEF = root / "docs" / "PROJEKTSTART.md"

TECH = ["Python", "PHP", "JavaScript / TypeScript", "C# / .NET", "Java / Kotlin", "Rust", "Go", "Swift", "andere"]
ECOSYSTEM = {"Python": "pip", "PHP": "composer", "JavaScript / TypeScript": "npm", "C# / .NET": "nuget",
             "Java / Kotlin": "maven", "Rust": "cargo", "Go": "gomod", "Swift": "swift"}
CHECK_CMD = {"Python": "python3 -m unittest discover -s tests", "PHP": "composer test", "JavaScript / TypeScript": "npm test",
             "C# / .NET": "dotnet test", "Java / Kotlin": "mvn -B verify", "Rust": "cargo test", "Go": "go test ./...",
             "Swift": "swift test"}
PREPARE = {"PHP": "composer install --no-interaction --no-progress", "JavaScript / TypeScript": "npm ci"}
CI_VERSION = {"Python": ("python", "3.x"), "JavaScript / TypeScript": ("node", "lts/*"), "Java / Kotlin": ("java", "21"),
              "C# / .NET": ("dotnet", "10.0.x")}
DELIVERY = ["Server", "GitHub Pages", "Installer (GitHub-Releases)", "App-Store", "nur Quellcode"]
OS_RUNNER = {"Windows": "windows-latest", "macOS": "macos-latest", "Linux": "ubuntu-latest"}
FRAMEWORKS = {
    ("web", "PHP"): ["Laravel", "Symfony", "ohne Framework"],
    ("web", "Python"): ["Django", "FastAPI", "Flask"],
    ("web", "JavaScript / TypeScript"): ["Vite + React", "Vite + Vue", "Next.js"],
    ("web", "C# / .NET"): ["ASP.NET Core", "Blazor"],
    ("desktop", "Python"): ["pywebview + Web-Oberfläche", "Qt (PySide6)", "tkinter"],
    ("desktop", "C# / .NET"): ["WPF", ".NET MAUI", "WinUI 3"],
    ("desktop", "JavaScript / TypeScript"): ["Electron", "Tauri"],
    ("desktop", "Rust"): ["Tauri", "egui"],
    ("desktop", "Swift"): ["SwiftUI"],
}


def _uniq(items: list) -> list:
    out = []
    for x in items:
        if x and x not in out:
            out.append(x)
    return out


def _first_tech(a: dict) -> str:
    return (a.get("technik") or [""])[0]


def _frameworks(a: dict) -> list[str]:
    art = "desktop" if a.get("art") == "desktop" else "web"
    if a.get("art") == "beides":
        return _uniq(FRAMEWORKS.get(("desktop", _first_tech(a)), [])[:2] + FRAMEWORKS.get(("web", _first_tech(a)), [])[:1] + ["offen"])[:4]
    return _uniq(FRAMEWORKS.get((art, _first_tech(a)), [])[:3] + ["offen"])


def _version_files(a: dict) -> list[str]:
    t = set(a.get("technik") or [])
    first = ["package.json"] if _first_tech(a) == "JavaScript / TypeScript" else ["version.py", "pyproject.toml"] if "Python" in t else []
    return _uniq(first + ["VERSION", "package.json" if "JavaScript / TypeScript" in t else "", "composer.json" if "PHP" in t else ""])[:4]


# Jede Frage: id, chip (Kurztitel ≤ 12 Zeichen), teil, frage, hilfe, typ (text, wahl, mehrfach, liste, janein),
# optionen (gültige Werte), klick (bis 4 Antworten zum Anklicken; Liste oder Funktion der bisherigen Antworten),
# info (Erklärung je Antwort), vorgabe, pflicht, wenn (Bedingung), wenn_text und ab (Fragen, von deren Antwort
# Vorschläge oder Bedingung abhängen – für die Fragerunden mit Claude).
# Ohne «klick» ist die Frage Freitext (Name, Zweck …); mit «optionen» über 4 Werten bietet «klick» die häufigsten an,
# die übrigen gehen über «Andere».
FRAGEN = [
    # --- A · Projekt ---------------------------------------------------------------------------------------------
    dict(id="name", chip="Name", teil="A · Projekt", frage="Wie heisst das Projekt (voller Name)?", typ="text", pflicht=True,
         hilfe="z. B. «SekBülach Intranet» oder «MarKusSXCH TagStudio»"),
    dict(id="zweck", chip="Zweck", teil="A · Projekt", frage="Was soll das Projekt leisten, und für wen? (ein bis zwei Sätze)",
         typ="text", pflicht=True, hilfe="wird zur Beschreibung bei «About» und zum Ziel im Steckbrief"),
    dict(id="nichtziele", chip="Nichtziele", teil="A · Projekt", frage="Was gehört ausdrücklich nicht dazu (Nichtziele)?", typ="liste",
         hilfe="schützt vor schleichender Ausweitung, z. B. «keine DJ-Mixing-Software»"),
    dict(id="kurz", ab=["name"], chip="Kurzname", teil="A · Projekt", frage="Welcher Kurzname soll in den Release-Titeln stehen?", typ="text",
         vorgabe=lambda a: a.get("name", "").split()[-1] if a.get("name") else "",
         klick=lambda a: _uniq([a.get("name", "").split()[-1], a.get("name", "").split()[0], a.get("name", "")])[:4] if a.get("name") else [],
         hilfe="erscheint als «Kurzname 0.2.0»"),
    dict(id="art", chip="Art", teil="A · Projekt", frage="Ist es eine Web-Anwendung, eine Desktop-Anwendung oder beides?",
         typ="wahl", optionen=["web", "desktop", "beides"], pflicht=True,
         info={"web": "Server und Browser", "desktop": "Installer bzw. App für Windows, macOS, Linux",
               "beides": "z. B. Web-Oberfläche, auch als App ausgeliefert"},
         hilfe="bestimmt Fehlerformular, Zielsysteme der Tests, Release-Dateien und Regeln für Agenten"),
    dict(id="zielgruppe", chip="Nutzer", teil="A · Projekt", frage="Wer nutzt die Anwendung?", typ="mehrfach",
         optionen=["Privatpersonen", "Unternehmen", "öffentliche Organe", "nur intern"], pflicht=True,
         info={"Privatpersonen": "Datenschutz nach DSG", "Unternehmen": "Kundinnen und Kunden, Firmen – DSG",
               "öffentliche Organe": "Schule, Gemeinde, Kanton, Bund – eigenes Datenschutzrecht, Barrierefreiheit",
               "nur intern": "nur die eigene Organisation"},
         hilfe="bestimmt, welches Datenschutzgesetz gilt, und Regeln zur Barrierefreiheit"),
    dict(id="organ", ab=["zielgruppe"], chip="Organ", teil="A · Projekt", frage="Welche öffentlichen Organe?", typ="wahl",
         optionen=["Kanton Zürich", "anderer Kanton", "Bund"], pflicht=True,
         wenn=lambda a: "öffentliche Organe" in (a.get("zielgruppe") or []), wenn_text="nur für öffentliche Organe",
         info={"Kanton Zürich": "Kanton, Gemeinden, Schulen – IDG (LS 170.4)", "anderer Kanton": "Datenschutzgesetz dieses Kantons",
               "Bund": "Bundesorgane – DSG"}),
    dict(id="repo", chip="Repository", teil="A · Projekt", frage="Ist das Repository neu oder gibt es es schon?", typ="wahl",
         optionen=["neu", "bestehend"], vorgabe="neu",
         info={"bestehend": "danach Teil C der CHECKLISTE.md (Labels, Tags, vorhandene Workflows)"}),
    # --- B · Verantwortung und Sichtbarkeit -------------------------------------------------------------------------
    dict(id="verantwortlich", chip="Freigabe", teil="B · Verantwortung und Sichtbarkeit",
         frage="Wer gibt Issues und Releases frei (Rolle genügt)?", typ="text", vorgabe="Projektverantwortliche:r",
         klick=["Projektverantwortliche:r", "Eigentümer:in", "Schulleitung", "Produktverantwortliche:r"]),
    dict(id="team", chip="Team", teil="B · Verantwortung und Sichtbarkeit", frage="Arbeitest du allein oder im Team?", typ="wahl",
         optionen=["allein", "team"], vorgabe="allein",
         info={"allein": "direkte Pushes auf main", "team": "Änderungen über Pull Requests, Squash-Merge"}),
    dict(id="sichtbarkeit", chip="Sichtbarkeit", teil="B · Verantwortung und Sichtbarkeit",
         frage="Ist das Repository öffentlich oder privat?", typ="wahl", optionen=["privat", "öffentlich"], vorgabe="privat",
         info={"privat": "nur Mitwirkende sehen es", "öffentlich": "vorher Verlauf ohne Geheimnisse und echte Daten; braucht Lizenz"}),
    dict(id="lizenz", chip="Lizenz", teil="B · Verantwortung und Sichtbarkeit", frage="Unter welcher Lizenz steht der Code?",
         typ="text", pflicht=lambda a: a.get("sichtbarkeit") == "öffentlich",
         klick=["MIT", "Apache-2.0", "GPL-3.0-or-later", "keine"],
         info={"MIT": "sehr frei, kurze Lizenz", "Apache-2.0": "frei, mit Patentklausel",
               "GPL-3.0-or-later": "Weitergabe nur unter gleicher Lizenz", "keine": "nur für private Projekte ohne Weitergabe"},
         hilfe="SPDX-Kennung; LICENSE wird aus der GitHub-Vorlage angelegt"),
    dict(id="lizenz_inhaber", ab=["lizenz", "name"], chip="Inhaber", teil="B · Verantwortung und Sichtbarkeit", frage="Auf wen lautet die Lizenz?",
         typ="text", wenn=lambda a: a.get("lizenz") not in (None, "", "keine"), wenn_text="nur mit Lizenz", vorgabe=lambda a: a.get("name", ""),
         klick=lambda a: [a.get("name", "")] if a.get("name") else []),
    # --- C · Technik und Grundgerüst --------------------------------------------------------------------------------
    dict(id="technik", ab=["art"], chip="Technik", teil="C · Technik und Grundgerüst", frage="In welchen Programmiersprachen wird entwickelt?",
         typ="mehrfach", optionen=TECH, pflicht=True,
         klick=lambda a: ["Python", "C# / .NET", "JavaScript / TypeScript", "Rust"] if a.get("art") == "desktop"
                         else ["PHP", "JavaScript / TypeScript", "Python", "C# / .NET"],
         hilfe="bestimmt Dependabot, Vorgaben für Prüfbefehl, CodeQL und die Liste der Fremdkomponenten"),
    dict(id="abhaengigkeiten", chip="Pakete", teil="C · Technik und Grundgerüst", frage="Welcher Grundsatz gilt für Abhängigkeiten?",
         typ="wahl", optionen=["nur Standardbibliothek", "geprüfte Pakete", "frei"], vorgabe="geprüfte Pakete",
         info={"nur Standardbibliothek": "im Kern keine Pakete; Pakete nur optional bzw. in Plugins (wie TagStudio)",
               "geprüfte Pakete": "bewährte Pakete erlaubt, neue erst nach Prüfung von Lizenz und Pflege",
               "frei": "keine Vorgabe, keine monatliche Prüfung"}),
    dict(id="betriebssysteme", ab=["art"], chip="Systeme", teil="C · Technik und Grundgerüst", frage="Für welche Betriebssysteme?",
         typ="mehrfach", optionen=["Windows", "macOS", "Linux"], vorgabe=["Windows", "macOS"],
         wenn=lambda a: a.get("art") in ("desktop", "beides"), wenn_text="nur Desktop bzw. beides",
         hilfe="darauf laufen die Tests im Workflow «pruefungen»"),
    dict(id="hosting", ab=["art"], chip="Hosting", teil="C · Technik und Grundgerüst", frage="Wo läuft die Web-Anwendung?", typ="text",
         wenn=lambda a: a.get("art") in ("web", "beides"), wenn_text="nur Web bzw. beides",
         klick=["Webhosting (PHP, MySQL)", "eigener Server / VPS", "Azure", "offen"],
         hilfe="genauer über «Andere», z. B. «Hostinger, PHP 8.4, MySQL»"),
    dict(id="auslieferung", ab=["art"], chip="Auslieferung", teil="C · Technik und Grundgerüst", frage="Wie kommt die Anwendung zu den Nutzer:innen?",
         typ="mehrfach", optionen=DELIVERY,
         klick=lambda a: [DELIVERY[2], DELIVERY[3], DELIVERY[4], DELIVERY[0]] if a.get("art") == "desktop"
                         else [DELIVERY[0], DELIVERY[1], DELIVERY[2], DELIVERY[4]],
         vorgabe=lambda a: [DELIVERY[2]] if a.get("art") == "desktop" else [DELIVERY[0]],
         info={DELIVERY[0]: "Deployment per SSH, Docker o. Ä.", DELIVERY[1]: "statische Seite, Workflow pages.yml",
               DELIVERY[2]: "Dateien am Release mit Prüfsummen", DELIVERY[3]: "Microsoft Store, Mac App Store …"}),
    dict(id="framework", ab=["art", "technik"], chip="Framework", teil="C · Technik und Grundgerüst", frage="Welches Framework bzw. welche Grundlage?",
         typ="text", vorgabe="offen", klick=_frameworks, info={"offen": "wird im Konzept geklärt"}),
    dict(id="daten", chip="Daten", teil="C · Technik und Grundgerüst", frage="Welche Daten verarbeitet die Anwendung?", typ="wahl",
         optionen=["keine Personendaten", "Personendaten", "besonders schützenswert"], pflicht=True,
         info={"Personendaten": "Namen, Kontakte, Konten …", "besonders schützenswert": "z. B. Gesundheit, Beurteilungen, Massnahmen"},
         hilfe="bestimmt Datenschutz-Hinweis in allen Formularen und Grundsätze in SECURITY.md"),
    dict(id="schutzbedarf", ab=["daten"], chip="Schutzbedarf", teil="C · Technik und Grundgerüst",
         frage="Welcher Schutzbedarf gilt für die Daten (Klassifizierung)?", typ="wahl",
         optionen=["öffentlich", "intern", "vertraulich", "geheim"], pflicht=True,
         vorgabe=lambda a: {"besonders schützenswert": "vertraulich", "Personendaten": "intern"}.get(a.get("daten", ""), "öffentlich"),
         info={"öffentlich": "darf jede Person sehen", "intern": "nur die eigene Organisation",
               "vertraulich": "nur Berechtigte; verschlüsselt, Zugriffe protokolliert",
               "geheim": "nur wenige Berechtigte; nur freigegebene Umgebungen und Dienste"},
         hilfe="ab «vertraulich» gelten strengere Grundsätze; das Repository sollte dann privat sein"),
    dict(id="anmeldung", chip="Anmeldung", teil="C · Technik und Grundgerüst", frage="Welche Anmeldungen und Zugänge braucht es?",
         typ="mehrfach", optionen=["keine", "eigene Benutzerkonten", "Entra ID / SSO", "externe Dienste (API)"], vorgabe=["keine"],
         info={"externe Dienste (API)": "API-Schlüssel oder OAuth, z. B. Spotify, Beatport"}),
    dict(id="sprachen", chip="Sprachen", teil="C · Technik und Grundgerüst", frage="In welchen Sprachen wird die Oberfläche ausgeliefert?",
         typ="liste", vorgabe=["de-CH"], klick=["de-CH", "de-CH, en", "de-CH, en, fr", "de-CH, fr, it"],
         hilfe="erste = Ausgangssprache; ab zwei Sprachen gilt die Übersetzungsregel"),
    dict(id="plugins", chip="Plugins", teil="C · Technik und Grundgerüst", frage="Gibt es Plugins oder Module mit eigener Version?",
         typ="janein", vorgabe=False, info={"ja": "deren Version muss bei jeder Änderung steigen (Prüfung in release.py)"}),
    # --- D · Ablauf -------------------------------------------------------------------------------------------------
    dict(id="pruefbefehl", ab=["technik"], chip="Prüfbefehl", teil="D · Ablauf", frage="Mit welchem Befehl laufen alle Prüfungen?", typ="text",
         vorgabe=lambda a: CHECK_CMD.get(_first_tech(a), "make check"),
         klick=lambda a: _uniq([CHECK_CMD.get(t, "") for t in a.get("technik") or []] + ["make check"])[:4],
         hilfe="läuft vor jedem Commit und im Workflow «pruefungen»"),
    dict(id="versionsdatei", ab=["technik"], chip="Versionsort", teil="D · Ablauf", frage="In welcher Datei steht die Versionsnummer?", typ="wahl",
         optionen=["VERSION", "version.py", "package.json", "composer.json", "pyproject.toml"],
         vorgabe=lambda a: _version_files(a)[0], klick=_version_files),
    dict(id="startversion", chip="Startversion", teil="D · Ablauf", frage="Mit welcher Version startet das Projekt?", typ="text",
         vorgabe="0.1.0", klick=["0.1.0", "1.0.0"], info={"0.1.0": "Prototyp", "1.0.0": "erster produktiver Stand"}),
    dict(id="agenten", chip="Agenten", teil="D · Ablauf", frage="Mit welchen KI-Agenten wird gearbeitet?", typ="mehrfach",
         optionen=["Claude", "GitHub Copilot", "keine"], vorgabe=["Claude"]),
    dict(id="meilenstein", ab=["startversion"], chip="Meilenstein", teil="D · Ablauf", frage="Wie heisst der erste Meilenstein?", typ="text",
         vorgabe=lambda a: f"{a.get('startversion') or '0.1.0'} – Grundgerüst",
         klick=lambda a: [f"{a.get('startversion') or '0.1.0'} – {t}" for t in ("Grundgerüst", "Prototyp", "Erste Version")]),
    dict(id="projekt_kopie", ab=["agenten"], chip="Kopie", teil="D · Ablauf", frage="Übergabe und Projektstand auch als Kopie im Claude-Projekt führen?",
         typ="janein", vorgabe=False, wenn=lambda a: "Claude" in (a.get("agenten") or []), wenn_text="nur mit Claude"),
    dict(id="funktionen", chip="Funktionen", teil="D · Ablauf", frage="Welche ersten Funktionen gehören in diesen Meilenstein?",
         typ="liste", hilfe="werden nach Bestätigung als Issues (mit Testliste) angelegt"),
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
    opts = q.get("optionen") or clicks(q, answers)
    for n, o in enumerate(opts, 1):
        extra = (q.get("info") or {}).get(o)
        print(f"  {n}. {o}" + (f" – {extra}" if extra else ""))
    if q["typ"] in ("text", "liste") and opts:
        print("  (Nummer wählen oder eigene Antwort schreiben)")
    shown = ", ".join(default) if isinstance(default, list) else ("ja" if default is True else "nein" if default is False else default or "")
    while True:
        raw = input(f"> [{shown}] " if shown else "> ").strip()
        value = parse(q, raw, answers) if raw else default
        problem = check(q, value, answers)
        if not problem:
            return value
        print(f"  ✗ {problem}")


def clicks(q: dict, answers: dict) -> list[str]:
    """Antworten zum Anklicken (höchstens 4): «klick», sonst die Optionen, bei Ja/Nein beides."""
    if q.get("klick"):
        return [x for x in _val(q["klick"], answers) if x][:4]
    if q["typ"] == "janein":
        return ["nein", "ja"]
    return list(q.get("optionen", []))[:4]


def normalize(q: dict, value):
    """Antworten aus Datei bzw. Klick («a, b», «ja») in den Typ der Frage bringen."""
    typ = q["typ"]
    strip = lambda v: v.replace(" (Vorschlag)", "").strip() if isinstance(v, str) else v
    value = [strip(v) for v in value] if isinstance(value, list) else strip(value)
    if typ in ("mehrfach", "liste") and isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    if typ == "janein" and isinstance(value, str):
        return value.strip().lower() in ("j", "ja", "y", "yes", "1", "true")
    return value


def parse(q: dict, raw: str, answers: dict | None = None):
    opts, typ = q.get("optionen") or clicks(q, answers or {}), q["typ"]
    pick = lambda s: opts[int(s) - 1] if s.isdigit() and 0 < int(s) <= len(opts) else s
    if typ == "wahl":
        return pick(raw)
    if typ == "mehrfach":
        return [pick(x.strip()) for x in raw.split(",") if x.strip()]
    if typ == "liste":
        return normalize(q, pick(raw))
    if typ == "janein":
        return normalize(q, pick(raw))
    return pick(raw)


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
    if q["id"] == "lizenz" and value == "keine" and answers.get("sichtbarkeit") == "öffentlich":
        return "öffentliche Repositorys brauchen eine Lizenz"
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
        value = normalize(q, value)
        problem = check(q, value, answers)
        if problem:
            problems.append(f"{q['id']}: {problem} – {q['frage']}")
        answers[q["id"]] = value
    return answers, problems


# --- Antworten → Konfiguration --------------------------------------------------------------------------------------

def laws(a: dict) -> list[str]:
    """Anwendbares Datenschutzrecht nach Zielgruppe (öffentliche Organe des Kantons Zürich: IDG, § 2 IDG)."""
    groups = set(a.get("zielgruppe") or [])
    out = []
    if "öffentliche Organe" in groups:
        out.append({"Kanton Zürich": "IDG (Kanton Zürich)", "anderer Kanton": "kantonales Datenschutzgesetz",
                    "Bund": "DSG (Bundesorgane)"}.get(a.get("organ", ""), "kantonales Datenschutzgesetz"))
    if groups & {"Privatpersonen", "Unternehmen", "nur intern"} and "DSG (Bundesorgane)" not in out:
        out.append("DSG")
    return out


def settings_from(a: dict) -> list[tuple[str, str, object]]:
    tech = list(a.get("technik") or [])
    delivery = list(a.get("auslieferung") or [])
    langs = list(a.get("sprachen") or ["de-CH"])
    out = [
        ("projekt", "name", a["name"]), ("projekt", "kurz", a.get("kurz") or a["name"]), ("projekt", "art", a["art"]),
        ("projekt", "verantwortlich", a.get("verantwortlich") or "Projektverantwortliche:r"),
        ("projekt", "pruefbefehl", a.get("pruefbefehl") or "make check"),
        ("projekt", "sprachen_auslieferung", langs if len(langs) > 1 else []),
        ("projekt", "lizenz", "" if a.get("lizenz") in (None, "", "keine") else a["lizenz"]), ("projekt", "lizenz_inhaber", a.get("lizenz_inhaber") or ""),
        ("repository", "sichtbarkeit", "oeffentlich" if a.get("sichtbarkeit") == "öffentlich" else "privat"),
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
    if data == "besonders schützenswert":
        out.append(("projekt", "datenschutz", "Keine echten Personendaten, Zugangsdaten oder Bildschirmfotos mit Personendaten anhängen – "
                                               "auch nicht teilweise oder verpixelt."))
        rules.append("Personendaten nur so weit wie nötig bearbeiten (Datensparsamkeit)")
    elif data == "Personendaten":
        rules.append("Personendaten nur so weit wie nötig bearbeiten (Datensparsamkeit); Testdaten immer erfunden")
    else:
        out.append(("projekt", "datenschutz", "Keine Zugangsdaten anhängen."))
    law = " bzw. ".join(laws(a))
    if data != "keine Personendaten" and law:
        rules.append(f"Personendaten nach {law} bearbeiten (Zweckbindung, Verhältnismässigkeit, Informationssicherheit)")
    level = a.get("schutzbedarf", "öffentlich")
    agent_rules = []
    if level in ("vertraulich", "geheim"):
        rules += [f"Schutzbedarf «{level}»: Daten verschlüsselt speichern und übertragen, Zugriffe protokollieren",
                  "Keine echten Daten in Tests, Issues, Protokollen und Bildschirmfotos"]
        agent_rules.append(f"Schutzbedarf «{level}»: nur erfundene Testdaten; keine echten Daten in Issues, Commits oder Bildschirmfotos")
    if level == "geheim":
        rules.append("Nur freigegebene Umgebungen und Dienste; keine Cloud-Dienste ohne ausdrückliche Freigabe")
        agent_rules.append("Schutzbedarf «geheim»: keine externen Dienste oder Cloud-Werkzeuge ohne ausdrückliche Freigabe")
    if "öffentliche Organe" in (a.get("zielgruppe") or []):
        agent_rules.append("Barrierefreiheit: Oberfläche nach WCAG 2.1 AA (eCH-0059) gestalten und prüfen")
        out.append(("issues", "zusatzlabels", [{"name": "barrierefreiheit", "farbe": "5319e7",
                                                 "beschreibung": "Zugänglichkeit nach WCAG 2.1 AA (eCH-0059)"}]))
    access = list(a.get("anmeldung") or [])
    if any(x != "keine" for x in access):
        rules.append("Zugangsdaten, Tokens und Schlüssel nie im Repository; nur verschlüsselt bzw. im Schlüsselbund speichern")
    if "Entra ID / SSO" in access:
        rules.append("Anmeldung über Microsoft Entra ID; Rechte über Gruppen, nicht über einzelne Konten")
    out.append(("projekt", "sicherheit_grundsaetze", rules))
    # Auslieferung
    release_after = ["pruefungen"] if a.get("pruefbefehl") else []
    if DELIVERY[2] in delivery:
        out += [("release_dateien", "artefakte", ["installer-*"]), ("release_dateien", "pruefsummen", True),
                ("versionierung", "vorabversionen_aufraeumen", True)]           # Beta-Installer nach der finalen Version weg
        release_after.append("installer")                                        # Workflow aus templates/workflows/installer.yml
    out.append(("versionierung", "release_nach", release_after))
    # Pflichtprüfung vor dem Merge: im Team bzw. öffentlich (Admins bleiben über das Ruleset ausgenommen)
    shared = a.get("team") == "team" or a.get("sichtbarkeit") == "öffentlich"
    out.append(("repository", "pflicht_pruefungen", ["pruefungen"] if shared and a.get("pruefbefehl") else []))
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
    out.append(("fremdkomponenten", "aktiv", dep != "frei"))
    if dep == "nur Standardbibliothek":
        agent_rules.append("Kern nur mit der Standardbibliothek; Pakete nur optional bzw. in Plugins mit eigener Umgebung")
    for n in a.get("nichtziele") or []:
        agent_rules.append(f"Nichtziel: {n}")
    out.append(("agenten", "regeln", agent_rules))
    agents = list(a.get("agenten") or [])
    out += [("copilot", "aktiv", "GitHub Copilot" in agents), ("agenten", "uebergabe", "Claude" in agents),
            ("agenten", "projekt_kopie", bool(a.get("projekt_kopie")))]
    out += [("start", "erledigt", True), ("start", "datum", datetime.date.today().isoformat())]
    return out


DEPLOY_START, DEPLOY_END = "# --- Deployment ", "# --- /Deployment"


def deployment(text: str, on: bool) -> str:
    """Block «Deployment» der Konfiguration ein- bzw. ausschalten (Zeilen mit «#~»)."""
    lines = text.splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        if line.startswith(DEPLOY_START):
            inside = True
            continue
        if line.startswith(DEPLOY_END):
            break
        if not inside:
            continue
        if on and line.startswith("#~"):
            lines[i] = line[3:] if line.startswith("#~ ") else line[2:]
        elif not on and not line.startswith("#"):
            lines[i] = ("#~ " + line) if line.strip() else "#~\n"
    return "".join(lines)


def toml_value(v) -> str:
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {toml_value(x)}" for k, x in v.items()) + " }"
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
            head, comment = m.group(1) + toml_value(value), m.group(3) or ""
            if comment:                                         # Kommentar in seiner Spalte lassen (mind. 1 Abstand)
                column = len(m.group(1)) + len(m.group(2)) + len(comment) - len(comment.lstrip())
                comment = " " * max(1, column - len(head)) + comment.lstrip()
            lines[i] = head + comment + (m.group(4) or "\n")
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

Steckbrief aus der Start-Checkliste (`start.py --ziel …` im GitHub-Blueprint). Er ist die Grundlage für das Grundgerüst
und für die Konfiguration in `.github/blueprint.toml`. Änderungen hier festhalten und `start.py` erneut ausführen.

## Ziel

{a.get('zweck') or '–'}

**Nichtziele:**

{non}

## Datenschutz

- Zielgruppe: {show(a.get('zielgruppe'))}
- Anwendbares Recht: {' bzw. '.join(laws(a)) or '–'}
- Daten: {show(a.get('daten'))} · Schutzbedarf: **{show(a.get('schutzbedarf'))}**

Die Zuordnung ist eine Arbeitshilfe, keine Rechtsberatung; bei öffentlichen Organen die zuständige
Datenschutzstelle einbeziehen (z. B. Vorabkontrolle bzw. Datenschutz-Folgenabschätzung).

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


def next_round(given: dict) -> dict:
    """Nächste Fragerunde für das Gespräch mit Claude: bis zu 4 Klickfragen (Format von AskUserQuestion) und die
    Freitextfragen davor. Bedingte Fragen kommen erst, wenn die Antworten feststehen, von denen sie abhängen."""
    answers, clicks_out, free = {}, [], []
    for q in FRAGEN:
        if q["id"] in given:
            answers[q["id"]] = normalize(q, given[q["id"]])
            continue
        pending = {x["id"] for x in clicks_out + free}
        if pending & set(q.get("ab", [])):
            break                                                    # hängt von offenen Antworten dieser Runde ab
        if not active(q, answers):
            continue
        options = clicks(q, answers)
        if not options:
            if clicks_out:
                break
            free.append({"id": q["id"], "frage": q["frage"], "hilfe": q.get("hilfe", ""), "pflicht": required(q, answers)})
            continue
        default = _val(q.get("vorgabe"), answers)
        defaults = default if isinstance(default, list) else ["ja" if default is True else "nein" if default is False else default]
        opts = sorted(options, key=lambda o: o not in defaults)      # Vorschlag zuerst
        clicks_out.append({
            "id": q["id"], "question": q["frage"], "header": q["chip"][:12], "multiSelect": q["typ"] == "mehrfach",
            "options": [{"label": o + (" (Vorschlag)" if o in defaults and len(opts) > 1 else ""),
                         **({"description": q["info"][o]} if (q.get("info") or {}).get(o) else {})} for o in opts],
        })
        if len(clicks_out) == 4:
            break
    return {"freitext": free, "fragen": clicks_out, "fertig": not free and not clicks_out,
            "hinweis": "Antworten (ohne «(Vorschlag)») mit der id in die Antwortdatei schreiben; «Andere» = eigene Antwort."}


def markdown() -> str:
    out = ["# Start-Checkliste", "",
           "Diese Fragen werden **vor** dem Einrichten des Repositorys (`apply.py`) und **vor** dem Grundgerüst des Projekts",
           "beantwortet – vom Blueprint aus im Terminal mit `python3 .github/blueprint/start.py --ziel ../projekt` oder im",
           "Gespräch mit Claude. Aus den Antworten entstehen im Ziel die Werte in `.github/blueprint.toml` und der Steckbrief",
           "`docs/PROJEKTSTART.md`. Solange",
           "`[start] erledigt = false` gilt, richtet `apply.py` nichts ein (nur Probelauf). Pflichtfragen sind mit * markiert.",
           "", "**Antworten zum Anklicken:** Fast jede Frage bietet Antworten zur Auswahl (im Terminal als Nummern, mit Claude",
           "als Klick-Antworten in Runden zu höchstens vier Fragen, `start.py --runde`). «Andere» bzw. eine eigene Eingabe",
           "geht immer. Freitext sind nur Name, Zweck, Nichtziele und erste Funktionen.", "",
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
        elif q["typ"] == "janein":
            line += " – ja · nein"
        elif isinstance(q.get("klick"), list):
            line += f" – Vorschläge: {' · '.join(q['klick'])} (oder eigene Antwort)"
        elif q.get("klick"):
            line += " – Vorschläge je nach bisherigen Antworten (oder eigene Antwort)"
        else:
            line += " – Freitext"
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
    ap.add_argument("--ziel", default="", help="Ordner des Ziel-Repositorys, z. B. ../mein-projekt")
    ap.add_argument("--antworten", default="")
    ap.add_argument("--probelauf", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--vorlage", action="store_true")
    ap.add_argument("--runde", action="store_true", help="nächste Fragerunde mit Klick-Antworten als JSON (für Claude)")
    ap.add_argument("--ueberschreiben", action="store_true", help="docs/PROJEKTSTART.md ersetzen, falls vorhanden")
    args = ap.parse_args(argv)
    if args.markdown:
        print(markdown(), end="")
        return 0
    if args.vorlage:
        print(template(), end="")
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import manifest  # noqa: E402
    target = Path(args.ziel).resolve() if args.ziel else SOURCE
    if not args.runde and (target == SOURCE.resolve() or manifest.is_blueprint(target)):
        print("✗ Ziel fehlt: start.py läuft vom Blueprint aus gegen ein anderes Repository, z. B.\n"
              "    python3 .github/blueprint/start.py --ziel ../mein-projekt", file=sys.stderr)
        return 1
    if not args.runde and not target.is_dir():
        print(f"✗ Ziel {target} gibt es nicht (zuerst das Repository anlegen bzw. klonen).", file=sys.stderr)
        return 1
    set_target(target)
    given = None
    if args.antworten and (Path(args.antworten).exists() or not args.runde):
        with open(args.antworten, "rb") as fh:
            given = tomllib.load(fh)
    if args.runde:
        print(json.dumps(next_round(given or {}), ensure_ascii=False, indent=1))
        return 0
    else:
        print("Start-Checkliste – Enter übernimmt den Vorschlag in [Klammern], * = Pflicht. Mehrere Antworten mit Komma.")
    answers, problems = collect(given)
    if problems:
        for p in problems:
            print(f"✗ {p}", file=sys.stderr)
        return 1
    if CONFIG.exists():
        text = CONFIG.read_text(encoding="utf-8")
    else:                                                       # Vorlage des Blueprints
        text = (SOURCE / ".github" / "blueprint.toml").read_text(encoding="utf-8")
        text = re.sub(r"^admin_issue = \d+", "admin_issue = 0", text, flags=re.M)
    new = text
    for section, key, value in settings_from(answers):
        new = set_value(new, section, key, value)
    server = DELIVERY[0] in (answers.get("auslieferung") or [])
    new = deployment(new, server)
    tomllib.loads(new)                                          # muss gültig bleiben
    prefix = "(Probelauf) " if args.probelauf else ""
    if answers.get("sichtbarkeit") == "öffentlich" and answers.get("schutzbedarf") in ("vertraulich", "geheim"):
        print(f"⚠ Schutzbedarf «{answers['schutzbedarf']}», aber öffentliches Repository – empfohlen: privat "
              "(Code, Issues und Verlauf sind sonst für alle sichtbar).")
    for section, key, value in settings_from(answers):
        print(f"{prefix}{section}.{key} = {toml_value(value)}")
    print(f"{prefix}Deployment (Umgebungen, Variablen, Secrets, Deploy-Keys): " + ("eingeschaltet – Werte eintragen" if server else "aus"))
    if args.probelauf:
        return 0
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(new, encoding="utf-8")
    print(f"✓ {CONFIG.relative_to(ROOT)} aktualisiert")
    if STECKBRIEF.exists() and not args.ueberschreiben:
        print(f"⚠ {STECKBRIEF.relative_to(ROOT)} gibt es schon – nicht überschrieben (--ueberschreiben)")
    else:
        STECKBRIEF.parent.mkdir(parents=True, exist_ok=True)
        STECKBRIEF.write_text(steckbrief(answers), encoding="utf-8")
        print(f"✓ {STECKBRIEF.relative_to(ROOT)} angelegt")
    z = args.ziel or "."
    print(f"\nNächste Schritte: python3 .github/blueprint/apply.py --ziel {z} --probelauf, danach ohne Probelauf; "
          "das Grundgerüst erst nach Bestätigung des Steckbriefs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
