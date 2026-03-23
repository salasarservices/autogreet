"""Poster composition engine using Pillow."""
from __future__ import annotations

import io
import logging
import os
from datetime import date
from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from image_tools import (
    ordinal,
    fetch_image_bytes,
    prepare_birthday_photo,
    prepare_anniversary_photo,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Font loading — cached so TTF is only parsed once per (path, size) pair
# ---------------------------------------------------------------------------

@lru_cache(maxsize=32)
def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError) as exc:
            logger.warning("Could not load font %r at size %d: %s", path, size, exc)
    return ImageFont.load_default()


def _hex_to_rgb(hex_colour: str) -> tuple[int, int, int]:
    """Convert '#RRGGBB' or 'RRGGBB' to (R, G, B). Falls back to white."""
    h = hex_colour.strip().lstrip("#")
    if len(h) == 6:
        try:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            pass
    logger.warning("Invalid hex colour %r — defaulting to white", hex_colour)
    return (255, 255, 255)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _build_text_lines(emp: dict, poster_type: str) -> list[tuple[str, str]]:
    """Return [(line_text, weight), ...] for the text block."""
    name = emp.get("name") or ""
    designation = emp.get("designation") or ""
    vertical = emp.get("vertical") or ""
    department = emp.get("department") or ""
    location = emp.get("location") or ""

    name = name.title() if poster_type == "birthday" else name.upper()
    line3 = f"{vertical} – {department}" if vertical and department else vertical or department

    return [
        (name, "bold"),
        (designation, "regular"),
        (line3, "regular"),
        (location, "regular"),
    ]


def _fit_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
              max_width: int) -> str:
    """Truncate text with ellipsis if it would exceed max_width pixels."""
    if not text:
        return text
    try:
        bbox = font.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return text
        # Binary-search for the longest fitting prefix
        ellipsis = "…"
        lo, hi = 0, len(text)
        while lo < hi - 1:
            mid = (lo + hi) // 2
            candidate = text[:mid] + ellipsis
            w = font.getbbox(candidate)[2]
            if w <= max_width:
                lo = mid
            else:
                hi = mid
        return text[:lo] + ellipsis
    except Exception:
        return text


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    lines: list[tuple[str, str]],
    cfg: dict,
    fonts: dict,
    text_colour: tuple[int, int, int],
    max_width: int = 600,
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

        safe_text = _fit_text(text, font, max_width)
        draw.text((x, y), safe_text, font=font, fill=text_colour)
        y += spacing


# ---------------------------------------------------------------------------
# Birthday poster
# ---------------------------------------------------------------------------

def _place_birthday_photo(base: Image.Image, photo: Image.Image, box: dict) -> Image.Image:
    """Place transparent-background birthday photo — contain-fit, bottom-left anchor."""
    bx, by, bw, bh = box["x"], box["y"], box["w"], box["h"]
    scale = min(bw / photo.width, bh / photo.height)
    new_w = round(photo.width * scale)
    new_h = round(photo.height * scale)
    photo_scaled = photo.resize((new_w, new_h), Image.LANCZOS)

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
    text_colour = _hex_to_rgb(b_cfg.get("text_colour", "#FFFFFF"))
    template_path = b_cfg.get("template", "assets/templates/birthday.png")
    base = Image.open(template_path).convert("RGBA")

    photo_url = emp.get("photo_url", "")
    if photo_url:
        try:
            img_bytes = fetch_image_bytes(photo_url)
            photo = prepare_birthday_photo(img_bytes, secrets.get("withoutbg_api_key", ""))
            base = _place_birthday_photo(base, photo, b_cfg["photo_box"])
        except Exception as exc:
            logger.warning("Birthday photo failed for %r: %s", emp.get("name"), exc)

    draw = ImageDraw.Draw(base)
    lines = _build_text_lines(emp, "birthday")
    poster_w = base.size[0]
    text_max_w = poster_w - b_cfg["text_block"]["x"] - 20
    _draw_text_block(draw, lines, b_cfg["text_block"], fonts, text_colour, max_width=text_max_w)
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
    text_colour = _hex_to_rgb(a_cfg.get("text_colour", "#FFFFFF"))
    template_path = a_cfg.get("template", "assets/templates/anniversary.png")
    base = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(base)

    # Years completed — correct calculation
    doj = emp.get("doj")
    years = 0
    if doj:
        years = today.year - doj.year - (
            (today.month, today.day) < (doj.month, doj.day)
        )

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
        fill=text_colour,
    )

    photo_box = a_cfg["photo_box"]
    photo_url = emp.get("photo_url", "")
    if photo_url:
        try:
            img_bytes = fetch_image_bytes(photo_url)
            photo = prepare_anniversary_photo(img_bytes, "", photo_box["w"], photo_box["h"])
            base.paste(
                photo.convert("RGBA"),
                (photo_box["x"], photo_box["y"]),
                photo.convert("RGBA"),
            )
        except Exception as exc:
            logger.warning("Anniversary photo failed for %r: %s", emp.get("name"), exc)

    lines = _build_text_lines(emp, "anniversary")
    poster_w = base.size[0]
    text_max_w = poster_w - a_cfg["text_block"]["x"] - 20
    _draw_text_block(draw, lines, a_cfg["text_block"], fonts, text_colour, max_width=text_max_w)
    return base


# ---------------------------------------------------------------------------
# Output helper
# ---------------------------------------------------------------------------

def poster_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
