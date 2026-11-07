#!/usr/bin/env python3
"""Plan für die Workflows «pruefungen», «CodeQL erweitert» und «installer» aus .github/blueprint.toml (nur Standardbibliothek).

    python3 .github/blueprint/ci_plan.py pruefungen   Betriebssysteme, Sprachversionen, Befehle; nur Doku geändert?
    python3 .github/blueprint/ci_plan.py codeql       aktiv? Sprachen (erkannt oder konfiguriert), Build-Modus, Runner
    python3 .github/blueprint/ci_plan.py installer    Installer bauen? Betriebssysteme, Bau-Befehl, hochzuladende Dateien

In GitHub Actions werden die Werte nach $GITHUB_OUTPUT geschrieben, sonst nur angezeigt. Die Workflows selbst
bleiben unverändert; was passiert, steht allein in [ci] bzw. [codeql] der Konfiguration. Vorgaben je nach
projekt.art: «web» (Server/Browser), «desktop» (Installer/App) oder «beides».
"""
from __future__ import annotations

import fnmatch
import itertools
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import release  # noqa: E402  (Konfiguration und Versionsdatei)

ROOT = release.ROOT
OS_BY_ART = {
    "web": ["ubuntu-latest"],
    "desktop": ["windows-latest", "macos-latest"],
    "beides": ["ubuntu-latest", "windows-latest", "macos-latest"],
}
DOC_PATTERNS = ["*.md", "docs/**", "LICENSE", "LICENSE.*", ".github/ISSUE_TEMPLATE/**", ".github/FUNDING.yml"]
OWN_CODEQL = "codeql-erweitert.yml"

# CodeQL: Dateiendung → Sprache; Build-Modus und Runner, wo nötig (PHP unterstützt CodeQL nicht)
LANG_BY_EXT = {
    ".py": "python",
    ".js": "javascript-typescript", ".mjs": "javascript-typescript", ".cjs": "javascript-typescript",
    ".jsx": "javascript-typescript", ".ts": "javascript-typescript", ".tsx": "javascript-typescript",
    ".vue": "javascript-typescript",
    ".rb": "ruby", ".go": "go", ".rs": "rust", ".swift": "swift", ".cs": "csharp",
    ".java": "java-kotlin", ".kt": "java-kotlin", ".kts": "java-kotlin",
    ".c": "c-cpp", ".cc": "c-cpp", ".cpp": "c-cpp", ".cxx": "c-cpp", ".h": "c-cpp", ".hpp": "c-cpp",
}
SKIP_DIRS = ("vendor/", "node_modules/", "dist/", "build/", "third_party/", ".venv/", ".github/blueprint/")  # ohne Blueprint selbst
BUILD_MODE = {"c-cpp": "autobuild", "go": "autobuild", "swift": "autobuild"}
RUNNER = {"swift": "macos-latest"}


def _list(value) -> list:
    if value in (None, "", []):
        return []
    return [value] if isinstance(value, str) else list(value)


def art(cfg: dict) -> str:
    a = cfg.get("projekt", {}).get("art", "web")
    return a if a in OS_BY_ART else "web"


def event() -> dict:
    path = os.environ.get("GITHUB_EVENT_PATH", "")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def is_public(cfg: dict, ev: dict) -> bool:
    repo = ev.get("repository") or {}
    if "private" in repo:
        return not repo["private"]
    return cfg.get("repository", {}).get("sichtbarkeit") == "oeffentlich"


