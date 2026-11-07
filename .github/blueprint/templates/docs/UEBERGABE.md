# Übergabe an einen neuen Chat – {{name}}

Stand: **JJJJ-MM-TT (hh:mm)** – ein Satz zum Stand (letztes Release, laufender Meilenstein, was im Beta-Test ist).
[PROJEKTSTAND.md](PROJEKTSTAND.md) (aktuell), [PROJEKTSTAND-ARCHIV.md](PROJEKTSTAND-ARCHIV.md) (Verlauf), Konzepte in
`docs/KONZEPT-*.md`. Bei jeder Übergabe nachführen.{{uebergabe_projekt}}

## Start nächster Chat (Übergabe JJJJ-MM-TT, hh:mm)

**Zuerst lesen:** CLAUDE.md → AGENTS.md → dieser Abschnitt → PROJEKTSTAND.md → passende KONZEPT-*.md.

**Stand Code und CI**
- `main` = `abc1234` (kurz, was der letzte Commit war). Arbeitsbaum sauber? CI auf `main` grün?
- Letztes Release **v0.1.0** (Datum). Release in Arbeit? Nächstes nur auf ausdrückliche Freigabe.
- Prüfen: `{{pruefbefehl}}` (Anzahl Tests, Dauer); weitere Prüfungen mit Befehl.

**Offene Issues und ihr Status**

| Issue | Meilenstein | Status | Inhalt / Testliste |
|---|---|---|---|
| #1 | 0.2.0 – Thema | `_3 Beta-Test` | was zu testen ist |
| #2 | Funktionen | `_1 bereit` | **nicht umgesetzt** – erst auf Wort von {{verantwortlich}} |

Schliessen erst nach «getestet ok» bzw. abgehakter Testliste.

**Hinweise für die Arbeit**
- Werkzeuge, Testdaten, Stolpersteine (z. B. Cache, Zugänge, was nur von Hand geht).

**Arbeitsregeln** (siehe AGENTS.md)
- Jedes Thema aus dem Chat → Issue mit Testliste; Status `_1 bereit` → `_2 in Arbeit` → `_3 Beta-Test`.
- Verbesserungen aus dem Test nur als Issue anlegen; umsetzen erst nach Freigabe.
- Releases nur nach ausdrücklicher Freigabe; `{{versionsdatei}}`, Tags und Releases nicht anfassen.
- Löschen nur nach Rückfrage.

## Sitzungen

Neueste oben. Je Sitzung: Datum und Zeit, Thema, umgesetzte Issues, Entscheide (mit Datum), Offenes. Ältere Sitzungen
gelegentlich gekürzt nach `PROJEKTSTAND-ARCHIV.md` verschieben.

### Sitzung JJJJ-MM-TT (hh:mm–) – Thema

- …

## Entscheide

Beschlüsse mit Datum, damit sie nicht erneut diskutiert werden («Entscheid JJJJ-MM-TT: …»). Dauerhafte Regeln
gehören zusätzlich in AGENTS.md.
