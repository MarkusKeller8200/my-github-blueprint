#!/usr/bin/env python3
"""Fremdkomponenten auf Änderungen prüfen (aus TagStudio) – läuft monatlich im Workflow «Fremdkomponenten prüfen».

    python3 .github/blueprint/third_party.py                    prüfen, Bericht ausgeben, Issue anlegen/aktualisieren
    python3 .github/blueprint/third_party.py --probelauf        nur Bericht, kein Issue
    python3 .github/blueprint/third_party.py --erfassen [--probelauf]
                                                                direkte Abhängigkeiten aus package.json, composer.json,
                                                                requirements*.txt, pyproject.toml, *.csproj, Cargo.toml
                                                                in die Liste aufnehmen (nur neue Einträge)
    python3 .github/blueprint/third_party.py --apply neu.json   geprüfte Stände aus dem Issue übernehmen

Konfiguration: [fremdkomponenten] in .github/blueprint.toml (aktiv, datei, label). Die Liste (Standard
docs/third-party.json) führt alle fremden Bibliotheken, Werkzeuge, Dienste und Vorlagen mit Lizenz – Grundlage für
eine Lizenzübersicht in der Anwendung bzw. Doku. Für jeden Eintrag mit «check» wird der aktuelle Stand geholt:
pypi, npm, packagist (Composer), nuget, crates (Rust) oder github (neueste Release-Version, sonst letzter Push)
und mit «checked» verglichen. Einträge mit «repo» (GitHub) bekommen Vertrauenssignale (Sterne, letzter Push,
archiviert). Abweichungen kommen in ein einziges Issue «Fremdkomponenten: Änderungen prüfen», das aktualisiert statt
doppelt angelegt wird; im Issue steht ein JSON-Block mit den neuen Ständen zum Übernehmen mit --apply.
Nur Standardbibliothek.
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".github" / "blueprint.toml"
API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
MARK = "<!-- third-party-check -->"
TITLE = "Fremdkomponenten: Änderungen prüfen"
UA = "github-blueprint-third-party-check"
GROUPS = {
    "app": "Dieses Projekt",
    "laufzeit": "Im Programm bzw. auf dem Server enthalten",
    "plugin": "Von Plugins bzw. Modulen bei Bedarf installiert",
    "entwicklung": "Bau, Tests und Entwicklung (nicht ausgeliefert)",
    "extern": "Externe Programme (von den Nutzer:innen installiert)",
    "dienst": "Online-Dienste",
    "vorlage": "Vorlagen, Formatbeschreibungen und Texte",
}


def settings() -> dict:
    try:
        with open(CONFIG, "rb") as fh:
            return tomllib.load(fh).get("fremdkomponenten", {})
    except OSError:
        return {}


def data_path() -> Path:
    return ROOT / settings().get("datei", "docs/third-party.json")


def _get(url: str, gh: bool = False, raw: bool = False):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if gh:
        h["Accept"] = "application/vnd.github+json"
        if TOKEN:
            h["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        body = r.read()
        return body if raw else json.loads(body or b"null")


def _pypi_license(info: dict) -> str:
    lic = (info.get("license_expression") or "").strip()
    if lic:
        return lic
    raw = (info.get("license") or "").strip()
    if raw and len(raw) <= 60 and "\n" not in raw:
        return raw
    cls = [c.split("::")[-1].strip() for c in info.get("classifiers") or [] if c.startswith("License ::")]
    return ", ".join(cls) or ("siehe Projekt" if raw else "")


def current(check: dict) -> dict:
    """Aktueller Stand einer Komponente: {"version", "license"} (Fehler → {"error"})."""
    q = urllib.parse.quote
    try:
        t = check.get("type")
        if t == "pypi":
            info = _get(f"https://pypi.org/pypi/{q(check['package'])}/json")["info"]
            return {"version": info.get("version") or "", "license": _pypi_license(info)}
        if t == "npm":
            j = _get(f"https://registry.npmjs.org/{q(check['package'], safe='@/')}/latest")
            lic = j.get("license")
            return {"version": j.get("version") or "", "license": lic.get("type", "") if isinstance(lic, dict) else (lic or "")}
        if t == "packagist":
            pkg = _get(f"https://repo.packagist.org/p2/{check['package']}.json")["packages"][check["package"]]
            stable = [p for p in pkg if not re.search(r"(dev|alpha|beta|rc)", p.get("version", ""), re.I)] or pkg
            lic = next((p["license"] for p in stable if p.get("license")), pkg[0].get("license") or [])   # p2: Felder vererbt
            return {"version": stable[0].get("version", "").lstrip("v"), "license": ", ".join(lic)}
        if t == "nuget":
            pid = check["package"].lower()
            versions = [v for v in _get(f"https://api.nuget.org/v3-flatcontainer/{pid}/index.json")["versions"] if "-" not in v]
            ver = versions[-1] if versions else ""
            lic = ""
            if ver:
                spec = ET.fromstring(_get(f"https://api.nuget.org/v3-flatcontainer/{pid}/{ver}/{pid}.nuspec", raw=True))
                el = next((e for e in spec.iter() if e.tag.endswith("license")), None)
                lic = (el.text or "").strip() if el is not None else ""
            return {"version": ver, "license": lic}
        if t == "crates":
            c = _get(f"https://crates.io/api/v1/crates/{q(check['package'])}")
            ver = c["crate"].get("max_stable_version") or c["crate"].get("max_version") or ""
            lic = next((v.get("license") or "" for v in c.get("versions", []) if v.get("num") == ver), "")
            return {"version": ver, "license": lic}
        if t == "github":
            repo = _get(f"{API}/repos/{check['repo']}", gh=True)
            lic = ((repo.get("license") or {}).get("spdx_id") or "").replace("NOASSERTION", "eigene")
            try:
                ver = _get(f"{API}/repos/{check['repo']}/releases/latest", gh=True).get("tag_name") or ""
            except urllib.error.HTTPError:
                ver = ""
            return {"version": ver or "Stand " + (repo.get("pushed_at") or "")[:10], "license": lic}
    except Exception as ex:  # noqa: BLE001 – ein Fehler betrifft nur diesen Eintrag
        return {"error": f"{type(ex).__name__}: {ex}"}
    return {"error": f"unbekannte Prüfart {check.get('type')}"}


def repo_info(repo: str, today: str = "") -> dict:
    j = _get(f"{API}/repos/{repo}", gh=True)
    return {"stars": j.get("stargazers_count") or 0, "archived": bool(j.get("archived")),
            "pushed": (j.get("pushed_at") or "")[:10], "full_name": j.get("full_name") or repo,
            "license": ((j.get("license") or {}).get("spdx_id") or "").replace("NOASSERTION", "eigene"),
            "date": today or datetime.date.today().isoformat()}


def collect_repo_info(items: list, fetch=repo_info, today: str = "") -> dict:
    out = {}
    for it in items:
        if it.get("repo"):
            try:
                out[it["id"]] = fetch(it["repo"], today)
            except Exception as ex:  # noqa: BLE001
                out[it["id"]] = {"error": f"{type(ex).__name__}: {ex}"}
    return out


def repo_warnings(items: list, infos: dict, today: str) -> list:
    """Hinweise zur Vertrauenswürdigkeit: archiviert, seit über 2 Jahren still, umbenannt, nicht erreichbar."""
    out = []
    t = datetime.date.fromisoformat(today)
    for it in items:
        inf = infos.get(it["id"])
        if not inf:
            continue
        if inf.get("error"):
            out.append((it, "Repository nicht abrufbar: " + inf["error"]))
            continue
        if inf.get("archived"):
            out.append((it, "archiviert (wird nicht mehr gepflegt)"))
        if inf.get("pushed"):
            try:
                if (t - datetime.date.fromisoformat(inf["pushed"])).days > 730:
                    out.append((it, f"seit {inf['pushed']} keine Änderungen"))
            except ValueError:
                pass
        if inf.get("full_name") and inf["full_name"].lower() != it["repo"].lower():
            out.append((it, f"umbenannt/verschoben nach {inf['full_name']}"))
    return out


def compare(items: list, fetch=current) -> list:
    out = []
    for it in items:
        chk = it.get("check")
        if not chk:
            continue
        new, old, what = fetch(chk), it.get("checked") or {}, []
        if new.get("error"):
            what.append("Fehler beim Abruf: " + new["error"])
        elif not old:
            what.append("noch nie geprüft")
        else:
            if old.get("version") != new.get("version"):
                what.append(f"Version {old.get('version') or '–'} → {new.get('version') or '–'}")
            if (old.get("license") or "") != (new.get("license") or ""):
                what.append(f"Lizenzangabe «{old.get('license') or '–'}» → «{new.get('license') or '–'}»")
        if what:
            out.append({"id": it["id"], "name": it["name"], "old": old, "new": new, "what": what,
                        "license": it.get("license", ""), "url": it.get("url", "")})
    return out


def report(changes: list, today: str, rel: str, infos: dict | None = None, warnings=()) -> str:
    lines = [MARK, f"Monatliche Prüfung der Fremdkomponenten vom {today} (Liste: `{rel}`).", ""]
    if warnings:
        lines += ["**Repositorys – bitte ansehen:**", ""] + \
                 [f"- [{it['name']}](https://github.com/{it['repo']}): {w}" for it, w in warnings] + [""]
    good = {k: v for k, v in (infos or {}).items() if not v.get("error")}
    if not changes:
        lines.append("Keine Änderungen.")
        if good:
            lines += ["", "<details><summary>Vertrauenssignale der Repositorys (JSON, mit --apply übernehmen)</summary>", "",
                      "```json", json.dumps({"_repo_info": good}, ensure_ascii=False, indent=1), "```", "</details>"]
        return "\n".join(lines)
    lines += ["Bitte prüfen: Passt die Lizenz weiterhin (auch für die Weitergabe im Installer bzw. auf dem Server)? "
              "Gibt es sicherheitsrelevante Änderungen? Muss die Lizenzübersicht angepasst werden?", "",
              "| Komponente | Änderung | Lizenz laut Liste |", "|---|---|---|"]
    for c in changes:
        lines.append(f"| [{c['name']}]({c['url']}) | {'; '.join(c['what'])} | {c['license']} |")
    upd = {c["id"]: {"version": c["new"].get("version", ""), "license": c["new"].get("license", ""), "date": today}
           for c in changes if not c["new"].get("error")}
    if good:
        upd["_repo_info"] = good
    lines += ["", f"- [ ] Änderungen geprüft, Lizenzangaben in `{rel}` bei Bedarf angepasst",
              "- [ ] Neue Stände übernommen: JSON unten speichern und "
              "`python3 .github/blueprint/third_party.py --apply datei.json` ausführen, committen", "",
              "<details><summary>Neue Stände (JSON)</summary>", "", "```json", json.dumps(upd, ensure_ascii=False, indent=1),
              "```", "</details>"]
    return "\n".join(lines)


def dump(data: dict) -> str:
    """Eine Zeile je Eintrag (gut lesbare Diffs)."""
    head = {k: v for k, v in data.items() if k != "items"}
    body = ",\n".join("    " + json.dumps(it, ensure_ascii=False) for it in data["items"])
    lines = json.dumps(head, ensure_ascii=False, indent=2).rstrip("}").rstrip()
    return f'{lines},\n  "items": [\n{body}\n  ]\n}}\n'


def empty(name: str = "", repo: str = "", license_: str = "") -> dict:
    items = [{"id": "app", "group": "app", "name": name or "Dieses Projekt", "use": "Dieses Projekt",
              "license": license_ or "–", "url": f"https://github.com/{repo}" if repo else ""}]
    return {"format": 1, "note": "Fremde Bibliotheken, Werkzeuge, Dienste und Vorlagen mit Lizenz. Wird monatlich vom "
            "Workflow «Fremdkomponenten prüfen» (.github/blueprint/third_party.py) verglichen; Änderungen kommen als Issue. "
            "Nach der Prüfung «checked» nachführen (--apply).", "groups": GROUPS, "items": items}


def apply(path_new: str, path: Path) -> int:
    upd = json.loads(Path(path_new).read_text(encoding="utf-8"))
    data = json.loads(path.read_text(encoding="utf-8"))
    infos, n = upd.pop("_repo_info", {}) or {}, 0
    for it in data["items"]:
        if it["id"] in upd:
            it["checked"] = upd[it["id"]]
            n += 1
        if it["id"] in infos and not infos[it["id"]].get("error"):
            it["repo_info"] = infos[it["id"]]
            n += 1
    path.write_text(dump(data), encoding="utf-8")
    return n


# --- Abhängigkeiten aus den Manifesten erfassen ---------------------------------------------------------------

def _req_name(line: str) -> str:
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith(("-", "git+", "http")):
        return ""
    return re.split(r"[\s<>=!~;\[@]", line, maxsplit=1)[0]


def manifest_deps(root: Path) -> list[dict]:
    """Direkte Abhängigkeiten → [{id, name, group, check}] (Laufzeit bzw. Entwicklung)."""
    found = []

    def add(kind: str, name: str, dev: bool):
        if name:
            found.append({"id": f"{kind}:{name}".lower(), "name": name, "group": "entwicklung" if dev else "laufzeit",
                          "check": {"type": kind, "package": name}})

    pkg = root / "package.json"
    if pkg.exists():
        j = json.loads(pkg.read_text(encoding="utf-8"))
        for sec, dev in (("dependencies", False), ("devDependencies", True), ("optionalDependencies", False)):
            for n in j.get(sec, {}):
                add("npm", n, dev)
    comp = root / "composer.json"
    if comp.exists():
        j = json.loads(comp.read_text(encoding="utf-8"))
        for sec, dev in (("require", False), ("require-dev", True)):
            for n in j.get(sec, {}):
                if "/" in n:                                          # ohne php, ext-*, lib-*
                    add("packagist", n, dev)
    for req in sorted(root.glob("requirements*.txt")):
        dev = any(x in req.name for x in ("dev", "test", "lint"))
        for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
            add("pypi", _req_name(line), dev)
    pyp = root / "pyproject.toml"
    if pyp.exists():
        t = tomllib.loads(pyp.read_text(encoding="utf-8"))
        for d in t.get("project", {}).get("dependencies", []):
            add("pypi", _req_name(d), False)
        for group, deps in t.get("project", {}).get("optional-dependencies", {}).items():
            for d in deps:
                add("pypi", _req_name(d), group in ("dev", "test", "lint", "docs"))
        for group, deps in t.get("dependency-groups", {}).items():
            for d in deps:
                if isinstance(d, str):
                    add("pypi", _req_name(d), True)
    for proj in sorted(glob.glob(str(root / "**" / "*.csproj"), recursive=True)):
        try:
            for el in ET.parse(proj).getroot().iter():
                if el.tag.endswith("PackageReference") and el.get("Include"):
                    add("nuget", el.get("Include"), False)
        except ET.ParseError:
            pass
    cargo = root / "Cargo.toml"
    if cargo.exists():
        t = tomllib.loads(cargo.read_text(encoding="utf-8"))
        for sec, dev in (("dependencies", False), ("build-dependencies", True), ("dev-dependencies", True)):
            for n in t.get(sec, {}):
                add("crates", n, dev)
    unique = {}
    for d in found:
        unique.setdefault(d["id"], d)
    return list(unique.values())


def capture(path: Path, dry: bool) -> int:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else empty(repo=REPO)
    have = {it["id"] for it in data["items"]}
    known = {(it.get("check") or {}).get("type", "") + ":" + (it.get("check") or {}).get("package", "").lower() for it in data["items"]}
    new = [d for d in manifest_deps(ROOT) if d["id"] not in have and d["id"] not in known]
    for d in new:
        print(f"{'(Probelauf) ' if dry else ''}neu: {d['name']} ({d['check']['type']}, {GROUPS[d['group']]})")
        data["items"].append({"id": d["id"], "group": d["group"], "name": d["name"], "use": "", "license": "", "url": "",
                              "check": d["check"]})
    if new and not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump(data), encoding="utf-8")
    print(f"{len(new)} neue Einträge" + (" – «use», «license» und «url» bitte ergänzen" if new else ""))
    return 0


# --- Issue -----------------------------------------------------------------------------------------------------

def gh(method: str, path: str, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                                          "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            return json.loads(data) if data else None
    except urllib.error.HTTPError as ex:
        print(f"::warning::GitHub-API {method} {path}: {ex.code} {ex.read()[:300]!r}")
        return None


def publish(text: str, changed: bool, label: str) -> None:
    issues = gh("GET", f"/repos/{REPO}/issues?state=open&labels={urllib.parse.quote(label)}&per_page=100") or []
    cur = next((i for i in issues if MARK in (i.get("body") or "")), None)
    if cur:
        gh("PATCH", f"/repos/{REPO}/issues/{cur['number']}", {"body": text})
        if changed:
            gh("POST", f"/repos/{REPO}/issues/{cur['number']}/comments", {"body": "Neue Prüfung – Liste oben aktualisiert."})
        print(f"Issue #{cur['number']} aktualisiert.")
    elif changed:
        r = gh("POST", f"/repos/{REPO}/issues", {"title": TITLE, "body": text, "labels": [label]})
        print(f"Issue #{r and r.get('number')} angelegt.")


def main(argv: list[str]) -> int:
    path, conf = data_path(), settings()
    rel = os.path.relpath(path, ROOT)
    dry = "--probelauf" in argv or "--dry-run" in argv
    if argv[:1] == ["--apply"] and len(argv) > 1:
        print(f"{apply(argv[1], path)} Einträge übernommen.")
        return 0
    if "--erfassen" in argv:
        return capture(path, dry)
    if os.environ.get("GITHUB_ACTIONS") and not conf.get("aktiv", False):
        print("::notice title=Fremdkomponenten::[fremdkomponenten] aktiv = false – nichts zu tun")
        return 0
    if not path.exists():
        print(f"::warning title=Fremdkomponenten::{rel} fehlt – mit «third_party.py --erfassen» anlegen")
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()
    changes = compare(data["items"])
    infos = collect_repo_info(data["items"], today=today) if TOKEN else {}
    warns = repo_warnings(data["items"], infos, today)
    # schon bekannte Hinweise (aus den gespeicherten repo_info) lösen keine neue Meldung aus
    known = {(it["id"], w) for it, w in repo_warnings(data["items"], {i["id"]: i["repo_info"] for i in data["items"]
                                                                       if i.get("repo_info")}, today)}
    new_warns = [(it, w) for it, w in warns if (it["id"], w) not in known]
    text = report(changes, today, rel, infos, warns)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text.replace(MARK, "") + "\n")
    if not dry and REPO and TOKEN:
        publish(text, bool(changes or new_warns), conf.get("label", "abhaengigkeiten"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
