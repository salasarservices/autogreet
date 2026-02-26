"""Image utilities: background removal, face-aware crop, ordinal helper."""
from __future__ import annotations

import io
import time
import requests
from PIL import Image


# ---------------------------------------------------------------------------
# Ordinal helper
# ---------------------------------------------------------------------------

def ordinal(n: int) -> str:
    """Return ordinal string for a positive integer (e.g. 1 -> '1st')."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# Background removal via withoutbg SDK
# ---------------------------------------------------------------------------

def remove_background(image_bytes: bytes, api_key: str, retries: int = 3) -> Image.Image:
    """Remove image background using the withoutbg Python SDK.

    Falls back to the raw image if the API call fails after retries.
    """
    try:
        from withoutbg import WithoutBg  # type: ignore
    except ImportError:
        # SDK not installed – return image as-is
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    for attempt in range(retries):
        try:
            client = WithoutBg(api_key=api_key)
            result_bytes = client.remove_background(image_bytes)
            return Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        except Exception as exc:  # noqa: BLE001
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                # Exhausted retries – return original
                return Image.open(io.BytesIO(image_bytes)).convert("RGBA")


def fetch_image_bytes(url: str, timeout: int = 15) -> bytes:
    """Download an image from a URL and return raw bytes."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Face-aware cover crop (MediaPipe with upward-biased fallback)
# ---------------------------------------------------------------------------

def _face_aware_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Crop *img* to *target_w x target_h* with face prominence.

    Strategy:
    1. Detect face with MediaPipe FaceDetection.
    2. Center horizontally on face centre; position vertically so face is in
       upper third of the crop box.
    3. Fall back to upward-biased centre crop if no face detected.
    """
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = round(src_w * scale)
    new_h = round(src_h * scale)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Try MediaPipe face detection
    cx, cy = _detect_face_center(img_resized)

    if cx is None:
        # Upward-biased fallback: centre horizontally, bias upward 30 %
        cx = new_w // 2
        cy = int(new_h * 0.35)

    # Compute crop box centred on (cx, cy) but clamped inside image
    left = max(0, min(cx - target_w // 2, new_w - target_w))
    top = max(0, min(cy - target_h // 3, new_h - target_h))

    return img_resized.crop((left, top, left + target_w, top + target_h))


def _detect_face_center(img: Image.Image) -> tuple[int | None, int | None]:
    """Return (cx, cy) of the first detected face in pixel coords, or (None, None)."""
    try:
        import mediapipe as mp  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return None, None

    mp_face = mp.solutions.face_detection  # type: ignore[attr-defined]
    rgb = img.convert("RGB")
    arr = np.array(rgb)

    with mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.4) as detector:
        results = detector.process(arr)

    if not results.detections:
        return None, None

    detection = results.detections[0]
    bbox = detection.location_data.relative_bounding_box
    w, h = img.size
    cx = int((bbox.xmin + bbox.width / 2) * w)
    cy = int((bbox.ymin + bbox.height / 2) * h)
    return cx, cy


def prepare_anniversary_photo(
    image_bytes: bytes, target_w: int, target_h: int
) -> Image.Image:
    """Cover-crop an employee photo for the anniversary poster."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    return _face_aware_crop(img, target_w, target_h)


def prepare_birthday_photo(
    image_bytes: bytes, api_key: str
) -> Image.Image:
    """Return a transparent-background cutout for the birthday poster."""
    return remove_background(image_bytes, api_key)
