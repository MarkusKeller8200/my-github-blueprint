#!/usr/bin/env python3
"""Konformitätsprüfung: erfüllt ein Repository die Pflichtregeln des GitHub-Blueprints? (nur Standardbibliothek)

    python3 .github/blueprint/konformitaet.py                     dieses Repository prüfen (im Projekt, z. B. Workflow)
    python3 .github/blueprint/konformitaet.py --ziel ../projekt   geklontes Ziel prüfen (vom Blueprint aus)
    python3 .github/blueprint/konformitaet.py --repo owner/name   nur über die GitHub-API prüfen (ohne Klon)
    python3 .github/blueprint/konformitaet.py --alle OWNER        alle eigenen Repositorys von OWNER (Übersicht)
    … --markdown                                                  Bericht als Markdown
    … --issue                                                     (Workflow) Issue anlegen/aktualisieren bzw. schliessen

Auch über «apply.py --ziel ../projekt --pruefen». Stufen je Regel: bestanden, nicht bestanden, nicht anwendbar,
nicht prüfbar (z. B. ohne gh-Anmeldung oder ohne API). Exit 1, wenn eine Regel nicht bestanden ist.

Pflichtregeln (Gruppen):
- About: Beschreibung, Website, mindestens drei Topics, «Include in the home page» (von Hand, bestätigt in
  [konformitaet] startseite_geprueft)
- Dokumente: README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, LICENSE (öffentlich), CHANGELOG mit «Unveröffentlicht»
- Issues und Meilensteine: Formulare Fehler/Verbesserung/Funktion, Status-Labels, Sammlungen bzw. Release-Meilenstein
- Versionierung: Versionsdatei mit SemVer, Release-Gate, Workflow release.yml
- Umgebungen: DEV/TEST/PROD wie in [betrieb] umgebungen festgelegt (Web); Kanäle über Vorabversionen (Desktop)
- KI-Übergabe: AGENTS.md mit Abschnitt «GitHub-Ablauf», docs/UEBERGABE.md, docs/PROJEKTSTAND.md
- Blueprint: Konfiguration mit beantworteter Start-Checkliste, Actions auf Commit-SHA gepinnt (öffentlich)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import release  # noqa: E402  (SemVer, Versionsdatei, Release-Gate)

BESTANDEN, NICHT, NA, OFFEN = "bestanden", "nicht bestanden", "nicht anwendbar", "nicht prüfbar"
ICON = {BESTANDEN: "✅", NICHT: "❌", NA: "➖", OFFEN: "❔"}
STATUS_LABELS = ["triage", "_1 bereit", "_2 in Arbeit", "_3 Beta-Test"]
SAMMLUNGEN = ["Fehler", "Verbesserungen", "Funktionen"]
FORMULARE = [".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/improvement.yml",
             ".github/ISSUE_TEMPLATE/feature_request.yml"]
MIN_THEMEN = 3
MARK = "<!-- blueprint:konformitaet -->"
TITLE = "Konformität: Abweichungen von den Blueprint-Vorgaben"
UMGEBUNGEN = ["entwicklung", "test", "produktion"]
KANAELE = ["entwicklung", "beta", "stabil"]


# --- Zugriff auf Dateien und GitHub -----------------------------------------------------------------------------

class LocalFiles:
    def __init__(self, root: Path):
        self.root = root

    def read(self, rel: str) -> str | None:
        p = self.root / rel
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None

    def listdir(self, rel: str) -> list[str]:
        p = self.root / rel
        return sorted(x.name for x in p.iterdir() if x.is_file()) if p.is_dir() else []


class RemoteFiles:
    """Dateien über die Contents-API (Standard-Branch)."""
    def __init__(self, repo: str):
        self.repo = repo

    def read(self, rel: str) -> str | None:
        try:
            data = gh(f"repos/{self.repo}/contents/{urllib.parse.quote(rel)}")
        except RuntimeError:
            return None
        if not isinstance(data, dict) or data.get("type") != "file":
            return None
        return base64.b64decode(data.get("content", "")).decode("utf-8", "replace")

    def listdir(self, rel: str) -> list[str]:
        try:
            data = gh(f"repos/{self.repo}/contents/{urllib.parse.quote(rel)}")
        except RuntimeError:
            return []
        return sorted(x["name"] for x in data if x.get("type") == "file") if isinstance(data, list) else []


def gh(path: str, *args: str):
    r = subprocess.run(["gh", "api", path, *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:200] or f"gh api {path} fehlgeschlagen")
    return json.loads(r.stdout) if r.stdout.strip() else None


class GitHub:
    """Zwischengespeicherte Lesezugriffe; Fehler → None (Regel «nicht prüfbar»)."""
    def __init__(self, repo: str):
        self.repo, self.cache, self.errors = repo, {}, {}

    def get(self, sub: str = ""):
        path = f"repos/{self.repo}" + (f"/{sub}" if sub else "")
        if path not in self.cache:
            try:
                self.cache[path] = gh(path)
            except (RuntimeError, FileNotFoundError, json.JSONDecodeError) as e:
                self.cache[path], self.errors[path] = None, str(e)
        return self.cache[path]

    def info(self):
        return self.get() if self.repo else None


# --- Regeln ---------------------------------------------------------------------------------------------------

def _result(gruppe: str, regel: str, status: str, hinweis: str = "") -> dict:
    return {"gruppe": gruppe, "regel": regel, "status": status, "hinweis": hinweis}


def load_cfg(files) -> dict | None:
    text = files.read(".github/blueprint.toml")
    if text is None:
        return None
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None


def first(files, names: list[str]) -> str:
    for n in names:
        if files.read(n) is not None:
            return n
    return ""


def public_of(cfg: dict, info: dict | None) -> bool:
    if info:
        return info.get("visibility") == "public" or info.get("private") is False
    return cfg.get("repository", {}).get("sichtbarkeit") == "oeffentlich"


def check_about(cfg: dict, info: dict | None, repo: str) -> list[dict]:
    g = "About"
    if info is None:
        return [_result(g, r, OFFEN, "GitHub nicht erreichbar (gh-Anmeldung bzw. GH_TOKEN)") for r in
                ("Beschreibung", "Website", f"Topics (mind. {MIN_THEMEN})")] + [check_startseite(cfg, repo)]
    out = []
    desc = (info.get("description") or "").strip()
    out.append(_result(g, "Beschreibung", BESTANDEN if desc else NICHT,
                       "" if desc else "repository.beschreibung setzen (Start-Checkliste: Zweck) und apply.py ausführen"))
    home = (info.get("homepage") or "").strip()
    out.append(_result(g, "Website", BESTANDEN if home else NICHT,
                       home if home else 'repository.webseite = "auto" (Pages- bzw. App-Adresse, sonst README) und apply.py ausführen'))
    topics = info.get("topics") or []
    ok = len(topics) >= MIN_THEMEN
    out.append(_result(g, f"Topics (mind. {MIN_THEMEN})", BESTANDEN if ok else NICHT,
                       ", ".join(topics) if ok else f"{len(topics)} gesetzt – repository.themen ergänzen und apply.py ausführen"))
    out.append(check_startseite(cfg, repo))
    return out


def check_startseite(cfg: dict, repo: str) -> dict:
    done = bool(cfg.get("konformitaet", {}).get("startseite_geprueft", False))
    return _result("About", "Include in the home page (Releases, Packages, Deployments)", BESTANDEN if done else OFFEN,
                   "" if done else f"GitHub bietet keine API: von Hand prüfen (https://github.com/{repo or 'OWNER/REPO'} → "
                                   "Zahnrad bei «About»), danach [konformitaet] startseite_geprueft = true")


def check_documents(cfg: dict, files, public: bool) -> list[dict]:
    g = "Dokumente"
    out = []
    readme = files.read("README.md")
    out.append(_result(g, "README", BESTANDEN if readme and len(readme.strip()) > 40 else NICHT,
                       "" if readme else "README.md fehlt"))
    for label, names in (("CONTRIBUTING", ["CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"]),
                         ("Security Policy", ["SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"]),
                         ("Code of Conduct", ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md", "docs/CODE_OF_CONDUCT.md"])):
        hit = first(files, names)
        out.append(_result(g, label, BESTANDEN if hit else NICHT, hit or f"{names[0]} fehlt – apply.py anwenden"))
    lic = first(files, ["LICENSE", "LICENSE.md", "LICENSE.txt"])
    if public:
        out.append(_result(g, "Lizenz", BESTANDEN if lic else NICHT, lic or "öffentlich ohne LICENSE – projekt.lizenz setzen"))
    else:
        out.append(_result(g, "Lizenz", BESTANDEN if lic else NA, lic or "privat: keine Pflicht"))
    log = files.read("CHANGELOG.md")
    ok = bool(log and release.UNRELEASED in log)
    out.append(_result(g, "CHANGELOG mit «Unveröffentlicht»", BESTANDEN if ok else NICHT,
                       "" if ok else ("CHANGELOG.md fehlt" if log is None else "Abschnitt «## [Unveröffentlicht]» fehlt")))
    return out


def check_issues(cfg: dict, files, gh_: GitHub | None) -> list[dict]:
    g = "Issues und Meilensteine"
    missing = [f for f in FORMULARE if files.read(f) is None]
    out = [_result(g, "Formulare Fehler, Verbesserung, Funktion", NICHT if missing else BESTANDEN,
                   ("fehlt: " + ", ".join(Path(f).name for f in missing)) if missing else "")]
    labels = gh_.get("labels?per_page=100") if gh_ else None
    if labels is None:
        out.append(_result(g, "Status-Labels", OFFEN, "GitHub nicht erreichbar"))
    else:
        names = {l["name"] for l in labels}
        miss = [l for l in STATUS_LABELS if l not in names]
        out.append(_result(g, "Status-Labels", NICHT if miss else BESTANDEN, ("fehlt: " + ", ".join(miss)) if miss else ""))
    ms = gh_.get("milestones?state=all&per_page=100") if gh_ else None
    if ms is None:
        out.append(_result(g, "Meilensteine", OFFEN, "GitHub nicht erreichbar"))
    else:
        titles = {m["title"] for m in ms}
        want = SAMMLUNGEN if cfg.get("meilensteine", {}).get("sammlungen", True) else []
        miss = [t for t in want if t not in titles]
        rel = [t for t in titles if re.match(r"^\d+\.\d+\.\d+", t)]
        hint = ("fehlt: " + ", ".join(miss)) if miss else ("kein Release-Meilenstein «X.Y.Z – Thema»" if not rel else "")
        out.append(_result(g, "Meilensteine (Sammlungen und Release)", NICHT if miss or not rel else BESTANDEN, hint))
    return out


def check_versioning(cfg: dict, files) -> list[dict]:
    g = "Versionierung"
    v = cfg.get("versionierung", {})
    name = v.get("datei", "VERSION")
    text = files.read(name)
    version = ""
    if text is not None:
        if name.endswith(".json"):
            try:
                version = str(json.loads(text).get("version", ""))
            except json.JSONDecodeError:
                version = ""
        else:
            m = re.search(r'''(?:^|\n)\s*(?:version\s*=\s*|VERSION\s*=\s*)?["']?(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)''', text)
            version = m.group(1) if m else ""
    ok = bool(release.SEMVER.match(version))
    out = [_result(g, "Versionsdatei mit SemVer", BESTANDEN if ok else NICHT,
                   f"{name}: {version}" if ok else f"{name} fehlt oder ohne gültige Version (MAJOR.MINOR.PATCH)")]
    state, message = release.release_gate(cfg)
    out.append(_result(g, "Release-Gate", NICHT if state == "warnung" else BESTANDEN, message))
    out.append(_result(g, "Workflow release.yml", BESTANDEN if files.read(".github/workflows/release.yml") else NICHT,
                       "" if files.read(".github/workflows/release.yml") else "apply.py anwenden"))
    return out


def planned_environments(cfg: dict) -> list[str]:
    b = cfg.get("betrieb", {})
    if "umgebungen" in b:
        return [x for x in b.get("umgebungen", []) if x]
    return [e["name"] for e in cfg.get("umgebungen", [])]


def check_environments(cfg: dict, gh_: GitHub | None) -> list[dict]:
    g = "Umgebungen"
    art = cfg.get("projekt", {}).get("art", "web")
    out = []
    planned = planned_environments(cfg)
    if art in ("web", "beides"):
        b = cfg.get("betrieb", {})
        if "umgebungen" not in b and not planned:
            out.append(_result(g, "DEV/TEST/PROD festgelegt", NICHT,
                               "[betrieb] umgebungen fehlt – Start-Checkliste (Frage «Umgebungen») beantworten"))
        elif not planned:
            out.append(_result(g, "DEV/TEST/PROD", NA, "bewusst keine Umgebungen ([betrieb] umgebungen = [])"))
        else:
            data = gh_.get("environments") if gh_ else None
            if data is None:
                out.append(_result(g, "DEV/TEST/PROD auf GitHub", OFFEN,
                                   "GitHub nicht erreichbar (Umgebungen: " + ", ".join(planned) + ")"))
            else:
                have = {e["name"] for e in data.get("environments", [])}
                miss = [x for x in planned if x not in have]
                out.append(_result(g, "DEV/TEST/PROD auf GitHub", NICHT if miss else BESTANDEN,
                                   ("fehlt: " + ", ".join(miss) + " – apply.py als Eigentümer:in ausführen") if miss else ", ".join(planned)))
    if art in ("desktop", "beides"):
        kan = cfg.get("betrieb", {}).get("kanaele", KANAELE)
        ok = "beta" in kan or "stabil" in kan
        out.append(_result(g, "Kanäle (Entwicklung, Beta, Stabil)", BESTANDEN if ok else NICHT,
                           "über Developer Releases, Vorabversionen X.Y.Z-beta.N und finale Versionen" if ok else
                           "[betrieb] kanaele festlegen"))
    return out


def check_handover(cfg: dict, files) -> list[dict]:
    g = "KI-Übergabe"
    agents = files.read("AGENTS.md")
    out = [_result(g, "AGENTS.md mit Abschnitt «GitHub-Ablauf»",
                   BESTANDEN if agents and "blueprint:github-ablauf" in agents else NICHT,
                   "" if agents else "AGENTS.md fehlt – apply.py anwenden")]
    if agents and "blueprint:github-ablauf" not in agents:
        out[0]["hinweis"] = "Abschnitt fehlt – apply.py anwenden"
    for rel in ("docs/UEBERGABE.md", "docs/PROJEKTSTAND.md"):
        ok = files.read(rel) is not None
        out.append(_result(g, rel, BESTANDEN if ok else NICHT, "" if ok else "fehlt – [agenten] uebergabe = true, apply.py"))
    return out


def check_blueprint(cfg: dict | None, files, public: bool, blueprint_version: str) -> list[dict]:
    g = "Blueprint"
    if cfg is None:
        return [_result(g, "Konfiguration .github/blueprint.toml", NICHT,
                        "fehlt – Blueprint anwenden (start.py, apply.py)")]
    out = [_result(g, "Start-Checkliste beantwortet", BESTANDEN if cfg.get("start", {}).get("erledigt") else NICHT,
                   "" if cfg.get("start", {}).get("erledigt") else "start.py --ziel … ausführen")]
    stand = (files.read(".github/blueprint/VERSION") or "").split()
    if not blueprint_version:
        out.append(_result(g, "Blueprint-Stand", NA if stand else NICHT,
                           f"Stand {' '.join(stand)} (Vergleich nur vom Blueprint aus)" if stand else ".github/blueprint/VERSION fehlt"))
    else:
        same = bool(stand) and stand[0] == blueprint_version
        out.append(_result(g, "Blueprint-Stand", BESTANDEN if same else NICHT,
                           f"{stand[0] if stand else '–'} (aktuell {blueprint_version})" + ("" if same else " – apply.py --aktualisieren")))
    pin = cfg.get("actions", {}).get("sha_pinning", "auto")
    needed = public if pin == "auto" else bool(pin)
    unpinned = []
    for name in files.listdir(".github/workflows"):
        if not name.endswith((".yml", ".yaml")):
            continue
        for action, ref in re.findall(r"uses:\s*([\w.-]+/[\w./-]+)@([\w.-]+)", files.read(f".github/workflows/{name}") or ""):
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                unpinned.append(f"{name}: {action}@{ref}")
    if not needed:
        out.append(_result(g, "Actions auf Commit-SHA gepinnt", NA if unpinned else BESTANDEN,
                           f"privat: keine Pflicht ({len(unpinned)} ungepinnt)" if unpinned else ""))
    else:
        out.append(_result(g, "Actions auf Commit-SHA gepinnt", NICHT if unpinned else BESTANDEN, "; ".join(unpinned[:5])))
    return out


def run_checks(files, repo: str, blueprint_version: str = "", use_github: bool = True) -> list[dict]:
    cfg = load_cfg(files)
    gh_ = GitHub(repo) if repo and use_github else None
    info = gh_.info() if gh_ else None
    public = public_of(cfg or {}, info)
    base = check_blueprint(cfg, files, public, blueprint_version)
    cfg = cfg or {}
    return (check_about(cfg, info, repo) + check_documents(cfg, files, public) + check_issues(cfg, files, gh_)
            + check_versioning(cfg, files) + check_environments(cfg, gh_) + check_handover(cfg, files) + base)


# --- Bericht -------------------------------------------------------------------------------------------------

def counts(results: list[dict]) -> dict[str, int]:
    out = {BESTANDEN: 0, NICHT: 0, NA: 0, OFFEN: 0}
    for r in results:
        out[r["status"]] += 1
    return out


def summary_line(results: list[dict]) -> str:
    c = counts(results)
    return f"{c[BESTANDEN]} bestanden, {c[NICHT]} nicht bestanden, {c[OFFEN]} nicht prüfbar, {c[NA]} nicht anwendbar"


def text_report(results: list[dict], repo: str) -> str:
    lines = [f"Konformität {repo or '(lokal)'}: {summary_line(results)}"]
    group = None
    for r in results:
        if r["gruppe"] != group:
            group = r["gruppe"]
            lines.append(f"\n{group}")
        lines.append(f"  {ICON[r['status']]} {r['regel']}" + (f" – {r['hinweis']}" if r["hinweis"] else ""))
    return "\n".join(lines)


def markdown_report(results: list[dict], repo: str) -> str:
    rows = "\n".join(f"| {r['gruppe']} | {r['regel']} | {ICON[r['status']]} {r['status']} | {r['hinweis'] or ''} |"
                     for r in results)
    todo = [r for r in results if r["status"] in (NICHT, OFFEN)]
    tasks = "\n".join(f"- [ ] {r['gruppe']}: {r['regel']}" + (f" – {r['hinweis']}" if r["hinweis"] else "") for r in todo)
    return (f"{MARK}\n## Konformität mit dem GitHub-Blueprint – {repo}\n\n{summary_line(results)}.\n\n"
            + (f"**Zu erledigen:**\n\n{tasks}\n\n" if tasks else "Alle Pflichtregeln erfüllt.\n\n")
            + "| Gruppe | Regel | Status | Hinweis |\n|---|---|---|---|\n" + rows + "\n\n"
            "Erneut prüfen: Actions → «Konformität prüfen» → Run workflow, bzw. im Blueprint "
            "`python3 .github/blueprint/apply.py --ziel ../projekt --pruefen`.\n")


def publish_issue(repo: str, results: list[dict], label: str) -> None:
    """Ein Issue mit den Abweichungen anlegen bzw. aktualisieren; ohne Abweichungen schliessen."""
    failing = counts(results)[NICHT] > 0
    body = markdown_report(results, repo)
    try:
        issues = gh(f"repos/{repo}/issues?state=open&per_page=100&labels={urllib.parse.quote(label)}") or []
    except RuntimeError as e:
        print(f"::warning title=Konformität::Issues nicht lesbar ({e})")
        return
    cur = next((i for i in issues if MARK in (i.get("body") or "")), None)
    try:
        if cur and not failing:
            gh(f"repos/{repo}/issues/{cur['number']}", "-X", "PATCH", "-f", f"body={body}", "-f", "state=closed",
               "-f", "state_reason=completed")
            print(f"Issue #{cur['number']} geschlossen – alle Pflichtregeln erfüllt.")
        elif cur:
            if (cur.get("body") or "") != body:
                gh(f"repos/{repo}/issues/{cur['number']}", "-X", "PATCH", "-f", f"body={body}")
                gh(f"repos/{repo}/issues/{cur['number']}/comments", "-X", "POST", "-f", "body=Neue Prüfung – Liste oben aktualisiert.")
            print(f"Issue #{cur['number']} aktualisiert.")
        elif failing:
            new = gh(f"repos/{repo}/issues", "-X", "POST", "-f", f"title={TITLE}", "-f", f"body={body}",
                     "-f", f"labels[]={label}", "-f", "labels[]=triage")
            print(f"Issue #{new and new.get('number')} angelegt.")
    except RuntimeError as e:
        print(f"::warning title=Konformität::Issue nicht geschrieben ({e})")


def all_repos(owner: str) -> list[str]:
    """Eigene, nicht archivierte Repositorys (keine Forks) von OWNER – zuerst als angemeldete:r Nutzer:in."""
    try:
        me = (gh("user") or {}).get("login", "")
    except RuntimeError:
        me = ""
    bases = (["user/repos?affiliation=owner"] if me.lower() == owner.lower() else []) + [f"users/{owner}/repos?type=owner",
                                                                                         f"orgs/{owner}/repos?type=all"]
    repos, last = None, ""
    for base in bases:
        try:
            repos, page = [], 1
            while True:
                batch = gh(f"{base}&per_page=100&page={page}") or []
                repos += batch
                if len(batch) < 100:
                    break
                page += 1
            break
        except RuntimeError as e:
            repos, last = None, str(e)
    if repos is None:
        raise RuntimeError(f"Repositorys von {owner} nicht lesbar: {last}")
    return sorted(r["full_name"] for r in repos if not r.get("archived") and not r.get("fork")
                  and r["owner"]["login"].lower() == owner.lower())


def own_blueprint_version() -> str:
    """Version des Blueprints, wenn dieses Skript im Blueprint selbst liegt (sonst leer)."""
    if (ROOT / ".github" / "blueprint-repo.toml").exists():
        return (HERE / "VERSION").read_text(encoding="utf-8").split()[0]
    return ""


def detect_repo(root: Path) -> str:
    if os.environ.get("GITHUB_REPOSITORY"):
        return os.environ["GITHUB_REPOSITORY"]
    r = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True, encoding="utf-8")
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", r.stdout.strip())
    return m.group(1) if m else ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Konformitätsprüfung nach dem GitHub-Blueprint")
    ap.add_argument("--ziel", default="", help="Ordner eines geklonten Repositorys (Standard: dieses)")
    ap.add_argument("--repo", default="", help="owner/name (Standard: aus git remote); ohne --ziel nur über die API")
    ap.add_argument("--alle", default="", metavar="OWNER", help="alle eigenen Repositorys von OWNER prüfen")
    ap.add_argument("--ohne-github", action="store_true", help="nur Dateien prüfen")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--issue", action="store_true", help="Issue anlegen/aktualisieren/schliessen (Workflow)")
    args = ap.parse_args(argv)
    bp_version = own_blueprint_version()

    if args.alle:
        failing = 0
        try:
            names = all_repos(args.alle)
        except RuntimeError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2
        print(f"| Repository | bestanden | nicht bestanden | nicht prüfbar | offene Regeln |\n|---|---|---|---|---|")
        for repo in names:
            if RemoteFiles(repo).read(".github/blueprint-repo.toml") is not None:
                print(f"| {repo} | – | – | – | Blueprint selbst (Vorlage, nicht geprüft) |")
                continue
            res = run_checks(RemoteFiles(repo), repo, bp_version)
            c = counts(res)
            failing += c[NICHT] > 0
            bad = ", ".join(r["regel"] for r in res if r["status"] == NICHT)
            print(f"| {repo} | {c[BESTANDEN]} | {c[NICHT]} | {c[OFFEN]} | {bad[:180]} |")
        return 1 if failing else 0

    if args.repo and not args.ziel:
        files, repo = RemoteFiles(args.repo), args.repo
        if files.read(".github/blueprint-repo.toml") is not None:
            print(f"{repo} ist der Blueprint selbst (Vorlage) – geprüft werden die Projekte.")
            return 0
    else:
        root = Path(args.ziel).resolve() if args.ziel else ROOT
        if (root / ".github" / "blueprint-repo.toml").exists():
            print("::notice title=Konformität::Das ist der Blueprint selbst – geprüft werden die Projekte "
                  "(--ziel, --repo oder --alle).")
            return 0
        files, repo = LocalFiles(root), args.repo or detect_repo(root)
    cfg = load_cfg(files) or {}
    if os.environ.get("GITHUB_ACTIONS") and not cfg.get("konformitaet", {}).get("workflow", True):
        print("::notice title=Konformität::[konformitaet] workflow = false – nichts zu tun")
        return 0
    results = run_checks(files, repo, bp_version, not args.ohne_github)
    print(markdown_report(results, repo) if args.markdown else text_report(results, repo))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(markdown_report(results, repo).replace(MARK, "") + "\n")
    if args.issue and repo:
        publish_issue(repo, results, cfg.get("konformitaet", {}).get("label", "blueprint"))
        return 0                                          # im Workflow meldet das Issue, nicht ein roter Lauf
    return 1 if counts(results)[NICHT] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
