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
Workflow release.yml an.
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".github" / "blueprint.toml"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z.-]+)?$")
UNRELEASED = "## [Unveröffentlicht]"


def config() -> dict:
    with open(CONFIG, "rb") as fh:
        return tomllib.load(fh)


def version_file(cfg: dict) -> Path:
    return ROOT / cfg.get("versionierung", {}).get("datei", "VERSION")


# --- Versionsdatei lesen/schreiben ----------------------------------------------------------------------------

def _patterns(name: str) -> list[re.Pattern]:
    if name.endswith(".py"):
        return [re.compile(r'^(VERSION\s*=\s*["\'])([^"\']+)(["\'])', re.M), re.compile(r'^(__version__\s*=\s*["\'])([^"\']+)(["\'])', re.M)]
    if name.endswith(".toml"):
        return [re.compile(r'^(version\s*=\s*")([^"]+)(")', re.M)]
    return []


def read_version(cfg: dict) -> str:
    path = version_file(cfg)
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
    pattern = cfg.get("versionierung", {}).get("plugin_manifeste", "")
    if pattern:
        tag = git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
        changed = set((git("diff", "--name-only", tag, "HEAD") or "").splitlines()) if tag else set()
        for manifest in sorted(glob.glob(str(ROOT / pattern))):
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
    if commit:
        if git("add", str(version_file(cfg).relative_to(ROOT)), "CHANGELOG.md") is None or git("commit", "-q", "-m", f"Version {version}") is None:
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


def wait_for(repo: str, sha: str, workflows: list[str], minutes: int = 45) -> None:
    deadline = time.time() + minutes * 60
    for name in workflows:
        while True:
            r = gh("api", f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50", "--jq",
                   f'[.workflow_runs[] | select(.name == "{name}")][0] | "\\(.status) \\(.conclusion)"', check_ok=False)
            state = r.stdout.strip()
            if state.startswith("completed"):
                if state != "completed success":
                    raise RuntimeError(f"Workflow «{name}» für {sha[:7]} ist nicht grün ({state}) – kein Release.")
                print(f"✓ {name} grün")
                break
            if time.time() > deadline:
                raise RuntimeError(f"Workflow «{name}» für {sha[:7]} nicht rechtzeitig fertig.")
            time.sleep(20)


def title(cfg: dict, version: str) -> str:
    return cfg.get("versionierung", {}).get("release_titel", "{kurz} {version}").format(
        kurz=cfg.get("projekt", {}).get("kurz", "Version"), name=cfg.get("projekt", {}).get("name", ""), version=version)


def github_release(cfg: dict, sha: str, backfill: bool) -> None:
    repo = os.environ["GH_REPO"]
    text = changelog()
    if backfill:
        rel = cfg.get("versionierung", {}).get("nachtragen_datei", "")
        lines = [l.split() for l in (ROOT / rel).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")] if rel else []
        for i, (version, commit) in enumerate(lines):
            if tag_exists(repo, f"v{version}"):
                print(f"v{version} gibt es schon")
                continue
            body = (notes(text, version) or "–") + "\n\n---\n_Rückwirkend angelegt._\n"
            gh("release", "create", f"v{version}", "--target", commit, "--title", title(cfg, version), "--notes", body,
               f"--latest={'true' if i == len(lines) - 1 else 'false'}")
            print(f"✓ v{version} → {commit[:7]}")
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
    wait_for(repo, sha, list(cfg.get("versionierung", {}).get("release_nach", [])))
    errors = check(cfg)
    if errors:
        raise RuntimeError("Prüfung fehlgeschlagen: " + "; ".join(errors))
    body = notes(text, version) or unreleased_text(text) or "–"
    args = ["release", "create", f"v{version}", "--target", sha, "--title", title(cfg, version), "--notes", body]
    if "-" in version:
        args.append("--prerelease")
    gh(*args)
    print(f"::notice title=Release angelegt::Tag v{version} und «{title(cfg, version)}» auf {sha[:7]}")


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
