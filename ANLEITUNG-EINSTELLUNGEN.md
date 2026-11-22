# Anleitung: Repository-Einstellungen einrichten

Schritt für Schritt nach `apply.py` – für ein neues wie für ein bestehendes Repository. Ergebnis: Die
Einstellungen aus `.github/blueprint.toml` setzt künftig der Workflow **Einstellungen anwenden** im Projekt; was
GitHub nicht per API anbietet, ist einmal von Hand erledigt.

**Voraussetzung:** `apply.py --ziel ../projekt` ist gelaufen, die Dateien sind committet und auf `main`
(darin `.github/workflows/einstellungen.yml`). In älteren Projekten holt `apply.py --ziel ../projekt --aktualisieren`
den Workflow.

> **Windows:** Bei Blueprint-Ständen vor 0.1.0 b0e4bac vor `apply.py` einmal `set PYTHONUTF8=1` setzen (sonst werden
> Meilensteine mit «–» im Titel nicht erkannt und doppelt angelegt). Neuere Stände brauchen das nicht.

## A · Token erzeugen (einmalig, gilt für mehrere Repositorys)

1. GitHub → Profilbild → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained
   tokens** → **Generate new token** (direkt: https://github.com/settings/personal-access-tokens/new).
2. Ausfüllen:
   - **Token name:** `BLUEPRINT_ADMIN_TOKEN`
   - **Expiration:** z. B. 1 Jahr – Ablaufdatum im Kalender eintragen
   - **Resource owner:** das Konto bzw. die Organisation der Repositorys
   - **Repository access:** «Only select repositories» → die Projekte auswählen (nicht «All repositories»)
3. **Permissions → Repository permissions:**
   - **Administration:** Read and write
   - **Issues:** Read and write
   - **Pages:** Read (nur für `webseite = "auto"`; falls nicht angeboten, weglassen)
   - «Metadata: Read» setzt GitHub automatisch; alles andere bleibt «No access».
4. **Generate token** → Token **sofort kopieren** (wird nur einmal angezeigt). Nirgends sonst ablegen.

## B · Secret im Projekt eintragen (je Repository)

5. Projekt → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   (`https://github.com/OWNER/PROJEKT/settings/secrets/actions`).
6. **Name:** `BLUEPRINT_ADMIN_TOKEN` (genau so) · **Secret:** Token einfügen → **Add secret**.

Persönliche Konten haben keine kontoweiten Secrets: das Secret in jedem Repository eintragen (gleiches Token,
sofern es dafür freigegeben ist). Bei Organisationen geht auch ein Organisations-Secret.

## C · Workflow testen

7. Projekt → **Actions** → **Einstellungen anwenden** → **Run workflow** → Häkchen **«Nur anzeigen, was geändert
   würde»** → **Run workflow**.
8. Lauf öffnen → **Zusammenfassung** lesen:
   - «0 Schritt(e), 0 Hinweis(e)» – alles gesetzt, fertig.
   - Schritte aufgeführt – stimmen sie, den Workflow **ohne** Häkchen nochmals starten.
   - «Secret … fehlt» – Teil B prüfen (Name exakt?).
   - «admin_issue = 0» oder «Start-Checkliste» – zuerst lokal `apply.py --ziel ../projekt` ausführen.
   - Fehler 403 / «Resource not accessible» – Token hat das Repository oder «Administration» nicht (Teil A).

## D · Liste «von Hand» abarbeiten

Am Schluss jedes Laufs (lokal und im Workflow) steht die Liste «Offen bzw. von Hand» – dafür bietet GitHub keine
API. Empfehlung:

| Punkt | Empfehlung | Wo |
|---|---|---|
| About → «Include in the home page» | **erledigen:** Releases an, Deployments an (bei Umgebungen oder GitHub Pages), Packages nur bei veröffentlichten Paketen. Danach in `.github/blueprint.toml` `[konformitaet] startseite_geprueft = true` (per PR) | Repo-Startseite → Zahnrad bei «About» |
| Releases: «Enable release immutability» | **erledigen** | Settings → General → Releases |
| Pushes: «Limit how many branches and tags can be updated in a single push» | **erledigen** (öffentlich: an, 5) | Settings → General → Pushes |
| Issues: «Auto-close issues with merged linked pull requests» | **erledigen.** Achtung: schliesst Issues, die im PR mit «Closes/Fixes #n» verlinkt sind – Agenten schreiben darum nur «Refs #n», geschlossen wird nach dem Test | Settings → General → Issues |
| Code review limits | **erledigen** (öffentlich) | Settings → Code review limits |
| Branches: keine klassischen Schutzregeln | **nichts tun** – der Schutz kommt aus den Rulesets | – |
| Social Preview (1280×640) | nach Bedarf – Bild mit `social_preview.py` erzeugen, von Hand hochladen | Settings → General → Social preview |
| Planung: GitHub-Projekt (Board) | nach Bedarf – für kleine Projekte genügen Meilensteine | `gh project create …`, docs/GITHUB-ABLAUF.md |
| Codespaces-Prebuilds | nach Bedarf | Settings → Codespaces |
| Sponsorships, Preserve (Archive Program) | nach Bedarf (öffentlich) | Settings → Features / Archives |
| Interaction limits | nur vorübergehend bei Spam | Settings → Interaction limits |

## E · Danach

- **Einstellungen ändern:** Wert in `.github/blueprint.toml` anpassen → PR → Merge. Der Workflow läuft beim Push auf
  `main` und setzt den Wert. KI-Agenten gehen genauso vor (nie direkt über die API).
- **Neues vom Blueprint:** Keine automatische Durchsetzung. Ob es Neues gibt, zeigen der Workflow «Konformität
  prüfen» und `apply.py --ziel ../projekt --probelauf`; übernehmen mit `--aktualisieren`, dann Teil C.
- **Token abgelaufen:** neues Token wie in Teil A, Wert in Teil B ersetzen. Ohne gültiges Token meldet der Workflow
  nur einen Hinweis und ändert nichts.
- **Abschluss prüfen:** `python3 .github/blueprint/apply.py --ziel ../projekt --pruefen` – offen bleibt höchstens
  «Include in the home page», bis `startseite_geprueft = true` gesetzt ist.
