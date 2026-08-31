#!/usr/bin/env python3
"""Regenerate the Open Graph social card and touch icon.

The card carries the current role as pixels, so it has to be rebuilt whenever
the title or affiliation in `_config.yml` changes -- otherwise link previews
keep advertising an old job. Reads the profile straight out of `_config.yml`
so there is only one place to edit.

    pip install Pillow PyYAML
    python scripts/make_social_card.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img"

# Preferred display/text faces, with fallbacks to fonts present on most Linux
# boxes and on GitHub's runners. Any OFL/DejaVu face renders acceptably.
FONT_DIRS = [
    Path("/mnt/skills/examples/canvas-design/canvas-fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/freefont"),
]
DISPLAY_BOLD = ["Outfit-Bold.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"]
TEXT_BOLD = ["InstrumentSans-Bold.ttf", "DejaVuSans-Bold.ttf", "FreeSansBold.ttf"]
TEXT_REGULAR = ["InstrumentSans-Regular.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]

INK = (7, 11, 20)
TEAL = (78, 224, 193)
TEXT = (232, 238, 251)
DIM = (167, 184, 212)
MUTE = (114, 134, 166)
LINK = (89, 164, 255)


def font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        for directory in FONT_DIRS:
            path = directory / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    raise SystemExit(f"none of {candidates} found in {[str(d) for d in FONT_DIRS]}")


def isobar_layer(size: tuple[int, int], lines: int = 26, alpha_scale: float = 0.75) -> Image.Image:
    """The streamline motif the live hero canvas draws, rendered statically."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    width, height = size
    for i in range(lines):
        r = i / (lines - 1)
        base = height * (0.02 + r * 1.02)
        amp = height * (0.05 + 0.07 * math.sin(r * math.pi))
        if r < 0.5:                                     # teal -> azure
            t = r * 2
            colour = (int(78 + 11 * t), int(224 - 60 * t), int(193 + 62 * t))
        else:                                           # azure -> violet
            t = (r - 0.5) * 2
            colour = (int(89 + 78 * t), int(164 - 25 * t), int(255 - 5 * t))
        alpha = int(90 * alpha_scale * (0.3 + 0.7 * math.sin(r * math.pi)))
        points = []
        for x in range(-20, width + 21, 8):
            u = x / width
            y = (base
                 + amp * math.sin(u * 4.1 + r * 3.4)
                 + amp * 0.55 * math.sin(u * 9.3 + r * 1.6)
                 + amp * 0.30 * math.cos(u * 2.2))
            points.append((x, y))
        draw.line(points, fill=colour + (alpha,), width=2)
    return layer


def main() -> int:
    profile = (yaml.safe_load((ROOT / "_config.yml").read_text(encoding="utf-8")) or {}).get("profile", {})
    # Follow whatever `profile.photo` points at, rather than a fixed filename.
    # The path was hardcoded, so changing the portrait in _config.yml left the
    # card advertising the previous photo.
    photo = (profile.get("photo") or "/assets/img/kwesi-quagraine.jpg").lstrip("/")
    portrait_path = ROOT / photo
    if not portrait_path.exists():
        raise SystemExit(f"missing {portrait_path} (profile.photo in _config.yml)")
    print(f"portrait: {portrait_path.relative_to(ROOT)}")

    W, H = 1200, 630
    card = Image.new("RGB", (W, H), INK)

    glow = Image.new("RGB", (W, H), INK)
    gd = ImageDraw.Draw(glow)
    for radius, centre, colour in ((520, (200, 120), (14, 60, 58)), (480, (980, 90), (44, 30, 80))):
        gd.ellipse([centre[0] - radius, centre[1] - radius, centre[0] + radius, centre[1] + radius], fill=colour)
    card = Image.blend(card, glow.filter(ImageFilter.GaussianBlur(140)), 0.85)

    lines = isobar_layer((W, H))
    card.paste(lines, (0, 0), lines)

    inset_w, inset_h = 300, 360
    # Cover-fit rather than stretch: the two portraits used so far have had
    # different aspect ratios, and resize() alone would distort the face.
    src = Image.open(portrait_path).convert("RGB")
    scale = max(inset_w / src.width, inset_h / src.height)
    scaled = src.resize((max(1, round(src.width * scale)), max(1, round(src.height * scale))), Image.LANCZOS)
    left = (scaled.width - inset_w) // 2
    top = int((scaled.height - inset_h) * 0.12)          # bias upward, towards the face
    face = scaled.crop((left, top, left + inset_w, top + inset_h))
    mask = Image.new("L", (inset_w, inset_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inset_w - 1, inset_h - 1], radius=28, fill=255)
    card.paste(face, (W - inset_w - 70, (H - inset_h) // 2), mask)

    d = ImageDraw.Draw(card)
    display = font(DISPLAY_BOLD, 92)

    eyebrow = f"{profile.get('role', '')} · {profile.get('affiliation_short', '')}".upper()
    d.text((72, 118), eyebrow, font=font(TEXT_BOLD, 22), fill=(120, 200, 200))

    d.text((72, 170), "Kwesi", font=display, fill=TEXT)
    d.text((72 + d.textlength("Kwesi ", font=display), 170), "A.", font=display, fill=TEAL)
    d.text((72, 262), "Quagraine", font=display, fill=TEXT)

    body = font(TEXT_REGULAR, 26)
    d.text((72, 390), f"{profile.get('role', '')}, {profile.get('affiliation', '')}", font=body, fill=DIM)
    secondary = profile.get("secondary_role")
    if secondary:
        d.text((72, 428),
               f"{secondary}, {profile.get('secondary_affiliation_short', '')} · {profile.get('location', '')}",
               font=body, fill=DIM)

    small = font(TEXT_BOLD, 20)
    d.text((72, 508), f"ORCID {profile.get('orcid', '')}", font=small, fill=MUTE)
    d.text((72, 540), "akumenyi.github.io", font=small, fill=LINK)

    card.save(OUT / "social-card.png", optimize=True)
    print(f"wrote {OUT / 'social-card.png'} ({(OUT / 'social-card.png').stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
