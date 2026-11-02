# Checkliste: Blueprint anwenden

Die Antworten kommen in `.github/blueprint.toml`. In Klammern steht der jeweilige Schlüssel. Teil A gilt immer,
Teil B nur für neue Repositorys, Teil C nur für bestehende.

## A · Für jedes Projekt

### Projekt
- [ ] Wie heisst das Projekt voll, und wie heisst es kurz für Release-Titel? (`projekt.name`, `projekt.kurz`, `versionierung.release_titel`)
- [ ] Wer gibt Issues und Releases frei? Eine Rolle genügt. (`projekt.verantwortlich`)
- [ ] Ist das Repository **öffentlich oder privat**?
  - Bei privaten Repositorys gibt es keine private Sicherheitsmeldung über GitHub. Wie werden Lücken stattdessen gemeldet? (`projekt.sicherheit_kontakt`)
- [ ] Gibt es Vorgaben zum **Datenschutz**, zum Beispiel nur Testdaten, IDG oder DSG? Welcher Hinweis soll in allen Formularen stehen? (`projekt.datenschutz`)
- [ ] Wo sehen Nutzer:innen die Version, die sie bei «Fehler melden» angeben? (`projekt.version_ort`)
- [ ] Mit welchem Befehl laufen alle Prüfungen vor einem Commit, zum Beispiel `composer ci:check`, `npm test` oder `make check`? (`projekt.pruefbefehl`)
- [ ] In welcher Sprache sind Oberfläche und Issues? Die Vorlagen sind auf Deutsch (Schweiz). (`projekt.sprache`)

### Issues
- [ ] Welche Bereiche soll die Auswahl in den Formularen anbieten? (`issues.bereiche`)
- [ ] Braucht es zusätzliche Vorlagen: «Plugin-Idee» oder «GUI-Baustein»? (`issues.zusatzvorlagen`)
- [ ] Braucht es weitere projektspezifische Labels, zum Beispiel `barrierefreiheit` oder `modul:x`? (`issues.zusatzlabels`)
- [ ] Sollen die englischen GitHub-Standard-Labels entfernt werden? Labels, die noch an Issues hängen, bleiben immer stehen. (`issues.standard_labels_entfernen`)

### Meilensteine
- [ ] Sollen die Sammlungen Fehler, Verbesserungen und Funktionen mit automatischer Zuordnung angelegt werden? (`meilensteine.sammlungen`)
- [ ] Gibt es schon einen ersten Release-Meilenstein, zum Beispiel «0.2.0 – Thema»? (`meilensteine.erster_release`)
- [ ] Sollen Meilensteine auch per Kommentar `/milestone …` verwaltet werden können, über ein Admin-Issue? (`workflows.milestone_admin`)

### Versionierung und Releases
- [ ] Wo steht die Versionsnummer: `VERSION`, `version.py`, `package.json`, `composer.json` oder `pyproject.toml`? (`versionierung.datei`)
- [ ] Mit welcher Version startet das Projekt? 0.x bedeutet Prototyp. (`versionierung.startversion`)
- [ ] Welche Workflows müssen grün sein, bevor ein Release entsteht, zum Beispiel `ci` oder `deploy`? (`versionierung.release_nach`)
- [ ] Gibt es Teile mit eigener Version, etwa Plugins oder Module, deren Version bei Änderungen steigen muss? Unter welchen Globs liegen die Manifeste, z. B. `["plugins/*/plugin.json", "modules/*/module.json"]`? (`versionierung.plugin_manifeste`)
- [ ] Rollt jeder Push automatisch aus? Dann gelten Stände zwischen zwei Releases als «Developer Release». Wo soll die Anwendung das anzeigen (z. B. über `git describe` beim Deployment)?
- [ ] Sollen KI-Agenten Issues anlegen und Status-Labels setzen dürfen? (Regeln in `AGENTS.md`)

### Repository-Einstellungen

Wie jede Einstellung angewendet wird: **API** setzt `apply.py`, sofern es mit Admin-Rechten läuft (lokal mit
`gh auth login` als Eigentümer:in oder über Claude). Der Workflow in Actions darf das nicht und meldet nur
Abweichungen. **Von Hand** bedeutet: GitHub bietet keine API; `apply.py` listet diese Punkte am Schluss mit Link auf.

