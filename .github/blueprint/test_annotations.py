#!/usr/bin/env python3
"""Fehlgeschlagene Tests als GitHub-Anmerkungen ausgeben – lesbar in der Übersicht des Laufs, ohne Log-Zugriff.

    python3 .github/blueprint/test_annotations.py DATEI [DATEI …]

Erkennt (nur Standardbibliothek):
- JUnit-XML (*.xml): pytest --junitxml, PHPUnit --log-junit, Jest/Vitest (junit-Reporter), Maven/Gradle, dotnet test
  mit JUnit-Logger, Playwright – also Web- wie Desktop-Projekte
- Textausgabe von Python unittest («FAIL: test_x (modul.Klasse)») und pytest («FAILED pfad::test – Meldung»)
Ohne erkannten Fehler erscheint das Ende der Ausgabe als eine Anmerkung. Beendet sich immer mit 0.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX = 3000


def esc(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")


def prop(text: str) -> str:
    return esc(text).replace(":", "%3A").replace(",", "%2C")


def emit(title: str, message: str, file: str = "", line: str = "") -> None:
    loc = (f"file={prop(file)}," if file else "") + (f"line={prop(line)}," if file and line else "")
    print(f"::error {loc}title={prop(title[:200])}::{esc(message[-MAX:])}")


def junit(path: Path) -> int:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        print(f"::warning::{path}: kein gültiges JUnit-XML ({e})")
        return 0
    n = 0
    for case in root.iter("testcase"):
        for kind in ("failure", "error"):
            for el in case.findall(kind):
                name = ".".join(x for x in (case.get("classname"), case.get("name")) if x)
                text = "\n".join(x for x in (el.get("message"), el.text) if x).strip() or kind
                emit(f"{kind.upper()} {name}", text, case.get("file", ""), case.get("line", ""))
                n += 1
    return n


def text_output(text: str) -> int:
    n = 0
    for block in re.split(r"^={50,}$", text, flags=re.M):        # Python unittest
        block = block.strip("\n")
        m = re.match(r"(FAIL|ERROR): (\S+) \(([^)]+)\)", block)
        if not m:
            continue
        body = block.split("-" * 70, 1)[-1].strip().split("\n" + "-" * 70)[0]
        where = m.group(3) if m.group(3).endswith("." + m.group(2)) else f"{m.group(3)}.{m.group(2)}"   # ab Python 3.11 mit Methode
        emit(f"{m.group(1)} {where}", body)
        n += 1
    for m in re.finditer(r"^(FAILED|ERROR) (\S+?)(?:::(\S+))?(?: - (.*))?$", text, flags=re.M):   # pytest -ra
        if m.group(2).startswith("("):                              # unittest-Zusammenfassung «FAILED (failures=1)»
            continue
        emit(f"{m.group(1)} {m.group(2)}{'::' + m.group(3) if m.group(3) else ''}", m.group(4) or m.group(1), m.group(2))
        n += 1
    return n


def main(paths: list[str]) -> int:
    paths = paths or ["test-output.txt"]
    found, tail = 0, ""
    for p in map(Path, paths):
        if not p.exists():
            print(f"::warning::Testausgabe {p} nicht gefunden")
            continue
        if p.suffix.lower() == ".xml":
            found += junit(p)
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
            found += text_output(text)
            tail = text[-2500:]
    if not found and tail:
        emit("Ausgabe (Ende)", tail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
