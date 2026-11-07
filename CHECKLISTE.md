# Checkliste: Blueprint anwenden

**Zuerst die [Start-Checkliste](START-CHECKLISTE.md)** (`python3 .github/blueprint/start.py --ziel ../projekt`): Sie stellt die
Grundfragen vor dem Einrichten und vor dem Grundgerüst, trägt die Antworten ein und legt `docs/PROJEKTSTART.md` an.
Diese Checkliste hier dient danach den Feineinstellungen.

Die Antworten kommen in `.github/blueprint.toml` **des Ziel-Repositorys**. In Klammern steht der jeweilige Schlüssel.
Alle Werkzeuge (`start.py`, `apply.py`) laufen vom Blueprint aus; ins Ziel kommt nur, was das Projekt braucht
([manifest.toml](.github/blueprint/manifest.toml)). Teil A gilt immer,
Teil B nur für neue Repositorys, Teil C nur für bestehende.

## A · Für jedes Projekt

### Projekt
- [ ] Wie heisst das Projekt voll, und wie heisst es kurz für Release-Titel? (`projekt.name`, `projekt.kurz`, `versionierung.release_titel`)
- [ ] Ist es eine **Web-Anwendung** (Server, Browser), eine **Desktop-Anwendung** (Installer für Windows, macOS, Linux) oder **beides**? Davon hängen die Vorgaben für «Fehler melden», Prüfungen, Release-Dateien und SECURITY.md ab. (`projekt.art`)
- [ ] Unter welcher **Lizenz** steht das Projekt (SPDX, z. B. `MIT`, `GPL-3.0-or-later`), auf wen lautet sie? Öffentliche Repositorys brauchen eine. (`projekt.lizenz`, `lizenz_inhaber`)
- [ ] In welchen Sprachen wird die Oberfläche ausgeliefert? Ab zwei Sprachen gilt: jeder Text im selben Commit in allen Sprachen. (`projekt.sprachen_auslieferung`)
- [ ] Verhaltenskodex (CODE_OF_CONDUCT.md)? Wohin werden Verstösse gemeldet? (`projekt.verhaltenskodex`, `verhaltenskodex_kontakt`)
- [ ] SECURITY.md: Antwortzeit, Tabelle «Unterstützte Versionen» (Desktop), was ausserhalb des Geltungsbereichs liegt (z. B. Plugins von Dritten, Signatur-Warnungen)? (`projekt.sicherheit_antwortzeit`, `sicherheit_versionstabelle`, `sicherheit_nicht_im_bereich`)
- [ ] Wer gibt Issues und Releases frei? Eine Rolle genügt. (`projekt.verantwortlich`)
- [ ] Ist das Repository **öffentlich oder privat**?
  - Bei privaten Repositorys gibt es keine private Sicherheitsmeldung über GitHub. Wie werden Lücken stattdessen gemeldet? (`projekt.sicherheit_kontakt`)
- [ ] Gibt es Vorgaben zum **Datenschutz**, zum Beispiel nur Testdaten, IDG oder DSG? Welcher Hinweis soll in allen Formularen stehen? (`projekt.datenschutz`)
- [ ] Wo sehen Nutzer:innen die Version, die sie bei «Fehler melden» angeben? (`projekt.version_ort`)
- [ ] Mit welchem Befehl laufen alle Prüfungen vor einem Commit, zum Beispiel `composer ci:check`, `npm test` oder `make check`? (`projekt.pruefbefehl`)
- [ ] Zusätzliche Punkte für die PR-Checkliste, z. B. «Nur erfundene Testdaten»? (`projekt.pr_checkliste`)
- [ ] Wie richtet man die Entwicklungsumgebung ein (Abschnitt in CONTRIBUTING)? (`projekt.entwicklung`)
- [ ] Sicherheitsgrundsätze für SECURITY.md, z. B. «Zugangsdaten nur verschlüsselt speichern»? (`projekt.sicherheit_grundsaetze`)
- [ ] Zusätzlicher Link bei «Neues Issue», z. B. zum Doku-Ordner? (`projekt.doku_url`, `doku_titel`, `doku_beschreibung`)
- [ ] In welcher Sprache sind Oberfläche und Issues? Die Vorlagen sind auf Deutsch (Schweiz). (`projekt.sprache`)

