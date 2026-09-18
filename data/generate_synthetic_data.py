"""Generates the synthetic receipt dataset (D-007: no real data). Deterministic given --seed.

Usage: python -m data.generate_synthetic_data --seed 1337 --count 45
"""

import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from data.vendor_pool import CATEGORIES, CURRENCIES, INJECTION_PAYLOAD_TEXT, LAYOUT_TEMPLATES, LINE_ITEMS_BY_CATEGORY, VENDORS

ROOT = Path(__file__).parent / "synthetic_receipts"
GENUINE_DIR = ROOT / "genuine"
TAMPERED_DIR = ROOT / "tampered"
ADVERSARIAL_DIR = ROOT / "adversarial"

CANVAS_SIZE = (400, 600)
Q_BASE = 92
Q_PATCH = 65
POLICY_MAX_TOTAL = 500.00
POLICY_CATEGORY_MAX = {"meals": 100.00, "travel": 1000.00, "office_supplies": 250.00}
POLICY_DISALLOWED = {"alcohol", "gifts"}
POLICY_MAX_AGE_DAYS = 90


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _random_date(rng: random.Random) -> date:
    days_ago = rng.randint(0, 18 * 30)
    return date.today() - timedelta(days=days_ago)


def _build_sample_fields(rng: random.Random) -> dict:
    vendor = rng.choice(VENDORS)
    category = rng.choice(CATEGORIES)
    currency = rng.choice(list(CURRENCIES.keys()))
    layout = rng.choice(LAYOUT_TEMPLATES)
    sample_date = _random_date(rng)

    item_pool = LINE_ITEMS_BY_CATEGORY[category]
    n_items = rng.randint(1, min(5, len(item_pool)))
    chosen = rng.sample(item_pool, n_items)
    line_items = []
    for name, lo, hi in chosen:
        price = round(rng.uniform(lo, hi), 2)
        line_items.append({"description": name, "price": price})
    total = round(sum(i["price"] for i in line_items), 2)

    return {
        "vendor": vendor,
        "category": category,
        "currency": currency,
        "layout_template": layout,
        "date": sample_date.isoformat(),
        "line_items": line_items,
        "total": total,
    }


def _expected_violation(fields: dict) -> tuple[bool, str]:
    if fields["total"] > POLICY_MAX_TOTAL:
        return True, "spend_limit"
    cat_max = POLICY_CATEGORY_MAX.get(fields["category"])
    if cat_max is not None and fields["total"] > cat_max:
        return True, "spend_limit"
    if fields["category"] in POLICY_DISALLOWED:
        return True, "category_restriction"
    age_days = (date.today() - date.fromisoformat(fields["date"])).days
    if age_days > POLICY_MAX_AGE_DAYS:
        return True, "receipt_age"
    return False, ""