| Einstellung | Frage | Schlüssel | Vorgabe privat / öffentlich | Wie |
|---|---|---|---|---|
| Sichtbarkeit | Öffentlich oder privat? Vor «öffentlich»: keine Geheimnisse und keine echten Daten in Code und Verlauf, Lizenz festgelegt? | `repository.sichtbarkeit` | – | API, nur mit `--sichtbarkeit` |
| Standard-Branch | Heisst er `main`? Andere Namen erfordern Anpassungen in den Workflows. | `repository.standard_branch` | main | API |
| Beschreibung, Webseite, Themen | Was steht bei «About»? | `repository.beschreibung`, `webseite`, `themen` | – | API |
| Template-Repository | Dient das Repository selbst als Vorlage? | `repository.vorlage` | aus | API |
| Releases | Sollen veröffentlichte Releases unveränderlich sein? Soll «Releases» auf der Startseite erscheinen? | – | an / an | von Hand |
| Social Preview | Titel, Untertitel und Farben des Vorschaubilds | `[social_preview]` | Bild aus `social_preview.py` | Bild per Skript, Hochladen von Hand |
| Wiki | Braucht es ein Wiki? Bei privaten Repositorys nur mit kostenpflichtigem Plan. | `repository.wiki` | aus / an | API |
| Issues | Issues eingeschaltet? «Auto-close issues with merged linked pull requests»? | `repository.issues` | an / an | API; Auto-close von Hand |
| Issue-Rechte | Wer darf Issues anlegen? Privat nur Mitwirkende, öffentlich alle mit GitHub-Konto. Bei Spam vorübergehend «Interaction limits». | – | – | von Hand bei Bedarf |
| Sponsoring | Wie kann man unterstützen? GitHub Sponsors, Buy Me a Coffee, Ko-fi, Liberapay, eigene Links (z. B. TWINT, PayPal) | `[sponsoring]` | – / nach Wahl | Dateien `FUNDING.yml` und `docs/UNTERSTUETZEN.md`; Schalter «Sponsorships» von Hand |
| Preserve this repository | Soll das Repository ins GitHub Archive Program? Nur öffentlich. | – | – / an | von Hand |
| Discussions | Gibt es ein Forum für Fragen und Ideen? | `repository.diskussionen` | aus / an | API |
| Projects | Sollen Planungs-Boards verfügbar sein? | `repository.projekte` | an / an | API |
| Pull Requests | Profil «solo» (Squash + Rebase, direkte Pushes) oder «team» (nur Squash, Auto-Merge)? Branch nach dem Merge löschen, «Update branch» anbieten | `repository.pr_profil` | solo / team | API |
| PR-Pflicht | Dürfen Änderungen am Standard-Branch nur per Pull Request kommen? Admins sind ausgenommen. | `repository.pr_pflicht` | aus / an | API (Ruleset) |
| Commits | Sign-off bei Commits im Browser verlangen (DCO)? | `repository.web_commit_signoff` | aus / an | API |
| Pushes | Begrenzung, wie viele Branches und Tags ein Push ändern darf? | – | aus / an (5) | von Hand |
| Push-Schutz | Secret Scanning mit Push-Schutz? Bei privaten Repositorys kostenpflichtig. | `repository.secret_scanning` | aus / an | API |
| Branch- und Tag-Schutz | Standard-Branch nicht löschen und nicht force-pushen; Tags `v*` unveränderlich | `repository.branch_schutz` | an / an | API (Rulesets; privat nur mit kostenpflichtigem Plan) |
| Actions-Rechte | Darf der `GITHUB_TOKEN` schreiben (Labels, Releases)? | – | Read and write | API, sonst von Hand |
| Fork-PR-Workflows | Brauchen Workflows aus Forks eine Freigabe? Nur öffentlich. | – | – / alle Aussenstehenden | von Hand |

**Sponsoring-Auswahl:**
- **GitHub Sponsors:** monatlich oder einmalig, ohne Gebühren. Einmal im Profil freischalten und den Wohnsitz Schweiz angeben.
- **Buy Me a Coffee** oder **Ko-fi:** einmalige kleine Beträge.
- **Liberapay:** wiederkehrende kleine Beträge.
- **Eigener Link:** z. B. TWINT oder PayPal, beliebt in der Schweiz.
- Dazu die Wege ohne Geld (Stern, Feedback, Testen, Weitersagen); sie stehen in `docs/UNTERSTUETZEN.md`.

### Sicherheit, Actions, Umgebungen, Zugänge

