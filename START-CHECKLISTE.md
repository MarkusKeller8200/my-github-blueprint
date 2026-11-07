# Start-Checkliste

Diese Fragen werden **vor** dem Einrichten des Repositorys (`apply.py`) und **vor** dem Grundgerüst des Projekts
beantwortet – im Terminal mit `python3 .github/blueprint/start.py` oder im Gespräch mit Claude. Aus den Antworten
entstehen die Werte in `.github/blueprint.toml` und der Steckbrief `docs/PROJEKTSTART.md`. Solange
`[start] erledigt = false` gilt, richtet `apply.py` nichts ein (nur Probelauf). Pflichtfragen sind mit * markiert.
Die ausführliche [CHECKLISTE.md](CHECKLISTE.md) bleibt für Feineinstellungen.

<!-- erzeugt mit: python3 .github/blueprint/start.py --markdown > START-CHECKLISTE.md -->

## A · Projekt

1. **Wie heisst das Projekt (voller Name)?** *
   <br>z. B. «SekBülach Intranet» oder «MarKusSXCH TagStudio»
2. **Kurzname für Release-Titel?**
   <br>erscheint als «Kurzname 0.2.0»
3. **Was soll das Projekt leisten, und für wen? (ein bis zwei Sätze)** *
   <br>wird zur Beschreibung bei «About» und zum Ziel im Steckbrief
4. **Was gehört ausdrücklich nicht dazu (Nichtziele)?**
   <br>schützt vor schleichender Ausweitung, z. B. «keine DJ-Mixing-Software»
5. **Ist es eine Web-Anwendung, eine Desktop-Anwendung oder beides?** * – web · desktop · beides
   <br>bestimmt Fehlerformular, Zielsysteme der Tests, Release-Dateien und Regeln für Agenten
6. **Neues oder bestehendes Repository?** – neu · bestehend
   <br>bestehend: danach Teil C der CHECKLISTE.md (Labels, Tags, vorhandene Workflows)

## B · Verantwortung und Sichtbarkeit

7. **Wer gibt Issues und Releases frei (Rolle genügt)?**
8. **Arbeitest du allein oder im Team?** – allein · team
   <br>allein: direkte Pushes; Team: Änderungen über Pull Requests
9. **Ist das Repository öffentlich oder privat?** – privat · oeffentlich
   <br>öffentlich erst ohne Geheimnisse und echte Daten im Verlauf; geändert wird nur mit apply.py --sichtbarkeit
10. **Unter welcher Lizenz steht der Code (SPDX)?** (* wenn öffentlich)
   <br>z. B. MIT, Apache-2.0, GPL-3.0-or-later; leer bei privaten Projekten ohne Weitergabe
11. **Auf wen lautet die Lizenz?** _(nur mit Lizenz)_

## C · Technik und Grundgerüst

12. **In welchen Programmiersprachen wird entwickelt?** * – Python · PHP · JavaScript / TypeScript · C# / .NET · Java / Kotlin · Rust · Go · Swift · andere (mehrere möglich)
   <br>bestimmt Dependabot, Vorgaben für Prüfbefehl, CodeQL und die Liste der Fremdkomponenten
13. **Welches Framework bzw. welche Grundlage?**
   <br>Web z. B. Laravel, Django, Vite + React; Desktop z. B. Python + pywebview, Electron, Tauri, WPF; «offen» = im Konzept klären
14. **Welcher Grundsatz gilt für Abhängigkeiten?** – nur Standardbibliothek im Kern, Pakete nur optional bzw. in Plugins · bewährte Pakete erlaubt, neue nur nach Prüfung von Lizenz und Pflege · frei
15. **Für welche Betriebssysteme?** – Windows · macOS · Linux (mehrere möglich) _(nur Desktop bzw. beides)_
   <br>darauf laufen die Tests im Workflow «pruefungen»
16. **Wo läuft die Web-Anwendung (Hosting, Server, Datenbank)?** _(nur Web bzw. beides)_
   <br>z. B. «Hostinger, PHP 8.4, MySQL» oder «Azure App Service»
17. **Wie kommt die Anwendung zu den Nutzer:innen?** – Server (Deployment per SSH, Docker o. Ä.) · GitHub Pages (statische Seite) · Installer über GitHub-Releases · App-Store (Microsoft Store, Mac App Store …) · nur als Quellcode (mehrere möglich)
   <br>Installer → Dateien am Release mit Prüfsummen; Pages → Workflow pages.yml
18. **Welche Daten verarbeitet die Anwendung?** * – keine Personendaten · Personendaten (DSG bzw. IDG beachten) · besonders schützenswerte Personendaten
   <br>bestimmt Datenschutz-Hinweis in allen Formularen und Grundsätze in SECURITY.md
19. **Welche Anmeldungen und Zugänge braucht es?** – keine · eigene Benutzerkonten · Microsoft Entra ID / SSO · externe Dienste mit API-Schlüssel oder OAuth (mehrere möglich)
20. **In welchen Sprachen wird die Oberfläche ausgeliefert?**
   <br>erste = Ausgangssprache, z. B. de-CH, en, fr; ab zwei Sprachen gilt die Übersetzungsregel
21. **Gibt es Plugins oder Module mit eigener Version?**
   <br>dann muss deren Version bei jeder Änderung steigen (Prüfung in release.py)

## D · Ablauf

22. **Mit welchem Befehl laufen alle Prüfungen?**
   <br>läuft vor jedem Commit und im Workflow «pruefungen»
23. **In welcher Datei steht die Versionsnummer?** – VERSION · version.py · package.json · composer.json · pyproject.toml
24. **Mit welcher Version startet das Projekt?**
   <br>0.x = Prototyp, 1.0.0 = erster produktiver Stand
25. **Wie heisst der erste Meilenstein?**
26. **Welche ersten Funktionen gehören in diesen Meilenstein?**
   <br>werden nach Bestätigung als Issues (mit Testliste) angelegt
27. **Mit welchen KI-Agenten wird gearbeitet?** – Claude · GitHub Copilot · keine (mehrere möglich)
28. **Übergabe und Projektstand auch als Kopie im Claude-Projekt führen?** _(nur mit Claude)_
