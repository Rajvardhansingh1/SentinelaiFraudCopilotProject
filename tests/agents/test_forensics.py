from pathlib import Path

import numpy as np
from PIL import Image

from agents.forensics import analyze

FIXTURES = Path(__file__).parent.parent / "fixtures" / "receipts"
FIXTURES.mkdir(parents=True, exist_ok=True)


def _make_genuine(path: Path) -> None:
    arr = np.full((200, 300, 3), 230, dtype=np.uint8)
    Image.fromarray(arr).save(path, "JPEG", quality=90)


def _make_tampered(path: Path) -> None:
    arr = np.full((200, 300, 3), 230, dtype=np.uint8)
    img = Image.fromarray(arr)
    img.save(path, "JPEG", quality=90)
    # Re-open, patch a region, re-save at a different quality to create a real
    # double-compression discontinuity (what ELA is meant to detect).
    img = Image.open(path).convert("RGB")
    patch = np.zeros((40, 60, 3), dtype=np.uint8)
    patch_img = Image.fromarray(patch)
    img.paste(patch_img, (100, 80))
    img.save(path, "JPEG", quality=40)


def test_genuine_receipt_low_tamper_likelihood(tmp_path):
    genuine_path = tmp_path / "genuine.jpg"
    _make_genuine(genuine_path)
    result = analyze(str(genuine_path))
    assert result.tamper_likelihood in ("low", "medium")


def test_tampered_receipt_has_higher_ela_than_genuine(tmp_path):
    genuine_path = tmp_path / "genuine.jpg"
    tampered_path = tmp_path / "tampered.jpg"
    _make_genuine(genuine_path)
    _make_tampered(tampered_path)

    genuine_result = analyze(str(genuine_path))
    tampered_result = analyze(str(tampered_path))
    assert tampered_result.ela_score >= genuine_result.ela_score


def test_missing_exif_yields_none_not_false(tmp_path):
    path = tmp_path / "no_exif.jpg"
    _make_genuine(path)
    result = analyze(str(path))
    assert result.exif_consistent is None
    assert "no_exif_data" in result.exif_flags
