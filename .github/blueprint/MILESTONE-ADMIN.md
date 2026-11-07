# Meilensteine verwalten (GitHub Actions)

Aus dem GitHub-Blueprint. Der Workflow [milestone-admin.yml](../workflows/milestone-admin.yml) verwaltet Meilensteine
über Kommentare – praktisch, wenn ein Werkzeug (z. B. eine KI-Integration) Issues zuweisen, aber keine Meilensteine
anlegen oder schliessen kann.

**Steuerungs-Issue:** die Nummer steht in `.github/blueprint.toml` → `[workflows] admin_issue` (beim Anwenden des Blueprints angelegt und geschlossen; Kommentare sind trotzdem möglich). Nur Kommentare auf diesem einen Issue lösen Aktionen aus, und nur von der Eigentümerin bzw. dem Eigentümer (bei Organisationen: deren Owner) sowie von Konten, die in `[workflows] milestone_admins` stehen und Mitglied bzw. Mitwirkende:r sind.

## Erlaubte Befehle

Je Kommentar **genau eine** Zeile:

```text
/milestone list
/milestone create 0.33.0 – Nächster Entwicklungsschritt
/milestone close 4
/milestone reopen 4
```

Die Antwort erscheint als Kommentar im Steuerungs-Issue. Doppelte Titel werden nicht erneut angelegt, bereits
geschlossene Meilensteine nicht nochmals geändert. Der Workflow verwendet nur `secrets.GITHUB_TOKEN` mit
`issues: write`, keinen persönlichen Token.

## Sicherheitsregeln

- Workflow und Python-Skript prüfen **beide** die Berechtigung (author_association); das Skript zusätzlich Repository-Namen, Liste `milestone_admins` und die feste Issue-Nummer.
- Befehlsparameter gehen nur als geprüfte Daten an die GitHub-REST-API, nie als Shell-Code.
- Keine Aktion bei Kommentaren anderer Personen oder in anderen Issues.
- Bei Änderung von Eigentümer, Issue-Nummer oder Berechtigungen Workflow und Skript prüfen.
- Nach Änderungen zuerst `/milestone list` testen; bei fehlender Antwort
  Actions → milestone-admin kontrollieren.
