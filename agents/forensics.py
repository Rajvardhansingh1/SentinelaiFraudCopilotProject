from typing import Literal

import cv2
import numpy as np
from pydantic import BaseModel

ELA_QUALITY = 90
ELA_BLOCK_SIZE = 16
# D-025: thresholds calibrated against the Phase 5 synthetic dataset's max-block-residual
# score, not the old whole-image-mean score (see D-025 for why that changed).
ELA_HIGH_THRESHOLD = 0.0095
ELA_MEDIUM_THRESHOLD = 0.0085

EDITOR_SOFTWARE_MARKERS = ("photoshop", "gimp", "paint.net", "affinity")


class ForensicsResult(BaseModel):
    """Agents-local per D-021 — never validated through /v1/generate (D-003)."""

    ela_score: float
    exif_consistent: bool | None
    exif_flags: list[str] = []
    tamper_likelihood: Literal["low", "medium", "high"]


def _ela_score(image_path: str) -> float:
    """Max-block-residual ELA (D-025): a tampered region is typically a small fraction
    of the image, so a whole-image mean diff drowns the localized recompression
    discontinuity in uniform background noise. Splitting into blocks and taking the
    max block mean isolates the edited region instead."""
    original = cv2.imread(image_path)
    if original is None:
        raise ValueError(f"could not read image: {image_path}")
    ok, encoded = cv2.imencode(".jpg", original, [cv2.IMWRITE_JPEG_QUALITY, ELA_QUALITY])
    if not ok:
        raise ValueError(f"could not re-encode image: {image_path}")
    recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    diff = cv2.absdiff(original, recompressed).astype(np.float32) / 255.0

    h, w = diff.shape[:2]
    block = ELA_BLOCK_SIZE
    block_means = [
        diff[y : y + block, x : x + block].mean()
        for y in range(0, h - block + 1, block)
        for x in range(0, w - block + 1, block)
    ]
    return float(max(block_means)) if block_means else float(diff.mean())


def _exif_check(image_path: str) -> tuple[bool | None, list[str]]:
    try:
        import exifread

        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
    except Exception:
        return None, ["no_exif_data"]

    if not tags:
        return None, ["no_exif_data"]

    flags: list[str] = []
    software = str(tags.get("Image Software", "")).lower()
    if any(marker in software for marker in EDITOR_SOFTWARE_MARKERS):
        flags.append("editor_software_detected")

    original_dt = tags.get("EXIF DateTimeOriginal")
    modify_dt = tags.get("Image DateTime")
    if original_dt and modify_dt and str(original_dt) != str(modify_dt):
        flags.append("create_modify_date_mismatch")

    return (len(flags) == 0), flags


def _tamper_likelihood(ela: float, exif_flags: list[str]) -> Literal["low", "medium", "high"]:
    if ela >= ELA_HIGH_THRESHOLD or "editor_software_detected" in exif_flags:
        return "high"
    if ela >= ELA_MEDIUM_THRESHOLD or "create_modify_date_mismatch" in exif_flags:
        return "medium"
    return "low"


def analyze(image_path: str) -> ForensicsResult:
    ela = _ela_score(image_path)
    exif_consistent, exif_flags = _exif_check(image_path)
    return ForensicsResult(
        ela_score=ela,
        exif_consistent=exif_consistent,
        exif_flags=exif_flags,
        tamper_likelihood=_tamper_likelihood(ela, exif_flags),
    )