def _render_receipt(fields: dict, extra_footer_text: str | None = None, footer_luminance_delta: int | None = None) -> Image.Image:
    img = Image.new("RGB", CANVAS_SIZE, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_body = _font(14)
    font_small = _font(10)

    y = 20
    draw.text((20, y), fields["vendor"], font=font_body, fill=(0, 0, 0))
    y += 24
    draw.text((20, y), fields["date"], font=font_small, fill=(40, 40, 40))
    y += 30

    symbol = CURRENCIES[fields["currency"]]
    for item in fields["line_items"]:
        draw.text((20, y), f"{item['description']}", font=font_small, fill=(0, 0, 0))
        draw.text((300, y), f"{symbol}{item['price']:.2f}", font=font_small, fill=(0, 0, 0))
        y += 20

    y += 10
    draw.text((20, y), "TOTAL", font=font_body, fill=(0, 0, 0))
    draw.text((280, y), f"{symbol}{fields['total']:.2f}", font=font_body, fill=(0, 0, 0))

    if extra_footer_text:
        base = 255
        delta = footer_luminance_delta or 12
        color = (base - delta, base - delta, base - delta)
        # D-037 follow-up: 7px was below RapidOCR's resolvable threshold at this canvas
        # size (confirmed via a real OCR pass — the payload was silently never read).
        # 13px + higher contrast (empirically tested against the real OCR engine) is the
        # smallest/lowest-contrast combination that actually gets read reliably.
        draw.text((20, CANVAS_SIZE[1] - 25), extra_footer_text, font=_font(13), fill=color)

    return img


def _save_jpeg(img: Image.Image, path: Path, quality: int = Q_BASE) -> None:
    img.save(path, "JPEG", quality=quality)


def _tamper(genuine_path: Path, out_path: Path, field: str, fields: dict, rng: random.Random) -> tuple[str, str]:
    img = cv2.imread(str(genuine_path))
    h, w = img.shape[:2]

    if field == "total":
        bbox = (275, 250, w - 10, 280)
        new_total = round(fields["total"] * rng.uniform(1.15, 1.4), 2)
        altered_from, altered_to = str(fields["total"]), str(new_total)
        fields["total"] = new_total
    elif field == "date":
        bbox = (18, 40, 150, 65)
        shifted = date.fromisoformat(fields["date"]) - timedelta(days=rng.randint(100, 400))
        altered_from, altered_to = fields["date"], shifted.isoformat()
        fields["date"] = shifted.isoformat()
    else:  # line_items
        bbox = (18, 88, 280, 108)
        old_desc = fields["line_items"][0]["description"]
        new_desc = old_desc + " (edited)"
        altered_from, altered_to = old_desc, new_desc
        fields["line_items"][0]["description"] = new_desc

    x0, y0, x1, y1 = bbox
    patch = img[y0:y1, x0:x1].copy()
    patch[:] = (255, 255, 255)
    ok, encoded = cv2.imencode(".jpg", patch, [cv2.IMWRITE_JPEG_QUALITY, Q_PATCH])
    patch_recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    img[y0:y1, x0:x1] = patch_recompressed

    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    symbol = CURRENCIES[fields["currency"]]
    if field == "total":
        draw.text((x0, y0), f"{symbol}{fields['total']:.2f}", font=_font(14), fill=(0, 0, 0))
    elif field == "date":
        draw.text((x0, y0), fields["date"], font=_font(10), fill=(40, 40, 40))
    else:
        draw.text((x0, y0), fields["line_items"][0]["description"], font=_font(10), fill=(0, 0, 0))

    _save_jpeg(pil_img, out_path, quality=Q_BASE)
    return altered_from, altered_to


def generate(seed: int, count: int, out_dir: Path | None = None) -> Path:
    rng = random.Random(seed)
    root = out_dir or ROOT
    genuine_dir = root / "genuine"
    tampered_dir = root / "tampered"
    adversarial_dir = root / "adversarial"
    for d in (genuine_dir, tampered_dir, adversarial_dir):
        d.mkdir(parents=True, exist_ok=True)

    rows = []
    field_cycle = ["total", "date", "line_items"]

    for i in range(1, count + 1):
        sample_id = f"S{i:03d}"
        fields = _build_sample_fields(rng)
        img = _render_receipt(fields)
        genuine_path = genuine_dir / f"genuine_{i:03d}.jpg"
        # ~20% of genuine samples get an unrelated re-save pass so "ever recompressed"
        # alone isn't a tell (§4 asymmetry note, ponytail-flagged as a known simplification).
        quality = Q_PATCH if rng.random() < 0.2 else Q_BASE
        _save_jpeg(img, genuine_path, quality=quality)

        violation, rule = _expected_violation(fields)
        rows.append(
            {
                "filename": f"genuine/genuine_{i:03d}.jpg",
                "sample_id": sample_id,
                "genuine_or_tampered": "genuine",
                "altered_field": "none",
                "altered_from": "",
                "altered_to": "",
                "vendor": fields["vendor"],
                "date": fields["date"],
                "total": fields["total"],
                "line_items_json": json.dumps(fields["line_items"]),
                "currency": fields["currency"],
                "category": fields["category"],
                "expected_policy_violation": violation,
                "violated_rule": rule,
                "has_injection_payload": False,
                "injection_payload_text": "",
                "layout_template": fields["layout_template"],
                "seed": seed,
            }
        )

        tampered_fields = json.loads(json.dumps(fields))  # deep copy
        field = field_cycle[(i - 1) % len(field_cycle)]
        tampered_path = tampered_dir / f"tampered_{i:03d}.jpg"
        altered_from, altered_to = _tamper(genuine_path, tampered_path, field, tampered_fields, rng)

        t_violation, t_rule = _expected_violation(tampered_fields)
        rows.append(
            {
                "filename": f"tampered/tampered_{i:03d}.jpg",
                "sample_id": sample_id,
                "genuine_or_tampered": "tampered",
                "altered_field": field,
                "altered_from": altered_from,
                "altered_to": altered_to,
                "vendor": tampered_fields["vendor"],
                "date": tampered_fields["date"],
                "total": tampered_fields["total"],
                "line_items_json": json.dumps(tampered_fields["line_items"]),
                "currency": tampered_fields["currency"],
                "category": tampered_fields["category"],
                "expected_policy_violation": t_violation,
                "violated_rule": t_rule,
                "has_injection_payload": False,
                "injection_payload_text": "",
                "layout_template": tampered_fields["layout_template"],
                "seed": seed,
            }
        )

    # adversarial sample: genuine on financial fields, hidden injection payload in footer
    adv_fields = _build_sample_fields(rng)
    adv_img = _render_receipt(adv_fields, extra_footer_text=INJECTION_PAYLOAD_TEXT, footer_luminance_delta=30)
    adv_path = adversarial_dir / "adversarial_001.jpg"
    _save_jpeg(adv_img, adv_path, quality=Q_BASE)
    adv_violation, adv_rule = _expected_violation(adv_fields)
    rows.append(
        {
            "filename": "adversarial/adversarial_001.jpg",
            "sample_id": "S_ADV_001",
            "genuine_or_tampered": "genuine",
            "altered_field": "none",
            "altered_from": "",
            "altered_to": "",
            "vendor": adv_fields["vendor"],
            "date": adv_fields["date"],
            "total": adv_fields["total"],
            "line_items_json": json.dumps(adv_fields["line_items"]),
            "currency": adv_fields["currency"],
            "category": adv_fields["category"],
            "expected_policy_violation": adv_violation,
            "violated_rule": adv_rule,
            "has_injection_payload": True,
            "injection_payload_text": INJECTION_PAYLOAD_TEXT,
            "layout_template": adv_fields["layout_template"],
            "seed": seed,
        }
    )

    labels_path = root.parent / "labels.csv"
    with open(labels_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return labels_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--count", type=int, default=45)
    args = parser.parse_args()
    path = generate(args.seed, args.count)
    print(f"Wrote {path}")