| Bereich | Frage | Schlüssel | Vorgabe privat / öffentlich | Wie |
|---|---|---|---|---|
| Code review limits | Dürfen nur Mitwirkende Pull Requests freigeben oder Änderungen verlangen? | – | – / an | von Hand |
| Rulesets | Welche Prüfungen müssen vor dem Merge grün sein? Lineare Historie? Copilot-Review? | `repository.pflicht_pruefungen`, `lineare_historie`, `copilot.code_review` | Branch: kein Löschen, kein Force-Push (öffentlich zusätzlich PR-Pflicht und lineare Historie); Tags `v*` unveränderlich; Admins ausgenommen | API |
| Branches | Klassische Branch-Schutzregeln? Nein, der Schutz kommt aus den Rulesets. | – | keine | – |
| Actions – General | Wie lange Artefakte und Protokolle aufbewahren? Dürfen Workflows schreiben? Dürfen sie Pull Requests genehmigen? Freigabe für Workflows aus Forks? | `actions.aufbewahrung_tage`, `fork_freigabe` | 30 / 90 Tage; Read and write; Genehmigen nein; öffentlich Freigabe für alle Aussenstehenden | API |
| Actions – Policies | Welche Actions sind erlaubt: alle, ausgewählte oder nur GitHub-eigene? Pinning auf Commit-SHA verlangen? | `actions.erlaubte_actions`, `zusaetzlich_erlaubt`, `sha_pinning` | ausgewählt: GitHub-eigene, verifizierte, Liste; Pinning aus | API |
| Actions – OIDC | Wird ohne gespeicherte Schlüssel in eine Cloud ausgerollt (Azure, AWS, GCP)? Dann eigene Subject-Claims, z. B. `repo` und `context`. | `actions.oidc_claims` | Standard | API |
| Webhooks | Muss ein externes System Ereignisse bekommen (Teams, Jira, eigener Server)? URL, Ereignisse, Name der Umgebungsvariablen für das Geheimnis | `[[webhooks]]` | keine | API |
| Copilot | Gibt es eine Copilot-Lizenz? Code Review automatisch? Coding Agent mit Firewall «Recommended allowlist», MCP nur bei Bedarf, Agent-Secrets in der Umgebung «copilot» | `[copilot]` | aus | Anweisungen `.github/copilot-instructions.md` (gelten für alle Agenten), Ruleset-Regel per API, Rest von Hand |
| Planning | GitHub-Projekt (Board) mit Status Triage, Bereit, In Arbeit, Beta-Test, Erledigt; Ansichten Board, Tabelle nach Meilenstein, Roadmap; Sub-Issues für Teilaufgaben | – | – | von Hand (`gh project create`) |
| Environments | Welche Zielumgebungen gibt es? Wer gibt Produktion frei? Welche Branches und Tags dürfen ausrollen? | `[[umgebungen]]` | «test» (nur main), «produktion» (Freigabe durch Eigentümer:in, nur main und `v*`); bei Pages zusätzlich «github-pages» | API (Freigaben privat nur mit kostenpflichtigem Plan) |
| Codespaces | Wird im Browser bzw. Codespace entwickelt? Prebuilds? | `codespaces.devcontainer` | aus | `.devcontainer/devcontainer.json`; Prebuilds von Hand |
| GitHub Pages | Soll eine Website bzw. Doku veröffentlicht werden? Aus welchem Ordner? | `[pages]` | aus | API und Workflow `pages.yml` (lokal anlegen) |
| Advanced Security | Dependabot-Warnungen und -Sicherheitsupdates, `dependabot.yml` (welche Ökosysteme), Secret Scanning mit Push-Schutz, CodeQL, private Sicherheitsmeldungen | `[sicherheit]`, `[dependabot]`, `repository.secret_scanning` | Warnungen und Updates an; Scanning und CodeQL öffentlich an (privat kostenpflichtig); private Meldungen öffentlich an | API und Datei |
| Deploy-Keys | Welche SSH-Zugänge braucht es? Vorbereitet sind: «Server – Pull» (nur lesen), «Backup – Spiegel» (nur lesen), «Extern – Push» (schreiben). Nicht benötigte entfernen. | `[[deploy_keys]]` | Einträge ohne Schlüssel | Mit `.pub`-Datei per API; ohne Datei steht die Anleitung (`ssh-keygen` → `gh repo deploy-key add`) unter «offen» |
| Secrets und Variablen | Was braucht das Deployment? Vorbereitet: Variablen `APP_URL` (test, produktion), `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PFAD`; Secrets `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS` (produktion); Beispiele für Dependabot, Codespaces und Agents | `[[variablen]]`, `[[secrets]]` | Variablen mit Beispielwerten; Secrets aus gleichnamiger Umgebungsvariable, sonst Platzhalter `NOCH-NICHT-GESETZT` | API bzw. `gh secret set` |

**Wichtig:** Diese Einstellungen brauchen Admin-Rechte. Führe `apply.py` dafür lokal mit deiner eigenen
`gh`-Anmeldung aus (`gh auth login`). Über Claude (Cloud-Sitzung) sind Schreibzugriffe auf Repository-Einstellungen
gesperrt. Claude legt dort nur Labels, Meilensteine und Issues an und erzeugt Dateien; alles andere erscheint als
Hinweis. Geheime Werte stehen nie in `.github/blueprint.toml`.

## B · Neues Repository

