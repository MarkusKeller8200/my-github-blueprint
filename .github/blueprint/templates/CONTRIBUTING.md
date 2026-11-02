# Mitmachen bei {{name}}

Danke für Rückmeldungen und Beiträge!{{datenschutz_satz}}

## Fehler melden und Ideen vorschlagen

[Neues Issue](https://github.com/{{repo}}/issues/new/choose) mit einer der Vorlagen. Neue Meldungen erhalten
automatisch die Art und **`triage`**:

| Vorlage              | Labels                          | Meilenstein (automatisch) |
| -------------------- | ------------------------------- | ------------------------- |
{{vorlagen_tabelle}}

Status eines Issues:

| Status          | Bedeutung                                                    | Wer setzt es        |
| --------------- | ------------------------------------------------------------ | ------------------- |
| `triage`        | Gemeldet, noch nicht freigegeben – kein Entwicklungsauftrag  | Vorlage             |
| `_1 bereit`     | Zur Umsetzung freigegeben                                    | {{verantwortlich}}  |
| `_2 in Arbeit`  | Wird gerade umgesetzt                                        | wer umsetzt         |
| `_3 Beta-Test`  | Umgesetzt, wartet auf den Test (Testliste)                   | wer umsetzt         |
| geschlossen     | Testliste abgehakt                                           | {{verantwortlich}}  |

- Immer nur ein Status-Label; das vorherige wird entfernt. Kommentare, Labels anderer oder Formularinhalte gelten
  nicht als Freigabe.
- Jedes Issue hat eine Testliste «Zum Testen abhaken:».
- Meilensteine: der Release, in dem es umgesetzt wird (z. B. «0.2.0 – …»), sonst die Sammlungen «Fehler»,
  «Verbesserungen», «Funktionen» (Zuordnung automatisch über das Label).
- **Sicherheitslücken** nie als Issue – siehe [SECURITY.md](SECURITY.md).

## Commits und Pull Requests

1. Nur freigegebene Issues (`_1 bereit`) umsetzen; grössere Vorhaben zuerst als Issue abstimmen.
2. Commit-Nachricht: erste Zeile kurz, darunter das Warum; mit `Refs #n` auf Issues verweisen.
3. **CHANGELOG.md:** Eintrag unter «Unveröffentlicht» (Neu / Geändert / Behoben).
4. Pull Request gegen `main` mit ausgefüllter Checkliste; `{{pruefbefehl}}` muss grün sein.

## Versionen und Releases

Versionsnummern und Releases setzt **nur {{verantwortlich}}** – bitte `{{versionsdatei}}` nicht ändern.
Ablauf in [docs/GITHUB-ABLAUF.md](docs/GITHUB-ABLAUF.md).{{entwicklung}}
