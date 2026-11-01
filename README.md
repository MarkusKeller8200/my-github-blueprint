# my-github-blueprint

Vorlage für GitHub-Projekte: Meldungen als Issues mit Freigabe, Status-Labels, Meilensteine, Versionierung und
Releases. Entstanden aus den Projekten **TagStudio** und **SekBülach Intranet**. Ein neues oder bestehendes
Repository lässt sich damit mit wenigen Handgriffen gleich aufsetzen.

## Was drin ist

| Teil | Inhalt |
|---|---|
| **Issue-Vorlagen** | Fehler melden, Verbesserung, Neue Funktion / Idee, optional Plugin-Idee und GUI-Baustein; alle setzen Art-Label und `triage`; Link zur privaten Sicherheitsmeldung |
| **Labels** | Art: `fehler`, `verbesserung`, `funktion`, `doku`, `sicherheit`, `duplikat`, `wird nicht umgesetzt` · Status: `triage` → `_1 bereit` → `_2 in Arbeit` → `_3 Beta-Test` |
| **Meilensteine** | Sammlungen Fehler / Verbesserungen / Funktionen (neue Issues werden automatisch zugeordnet) und Release-Meilensteine «X.Y.Z – Thema» |
| **Workflows** | `issue-milestone.yml` (Zuordnung), `milestone-admin.yml` (`/milestone …` per Kommentar), `release.yml` (Tag und GitHub-Release nach Freigabe), `blueprint-anwenden.yml` (Einrichten) |
| **Dokumente** | CONTRIBUTING.md, SECURITY.md, CHANGELOG.md (Keep a Changelog), docs/GITHUB-ABLAUF.md, PR-Vorlage, Abschnitt für AGENTS.md (Regeln für KI-Agenten) |
| **Werkzeuge** | `.github/blueprint/apply.py` (anwenden, mit Probelauf), `.github/blueprint/release.py` (Version setzen, prüfen, Release-Text, Developer Release) |
| **Repository-Einstellungen** | Sichtbarkeit, Standard-Branch, Wiki, Discussions, Projects, Pull-Request-Profil (solo/team), Sign-off, Secret Scanning, Rulesets für Branch und Tags, Actions-Rechte – per API (`settings.py`); Social Preview (`social_preview.py`), Sponsoring (`FUNDING.yml`) und weitere Punkte ohne API als Liste «Von Hand» |
| **Sicherheit und Betrieb** | Actions-Richtlinien und -Aufbewahrung, Fork-Freigabe, OIDC, Umgebungen test/produktion, Webhooks, Pages, Dependabot (`dependabot.yml`), CodeQL, private Sicherheitsmeldungen, vorbereitete Deploy-Keys, Variablen und Secrets (`advanced.py`); `copilot-instructions.md`, optional `devcontainer.json` |
| **Konfiguration** | `.github/blueprint.toml`: alle projektspezifischen Werte, siehe [CHECKLISTE.md](CHECKLISTE.md) |

Alles läuft nur mit der Python-Standardbibliothek (3.11+) und der `gh`-CLI, die auf GitHub-Runnern vorhanden ist.
Es braucht keine Pakete und keinen persönlichen Token.

## Der Ablauf in Kürze

1. Meldung über ein Formular → Label `triage`, automatisch in einer Sammlung.
2. Die/der Projektverantwortliche gibt frei → `_1 bereit`, eventuell in einen Release-Meilenstein.
3. Umsetzung → `_2 in Arbeit`, Commits mit `Refs #n`, CHANGELOG unter «Unveröffentlicht».
4. Ausgerollt → `_3 Beta-Test`, die Testliste «Zum Testen abhaken:» wartet.
5. Abgehakt → Issue geschlossen. Ist der Meilenstein leer: Release ankündigen und nach Freigabe
   `python3 .github/blueprint/release.py set X.Y.Z --commit` und Push. `release.yml` legt dann Tag `vX.Y.Z` und
   das Release an.

Dazwischen gilt jeder Stand auf `main` als «Developer Release». Details stehen in
[docs/GITHUB-ABLAUF.md](.github/blueprint/templates/docs/GITHUB-ABLAUF.md) (Vorlage).

## Anwenden

**Neues Repository**

1. Auf GitHub «Use this template» wählen (dieses Repository als Template markieren: Settings → Template repository).
2. `.github/blueprint.toml` anhand der [CHECKLISTE.md](CHECKLISTE.md) ausfüllen.
3. Settings → Actions → General → Workflow permissions: «Read and write permissions».
4. Actions → **Blueprint anwenden** → Run workflow, zuerst mit «Probelauf».

**Bestehendes Repository**

```bash
git clone https://github.com/MarkusKeller8200/my-github-blueprint.git
cd my-github-blueprint
python3 .github/blueprint/apply.py --ziel ../mein-projekt --repo owner/mein-projekt --probelauf  # nur anzeigen
python3 .github/blueprint/apply.py --ziel ../mein-projekt --repo owner/mein-projekt              # Blueprint kopieren
# im Projekt: .github/blueprint.toml ausfüllen, dann
python3 .github/blueprint/apply.py --probelauf && python3 .github/blueprint/apply.py
```

Bestehende Dateien werden nie überschrieben (ausser mit `--ueberschreiben`), Abweichungen werden gemeldet. Die
Fragen für bestehende Projekte stehen in Teil C der Checkliste.

**Mit Claude:** «Wende my-github-blueprint auf Repository X an». Claude geht die Checkliste durch, macht den
Probelauf und legt nach Bestätigung Dateien, Labels, Meilensteine und Issues an. Repository-Einstellungen wendest du
danach lokal an (`gh auth login`, dann `apply.py`). Tags und Releases legt nur GitHub Actions an.

## Dieses Repository einrichten

Die Einstellungen von my-github-blueprint selbst stehen in `.github/blueprint-repo.toml`: öffentlich, Template,
About-Text, Webseite, Topics, Pages. Angewendet werden sie lokal mit:

```bash
gh auth login
python3 .github/blueprint/apply.py --config .github/blueprint-repo.toml --nur-github --probelauf
python3 .github/blueprint/apply.py --config .github/blueprint-repo.toml --nur-github
```

## Aktualisieren

Verbesserungen am Ablauf kommen hierher. Für ein Projekt danach nochmals mit `--ziel … --ueberschreiben` kopieren
bzw. die Workflows und `.github/blueprint/` ersetzen und «Blueprint anwenden» starten. Der AGENTS.md-Abschnitt
zwischen den Markierungen wird dabei aktualisiert.

## Unterstützen

Gefällt dir der Blueprint? Ein ⭐, Rückmeldungen über die Issues oder ein Kaffee auf
[Ko-fi](https://ko-fi.com/markussxch) helfen weiter.

## Hinweis zu diesem Repository

Die Workflows sind auch hier aktiv, wirken aber nur, wenn die Konfiguration es verlangt. Solange
`admin_issue = 0` gilt und kein Release freigegeben ist, passiert nichts. «Blueprint anwenden» sollte hier nicht
gestartet werden; das Repository bleibt eine Vorlage.