1. [ ] Neues Repository auf GitHub aus diesem Blueprint erstellen: «Use this template», wenn `my-github-blueprint`
   als Template-Repository markiert ist, sonst die Ordner `.github/blueprint`, `.github/workflows` und
   `.github/blueprint.toml` kopieren.
2. [ ] `.github/blueprint.toml` mit den Antworten aus Teil A ausfüllen und committen.
3. [ ] Repository-Einstellungen anwenden: lokal als Eigentümer:in mit `python3 .github/blueprint/apply.py --probelauf`,
   danach ohne Probelauf, oder über Claude. Das setzt auch die Actions-Rechte «Read and write». Anschliessend die
   Liste «Von Hand» abarbeiten, unter anderem Social Preview, Sponsorships und Preserve.
4. [ ] Actions → **Blueprint anwenden** → Run workflow, zuerst mit «Probelauf», dann ohne.
5. [ ] Ergebnis prüfen: Labels, Meilensteine, Admin-Issue, Dateien (CONTRIBUTING, SECURITY, CHANGELOG,
   docs/GITHUB-ABLAUF.md, Issue-Vorlagen).
6. [ ] README um einen Abschnitt «Mitmachen» mit Link auf `CONTRIBUTING.md` ergänzen.
7. [ ] Testen: ein Test-Issue pro Vorlage anlegen (es bekommt Labels und Meilenstein), `/milestone list` auf dem
   Admin-Issue ausprobieren, danach die Test-Issues schliessen.

## C · Bestehendes Repository

Grundsatz: Es wird nichts überschrieben oder gelöscht, ohne dass du es bestätigst.

1. [ ] **Bestandsaufnahme.** Es gibt schon:
   - Issue-Vorlagen, eine PR-Vorlage, CONTRIBUTING, SECURITY, CHANGELOG, AGENTS.md
   - Labels und Meilensteine
   - Workflows mit gleichem Namen (`release.yml` usw.)
   - Tags und Releases
2. [ ] **Probelauf** vom Blueprint-Repo aus: `python3 .github/blueprint/apply.py --ziel ../projekt --repo owner/projekt --probelauf`.
   Er zeigt alle Schritte und Konflikte, ohne etwas zu ändern.
3. [ ] **Bestehende Dateien.** Bleiben sie und werden von Hand angeglichen, oder ersetzt sie `--ueberschreiben`?
   Das CHANGELOG braucht den Abschnitt «## [Unveröffentlicht]».
4. [ ] **Labels.** Soll es eine Zuordnung alt → neu geben, zum Beispiel `bug` → `fehler` oder `enhancement` → `verbesserung`?
   - Umbenennen behält die Zuordnung zu den Issues, Löschen nicht.
   - Standard-Labels, die noch verwendet werden, entfernt der Blueprint nie.
5. [ ] **Offene Issues.** Bekommen alle bestehenden Issues `triage`? Werden sie den Sammlungen zugeordnet?
6. [ ] **Versionen.**
   - Wie ist die aktuelle Version, und gibt es schon Tags?
   - Wenn keine: Sollen frühere Versionen rückwirkend Tags und Releases bekommen? Dann eine Datei mit Zeilen
     «Version Commit» anlegen (`versionierung.nachtragen_datei`). Die Tags lokal setzen und pushen
     (`grep -v '^#' DATEI | while read v s; do git tag "v$v" "$s"; done; git push origin --tags`), dann release → Run
     workflow → «nachtragen». Der Workflow legt nur die Releases an, weil der `GITHUB_TOKEN` keine Tags auf alte
     Commits mit anderen Workflow-Dateien setzen darf.
   - Bisher wurde die Version bei jeder Änderung erhöht? Ab jetzt nur noch beim freigegebenen Release.
7. [ ] **Konflikte mit Workflows.** Gibt es schon einen Release- oder Tag-Mechanismus, zum Beispiel einen
   Installer-Build? Wird er ersetzt oder angepasst?
8. [ ] **Rechte.** Darf der `GITHUB_TOKEN` schreiben (Settings → Actions)? Haben die eingesetzten Werkzeuge,
   etwa KI-Agenten, Zugriff auf das Repository?
9. [ ] Anwenden ohne Probelauf, Testen wie in B.7 und den Ablauf im Team bzw. in AGENTS.md bekannt machen.

## Was der Blueprint bewusst nicht macht

- Er legt keine Repositorys an. Repository-Einstellungen ändert er nur mit Admin-Rechten und nach einem Probelauf;
  die Sichtbarkeit nur mit `--sichtbarkeit`.
- Er löscht keine Dateien, Issues, Tags oder Releases. Labels entfernt er nur, wenn sie unbenutzt sind und es
  eingeschaltet ist.
- Er setzt keine Versionen und erstellt keine Releases ohne ausdrückliche Freigabe.
