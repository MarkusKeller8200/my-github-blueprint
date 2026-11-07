# Start-Checkliste

Diese Fragen werden **vor** dem Einrichten des Repositorys (`apply.py`) und **vor** dem Grundgerüst des Projekts
beantwortet – vom Blueprint aus im Terminal mit `python3 .github/blueprint/start.py --ziel ../projekt` oder im
Gespräch mit Claude. Aus den Antworten entstehen im Ziel die Werte in `.github/blueprint.toml` und der Steckbrief
`docs/PROJEKTSTART.md`. Solange
`[start] erledigt = false` gilt, richtet `apply.py` nichts ein (nur Probelauf). Pflichtfragen sind mit * markiert.

**Antworten zum Anklicken:** Fast jede Frage bietet Antworten zur Auswahl (im Terminal als Nummern, mit Claude
als Klick-Antworten in Runden zu höchstens vier Fragen, `start.py --runde`). «Andere» bzw. eine eigene Eingabe
geht immer. Freitext sind nur Name, Zweck, Nichtziele und erste Funktionen.

Die ausführliche [CHECKLISTE.md](CHECKLISTE.md) bleibt für Feineinstellungen.

<!-- erzeugt mit: python3 .github/blueprint/start.py --markdown > START-CHECKLISTE.md -->

## A · Projekt

1. **Wie heisst das Projekt (voller Name)?** * – Freitext
   <br>z. B. «SekBülach Intranet» oder «MarKusSXCH TagStudio»
2. **Was soll das Projekt leisten, und für wen? (ein bis zwei Sätze)** * – Freitext
   <br>wird zur Beschreibung bei «About» und zum Ziel im Steckbrief
3. **Was gehört ausdrücklich nicht dazu (Nichtziele)?** – Freitext
   <br>schützt vor schleichender Ausweitung, z. B. «keine DJ-Mixing-Software»
4. **Welcher Kurzname soll in den Release-Titeln stehen?** – Vorschläge je nach bisherigen Antworten (oder eigene Antwort)
   <br>erscheint als «Kurzname 0.2.0»
5. **Ist es eine Web-Anwendung, eine Desktop-Anwendung oder beides?** * – web · desktop · beides
   <br>bestimmt Fehlerformular, Zielsysteme der Tests, Release-Dateien und Regeln für Agenten
6. **Wer nutzt die Anwendung?** * – Privatpersonen · Unternehmen · öffentliche Organe · nur intern (mehrere möglich)
   <br>bestimmt, welches Datenschutzgesetz gilt, und Regeln zur Barrierefreiheit
7. **Welche öffentlichen Organe?** * – Kanton Zürich · anderer Kanton · Bund _(nur für öffentliche Organe)_
8. **Ist das Repository neu oder gibt es es schon?** – neu · bestehend

## B · Verantwortung und Sichtbarkeit

9. **Wer gibt Issues und Releases frei (Rolle genügt)?** – Vorschläge: Projektverantwortliche:r · Eigentümer:in · Schulleitung · Produktverantwortliche:r (oder eigene Antwort)
10. **Arbeitest du allein oder im Team?** – allein · team
11. **Ist das Repository öffentlich oder privat?** – privat · öffentlich
12. **Unter welcher Lizenz steht der Code?** (* wenn öffentlich) – Vorschläge: MIT · Apache-2.0 · GPL-3.0-or-later · keine (oder eigene Antwort)
   <br>SPDX-Kennung; LICENSE wird aus der GitHub-Vorlage angelegt
13. **Auf wen lautet die Lizenz?** – Vorschläge je nach bisherigen Antworten (oder eigene Antwort) _(nur mit Lizenz)_

## C · Technik und Grundgerüst

14. **In welchen Programmiersprachen wird entwickelt?** * – Python · PHP · JavaScript / TypeScript · C# / .NET · Java / Kotlin · Rust · Go · Swift · andere (mehrere möglich)
   <br>bestimmt Dependabot, Vorgaben für Prüfbefehl, CodeQL und die Liste der Fremdkomponenten
15. **Welcher Grundsatz gilt für Abhängigkeiten?** – nur Standardbibliothek · geprüfte Pakete · frei
16. **Für welche Betriebssysteme?** – Windows · macOS · Linux (mehrere möglich) _(nur Desktop bzw. beides)_
   <br>darauf laufen die Tests im Workflow «pruefungen»
17. **Wo läuft die Web-Anwendung?** – Vorschläge: Webhosting (PHP, MySQL) · eigener Server / VPS · Azure · offen (oder eigene Antwort) _(nur Web bzw. beides)_
   <br>genauer über «Andere», z. B. «Hostinger, PHP 8.4, MySQL»
18. **Wie kommt die Anwendung zu den Nutzer:innen?** – Server · GitHub Pages · Installer (GitHub-Releases) · App-Store · nur Quellcode (mehrere möglich)
19. **Welches Framework bzw. welche Grundlage?** – Vorschläge je nach bisherigen Antworten (oder eigene Antwort)
20. **Welche Daten verarbeitet die Anwendung?** * – keine Personendaten · Personendaten · besonders schützenswert
   <br>bestimmt Datenschutz-Hinweis in allen Formularen und Grundsätze in SECURITY.md
21. **Welcher Schutzbedarf gilt für die Daten (Klassifizierung)?** * – öffentlich · intern · vertraulich · geheim
   <br>ab «vertraulich» gelten strengere Grundsätze; das Repository sollte dann privat sein
22. **Welche Anmeldungen und Zugänge braucht es?** – keine · eigene Benutzerkonten · Entra ID / SSO · externe Dienste (API) (mehrere möglich)
23. **In welchen Sprachen wird die Oberfläche ausgeliefert?** – Vorschläge: de-CH · de-CH, en · de-CH, en, fr · de-CH, fr, it (oder eigene Antwort)
   <br>erste = Ausgangssprache; ab zwei Sprachen gilt die Übersetzungsregel
24. **Gibt es Plugins oder Module mit eigener Version?** – ja · nein

## D · Ablauf

25. **Mit welchem Befehl laufen alle Prüfungen?** – Vorschläge je nach bisherigen Antworten (oder eigene Antwort)
   <br>läuft vor jedem Commit und im Workflow «pruefungen»
26. **In welcher Datei steht die Versionsnummer?** – VERSION · version.py · package.json · composer.json · pyproject.toml
27. **Mit welcher Version startet das Projekt?** – Vorschläge: 0.1.0 · 1.0.0 (oder eigene Antwort)
28. **Mit welchen KI-Agenten wird gearbeitet?** – Claude · GitHub Copilot · keine (mehrere möglich)
29. **Wie heisst der erste Meilenstein?** – Vorschläge je nach bisherigen Antworten (oder eigene Antwort)
30. **Übergabe und Projektstand auch als Kopie im Claude-Projekt führen?** – ja · nein _(nur mit Claude)_
31. **Welche ersten Funktionen gehören in diesen Meilenstein?** – Freitext
   <br>werden nach Bestätigung als Issues (mit Testliste) angelegt
