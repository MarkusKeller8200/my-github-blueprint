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
- [ ] Gibt es Teile mit eigener Version, etwa Plugins oder Module, deren Version bei Änderungen steigen muss? Unter welchem Glob liegen die Manifeste? (`versionierung.plugin_manifeste`)
- [ ] Rollt jeder Push automatisch aus? Dann gelten Stände zwischen zwei Releases als «Developer Release». Wo soll die Anwendung das anzeigen (z. B. über `git describe` beim Deployment)?
- [ ] Sollen KI-Agenten Issues anlegen und Status-Labels setzen dürfen? (Regeln in `AGENTS.md`)

## B · Neues Repository

1. [ ] Neues Repository auf GitHub aus diesem Blueprint erstellen: «Use this template», wenn `my-github-blueprint`
   als Template-Repository markiert ist, sonst die Ordner `.github/blueprint`, `.github/workflows` und
   `.github/blueprint.toml` kopieren.
2. [ ] `.github/blueprint.toml` mit den Antworten aus Teil A ausfüllen und committen.
3. [ ] Unter Settings → Actions → General die Option «Read and write permissions» für den `GITHUB_TOKEN` setzen,
   damit Workflows Labels, Meilensteine und Releases anlegen dürfen.
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
     «Version Commit» anlegen (`versionierung.nachtragen_datei`) und release → Run workflow → «nachtragen» starten.
   - Bisher wurde die Version bei jeder Änderung erhöht? Ab jetzt nur noch beim freigegebenen Release.
7. [ ] **Konflikte mit Workflows.** Gibt es schon einen Release- oder Tag-Mechanismus, zum Beispiel einen
   Installer-Build? Wird er ersetzt oder angepasst?
8. [ ] **Rechte.** Darf der `GITHUB_TOKEN` schreiben (Settings → Actions)? Haben die eingesetzten Werkzeuge,
   etwa KI-Agenten, Zugriff auf das Repository?
9. [ ] Anwenden ohne Probelauf, Testen wie in B.7 und den Ablauf im Team bzw. in AGENTS.md bekannt machen.

## Was der Blueprint bewusst nicht macht

- Er legt keine Repositorys an und ändert keine Repository-Einstellungen wie Template-Markierung, Branch-Schutz
  oder Actions-Rechte.
- Er löscht keine Dateien, Issues, Tags oder Releases. Labels entfernt er nur, wenn sie unbenutzt sind und es
  eingeschaltet ist.
- Er setzt keine Versionen und erstellt keine Releases ohne ausdrückliche Freigabe.
