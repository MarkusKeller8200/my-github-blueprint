# Datenschutz – {{name}}

Arbeitsgrundlage für den Datenschutz in diesem Projekt (aus der Start-Checkliste des GitHub-Blueprints). Sie hält
fest, was zu klären ist – sie ist **keine Aussage, dass das Projekt datenschutzkonform ist**. Jeder Punkt startet mit
Status **OFFEN** und wird erst nach Klärung durch {{verantwortlich}} auf **BESCHLOSSEN** gesetzt (mit Datum und
Quelle bzw. Entscheid).

| Grundlage | Wert |
|---|---|
| Daten | {{ds_daten}} |
| Schutzbedarf | {{ds_schutzbedarf}} |
| Anwendbares Recht | {{ds_recht}} |

Werte ändern: `[datenschutz]` in `.github/blueprint.toml`.{{ds_dsfa}}

## 1. Datenfluss

**Status: OFFEN**

- Welche Personendaten werden erhoben, von wem, zu welchem Zweck?
- Wo werden sie gespeichert (Server, Region, Anbieter) und wohin fliessen sie (Schnittstellen, Exporte, E-Mail)?
- Skizze oder Tabelle: Quelle → Verarbeitung → Ablage → Empfänger.

## 2. Aufbewahrung und Löschung

**Status: OFFEN**

- Aufbewahrungsfrist je Datenart (gesetzliche Grundlage bzw. Archivpflicht).
- Wer löscht wann und wie (automatisch, von Hand)? Wie werden Löschungen nachgewiesen?
- Umgang mit Daten ausgetretener Personen und mit Testdaten.

## 3. Zugriffskonzept

**Status: OFFEN**

- Rollen und Rechte: wer sieht und ändert welche Daten?
- Anmeldung, Mehrfaktor, Protokollierung der Zugriffe.
- Administratorzugänge und Notfallzugriff.

## 4. Drittanbieter und KI-Dienste

**Status: OFFEN**

- Welche externen Dienste (Hosting, E-Mail, Analyse, Bibliotheken mit Netzwerkzugriff) erhalten Daten?
- KI-Dienste: Werden Personendaten an KI-Dienste übermittelt? Wenn ja, mit welcher Rechtsgrundlage und welchem Vertrag
  (Auftragsbearbeitung, Datenstandort, keine Nutzung zum Training)?
- Verträge und Auftragsbearbeitungen sind festgehalten (Ablageort).

## 5. Backups und Wiederherstellung

**Status: OFFEN**

- Was wird wie oft gesichert, wo liegen die Sicherungen, wie lange werden sie aufbewahrt?
- Sind Sicherungen verschlüsselt? Wann wurde die Wiederherstellung zuletzt getestet?

## 6. Rechte der betroffenen Personen

**Status: OFFEN**

- Auskunft, Berichtigung, Löschung: Ablauf und zuständige Stelle.
- Information der betroffenen Personen (Datenschutzerklärung bzw. Hinweis in der Anwendung).

## Entscheide

| Datum | Punkt | Entscheid | Quelle |
|---|---|---|---|
| | | | |
