"""Selbsttests des GitHub-Blueprints (nur Standardbibliothek).

    python3 -m unittest discover -s .github/blueprint/tests -v

Kern ist der Ballast-Test: Ein Ziel-Repository – leer angelegt oder als Kopie über «Use this template» – enthält nach
start.py und apply.py nur, was das Projekt braucht. Jede Datei des Blueprints muss in manifest.toml stehen.
"""
from __future__ import annotations

import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

BP = Path(__file__).resolve().parents[1]           # .github/blueprint
SOURCE = BP.parents[1]
sys.path.insert(0, str(BP))
import manifest  # noqa: E402
import start  # noqa: E402

PY = sys.executable
GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.org", "-c", "init.defaultBranch=main"]

ANTWORTEN = {
    "web": {
        "name": "Test Web", "zweck": "Ein Intranet für Lehrpersonen.", "art": "web", "zielgruppe": ["öffentliche Organe"],
        "organ": "Kanton Zürich", "sichtbarkeit": "privat", "lizenz": "keine", "technik": ["PHP"],
        "hosting": "Webhosting (PHP, MySQL)", "auslieferung": ["Server"], "daten": "Personendaten", "schutzbedarf": "intern",
        "versionsdatei": "composer.json", "funktionen": ["Anmeldung"],
    },
    "desktop": {
        "name": "Test Desktop", "zweck": "Bilder verschlagworten.", "art": "desktop", "zielgruppe": ["Privatpersonen"],
        "sichtbarkeit": "privat", "lizenz": "keine", "technik": ["Python"], "betriebssysteme": ["Windows", "macOS"],
        "auslieferung": ["Installer (GitHub-Releases)"], "daten": "keine Personendaten", "schutzbedarf": "öffentlich",
        "sprachen": ["de-CH", "en"], "versionsdatei": "pyproject.toml", "abhaengigkeiten": "nur Standardbibliothek",
    },
    "beides": {
        "name": "Test Beides", "zweck": "Web-Oberfläche, auch als App.", "art": "beides", "zielgruppe": ["Unternehmen"],
        "sichtbarkeit": "privat", "lizenz": "keine", "technik": ["JavaScript / TypeScript"],
        "betriebssysteme": ["Windows", "macOS", "Linux"], "hosting": "eigener Server / VPS",
        "auslieferung": ["Server", "Installer (GitHub-Releases)"], "daten": "keine Personendaten",
        "schutzbedarf": "öffentlich", "versionsdatei": "package.json", "abhaengigkeiten": "frei",
    },
}


def toml_dump(data: dict) -> str:
    return "".join(f"{k} = {start.toml_value(v)}\n" for k, v in data.items())


