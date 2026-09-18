import re

from proxy.schemas import PIIResult

PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "api_key": re.compile(r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{16,}\b", re.I),
}

# D-016/OD-010: Presidio adds NER-based PERSON/LOCATION/etc detection on top of the
# regex patterns above. Optional — falls back to regex-only if the model isn't installed
# (spaCy `en_core_web_lg` must be downloaded separately: `python -m spacy download en_core_web_lg`).
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


def _presidio_types(text: str) -> list[str]:
    analyzer = _get_presidio_analyzer()
    if analyzer is None:
        return []
    results = analyzer.analyze(text=text, language="en")
    return sorted({r.entity_type.lower() for r in results})


def check_pii(text: str) -> PIIResult:
    regex_types = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    all_types = sorted(set(regex_types) | set(_presidio_types(text)))
    return PIIResult(found=bool(all_types), redacted=False, types=all_types)


def redact_pii(text: str) -> tuple[str, PIIResult]:
    result = check_pii(text)
    redacted = text
    for name, pattern in PATTERNS.items():
        if name in result.types:
            redacted = pattern.sub(f"[REDACTED_{name.upper()}]", redacted)
    return redacted, result.model_copy(update={"redacted": result.found})
