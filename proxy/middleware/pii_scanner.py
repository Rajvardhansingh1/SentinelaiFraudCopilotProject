import re

from proxy.schemas import PIIResult

PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "api_key": re.compile(r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{16,}\b", re.I),
}

# D-016/OD-010: Presidio adds NER-based detection on top of the regex patterns
# above. Optional — falls back to regex-only if the model isn't installed
# (spaCy `en_core_web_lg` must be downloaded separately: `python -m spacy download en_core_web_lg`).
#
# D-054 bug fix: Presidio's default recognizer set includes broad, non-PII
# "context" entity types — LOCATION (country/city names, e.g. "France"),
# DATE_TIME, NRP (nationality/religion/political group), URL. Treating any
# of those as "found PII" produces false positives on completely ordinary
# text ("What is the capital of France?" was flagged as containing PII).
# Only genuine identifying-information entity types count here.
_PRESIDIO_PII_ENTITY_TYPES = {
    "person",
    "email_address",
    "phone_number",
    "credit_card",
    "iban_code",
    "ip_address",
    "crypto",
    "medical_license",
    "us_ssn",
    "us_bank_number",
    "us_driver_license",
    "us_passport",
    "us_itin",
    "uk_nhs",
    "au_abn",
    "au_acn",
    "au_tfn",
    "au_medicare",
    "sg_nric_fin",
    "in_aadhaar",
    "in_pan",
}

_presidio_analyzer = None
_presidio_checked = False


def _get_presidio_analyzer():
    global _presidio_analyzer, _presidio_checked
    if _presidio_checked:
        return _presidio_analyzer
    _presidio_checked = True
    try:
        from presidio_analyzer import AnalyzerEngine

        _presidio_analyzer = AnalyzerEngine()
    except Exception:
        _presidio_analyzer = None
    return _presidio_analyzer


def _presidio_results(text: str) -> list:
    """Raw Presidio matches, already filtered to real-PII entity types —
    carries start/end so redact_pii can strip the exact matched span."""
    analyzer = _get_presidio_analyzer()
    if analyzer is None:
        return []
    results = analyzer.analyze(text=text, language="en")
    return [r for r in results if r.entity_type.lower() in _PRESIDIO_PII_ENTITY_TYPES]


def _presidio_types(text: str) -> list[str]:
    return sorted({r.entity_type.lower() for r in _presidio_results(text)})


def check_pii(text: str) -> PIIResult:
    regex_types = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    all_types = sorted(set(regex_types) | set(_presidio_types(text)))
    return PIIResult(found=bool(all_types), redacted=False, types=all_types)


def redact_pii(text: str) -> tuple[str, PIIResult]:
    """Redacts every matched span — both regex hits and Presidio hits (using
    Presidio's own start/end offsets) — so `redacted=True` is never claimed
    without the underlying text actually being stripped (D-054: previously a
    Presidio-only match like a person's name left the text untouched while
    still reporting redacted=True)."""
    result = check_pii(text)
    if not result.found:
        return text, result

    spans: list[tuple[int, int, str]] = []
    for name, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            spans.append((m.start(), m.end(), name.upper()))
    for r in _presidio_results(text):
        spans.append((r.start, r.end, r.entity_type.upper()))

    # Single left-to-right pass over the ORIGINAL text's offsets — never
    # mutate the string in place while indexing into it with old offsets.
    # Longest span first at a given start so a longer overlapping match
    # (e.g. a multi-word Presidio PERSON span) wins over a shorter one.
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    pieces: list[str] = []
    cursor = 0
    for start, end, label in spans:
        if start < cursor:
            continue  # overlaps a span already emitted
        pieces.append(text[cursor:start])
        pieces.append(f"[REDACTED_{label}]")
        cursor = end
    pieces.append(text[cursor:])

    return "".join(pieces), result.model_copy(update={"redacted": True})
