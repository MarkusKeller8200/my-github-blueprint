#!/usr/bin/env python3
"""Dokumenttest (GitHub-Blueprint, für reine Dokumentations-Repositorys) – nur Python-Standardbibliothek.

    python3 tests/test_dokumente.py

Prüft alle Markdown-Dateien im Repository:
- relative Links und Bilder zeigen auf vorhandene Dateien (Anker innerhalb von Dateien werden nicht geprüft);
- keine offensichtlichen Geheimnisse (Zugangsschlüssel, private Schlüssel, Tokens) im Text.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
IGNORIEREN = {".git", "node_modules", "vendor", "_site", ".venv"}
LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
GEHEIMNISSE = [
    ("privater Schlüssel", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("GitHub-Token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("AWS-Schlüssel", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack-Token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google-API-Schlüssel", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Passwort im Klartext", re.compile(r"(?i)\b(?:passwort|password|pwd)\s*[:=]\s*[\"']?[^\s\"'<>]{6,}")),
]


def dokumente() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if not IGNORIEREN & set(p.relative_to(ROOT).parts))


def ohne_code(text: str) -> str:
    """Codeblöcke und Inline-Code entfernen (Beispiele dort sind keine Links)."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


class Dokumente(unittest.TestCase):
    def test_relative_links(self):
        tote = []
        for doc in dokumente():
            for ziel in LINK.findall(ohne_code(doc.read_text(encoding="utf-8"))):
                if re.match(r"^[a-z][a-z0-9+.-]*:", ziel, re.I) or ziel.startswith("#"):
                    continue                                    # http:, mailto:, computer: … und Anker
                pfad = unquote(ziel.split("#", 1)[0].split("?", 1)[0])
                if not pfad:
                    continue
                datei = (ROOT / pfad.lstrip("/")) if pfad.startswith("/") else (doc.parent / pfad)
                if not datei.exists():
                    tote.append(f"{doc.relative_to(ROOT)} → {ziel}")
        self.assertEqual(tote, [], "Tote relative Links:\n  " + "\n  ".join(tote))

    def test_keine_geheimnisse(self):
        funde = []
        for doc in dokumente():
            for nr, zeile in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
                for name, muster in GEHEIMNISSE:
                    if muster.search(zeile):
                        funde.append(f"{doc.relative_to(ROOT)}:{nr} ({name})")
        self.assertEqual(funde, [], "Mögliche Geheimnisse – entfernen und Zugangsdaten ersetzen:\n  " + "\n  ".join(funde))


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
