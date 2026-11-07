# my-github-blueprint

Vorlage für GitHub-Projekte: Meldungen als Issues mit Freigabe, Status-Labels, Meilensteine, Versionierung und
Releases. Entstanden aus **TagStudio** (Desktop-Anwendung) und **SekBülach Intranet** (Web-Anwendung) und für
beide Arten gedacht.

Der Blueprint bleibt hier. Ins Projekt kommt **nur, was es braucht**: die Workflows und Skripte der eingeschalteten
Funktionen und die daraus erzeugten Dateien. Werkzeuge für die Einrichtung, Vorlagen, Checklisten und diese
Webseite bleiben im Blueprint. Was wohin gehört, legt [manifest.toml](.github/blueprint/manifest.toml) fest. Ein
Selbsttest prüft das bei jeder Änderung.

## In fünf Schritten zum Projekt

```bash
git clone https://github.com/MarkusKeller8200/my-github-blueprint.git
git clone https://github.com/OWNER/mein-projekt.git          # leeres Repository, neben dem Blueprint
cd my-github-blueprint
python3 .github/blueprint/start.py --ziel ../mein-projekt             # 1. Start-Checkliste (31 Fragen)
python3 .github/blueprint/apply.py --ziel ../mein-projekt --probelauf # 2. zeigen, was passiert
gh auth login && python3 .github/blueprint/apply.py --ziel ../mein-projekt   # 3. anwenden
git -C ../mein-projekt add -A && git -C ../mein-projekt commit -m "GitHub-Blueprint angewendet"   # 4. prüfen, committen
git -C ../mein-projekt push                                           # 5. pushen
```

Danach die Liste «Von Hand» abarbeiten, die `apply.py` am Schluss ausgibt (z. B. Social Preview).

- **«Use this template»** geht auch. Die Kopie enthält dann zuerst den ganzen Blueprint.
  `apply.py --ziel ../mein-projekt --aufraeumen` entfernt diesen Ballast nach Rückfrage.
- **Bestehendes Repository:** gleiche Befehle. Bestehende Dateien werden nie überschrieben, Abweichungen werden gemeldet.
  Siehe Teil C der [CHECKLISTE.md](CHECKLISTE.md).
- **Mit Claude:** «Wende my-github-blueprint auf Repository X an». Claude stellt die Fragen der
  [Start-Checkliste](START-CHECKLISTE.md) in Runden mit Antworten zum Anklicken (`start.py --runde`). Danach folgt
  der Probelauf, und erst nach deiner Bestätigung wird angewendet. Das Grundgerüst entsteht erst, wenn der Steckbrief
  `docs/PROJEKTSTART.md` bestätigt ist.

Alles läuft nur mit der Python-Standardbibliothek (3.11+) und der `gh`-CLI. Es braucht keine Pakete und keinen
persönlichen Token.

## Was ins Projekt kommt

| Teil | Inhalt |
|---|---|
| **Desktop und Web** | `projekt.art` = `web`, `desktop` oder `beides` bestimmt die Formulare, die Zielsysteme der Prüfungen, Installer, SECURITY.md und die Regeln in AGENTS.md |
| **Issues und Labels** | Formulare Fehler, Verbesserung, Funktion (optional Plugin, GUI, Übersetzung) · Art-Labels · Status `triage` → `_1 bereit` → `_2 in Arbeit` → `_3 Beta-Test` |
| **Meilensteine** | Sammlungen Fehler / Verbesserungen / Funktionen (automatische Zuordnung) und Release-Meilensteine; `/milestone …` per Kommentar |
| **Workflows** (nur eingeschaltete) | `release.yml` (Tag und Release nach Freigabe) · `issue-milestone.yml` · `milestone-admin.yml` · `pruefungen.yml` · `installer.yml` (Desktop) · `codeql-erweitert.yml` · `fremdkomponenten.yml` · `aufraeumen.yml` · `pages.yml`. Alle Actions sind auf Commit-SHAs gepinnt |
| **Dokumente** | README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, LICENSE, CHANGELOG, docs/GITHUB-ABLAUF.md, PR-Vorlage, AGENTS.md, CLAUDE.md, Übergabe und Projektstand, Konzeptvorlage, Steckbrief `docs/PROJEKTSTART.md` |
| **Repository-Einstellungen** | Sichtbarkeit, Pull-Request-Profil, Rulesets, Secret Scanning, Dependabot, CodeQL, Actions-Richtlinien, Umgebungen, Variablen und Secrets für das Deployment (nur bei Auslieferung «Server»); per API, der Rest als Liste «Von Hand» |

Alle Werte stehen in `.github/blueprint.toml` des Projekts. Feineinstellungen beschreibt die
[CHECKLISTE.md](CHECKLISTE.md).

## Der Ablauf im Projekt

1. Meldung über ein Formular → Label `triage`, automatisch in einer Sammlung.
2. Die/der Projektverantwortliche gibt frei → `_1 bereit`.
3. Umsetzung → `_2 in Arbeit`, Commits mit `Refs #n`, CHANGELOG unter «Unveröffentlicht».
4. Ausgerollt → `_3 Beta-Test`, die Testliste «Zum Testen abhaken:» wartet.
5. Abgehakt → Issue geschlossen. Ist der Meilenstein leer: Release nach Freigabe mit
   `python3 .github/blueprint/release.py set X.Y.Z --commit`. `release.yml` legt Tag und Release an, sobald der
   Commit grün ist.

Details: [docs/GITHUB-ABLAUF.md](.github/blueprint/templates/docs/GITHUB-ABLAUF.md) (Vorlage).

## Aktualisieren

Verbesserungen am Ablauf kommen hierher. In einem Projekt übernimmt
`python3 .github/blueprint/apply.py --ziel ../mein-projekt --aktualisieren --probelauf` (danach ohne `--probelauf`)
die neuen Laufzeitdateien. Es zeigt die Unterschiede je Datei. Welcher Stand im Projekt steckt, steht in dessen
`.github/blueprint/VERSION`.

## Dieses Repository

- **Selbsttests:** `python3 -m unittest discover -s .github/blueprint/tests -v` (auch im Workflow
  `blueprint-selbsttest`). Eine neue Datei braucht einen Eintrag in `manifest.toml`, sonst schlägt der Test fehl.
- **Einstellungen** von my-github-blueprint selbst stehen in `.github/blueprint-repo.toml`:
  `python3 .github/blueprint/apply.py --config .github/blueprint-repo.toml --nur-github --probelauf`.
- Die Projekt-Workflows liegen hier auch, wirken aber nur, wenn die Konfiguration es verlangt; in der Vorlage
  `.github/blueprint.toml` ist alles aus.

## Unterstützen

Gefällt dir der Blueprint? Ein ⭐, Rückmeldungen über die Issues oder ein Kaffee auf
[Ko-fi](https://ko-fi.com/markussxch) helfen weiter.