### Issues
- [ ] Welche Bereiche soll die Auswahl in den Formularen anbieten? (`issues.bereiche`)
- [ ] Braucht es zusätzliche Vorlagen: «Plugin-Idee», «GUI-Baustein» oder «Übersetzung einreichen»? Wo liegen die Übersetzungen? (`issues.zusatzvorlagen`, `uebersetzung_ablage`)
- [ ] «Fehler melden»: Passen die Vorgaben für Plattform (Browser bzw. Betriebssystem) und Variante (Umgebung bzw. Installer/Quellcode)? Wo liegt das Protokoll? (`issues.plattformen`, `varianten`, `protokoll_ort`)
- [ ] Braucht es weitere projektspezifische Labels, zum Beispiel `barrierefreiheit` oder `modul:x`? (`issues.zusatzlabels`)
- [ ] Sollen die englischen GitHub-Standard-Labels entfernt werden? Labels, die noch an Issues hängen, bleiben immer stehen. (`issues.standard_labels_entfernen`)

### Meilensteine
- [ ] Sollen die Sammlungen Fehler, Verbesserungen und Funktionen mit automatischer Zuordnung angelegt werden? (`meilensteine.sammlungen`)
- [ ] Gibt es schon einen ersten Release-Meilenstein, zum Beispiel «0.2.0 – Thema»? (`meilensteine.erster_release`)
- [ ] Sollen Meilensteine auch per Kommentar `/milestone …` verwaltet werden können, über ein Admin-Issue? (`workflows.milestone_admin`)

### Versionierung und Releases
- [ ] Wo steht die Versionsnummer: `VERSION`, `version.py`, `package.json`, `composer.json` oder `pyproject.toml`? (`versionierung.datei`)
- [ ] Mit welcher Version startet das Projekt? 0.x bedeutet Prototyp. (`versionierung.startversion`)
- [ ] Welche Workflows müssen grün sein, bevor ein Release entsteht, zum Beispiel `pruefungen` oder `installer`? Ohne Eintrag entsteht ein Release ungeprüft. Das ist nur als begründete Ausnahme gedacht, etwa bei einem reinen Doku-Repository; sonst warnen `apply.py` und `release.py`. (`versionierung.release_nach`, `ohne_pruefung`)
- [ ] Gibt es Teile mit eigener Version, etwa Plugins oder Module, deren Version bei Änderungen steigen muss? Unter welchen Globs liegen die Manifeste, z. B. `["plugins/*/plugin.json", "modules/*/module.json"]`? (`versionierung.plugin_manifeste`)
- [ ] **Desktop:** Welche Workflows bauen die Installer, unter welchem Artefakt-Namen? Prüfsummen und VirusTotal (Secret `VIRUSTOTAL_API_KEY`, kostenloses Konto)? Beta-Releases nach der finalen Version entfernen? (`release_dateien.artefakte`, `pruefsummen`, `virustotal`, `versionierung.vorabversionen_aufraeumen`)
- [ ] Rollt jeder Push automatisch aus? Dann gelten Stände zwischen zwei Releases als «Developer Release». Wo soll die Anwendung das anzeigen (z. B. über `git describe` beim Deployment)?
- [ ] Sollen KI-Agenten Issues anlegen und Status-Labels setzen dürfen? (Regeln in `AGENTS.md`)

