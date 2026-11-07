#!/usr/bin/env python3
"""Versionen und Releases nach dem GitHub-Blueprint (nur Python-Standardbibliothek, Python 3.11+).

    python3 .github/blueprint/release.py version              aktuelle Version
    python3 .github/blueprint/release.py planned              geplante nächste Version (Developer Release)
    python3 .github/blueprint/release.py check                Version, CHANGELOG, Plugin-Versionen prüfen
    python3 .github/blueprint/release.py notes [X.Y.Z]        Abschnitt aus dem CHANGELOG (Text für das Release)
    python3 .github/blueprint/release.py set X.Y.Z [--commit] Version setzen, «Unveröffentlicht» → [X.Y.Z] – Datum
    python3 .github/blueprint/release.py github-release [--sha SHA] [--nachtragen]
                                                              (nur in GitHub Actions) Tag + Release anlegen

«set» nur nach ausdrücklicher Freigabe durch die/den Projektverantwortliche:n. Tag und Release legt danach der
Workflow release.yml an. Bei einer finalen Version führt «set» auch die Tabelle «Unterstützte Versionen» in
SECURITY.md nach (zwischen den Markierungen <!-- blueprint:versionen -->).

Release-Dateien ([release_dateien] artefakte, z. B. Installer einer Desktop-Anwendung): Die Workflows aus
release_nach laden sie mit actions/upload-artifact hoch; «github-release» holt die passenden Artefakte dieses Commits,
legt SHA256SUMS.txt dazu, prüft sie auf Wunsch bei VirusTotal (Fund → kein Release) und hängt alles ans Release.
Mit versionierung.vorabversionen_aufraeumen = true werden nach einer finalen Version die Release-Einträge ihrer
Vorabversionen entfernt (Tags bleiben).
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))   # release_checks, cleanup
CONFIG = ROOT / ".github" / "blueprint.toml"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z.-]+)?$")
UNRELEASED = "## [Unveröffentlicht]"
SEC_START, SEC_END = "<!-- blueprint:versionen -->", "<!-- /blueprint:versionen -->"


def config() -> dict:
    with open(CONFIG, "rb") as fh:
        return tomllib.load(fh)


def version_file(cfg: dict, root: Path = ROOT) -> Path:
    return root / cfg.get("versionierung", {}).get("datei", "VERSION")


# --- Versionsdatei lesen/schreiben ----------------------------------------------------------------------------

def _patterns(name: str) -> list[re.Pattern]:
    if name.endswith(".py"):
        return [re.compile(r'^(VERSION\s*=\s*["\'])([^"\']+)(["\'])', re.M), re.compile(r'^(__version__\s*=\s*["\'])([^"\']+)(["\'])', re.M)]
    if name.endswith(".toml"):
        return [re.compile(r'^(version\s*=\s*")([^"]+)(")', re.M)]
    return []


def read_version(cfg: dict, root: Path = ROOT) -> str:
    path = version_file(cfg, root)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return str(json.loads(text).get("version", ""))
    for pattern in _patterns(path.name):
        m = pattern.search(text)
        if m:
            return m.group(2)
    return text.strip()


def write_version(cfg: dict, version: str) -> None:
    path = version_file(cfg)
    if path.suffix == ".json":
        text = path.read_text(encoding="utf-8")
        new, n = re.subn(r'("version"\s*:\s*")[^"]*(")', lambda m: m.group(1) + version + m.group(2), text, count=1)
        if n != 1:
            raise ValueError(f"{path.name}: kein Feld «version» gefunden.")
        path.write_text(new, encoding="utf-8")
        return
    for pattern in _patterns(path.name):
        text = path.read_text(encoding="utf-8")
        new, n = pattern.subn(lambda m: m.group(1) + version + m.group(3), text, count=1)
        if n == 1:
            path.write_text(new, encoding="utf-8")
            return
    if _patterns(path.name):
        raise ValueError(f"{path.name}: keine Versionszeile gefunden.")
    path.write_text(version + "\n", encoding="utf-8")


# --- SemVer und CHANGELOG ------------------------------------------------------------------------------------

def key(v: str):
    m = SEMVER.match(v or "")
    if not m:
        raise ValueError(f"«{v}» ist keine gültige Version (MAJOR.MINOR.PATCH).")
    pre = m.group(4)
    ids = tuple((0, int(x), "") if x.isdigit() else (1, 0, x) for x in pre.lstrip("-").split(".")) if pre else ()
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if pre else 1, ids)


def changelog() -> str:
    path = ROOT / "CHANGELOG.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def unreleased_text(text: str) -> str:
    start = text.find(UNRELEASED)
    if start < 0:
        return ""
    rest = text[start + len(UNRELEASED):]
    m = re.search(r"^## \[", rest, re.M)
    return rest[: m.start() if m else len(rest)].strip()


def notes(text: str, version: str) -> str:
    m = re.search(r"^## \[" + re.escape(version) + r"\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def planned(version: str, text: str) -> str:
    m = SEMVER.match(version or "")
    if not m:
        return version
    if m.group(4):
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    titles = {t.strip() for t in re.findall(r"^### (.+)$", unreleased_text(text), re.M)}
    if titles and titles <= {"Behoben"}:
        return f"{m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}"
    return f"{m.group(1)}.{int(m.group(2)) + 1}.0"


# --- Git -----------------------------------------------------------------------------------------------------

def git(*args: str) -> str | None:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def plugin_version(v: str) -> str | None:
    if re.fullmatch(r"\d+\.\d+", v or ""):
        v += ".0"
    return v if SEMVER.match(v or "") else None


def check(cfg: dict) -> list[str]:
    errors = []
    version = read_version(cfg)
    text = changelog()
    if not SEMVER.match(version):
        errors.append(f"{version_file(cfg).name}: «{version}» ist keine gültige Version.")
    if UNRELEASED not in text:
        errors.append("CHANGELOG.md: Abschnitt «## [Unveröffentlicht]» fehlt.")
    elif SEMVER.match(version) and "-" not in version and f"## [{version}]" not in text and git("tag", "-l", "v[0-9]*"):
        errors.append(f"CHANGELOG.md: Abschnitt für Version {version} fehlt.")
    patterns = cfg.get("versionierung", {}).get("plugin_manifeste", [])
    patterns = [patterns] if isinstance(patterns, str) else list(patterns)
    patterns = [p for p in patterns if p]
    if patterns:
        tag = git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
        changed = set((git("diff", "--name-only", tag, "HEAD") or "").splitlines()) if tag else set()
        manifests = sorted({m for p in patterns for m in glob.glob(str(ROOT / p))})
        for manifest in manifests:
            rel = os.path.relpath(manifest, ROOT)
            folder = os.path.dirname(rel)
            current = plugin_version(str(json.loads(Path(manifest).read_text(encoding="utf-8")).get("version", "")))
            if current is None:
                errors.append(f"{rel}: «version» fehlt oder ist ungültig (z. B. 1.0 oder 1.0.1).")
                continue
            if tag and any(f.startswith(folder + "/") for f in changed):
                old = git("show", f"{tag}:{rel}")
                before = plugin_version(str(json.loads(old).get("version", ""))) if old else None
                if before and key(current) <= key(before):
                    errors.append(f"{rel}: geändert seit {tag}, aber «version» ist noch {current} – bitte erhöhen.")
    return errors


def security_table(version: str) -> str:
    """Tabelle «Unterstützte Versionen»: die aktuelle Minor-Reihe wird unterstützt, ältere nicht."""
    m = SEMVER.match(version)
    line = f"{m.group(1)}.{m.group(2)}"
    return (f"{SEC_START}\n| Version | Unterstützt |\n| ------- | ----------- |\n| {line + '.x':<7} | ✅          |\n"
            f"| {'< ' + line:<7} | ❌          |\n{SEC_END}")


def update_security(version: str) -> bool:
    path = ROOT / "SECURITY.md"
    if "-" in version or not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if SEC_START not in text or SEC_END not in text:
        return False
    new = re.sub(re.escape(SEC_START) + r".*?" + re.escape(SEC_END), lambda _m: security_table(version), text, flags=re.S)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def set_version(cfg: dict, version: str, commit: bool) -> None:
    if not SEMVER.match(version):
        raise ValueError(f"«{version}» ist keine gültige Version (z. B. 0.2.0).")
    current = read_version(cfg)
    if SEMVER.match(current or "") and key(version) <= key(current):
        raise ValueError(f"Die neue Version muss grösser sein als die aktuelle ({current}).")
    text = changelog()
    if f"## [{version}]" in text:
        raise ValueError(f"Version {version} steht schon im CHANGELOG.")
    if not unreleased_text(text):
        raise ValueError("Unter «Unveröffentlicht» stehen keine Änderungen – nichts zu veröffentlichen.")
    if "-" not in version:
        today = datetime.date.today().isoformat()
        (ROOT / "CHANGELOG.md").write_text(text.replace(UNRELEASED, f"{UNRELEASED}\n\n## [{version}] – {today}", 1), encoding="utf-8")
    write_version(cfg, version)
    print(f"✓ {version_file(cfg).name}: {current} → {version}")
    files = [str(version_file(cfg).relative_to(ROOT)), "CHANGELOG.md"]
    if update_security(version):
        files.append("SECURITY.md")
        print(f"✓ SECURITY.md: unterstützte Versionen ab {version.rsplit('.', 1)[0]}.x")
    if commit:
        if git("add", *files) is None or git("commit", "-q", "-m", f"Version {version}") is None:
            raise RuntimeError("git commit fehlgeschlagen.")
        print(f"✓ Commit «Version {version}» – jetzt pushen; Tag und Release legt der Workflow «release» an.")


# --- GitHub Actions: Tag + Release ---------------------------------------------------------------------------

def gh(*args: str, check_ok: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check_ok and r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} …: {r.stderr.strip()}")
    return r


def tag_exists(repo: str, tag: str) -> bool:
    return gh("api", f"repos/{repo}/git/ref/tags/{tag}", "--silent", check_ok=False).returncode == 0


def wait_for(repo: str, sha: str, workflows: list[str], minutes: int = 45, grace: int = 5) -> list[int] | None:
    """Wartet, bis die genannten Workflows für diesen Commit fertig sind → IDs der grünen Läufe. None = kein Release
    jetzt (Workflow nicht grün oder für diesen Commit gar nicht gelaufen, z. B. reine Doku-Änderung)."""
    start = time.time()
    ids: list[int] = []
    for name in workflows:
        while True:
            r = gh("api", f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50", "--jq",
                   f'[.workflow_runs[] | select(.name == "{name}")][0] | "\\(.status) \\(.conclusion) \\(.id)"', check_ok=False)
            state, _, run_id = r.stdout.strip().rpartition(" ")
            if state.startswith("completed"):
                if state != "completed success":
                    print(f"::notice title=Kein Release::Workflow «{name}» für {sha[:7]} ist nicht grün ({state}). Das Release entsteht beim nächsten grünen Push.")
                    return None
                print(f"✓ {name} grün")
                ids.append(int(run_id))
                break
            if state in ("", "null", "null null") and time.time() - start > grace * 60:
                print(f"::notice title=Kein Release::Workflow «{name}» lief für {sha[:7]} nicht. Das Release entsteht beim nächsten Push mit «{name}» oder von Hand (Run workflow).")
                return None
            if time.time() - start > minutes * 60:
                print(f"::warning title=Kein Release::Workflow «{name}» für {sha[:7]} nicht rechtzeitig fertig.")
                return None
            time.sleep(20)
    return ids


def release_files(cfg: dict, run_ids: list[int], folder: Path) -> tuple[list[Path], str]:
    """Artefakte der grünen Läufe holen, prüfen → (Dateien fürs Release, Zusatztext für die Versionshinweise)."""
    rd = cfg.get("release_dateien", {})
    patterns = [p for p in rd.get("artefakte", []) if p]
    if not patterns:
        return [], ""
    if not run_ids:
        raise RuntimeError("[release_dateien] artefakte gesetzt, aber versionierung.release_nach nennt keinen Workflow, der sie hochlädt.")
    raw = folder / "_artefakte"
    for run_id in run_ids:
        for pattern in patterns:
            gh("run", "download", str(run_id), "-p", pattern, "-D", str(raw), check_ok=False)
    files: list[Path] = []
    for f in sorted(p for p in raw.rglob("*") if p.is_file()) if raw.exists() else []:
        target = folder / f.name
        if target.exists():
            raise RuntimeError(f"Release-Datei {f.name} kommt mehrfach vor – Namen in den Artefakten eindeutig machen.")
        shutil.move(str(f), target)
        files.append(target)
    if not files:
        raise RuntimeError(f"Keine Artefakte zu {', '.join(patterns)} in den Läufen {', '.join(map(str, run_ids))} – kein Release.")
    import release_checks  # noqa: E402  (Prüfsummen, VirusTotal)
    extra = []
    if rd.get("virustotal", False):
        key = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
        if not key or key == "NOCH-NICHT-GESETZT":                  # Platzhalter aus advanced.py
            print("::notice title=VirusTotal::Kein Secret VIRUSTOTAL_API_KEY – Prüfung übersprungen")
        else:
            results = [release_checks.scan(str(f), key) for f in files]
            bad = [r for r in results if release_checks.flagged(r["stats"])]
            for r in bad:
                print(f"::error title=VirusTotal::{r['name']}: {release_checks.flagged(r['stats'])} Scanner melden etwas ({r['link']})")
            if bad:
                raise RuntimeError("VirusTotal meldet Funde – Release angehalten. Prüfen, danach von Hand «release» starten.")
            extra.append(release_checks.report_md(results).strip())
    if rd.get("pruefsummen", True):
        release_checks.write_sums(str(folder))
        files.append(folder / release_checks.SUMS)
        extra.append(f"Prüfsummen: `{release_checks.SUMS}` (prüfen mit `sha256sum -c {release_checks.SUMS}`).")
    print(f"✓ {len(files)} Release-Datei(en): {', '.join(f.name for f in files)}")
    return files, "\n\n".join(e for e in extra if e)


def title(cfg: dict, version: str) -> str:
    return cfg.get("versionierung", {}).get("release_titel", "{kurz} {version}").format(
        kurz=cfg.get("projekt", {}).get("kurz", "Version"), name=cfg.get("projekt", {}).get("name", ""), version=version)


def github_release(cfg: dict, sha: str, backfill: bool) -> None:
    repo = os.environ["GH_REPO"]
    text = changelog()
    if backfill:
        rel = cfg.get("versionierung", {}).get("nachtragen_datei", "")
        lines = [l.split() for l in (ROOT / rel).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")] if rel else []
        # Der GITHUB_TOKEN darf keine Tags auf alte Commits setzen, deren Workflow-Dateien abweichen
        # («Resource not accessible by integration»). Tags darum vorher lokal setzen und pushen:
        #   grep -v '^#' DATEI | while read v s; do git tag "v$v" "$s"; done; git push origin --tags
        # Hier werden nur die Releases zu vorhandenen Tags angelegt.
        for i, (version, commit) in enumerate(lines):
            if gh("release", "view", f"v{version}", check_ok=False).returncode == 0:
                print(f"Release v{version} gibt es schon")
                continue
            if not tag_exists(repo, f"v{version}"):
                print(f"::warning title=Tag fehlt::v{version} – zuerst lokal setzen und pushen (siehe docs/GITHUB-ABLAUF.md)")
                continue
            body = (notes(text, version) or "–") + "\n\n---\n_Rückwirkend angelegt._\n"
            gh("release", "create", f"v{version}", "--verify-tag", "--title", title(cfg, version), "--notes", body,
               f"--latest={'true' if i == len(lines) - 1 else 'false'}")
            print(f"✓ Release v{version} ({commit[:7]})")
        return
    version = read_version(cfg)
    if not SEMVER.match(version):
        raise ValueError(f"Ungültige Version «{version}».")
    if tag_exists(repo, f"v{version}"):
        print(f"Tag v{version} gibt es schon – Developer Release, kein neues Release.")
        return
    if "-" not in version and f"## [{version}]" not in text:
        print(f"Version {version} hat noch keinen Abschnitt im CHANGELOG – noch nicht freigegeben, kein Release.")
        return
    if cfg.get("versionierung", {}).get("nachtragen_datei") and not git("tag", "-l", "v[0-9]*"):
        print("::notice title=Noch keine Versions-Tags::Zuerst von Hand «release» mit «nachtragen» starten.")
        return
    run_ids = wait_for(repo, sha, list(cfg.get("versionierung", {}).get("release_nach", [])))
    if run_ids is None:
        return
    errors = check(cfg)
    if errors:
        raise RuntimeError("Prüfung fehlgeschlagen: " + "; ".join(errors))
    with tempfile.TemporaryDirectory() as tmp:
        files, extra = release_files(cfg, run_ids, Path(tmp))
        body = notes(text, version) or unreleased_text(text) or "–"
        if extra:
            body += "\n\n---\n\n" + extra
        args = ["release", "create", f"v{version}", "--target", sha, "--title", title(cfg, version), "--notes", body]
        if "-" in version:
            args.append("--prerelease")
        gh(*args, *map(str, files))
    print(f"::notice title=Release angelegt::Tag v{version} und «{title(cfg, version)}» auf {sha[:7]}")
    if "-" not in version and cfg.get("versionierung", {}).get("vorabversionen_aufraeumen", False):
        import cleanup  # noqa: E402  (liegt neben diesem Skript)
        try:
            cleanup.betas(dry=False)
        except RuntimeError as e:
            print(f"::warning title=Vorabversionen::nicht aufgeräumt ({e})")


def main(argv: list[str]) -> int:
    cfg = config()
    cmd = argv[0] if argv else "--help"
    try:
        if cmd == "version":
            print(read_version(cfg))
        elif cmd == "planned":
            print(planned(read_version(cfg), changelog()))
        elif cmd == "notes":
            version = argv[1] if len(argv) > 1 else read_version(cfg)
            print(notes(changelog(), version) or unreleased_text(changelog()))
        elif cmd == "check":
            errors = check(cfg)
            for e in errors:
                print(f"✗ {e}", file=sys.stderr)
            if errors:
                return 1
            print(f"✓ Version {read_version(cfg)} – CHANGELOG und Manifeste passen.")
        elif cmd == "set" and len(argv) > 1:
            set_version(cfg, argv[1], "--commit" in argv)
        elif cmd == "github-release":
            sha = argv[argv.index("--sha") + 1] if "--sha" in argv else (git("rev-parse", "HEAD") or "")
            github_release(cfg, sha, "--nachtragen" in argv)
        else:
            print(__doc__)
            return 0 if cmd in ("--help", "-h") else 1
    except (ValueError, RuntimeError, OSError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
