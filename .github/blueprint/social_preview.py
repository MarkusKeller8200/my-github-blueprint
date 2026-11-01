#!/usr/bin/env python3
"""Social-Preview-Bild (1280×640) für ein Repository erzeugen – GitHub-Blueprint.

    python3 .github/blueprint/social_preview.py [--repo owner/name]

Schreibt .github/social-preview.svg (immer, nur Standardbibliothek) und .github/social-preview.png (mit Pillow
oder ImageMagick, falls vorhanden; sonst das SVG z. B. im Browser als PNG speichern). Hochladen von Hand:
Settings → General → Social preview → Edit → Upload an image (GitHub bietet dafür keine API).
Werte aus .github/blueprint.toml: [social_preview], sonst projekt.name und repository.beschreibung.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import textwrap
import tomllib
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
W, H = 1280, 640


def values(repo: str) -> dict:
    with open(ROOT / ".github" / "blueprint.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    sp, p, r = cfg.get("social_preview", {}), cfg.get("projekt", {}), cfg.get("repository", {})
    return {
        "titel": sp.get("titel") or p.get("name", "Projekt"),
        "untertitel": sp.get("untertitel") or r.get("beschreibung", ""),
        "farbe": sp.get("farbe", "#0b3d63"),
        "akzent": sp.get("akzent", "#f2b705"),
        "repo": repo,
    }


def lines(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width)[:3] if text else []


def svg(v: dict) -> str:
    title = lines(v["titel"], 22)
    sub = lines(v["untertitel"], 48)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{v["farbe"]}"/>',
             f'<rect x="80" y="120" width="16" height="{80 * len(title) + 40}" fill="{v["akzent"]}"/>']
    y = 190
    for t in title:
        parts.append(f'<text x="124" y="{y}" font-family="Helvetica, Arial, sans-serif" font-size="72" font-weight="700" fill="#ffffff">{escape(t)}</text>')
        y += 84
    y += 24
    for s in sub:
        parts.append(f'<text x="124" y="{y}" font-family="Helvetica, Arial, sans-serif" font-size="36" fill="#dbe7f0">{escape(s)}</text>')
        y += 48
    if v["repo"]:
        parts.append(f'<text x="124" y="{H - 70}" font-family="Menlo, Consolas, monospace" font-size="28" fill="{v["akzent"]}">github.com/{escape(v["repo"])}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def png_pillow(v: dict, out: Path) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    def font(size: int, bold: bool = False, mono: bool = False):
        names = (["DejaVuSansMono.ttf"] if mono else []) + (["DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf"])
        for name in names:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)

    img = Image.new("RGB", (W, H), v["farbe"])
    d = ImageDraw.Draw(img)
    title = lines(v["titel"], 22)
    d.rectangle([80, 120, 96, 120 + 80 * len(title) + 40], fill=v["akzent"])
    y = 130
    for t in title:
        d.text((124, y), t, font=font(72, bold=True), fill="#ffffff")
        y += 84
    y += 24
    for s in lines(v["untertitel"], 48):
        d.text((124, y), s, font=font(36), fill="#dbe7f0")
        y += 48
    if v["repo"]:
        d.text((124, H - 100), f"github.com/{v['repo']}", font=font(28, mono=True), fill=v["akzent"])
    img.save(out)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="")
    args = ap.parse_args()
    v = values(args.repo)
    out_svg, out_png = ROOT / ".github" / "social-preview.svg", ROOT / ".github" / "social-preview.png"
    out_svg.write_text(svg(v), encoding="utf-8")
    print(f"✓ {out_svg.relative_to(ROOT)}")
    if png_pillow(v, out_png) or (shutil.which("convert") and subprocess.run(["convert", str(out_svg), str(out_png)]).returncode == 0):
        print(f"✓ {out_png.relative_to(ROOT)} – jetzt hochladen: Settings → General → Social preview")
    else:
        print("PNG nicht erzeugt (weder Pillow noch ImageMagick) – SVG im Browser öffnen und als PNG speichern.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