### Prüfungen, Sicherheit und Pflege
- [ ] Soll der Workflow **pruefungen** die Tests ausführen? Auf welchen Systemen (Web: Linux; Desktop: Windows und macOS; bei Betas weniger)? Welche Sprachversionen, welcher Vorbereitungsbefehl (`npm ci`, `composer install`)? Liefern die Tests JUnit-XML? Oberflächentests unter Linux mit virtuellem Bildschirm? (`[ci]`)
- [ ] Sollen CodeQL-Funde als Issues erscheinen (Workflow «CodeQL erweitert» statt Standard-Setup)? Welche Sprachen, braucht eine kompilierte Sprache einen Bau-Befehl? (`[codeql]`)
- [ ] Sollen die verwendeten Bibliotheken, Werkzeuge und Dienste monatlich auf neue Versionen und Lizenzwechsel geprüft werden? (`[fremdkomponenten]`; danach Liste ergänzen)
- [ ] Sollen alte Workflow-Durchläufe automatisch gelöscht werden, nach wie vielen Tagen? (`aufraeumen.actions_verlauf_tage`)
- [ ] Dependabot: Präfix für Commit-Nachrichten? (`dependabot.commit_praefix`)

### Zusammenarbeit mit KI-Agenten
- [ ] Übergabe zwischen Chats mit CLAUDE.md, docs/UEBERGABE.md, docs/PROJEKTSTAND.md? Kopien im Claude-Projekt? (`agenten.uebergabe`, `projekt_kopie`)
- [ ] Konzeptvorlage mit Verbindlichkeitsstufen? Eigene Leitplanken für AGENTS.md? (`agenten.konzepte`, `regeln`)

### Repository-Einstellungen

Wie jede Einstellung angewendet wird: **API** setzt `apply.py`, sofern es mit Admin-Rechten läuft (lokal mit
`gh auth login` als Eigentümer:in oder über Claude). **Von Hand** bedeutet: GitHub bietet keine API; `apply.py` listet diese Punkte am Schluss mit Link auf.

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
| Rulesets | Welche Prüfungen müssen vor dem Merge grün sein (im Team bzw. öffentlich: `pruefungen`; `apply.py` warnt bei Namen, die es im Ziel nicht gibt)? Lineare Historie? Copilot-Review? | `repository.pflicht_pruefungen`, `lineare_historie`, `copilot.code_review` | Branch: kein Löschen, kein Force-Push (öffentlich zusätzlich PR-Pflicht und lineare Historie); Tags `v*` unveränderlich; Admins ausgenommen | API |
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
| Secrets und Variablen | Was braucht das Deployment? Vorbereitet im Block «Deployment» (nur mit Auslieferung «Server» eingeschaltet): Variablen `APP_URL` (test, produktion), `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PFAD`; Secrets `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS` (produktion); Beispiele für Dependabot, Codespaces und Agents | `[[variablen]]`, `[[secrets]]`, `secrets_einstellungen.platzhalter` | Variablen ohne Wert (erscheinen unter «Von Hand»); Secrets aus gleichnamiger Umgebungsvariable, sonst unter «Von Hand» (kein Platzhalter) | API bzw. `gh secret set` |

**Wichtig:** Diese Einstellungen brauchen Admin-Rechte. Führe `apply.py` dafür lokal mit deiner eigenen
`gh`-Anmeldung aus (`gh auth login`). Über Claude (Cloud-Sitzung) sind Schreibzugriffe auf Repository-Einstellungen
gesperrt. Claude legt dort nur Labels, Meilensteine und Issues an und erzeugt Dateien; alles andere erscheint als
Hinweis. Geheime Werte stehen nie in `.github/blueprint.toml`.

## B · Neues Repository

Zwei Wege; beide enden mit einem Ziel-Repository, das nur enthält, was das Projekt braucht.

**Empfohlen: leeres Repository**

1. [ ] Auf GitHub ein leeres Repository anlegen und neben den Blueprint klonen (`../projekt`).
2. [ ] Start-Checkliste: `python3 .github/blueprint/start.py --ziel ../projekt`. Feineinstellungen aus Teil A in
   `../projekt/.github/blueprint.toml` ergänzen, `docs/PROJEKTSTART.md` prüfen.
3. [ ] `python3 .github/blueprint/apply.py --ziel ../projekt --probelauf`, danach ohne Probelauf – lokal als
   Eigentümer:in mit `gh auth login`, damit auch die Repository-Einstellungen gesetzt werden. Anschliessend die
   Liste «Von Hand» abarbeiten, unter anderem Social Preview, Sponsorships und Preserve.
