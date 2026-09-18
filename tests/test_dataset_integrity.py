import csv
import json
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).parent.parent
LABELS_PATH = ROOT / "data" / "labels.csv"
RECEIPTS_DIR = ROOT / "data" / "synthetic_receipts"
POLICY_PATH = ROOT / "agents" / "policies" / "expense_policy.yaml"


def _load_rows() -> list[dict]:
    with open(LABELS_PATH, newline="") as f:
        return list(csv.DictReader(f))


def test_every_filename_resolves_to_an_existing_file():
    rows = _load_rows()
    for row in rows:
        assert (RECEIPTS_DIR / row["filename"]).is_file(), row["filename"]


def test_genuine_and_tampered_counts_match_and_are_in_band():
    rows = _load_rows()
    genuine = [r for r in rows if r["genuine_or_tampered"] == "genuine" and not r["filename"].startswith("adversarial")]
    tampered = [r for r in rows if r["genuine_or_tampered"] == "tampered"]
    assert 40 <= len(genuine) <= 60
    assert len(genuine) == len(tampered)


def test_every_image_opens_as_valid_jpeg():
    rows = _load_rows()
    for row in rows:
        with Image.open(RECEIPTS_DIR / row["filename"]) as img:
            img.verify()


def test_genuine_samples_are_not_byte_identical():
    rows = [r for r in _load_rows() if r["genuine_or_tampered"] == "genuine" and not r["filename"].startswith("adversarial")]
    sizes = {(RECEIPTS_DIR / r["filename"]).stat().st_size for r in rows[:10]}
    assert len(sizes) > 1


def test_directory_matches_genuine_or_tampered_label():
    rows = _load_rows()
    for row in rows:
        if row["filename"].startswith("adversarial"):
            continue
        expected_dir = row["genuine_or_tampered"]
        assert row["filename"].startswith(expected_dir + "/")


def test_tampered_rows_have_alteration_details_genuine_rows_do_not():
    rows = _load_rows()
    for row in rows:
        if row["genuine_or_tampered"] == "tampered":
            assert row["altered_field"] != "none"
            assert row["altered_from"] != ""
            assert row["altered_to"] != ""
        else:
            assert row["altered_field"] == "none"


def test_policy_violation_flag_and_rule_are_consistent():
    rows = _load_rows()
    for row in rows:
        violation = row["expected_policy_violation"] == "True"
        rule = row["violated_rule"]
        assert violation == bool(rule), row["sample_id"]


def test_exactly_one_row_has_injection_payload():
    rows = _load_rows()
    flagged = [r for r in rows if r["has_injection_payload"] == "True"]
    assert len(flagged) == 1
    assert flagged[0]["injection_payload_text"]


def test_categories_exist_in_policy_yaml():
    with open(POLICY_PATH) as f:
        policy = yaml.safe_load(f)
    valid_categories = set(policy["spend_limits"]["category_max"]) | set(policy["category_restrictions"]["disallowed_categories"])
    rows = _load_rows()
    for row in rows:
        assert row["category"] in valid_categories, row["category"]


def test_line_items_json_is_parseable():
    rows = _load_rows()
    for row in rows:
        items = json.loads(row["line_items_json"])
        assert isinstance(items, list)
        assert len(items) >= 1
