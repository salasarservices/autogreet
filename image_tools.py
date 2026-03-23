"""Image utilities: background removal, face-aware crop, ordinal helper."""
from __future__ import annotations

import io
import logging
from typing import Literal

import requests
from PIL import Image

logger = logging.getLogger(__name__)


def ordinal(n: int) -> str:
    """Return ordinal string for integer n (1 → '1st', 11 → '11th', etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def fetch_image_bytes(url: str) -> bytes:
    """Download an image from *url* and return raw bytes."""
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.content


def remove_background(img_bytes: bytes, api_key: str) -> Image.Image:
    """
    Remove background via withoutbg.com API.
    Returns a PIL Image with transparency (RGBA).
    Raises RuntimeError if the API call fails.
    """
    resp = requests.post(
        "https://api.withoutbg.com/v1.0/image-without-background",
        headers={"X-API-Key": api_key},
        files={"image": ("photo.jpg", img_bytes, "image/jpeg")},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Background removal API returned {resp.status_code}: {resp.text[:200]}"
        )
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")


def _face_crop_box(img: Image.Image, target_w: int, target_h: int) -> tuple[int, int, int, int]:
    """
    Return a (left, upper, right, lower) crop box that:
    - fills target_w × target_h exactly (cover-fit)
    - biases toward the top third of the image to keep faces in frame
    """
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    scaled_w = round(src_w * scale)
    scaled_h = round(src_h * scale)

    # Horizontal centre
    left = (scaled_w - target_w) // 2
    # Vertical: bias to top 35 % so face stays in frame
    top = round((scaled_h - target_h) * 0.35)

    return (left, top, left + target_w, top + target_h)


def prepare_birthday_photo(img_bytes: bytes, api_key: str) -> Image.Image:
    """
    Prepare a birthday photo:
    - remove background (best-effort; falls back to original if API unavailable)
    - return RGBA image, original size
    """
    if api_key:
        try:
            return remove_background(img_bytes, api_key)
        except Exception as exc:
            logger.warning("Background removal failed (using original): %s", exc)

    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    return img


def prepare_anniversary_photo(img_bytes: bytes, api_key: str, target_w: int, target_h: int) -> Image.Image:
    """
    Prepare an anniversary photo:
    - cover-crop to target dimensions with face-aware top bias
    - return RGB image
    """
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    scaled = img.resize((round(src_w * scale), round(src_h * scale)), Image.LANCZOS)
    box = _face_crop_box(scaled, target_w, target_h)
    return scaled.crop(box)