4. [ ] Im Ziel prüfen und committen (`git -C ../projekt status`, dann Commit und Push).

**Auch möglich: «Use this template»**

1. [ ] «Use this template» wählen und das neue Repository neben den Blueprint klonen (`../projekt`). Die Kopie enthält
   zuerst den ganzen Blueprint – das ist Ballast.
2. [ ] Start-Checkliste wie oben: `python3 .github/blueprint/start.py --ziel ../projekt` (im Blueprint, nicht in der Kopie).
3. [ ] `python3 .github/blueprint/apply.py --ziel ../projekt --aufraeumen --probelauf` zeigt, was entfernt würde
   (Blueprint-Dateien, Werkzeuge, Workflows ausgeschalteter Funktionen). Ohne `--probelauf` fragt `apply.py` nach
   und entfernt erst nach «ja» (mit `git rm`, über den Verlauf wiederherstellbar); das README des Blueprints wird
   durch das README des Projekts ersetzt.
4. [ ] Im Ziel prüfen und committen.

**Danach (beide Wege)**

1. [ ] Ergebnis prüfen: Labels, Meilensteine, Admin-Issue, Dateien (CONTRIBUTING, SECURITY, CHANGELOG,
   docs/GITHUB-ABLAUF.md, Issue-Vorlagen, CLAUDE.md, docs/UEBERGABE.md) und nur die Workflows der eingeschalteten
   Funktionen.
2. [ ] Testen: ein Test-Issue pro Vorlage anlegen (es bekommt Labels und Meilenstein), `/milestone list` auf dem
   Admin-Issue ausprobieren, danach die Test-Issues schliessen.
3. [ ] Später ein- oder ausgeschaltete Funktionen: erneut `apply.py --ziel ../projekt` – neue Workflows kommen dazu,
   nicht mehr benötigte meldet es als Ballast (`--aufraeumen`). Neuerungen des Blueprints übernimmt
   `apply.py --ziel ../projekt --aktualisieren` (zuerst mit `--probelauf`).

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
   Liegen noch ältere Kopien des Blueprints im Projekt (z. B. `.github/blueprint/apply.py`, `blueprint-anwenden.yml`),
   meldet `apply.py` sie als Ballast; entfernt werden sie nur mit `--aufraeumen` nach Rückfrage.
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
   Installer-Build? Wird er ersetzt oder angepasst? Ein bestehender Installer-Workflow kann bleiben: er lädt die
   Dateien als Artefakte hoch, `release.yml` hängt sie an (`release_dateien.artefakte`). Gibt es schon eine CI oder
   einen eigenen CodeQL-Workflow? Dann `[ci] aktiv = false` lassen bzw. «CodeQL erweitert» überspringt sich selbst.
8. [ ] **Rechte.** Darf der `GITHUB_TOKEN` schreiben (Settings → Actions)? Haben die eingesetzten Werkzeuge,
   etwa KI-Agenten, Zugriff auf das Repository?
9. [ ] Anwenden ohne Probelauf, Testen wie in Teil B («Danach») und den Ablauf im Team bzw. in AGENTS.md bekannt machen.

## Was der Blueprint bewusst nicht macht

- Er legt keine Repositorys an. Repository-Einstellungen ändert er nur mit Admin-Rechten und nach einem Probelauf;
  die Sichtbarkeit nur mit `--sichtbarkeit`.
- Er löscht keine Issues oder Tags. Dateien entfernt er nur mit `--aufraeumen` nach ausdrücklicher Bestätigung und
  nur, wenn sie laut Manifest nicht ins Projekt gehören (eigene Dateien des Projekts bleiben). Labels entfernt er nur, wenn sie unbenutzt sind und es eingeschaltet
  ist. Release-Einträge erledigter Vorabversionen (`versionierung.vorabversionen_aufraeumen`) und alte
  Workflow-Durchläufe (`aufraeumen.actions_verlauf_tage`) entfernt er nur, wenn du es einschaltest.
- Er setzt keine Versionen und erstellt keine Releases ohne ausdrückliche Freigabe.