def changed_files(ev: dict) -> list[str] | None:
    """Geänderte Dateien dieses Pushes bzw. Pull Requests; None = unbekannt (dann wird alles geprüft)."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "pull_request" in ev:
        base, head = ev["pull_request"]["base"]["sha"], ev["pull_request"]["head"]["sha"]
    elif ev.get("before") and ev.get("after"):
        base, head = ev["before"], ev["after"]
    else:
        return None
    if not repo or set(base) == {"0"}:
        return None
    r = subprocess.run(["gh", "api", f"repos/{repo}/compare/{base}...{head}", "--jq", "[.files[].filename]"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    files = json.loads(r.stdout or "[]")
    return files if 0 < len(files) < 300 else None   # die API liefert höchstens 300 Dateien


def only_docs(files: list[str] | None, patterns: list[str]) -> bool:
    if not files:
        return False
    return all(any(fnmatch.fnmatch(f, p) or fnmatch.fnmatch(os.path.basename(f), p) for p in patterns) for f in files)


def plan_pruefungen(cfg: dict, ev: dict) -> dict:
    c = cfg.get("ci", {})
    out = {"aktiv": "false", "matrix": json.dumps({"include": []}), "grund": "", "timeout": "30"}
    if not c.get("aktiv", False):
        out["grund"] = "[ci] aktiv = false"
        return out
    if c.get("nur_doku_ueberspringen", True) and only_docs(changed_files(ev), _list(c.get("doku_muster")) or DOC_PATTERNS):
        out["grund"] = "nur Dokumentation geändert"
        return out
    systems = c.get("betriebssysteme", "auto")
    systems = OS_BY_ART[art(cfg)] if systems == "auto" else _list(systems)
    version = release.read_version(cfg)
    beta = _list(c.get("betriebssysteme_beta"))
    if beta and "-" in version:
        systems = [s for s in systems if s in beta] or beta
    langs = {k: _list(c.get(k)) or [""] for k in ("python", "node", "java", "dotnet")}
    include = []
    for os_name in systems:
        for combo in itertools.product(*langs.values()):
            entry = dict(zip(langs, combo), os=os_name)
            label = " · ".join([os_name] + [f"{k} {v}" for k, v in entry.items() if k != "os" and v])
            include.append({**entry, "name": label})
    befehl = c.get("befehl", "") or cfg.get("projekt", {}).get("pruefbefehl", "")
    if not befehl:
        out["grund"] = "kein Prüfbefehl ([ci] befehl bzw. projekt.pruefbefehl)"
        return out
    return {
        "aktiv": "true", "grund": "", "matrix": json.dumps({"include": include}),
        "befehl": befehl, "vorbereiten": c.get("vorbereiten", ""),
        "xvfb": "true" if c.get("virtueller_bildschirm", False) else "false",
        "testausgabe": c.get("testausgabe", ""), "timeout": str(int(c.get("timeout_minuten", 30))),
    }


ARTEFAKT = {"windows-latest": "windows", "macos-latest": "macos", "ubuntu-latest": "linux"}


def tag_exists(tag: str) -> bool:
    r = subprocess.run(["git", "-C", str(ROOT), "tag", "-l", tag], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == tag


def plan_installer(cfg: dict, ev: dict) -> dict:
    i, c = cfg.get("installer", {}), cfg.get("ci", {})
    out = {"aktiv": "false", "matrix": json.dumps({"include": []}), "grund": "", "timeout": "60"}
    rd = [p for p in cfg.get("release_dateien", {}).get("artefakte", []) if p]
    if not rd or "installer" not in cfg.get("versionierung", {}).get("release_nach", []):
        out["grund"] = "kein Installer konfiguriert (release_dateien.artefakte bzw. versionierung.release_nach)"
        return out
    version = release.read_version(cfg)
    manual = os.environ.get("EREIGNIS", "") == "workflow_dispatch"
    if i.get("nur_neue_version", True) and not manual and version and tag_exists(f"v{version}"):
        out["grund"] = f"Version {version} hat schon einen Tag – kein neuer Installer nötig (Developer Release)"
        return out
    befehl = i.get("befehl", "").strip()
    if not befehl:
        out["grund"] = "[installer] befehl fehlt – ohne Bau-Befehl entsteht kein Installer und damit kein Release"
        out["fehler"] = "true"
        return out
    systems = i.get("betriebssysteme", "auto")
    if systems == "auto":
        systems = c.get("betriebssysteme", "auto")
    systems = OS_BY_ART[art(cfg)] if systems == "auto" else _list(systems)
    langs = {k: (_list(c.get(k)) or [""])[0] for k in ("python", "node", "java", "dotnet")}
    include = [{**langs, "os": s, "artefakt": ARTEFAKT.get(s, s), "name": f"Installer · {s}"} for s in systems]
    return {"aktiv": "true", "grund": "", "matrix": json.dumps({"include": include}), "befehl": befehl,
            "vorbereiten": i.get("vorbereiten", "") or c.get("vorbereiten", ""),
            "dateien": i.get("dateien", "dist/*"), "timeout": str(int(i.get("timeout_minuten", 60)))}


def detect_languages() -> list[str]:
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True)
    found = set()
    for f in r.stdout.splitlines():
        if f.startswith(SKIP_DIRS):
            continue
        if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml")):
            found.add("actions")
        lang = LANG_BY_EXT.get(os.path.splitext(f)[1].lower())
        if lang:
            found.add(lang)
    return sorted(found)


def other_codeql_workflows() -> list[str]:
    folder = ROOT / ".github" / "workflows"
    hits = []
    for p in sorted(folder.glob("*.y*ml")) if folder.exists() else []:
        if p.name != OWN_CODEQL and "github/codeql-action/analyze" in p.read_text(encoding="utf-8", errors="replace"):
            hits.append(p.name)
    return hits


def default_setup_active() -> bool:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        return False
    r = subprocess.run(["gh", "api", f"repos/{repo}/code-scanning/default-setup", "--jq", ".state"], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "configured"


def plan_codeql(cfg: dict, ev: dict) -> dict:
    q, s = cfg.get("codeql", {}), cfg.get("sicherheit", {})
    out = {"aktiv": "false", "matrix": json.dumps({"include": []}), "issues": "false", "grund": ""}
    mode = q.get("workflow", "auto")
    public = is_public(cfg, ev)
    scanning = s.get("code_scanning", "auto")
    scanning = public if scanning == "auto" else bool(scanning)
    if mode is False or (mode == "auto" and not scanning):
        out["grund"] = "[codeql] workflow bzw. sicherheit.code_scanning aus (privat nur mit GitHub Advanced Security)"
        return out
    if (ev.get("repository") or {}).get("is_template"):
        out["grund"] = "Template-Repository (my-github-blueprint selbst) – nur in Projekten aktiv"
        return out
    if default_setup_active():
        out["grund"] = ("Standard-Setup von CodeQL ist eingeschaltet – beides zusammen geht nicht. apply.py (vom Blueprint aus) schaltet es um "
                        "(Repository-Einstellungen), oder [codeql] workflow = false")
        return out
    others = other_codeql_workflows()
    if others and mode == "auto":
        out["grund"] = f"eigener CodeQL-Workflow vorhanden ({', '.join(others)}) – [codeql] workflow = true erzwingt diesen"
        return out
    langs = q.get("sprachen", "auto")
    langs = detect_languages() if langs == "auto" else _list(langs)
    if not langs:
        out["grund"] = "keine von CodeQL unterstützte Sprache gefunden"
        return out
    modes, runners = dict(BUILD_MODE, **q.get("build_modus", {})), dict(RUNNER, **q.get("runner", {}))
    include = [{"language": l, "build_mode": modes.get(l, "none"), "os": runners.get(l, "ubuntu-latest")} for l in langs]
    return {"aktiv": "true", "grund": "", "matrix": json.dumps({"include": include}),
            "issues": "true" if q.get("issues", True) else "false", "bau_befehl": q.get("bau_befehl", "")}


def write_outputs(values: dict) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    lines = []
    for k, v in values.items():
        v = str(v)
        if "\n" in v:
            mark = f"EOF_{uuid.uuid4().hex}"
            lines.append(f"{k}<<{mark}\n{v}\n{mark}")
        else:
            lines.append(f"{k}={v}")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    for k, v in values.items():
        print(f"{k}: {v}")


def main(argv: list[str]) -> int:
    plans = {"pruefungen": plan_pruefungen, "codeql": plan_codeql, "installer": plan_installer}
    if not argv or argv[0] not in plans:
        print(__doc__)
        return 1
    cfg, ev = release.config(), event()
    values = plans[argv[0]](cfg, ev)
    failed = values.pop("fehler", "") == "true"
    if values.get("grund"):
        print(f"::{'error' if failed else 'notice'} title={argv[0]} {'fehlgeschlagen' if failed else 'übersprungen'}::{values['grund']}")
    write_outputs(values)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
