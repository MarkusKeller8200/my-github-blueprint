#!/usr/bin/env python3
"""Manifest des GitHub-Blueprints: was gehört in ein Ziel-Repository, was ist Ballast? (nur Standardbibliothek)

    python3 .github/blueprint/manifest.py                    Einteilung aller Dateien anzeigen
    python3 .github/blueprint/manifest.py --pruefen          jede Datei genau einmal im Manifest? (Exit 1 sonst)
    python3 .github/blueprint/manifest.py --ziel ../projekt  Laufzeitdateien und Ballast für ein Ziel anzeigen

Die Einteilung steht in manifest.toml (blueprint / einrichtung / laufzeit). Laufzeitdateien kommen nur ins Ziel,
wenn ihre Bedingung in dessen .github/blueprint.toml zutrifft. apply.py kopiert danach, und
«apply.py --aufraeumen» entfernt den Ballast – nach Rückfrage.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]                       # Wurzel des Blueprint-Repositorys
MANIFEST = HERE / "manifest.toml"
BLUEPRINT_REPO = "markuskeller8200/my-github-blueprint"
IGNORE_PARTS = {".git", "__pycache__"}


def _auto(value, public: bool, if_public, if_private):
    return (if_public if public else if_private) if value == "auto" else value


def _public(cfg: dict) -> bool:
    return cfg.get("repository", {}).get("sichtbarkeit") == "oeffentlich"


def _codeql(cfg: dict) -> bool:
    mode = cfg.get("codeql", {}).get("workflow", "auto")
    if mode is False:
        return False
    if mode is True:
        return True
    scanning = cfg.get("sicherheit", {}).get("code_scanning", "auto")
    return bool(_auto(scanning, _public(cfg), True, False))


def _release_files(cfg: dict) -> bool:
    return bool([p for p in cfg.get("release_dateien", {}).get("artefakte", []) if p])


# Bedingung → zutreffend für diese Konfiguration?
BEDINGUNGEN = {
    "sammlungen": lambda c: bool(c.get("meilensteine", {}).get("sammlungen", True)),
    "milestone_admin": lambda c: bool(c.get("workflows", {}).get("milestone_admin", True)),
    "ci": lambda c: bool(c.get("ci", {}).get("aktiv", False)),
    "codeql": _codeql,
    "fremdkomponenten": lambda c: bool(c.get("fremdkomponenten", {}).get("aktiv", False)),
    "aufraeumen": lambda c: int(c.get("aufraeumen", {}).get("actions_verlauf_tage", 0) or 0) > 0,
    "vorabversionen": lambda c: bool(c.get("versionierung", {}).get("vorabversionen_aufraeumen", False)),
    "release_dateien": _release_files,
    "installer": lambda c: _release_files(c) and "installer" in c.get("versionierung", {}).get("release_nach", []),
}


def load() -> list[dict]:
    with open(MANIFEST, "rb") as fh:
        entries = tomllib.load(fh).get("eintrag", [])
    for e in entries:
        if e.get("art") not in ("blueprint", "einrichtung", "laufzeit"):
            raise ValueError(f"manifest.toml: unbekannte art «{e.get('art')}» bei «{e.get('muster')}»")
        unknown = [w for w in e.get("wenn", []) if w not in BEDINGUNGEN]
        if unknown:
            raise ValueError(f"manifest.toml: unbekannte Bedingung {unknown} bei «{e['muster']}»")
    return entries


def matches(entry: dict, path: str) -> bool:
    return fnmatch.fnmatchcase(path, entry["muster"])


def files(root: Path) -> list[str]:
    """Dateien eines Repositorys (relativ, mit «/»): bei Git die verwalteten und neuen, sonst alle."""
    r = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                       capture_output=True, text=True)
    if r.returncode == 0 and (root / ".git").exists():
        names = [n for n in r.stdout.splitlines() if (root / n).is_file()]
    else:
        names = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]
    return sorted(n for n in names if not IGNORE_PARTS & set(n.split("/")))


def entry_for(path: str, entries: list[dict]) -> list[dict]:
    return [e for e in entries if matches(e, path)]


def check_coverage(root: Path = SOURCE, entries: list[dict] | None = None) -> list[str]:
    """Probleme: Dateien ohne bzw. mit mehreren Einträgen, Einträge ohne Datei."""
    entries = entries if entries is not None else load()
    problems = []
    names = files(root)
    for n in names:
        hits = entry_for(n, entries)
        if not hits:
            problems.append(f"{n}: steht nicht im Manifest (.github/blueprint/manifest.toml)")
        elif len(hits) > 1:
            problems.append(f"{n}: passt auf mehrere Einträge ({', '.join(h['muster'] for h in hits)})")
    for e in entries:
        if not e.get("frueher") and not any(matches(e, n) for n in names):
            problems.append(f"Manifest-Eintrag «{e['muster']}» passt auf keine Datei")
    return problems


def wanted(entry: dict, cfg: dict) -> bool:
    if entry["art"] != "laufzeit":
        return False
    conds = entry.get("wenn", [])
    return not conds or any(BEDINGUNGEN[c](cfg) for c in conds)


def runtime_files(cfg: dict, entries: list[dict] | None = None) -> list[str]:
    """Laufzeitdateien aus dem Blueprint, die für diese Konfiguration ins Ziel kopiert werden."""
    entries = entries if entries is not None else load()
    out = []
    for n in files(SOURCE):
        hits = entry_for(n, entries)
        if hits and not hits[0].get("erzeugt") and wanted(hits[0], cfg):
            out.append(n)
    return out


def _same(a: Path, b: Path) -> bool:
    try:
        return hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()
    except OSError:
        return False


def ballast(target: Path, cfg: dict, entries: list[dict] | None = None) -> list[tuple[str, str]]:
    """Dateien im Ziel, die dort nicht hingehören → [(Pfad, Grund)]. Eigene Dateien des Projekts bleiben unberührt."""
    entries = entries if entries is not None else load()
    out = []
    for n in files(target):
        hits = entry_for(n, entries)
        if not hits:
            continue                                          # eigene Datei des Projekts
        e = hits[0]
        if e.get("nur_gleich") and not _same(target / n, SOURCE / n):
            continue                                          # gleicher Name, aber eigener Inhalt des Projekts
        if e["art"] == "blueprint":
            out.append((n, "gehört nur zum Blueprint"))
        elif e["art"] == "einrichtung":
            out.append((n, "Werkzeug für die Einrichtung (läuft vom Blueprint aus)"))
        elif not e.get("erzeugt") and not wanted(e, cfg):
            out.append((n, f"Funktion ausgeschaltet ({', '.join(e.get('wenn', []))})"))
    return out


def is_blueprint(root: Path) -> bool:
    """Ist dieser Ordner das Blueprint-Repository selbst (nicht eine Kopie daraus)?"""
    r = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True)
    url = r.stdout.strip().lower().removesuffix(".git")
    return url.endswith(BLUEPRINT_REPO)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Manifest des GitHub-Blueprints")
    ap.add_argument("--pruefen", action="store_true", help="jede Datei genau einmal im Manifest?")
    ap.add_argument("--ziel", default="", help="Ziel-Repository: Laufzeitdateien und Ballast anzeigen")
    args = ap.parse_args(argv)
    entries = load()
    if args.pruefen:
        problems = check_coverage(SOURCE, entries)
        for p in problems:
            print(f"✗ {p}")
        print("✓ Manifest vollständig" if not problems else f"{len(problems)} Problem(e)")
        return 1 if problems else 0
    if args.ziel:
        target = Path(args.ziel).resolve()
        with open(target / ".github" / "blueprint.toml", "rb") as fh:
            cfg = tomllib.load(fh)
        print("Laufzeitdateien für dieses Ziel:")
        for n in runtime_files(cfg, entries):
            print(f"  {n}")
        found = ballast(target, cfg, entries)
        print("Ballast im Ziel:" if found else "Kein Ballast im Ziel.")
        for n, why in found:
            print(f"  {n} – {why}")
        return 0
    for n in files(SOURCE):
        hits = entry_for(n, entries)
        art = hits[0]["art"] if hits else "FEHLT"
        cond = ", ".join(hits[0].get("wenn", [])) if hits else ""
        print(f"{art:<12} {n}" + (f"  (wenn {cond})" if cond else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
