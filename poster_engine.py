"""Poster composition engine using Pillow."""
from __future__ import annotations

import io
import os
from datetime import date
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from image_tools import (
    ordinal,
    fetch_image_bytes,
    prepare_birthday_photo,
    prepare_anniversary_photo,
)


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Text block helpers
# ---------------------------------------------------------------------------

def _build_text_lines(emp: dict, poster_type: str) -> list[tuple[str, str]]:
    """Return [(line_text, weight), ...] for the 4-line text block."""
    name = emp["name"] or ""
    designation = emp["designation"] or ""
    vertical = emp["vertical"] or ""
    department = emp["department"] or ""
    location = emp["location"] or ""

    if poster_type == "birthday":
        name = name.title()
    else:
        name = name.upper()

    line3 = f"{vertical} - {department}" if vertical and department else vertical or department

    return [
        (name, "bold"),
        (designation, "regular"),
        (line3, "regular"),
        (location, "regular"),
    ]


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    lines: list[tuple[str, str]],
    cfg: dict,
    fonts: dict,
) -> None:
    x = cfg["x"]
    y = cfg["y"]
    spacing = cfg.get("line_spacing", 48)
    size_name = cfg.get("font_size_name", 38)
    size_detail = cfg.get("font_size_detail", 26)

    for i, (text, weight) in enumerate(lines):
        if i == 0:
            font = _load_font(fonts.get("bold") or fonts.get("regular", ""), size_name)
        else:
            font = _load_font(fonts.get("regular", ""), size_detail)
        draw.text((x, y), text, font=font, fill=(255, 255, 255))
        y += spacing


# ---------------------------------------------------------------------------
# Birthday poster
# ---------------------------------------------------------------------------

def _place_birthday_photo(
    base: Image.Image,
    photo: Image.Image,
    box: dict,
) -> Image.Image:
    """Place transparent-background birthday photo with contain-fit, bottom-left anchor."""
    bx, by, bw, bh = box["x"], box["y"], box["w"], box["h"]

    # Contain fit
    scale = min(bw / photo.width, bh / photo.height)
    new_w = round(photo.width * scale)
    new_h = round(photo.height * scale)
    photo_scaled = photo.resize((new_w, new_h), Image.LANCZOS)

    # Bottom-left anchor
    paste_x = bx
    paste_y = by + bh - new_h

    if photo_scaled.mode == "RGBA":
        base.paste(photo_scaled, (paste_x, paste_y), photo_scaled)
    else:
        base.paste(photo_scaled, (paste_x, paste_y))
    return base


def generate_birthday_poster(
    emp: dict,
    cfg: dict,
    secrets: dict,
    today: date | None = None,
) -> Image.Image:
    """Compose and return a birthday poster Image for *emp*."""
    b_cfg = cfg["birthday"]
    fonts = cfg.get("fonts", {})

    template_path = b_cfg.get("template", "assets/templates/birthday.png")
    base = Image.open(template_path).convert("RGBA")

    # Employee photo
    photo_url = emp.get("photo_url", "")
    if photo_url:
        try:
            img_bytes = fetch_image_bytes(photo_url)
            photo = prepare_birthday_photo(img_bytes, secrets.get("withoutbg_api_key", ""))
            base = _place_birthday_photo(base, photo, b_cfg["photo_box"])
        except Exception:  # noqa: BLE001
            pass  # Photo is best-effort

    # Text block
    draw = ImageDraw.Draw(base)
    lines = _build_text_lines(emp, "birthday")
    _draw_text_block(draw, lines, b_cfg["text_block"], fonts)

    return base


# ---------------------------------------------------------------------------
# Anniversary poster
# ---------------------------------------------------------------------------

def generate_anniversary_poster(
    emp: dict,
    cfg: dict,
    secrets: dict,
    today: date | None = None,
) -> Image.Image:
    """Compose and return an anniversary poster Image for *emp*."""
    if today is None:
        today = date.today()

    a_cfg = cfg["anniversary"]
    fonts = cfg.get("fonts", {})

    template_path = a_cfg.get("template", "assets/templates/anniversary.png")
    base = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(base)

    # Years completed
    doj = emp.get("doj")
    years = 0
    if doj:
        years = today.year - doj.year

    # Ordinal year label
    year_lbl_cfg = a_cfg.get("year_label", {})
    year_font = _load_font(
        fonts.get("year") or fonts.get("bold") or fonts.get("regular", ""),
        year_lbl_cfg.get("font_size", 64),
    )
    ordinal_str = ordinal(years)
    draw.text(
        (year_lbl_cfg.get("x", 80), year_lbl_cfg.get("y", 80)),
        ordinal_str,
        font=year_font,
        fill=(255, 255, 255),
    )

    # Employee photo (face-aware cover crop)
    photo_box = a_cfg["photo_box"]
    photo_url = emp.get("photo_url", "")
    if photo_url:
        try:
            img_bytes = fetch_image_bytes(photo_url)
            photo = prepare_anniversary_photo(
                img_bytes, photo_box["w"], photo_box["h"]
            )
            base.paste(
                photo.convert("RGBA"),
                (photo_box["x"], photo_box["y"]),
                photo.convert("RGBA"),
            )
        except Exception:  # noqa: BLE001
            pass

    # Text block
    lines = _build_text_lines(emp, "anniversary")
    _draw_text_block(draw, lines, a_cfg["text_block"], fonts)

    return base


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------

def poster_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