def run(*args: str, cwd: Path = SOURCE, check: bool = True, **kw) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1")
    env.pop("GITHUB_ACTIONS", None)                 # apply.py soll auch Workflows anlegen
    env.pop("GITHUB_REPOSITORY", None)
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, **kw)
    if check and r.returncode != 0:
        raise AssertionError(f"{' '.join(args)} → {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


def snapshot(root: Path) -> dict[str, str]:
    return {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in manifest.files(root)}


def config(root: Path) -> dict:
    with open(root / ".github" / "blueprint.toml", "rb") as fh:
        return tomllib.load(fh)


class Grundlagen(unittest.TestCase):
    def test_manifest_vollstaendig(self):
        self.assertEqual(manifest.check_coverage(), [])

    def test_neue_datei_ohne_eintrag_faellt_auf(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "neu.txt").write_text("x", encoding="utf-8")
            problems = manifest.check_coverage(Path(tmp), [])
            self.assertTrue(any("neu.txt" in p for p in problems))

    def test_start_checkliste_aktuell(self):
        r = run(PY, str(BP / "start.py"), "--markdown")
        self.assertEqual(r.stdout, (SOURCE / "START-CHECKLISTE.md").read_text(encoding="utf-8"),
                         "START-CHECKLISTE.md neu erzeugen: python3 .github/blueprint/start.py --markdown > START-CHECKLISTE.md")

    def test_skripte_kompilieren(self):
        for f in BP.glob("*.py"):
            py_compile.compile(str(f), doraise=True)

    def test_vorlage_ist_gueltig_und_neutral(self):
        cfg = config(SOURCE)
        self.assertFalse(cfg["start"]["erledigt"], "Vorlage: [start] erledigt = false")
        self.assertEqual(cfg["workflows"]["admin_issue"], 0)
        self.assertEqual(cfg.get("variablen", []), [], "Deployment-Beispiele in der Vorlage nur auskommentiert (#5)")
        self.assertEqual(cfg.get("secrets", []), [])
        self.assertEqual(cfg.get("deploy_keys", []), [])
        self.assertEqual(cfg.get("umgebungen", []), [])

    def test_actions_ueberall_gleich_gepinnt(self):
        seen: dict[str, set[str]] = {}
        files = list((SOURCE / ".github" / "workflows").glob("*.yml")) + list((BP / "templates" / "workflows").glob("*.yml"))
        for f in files:
            for action, ref in re.findall(r"uses:\s*([\w.-]+/[\w./-]+)@([\w.-]+)", f.read_text(encoding="utf-8")):
                seen.setdefault(action, set()).add(ref)
        for action, refs in seen.items():
            self.assertEqual(len(refs), 1, f"{action} mit verschiedenen Ständen: {refs} (Vorlagen nachführen)")
            self.assertRegex(next(iter(refs)), r"^[0-9a-f]{40}$", f"{action} nicht auf einen Commit-SHA gepinnt (#9)")

    def test_vorlagen_ohne_unbekannte_platzhalter(self):
        sys.path.insert(0, str(BP))
        import apply  # noqa: E402
        ctx = apply.context(config(SOURCE), "owner/projekt", None)
        for f in (BP / "templates").rglob("*"):
            if f.is_file() and f.suffix in (".md", ".yml", ".json"):
                apply.render(f.read_text(encoding="utf-8"), ctx)       # KeyError bei unbekanntem Platzhalter


class Einzelteile(unittest.TestCase):
    def test_kommentare_bleiben_ausgerichtet(self):
        text = '[projekt]\nkurz = "Projekt"                            # kurzer Name\n'
        new = start.set_value(text, "projekt", "kurz", "TD")
        self.assertEqual(new.index("#"), text.index("#"), "Kommentar in derselben Spalte (#13)")
        long = start.set_value(text, "projekt", "kurz", "x" * 60)
        self.assertIn('" # kurzer Name', long)
        self.assertEqual(tomllib.loads(long)["projekt"]["kurz"], "x" * 60)

    def test_deployment_block(self):
        text = (SOURCE / ".github" / "blueprint.toml").read_text(encoding="utf-8")
        on = start.deployment(text, True)
        self.assertEqual([u["name"] for u in tomllib.loads(on)["umgebungen"]], ["test", "produktion"])
        self.assertEqual(start.deployment(on, False), text, "aus- und wieder einschalten ergibt die Vorlage")

    def test_milestone_admin_berechtigung(self):
        import milestone_admin as ma
        owner = {"author_association": "OWNER", "user": {"login": "chefin"}}
        member = {"author_association": "MEMBER", "user": {"login": "Anna"}}
        stranger = {"author_association": "NONE", "user": {"login": "anna"}}
        self.assertTrue(ma.authorized(owner, []), "Owner – auch bei Organisationen (#10)")
        self.assertFalse(ma.authorized(member, []))
        self.assertTrue(ma.authorized(member, ["anna"]))
        self.assertFalse(ma.authorized(stranger, ["anna"]), "eingetragen, aber nicht Mitglied")
        with self.assertRaisesRegex(ValueError, "Befehle"):
            ma.parse_command("/milestone foo")                 # Meldungen auf Deutsch (#14)

    def test_installer_plan(self):
        import ci_plan
        cfg = {"projekt": {"art": "desktop"}, "release_dateien": {"artefakte": ["installer-*"]},
               "versionierung": {"release_nach": ["installer"], "datei": "GIBT-ES-NICHT"}, "ci": {"python": "3.x"}}
        plan = ci_plan.plan_installer(cfg, {})
        self.assertEqual(plan.get("fehler"), "true", "ohne Bau-Befehl kein stilles Überspringen (#6)")
        cfg["installer"] = {"befehl": "make dist"}
        plan = ci_plan.plan_installer(cfg, {})
        self.assertEqual(plan["aktiv"], "true")
        self.assertEqual([x["artefakt"] for x in json.loads(plan["matrix"])["include"]], ["windows", "macos"])


class Ziel(unittest.TestCase):
    """Ein Ziel-Repository je Art: leer angelegt, Start-Checkliste, apply.py → nur, was das Projekt braucht."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projekt"
        self.root.mkdir()
        run(*GIT, "init", "-q", cwd=self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def start(self, art: str, extra: dict | None = None) -> None:
        answers = Path(self.tmp.name) / "antworten.toml"
        answers.write_text(toml_dump({**ANTWORTEN[art], **(extra or {})}), encoding="utf-8")
        run(PY, str(BP / "start.py"), "--ziel", str(self.root), "--antworten", str(answers))

    def apply(self, *extra: str, check: bool = True) -> subprocess.CompletedProcess:
        return run(PY, str(BP / "apply.py"), "--ziel", str(self.root), "--repo", "test/projekt", "--nur-dateien", *extra, check=check)

    def assert_schlank(self) -> None:
        cfg = config(self.root)
        self.assertEqual(manifest.ballast(self.root, cfg), [])
        entries = manifest.load()
        wanted = set(manifest.runtime_files(cfg))
        for n in manifest.files(self.root):
            hits = manifest.entry_for(n, entries)
            if hits and hits[0].get("nur_gleich") and not manifest._same(self.root / n, SOURCE / n):
                continue                                    # eigene Datei des Projekts mit gleichem Namen
            if hits and hits[0]["art"] != "laufzeit":
                self.fail(f"{n} gehört nicht ins Ziel ({hits[0]['art']})")
            if n.startswith(".github/blueprint/") and n != ".github/blueprint/VERSION":
                self.assertIn(n, wanted, f"{n} ist Ballast")
        # Workflows rufen nur vorhandene Skripte auf, Skripte importieren nur vorhandene Module
        for wf in (self.root / ".github" / "workflows").glob("*.yml"):
            for script in re.findall(r"\.github/blueprint/(\w+\.py)", wf.read_text(encoding="utf-8")):
                self.assertTrue((self.root / ".github" / "blueprint" / script).exists(), f"{wf.name} braucht {script}")
        local = {p.stem for p in BP.glob("*.py")}
        for py in (self.root / ".github" / "blueprint").glob("*.py"):
            for mod in re.findall(r"^import (\w+)", py.read_text(encoding="utf-8"), re.M):
                if mod in local:
                    self.assertTrue((py.parent / f"{mod}.py").exists(), f"{py.name} importiert {mod}.py")
        for py in (self.root / ".github" / "blueprint").glob("*.py"):
            py_compile.compile(str(py), doraise=True)

    def workflows(self) -> set[str]:
        return {p.name for p in (self.root / ".github" / "workflows").glob("*.yml")}

    def test_web(self):
        self.start("web")
        self.apply()
        self.assert_schlank()
        self.assertEqual(self.workflows(), {"release.yml", "issue-milestone.yml", "milestone-admin.yml", "pruefungen.yml",
                                            "fremdkomponenten.yml"})
        cfg = config(self.root)
        self.assertEqual(len(cfg.get("umgebungen", [])), 2, "Web mit Server: Umgebungen test/produktion aktiv (#5)")
        self.assertTrue(cfg.get("variablen"), "Variablen für das Deployment vorbereitet")
        self.assertTrue(all(v["wert"] == "" for v in cfg["variablen"]), "keine Beispielwerte (example.org) aktiv")
        self.assertEqual(json.loads((self.root / "composer.json").read_text(encoding="utf-8"))["version"], "0.1.0")

    def test_desktop(self):
        self.start("desktop")
        self.apply()
        self.assert_schlank()
        self.assertEqual(self.workflows(), {"release.yml", "issue-milestone.yml", "milestone-admin.yml", "pruefungen.yml",
                                            "fremdkomponenten.yml", "installer.yml"})
        cfg = config(self.root)
        self.assertEqual(cfg.get("umgebungen", []), [], "Desktop ohne Server: keine Umgebungen (#5)")
        self.assertEqual(cfg.get("variablen", []), [])
        self.assertEqual(cfg.get("secrets", []), [])
        self.assertTrue(cfg["versionierung"]["vorabversionen_aufraeumen"], "#12")
        self.assertTrue((self.root / ".github" / "blueprint" / "release_checks.py").exists())
        self.assertTrue((self.root / ".github" / "blueprint" / "cleanup.py").exists(), "für vorabversionen_aufraeumen")
        self.assertIn('version = "0.1.0"', (self.root / "pyproject.toml").read_text(encoding="utf-8"))

    def test_beides(self):
        self.start("beides")
        self.apply()
        self.assert_schlank()
        self.assertIn("installer.yml", self.workflows())
        self.assertNotIn("fremdkomponenten.yml", self.workflows(), "Abhängigkeiten «frei»: keine monatliche Prüfung")

    def test_minimal_nur_noetige_workflows(self):
        self.start("web", {"abhaengigkeiten": "frei", "auslieferung": ["nur Quellcode"]})
        text = (self.root / ".github" / "blueprint.toml").read_text(encoding="utf-8")
        (self.root / ".github" / "blueprint.toml").write_text(start.set_value(text, "ci", "aktiv", False), encoding="utf-8")
        self.apply()
        self.assert_schlank()
        self.assertEqual(self.workflows(), {"release.yml", "issue-milestone.yml", "milestone-admin.yml"})

    def test_funktion_ausschalten_meldet_ballast(self):
        self.start("web")
        self.apply()
        path = self.root / ".github" / "blueprint.toml"
        path.write_text(start.set_value(path.read_text(encoding="utf-8"), "ci", "aktiv", False), encoding="utf-8")
        r = self.apply()
        self.assertIn("pruefungen.yml", r.stdout)
        self.assertTrue((self.root / ".github" / "workflows" / "pruefungen.yml").exists(), "ohne --aufraeumen bleibt alles")
        self.apply("--aufraeumen", "--ja")
        self.assertFalse((self.root / ".github" / "workflows" / "pruefungen.yml").exists())
        self.assert_schlank()

    def test_probelauf_aendert_nichts(self):
        self.start("desktop")
        before = snapshot(self.root)
        self.apply("--probelauf")
        self.assertEqual(snapshot(self.root), before)

    def test_fruehere_blueprint_datei_ist_ballast(self):
        self.start("web")
        old = self.root / ".github" / "workflows" / "blueprint-anwenden.yml"
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text("name: Blueprint anwenden\n", encoding="utf-8")
        self.assertIn(".github/workflows/blueprint-anwenden.yml", [n for n, _ in manifest.ballast(self.root, config(self.root))])

    def test_ohne_start_checkliste_nichts(self):
        r = self.apply(check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Start-Checkliste", r.stderr)

    def test_blueprint_selbst_ist_kein_ziel(self):
        r = run(PY, str(BP / "apply.py"), "--ziel", str(SOURCE), "--nur-dateien", "--repo", "x/y", check=False)
        self.assertNotEqual(r.returncode, 0)
        r = run(PY, str(BP / "start.py"), check=False)
        self.assertNotEqual(r.returncode, 0)

    def test_aktualisieren(self):
        self.start("web")
        self.apply()
        release_py = self.root / ".github" / "blueprint" / "release.py"
        release_py.write_text(release_py.read_text(encoding="utf-8") + "\n# alt\n", encoding="utf-8")
        r = self.apply()
        self.assertIn("weicht vom Blueprint ab", r.stdout)
        r = self.apply("--aktualisieren", "--probelauf")
        self.assertIn("release.py aktualisiert", r.stdout)
        self.assertIn("# alt", release_py.read_text(encoding="utf-8"))
        self.apply("--aktualisieren")
        self.assertEqual(release_py.read_bytes(), (BP / "release.py").read_bytes())
        version = (self.root / ".github" / "blueprint" / "VERSION").read_text(encoding="utf-8").split()[0]
        self.assertEqual(version, (BP / "VERSION").read_text(encoding="utf-8").split()[0])


class Vorlagenkopie(unittest.TestCase):
    """«Use this template»: ganze Kopie des Blueprints → nach --aufraeumen nur noch, was das Projekt braucht."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "kopie"
        for n in manifest.files(SOURCE):
            dst = self.root / n
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / n, dst)
        run(*GIT, "init", "-q", cwd=self.root)
        run(*GIT, "add", "-A", cwd=self.root)
        run(*GIT, "commit", "-qm", "Kopie", cwd=self.root)
        answers = Path(self.tmp.name) / "antworten.toml"
        answers.write_text(toml_dump(ANTWORTEN["desktop"]), encoding="utf-8")
        run(PY, str(BP / "start.py"), "--ziel", str(self.root), "--antworten", str(answers))

    def tearDown(self):
        self.tmp.cleanup()

    def apply(self, *extra: str) -> subprocess.CompletedProcess:
        return run(PY, str(BP / "apply.py"), "--ziel", str(self.root), "--repo", "test/kopie", "--nur-dateien", *extra)

    def test_ballast_wird_gemeldet(self):
        r = self.apply()
        self.assertIn("Ballast", r.stdout)
        self.assertTrue((self.root / "CHECKLISTE.md").exists())

    def test_ohne_bestaetigung_wird_nichts_entfernt(self):
        before = snapshot(self.root)
        r = self.apply("--aufraeumen")
        self.assertIn("Bestätigung fehlt", r.stdout)
        for n in before:
            self.assertTrue((self.root / n).exists(), f"{n} wurde ohne Bestätigung entfernt")

    def test_aufraeumen(self):
        self.apply("--aufraeumen", "--ja")
        Ziel.assert_schlank(self)
        for n in ("CHECKLISTE.md", "START-CHECKLISTE.md", ".github/blueprint-repo.toml", ".github/FUNDING.yml",
                  ".github/blueprint/apply.py", ".github/blueprint/start.py", ".github/workflows/blueprint-site.yml",
                  ".github/workflows/blueprint-anwenden.yml", ".github/blueprint/templates/README.md"):
            self.assertFalse((self.root / n).exists(), f"{n} ist noch da")
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# Test Desktop"), "README des Projekts statt des Blueprints")
        status = run("git", "status", "--porcelain", cwd=self.root).stdout
        self.assertIn("D  CHECKLISTE.md", status, "entfernt mit git rm (über den Verlauf wiederherstellbar)")

    workflows = Ziel.workflows


if __name__ == "__main__":
    unittest.main()
