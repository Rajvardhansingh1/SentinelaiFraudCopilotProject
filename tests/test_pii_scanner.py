from proxy.middleware import pii_scanner
from proxy.middleware.pii_scanner import check_pii, redact_pii


def test_clean_text_not_flagged():
    result = check_pii("The total was 42.50 for office supplies.")
    assert result.found is False


def test_email_detected():
    result = check_pii("Contact me at jane.doe@example.com for details.")
    assert result.found is True
    assert "email" in result.types


def test_api_key_detected():
    result = check_pii("here is my key sk-ABCDEFGHIJKLMNOPQRST")
    assert "api_key" in result.types


def test_redact_removes_email():
    redacted, result = redact_pii("Contact jane.doe@example.com now")
    assert "jane.doe@example.com" not in redacted
    assert result.redacted is True


def test_presidio_absent_falls_back_to_regex_only(monkeypatch):
    monkeypatch.setattr(pii_scanner, "_presidio_checked", False)
    monkeypatch.setattr(pii_scanner, "_presidio_analyzer", None)
    result = check_pii("email me at jane.doe@example.com")
    assert "email" in result.types


def test_presidio_results_merged_when_available(monkeypatch):
    class FakeEntity:
        entity_type = "PERSON"
        start = 0
        end = 10

    class FakeAnalyzer:
        def analyze(self, text, language):
            return [FakeEntity()]

    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: FakeAnalyzer())
    result = check_pii("John Smith submitted this claim")
    assert "person" in result.types


# --- D-054 regression: Presidio's broad "context" entity types (LOCATION,
# DATE_TIME, NRP, URL) must never count as PII on their own — a real
# Presidio version bump flagged "France" in "What is the capital of
# France?" as LOCATION, treating an ordinary question as containing PII. ---


def _fake_analyzer_returning(entity_type, start=0, end=6):
    class FakeEntity:
        pass

    e = FakeEntity()
    e.entity_type = entity_type
    e.start = start
    e.end = end

    class FakeAnalyzer:
        def analyze(self, text, language):
            return [e]

    return FakeAnalyzer()


def test_presidio_location_entity_not_flagged_as_pii(monkeypatch):
    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: _fake_analyzer_returning("LOCATION"))
    result = check_pii("What is the capital of France?")
    assert result.found is False
    assert result.types == []


def test_presidio_date_time_entity_not_flagged_as_pii(monkeypatch):
    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: _fake_analyzer_returning("DATE_TIME"))
    result = check_pii("The meeting is next Tuesday.")
    assert result.found is False


def test_presidio_nrp_entity_not_flagged_as_pii(monkeypatch):
    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: _fake_analyzer_returning("NRP"))
    result = check_pii("She is French.")
    assert result.found is False


def test_presidio_url_entity_not_flagged_as_pii(monkeypatch):
    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: _fake_analyzer_returning("URL"))
    result = check_pii("See https://example.com for details.")
    assert result.found is False


def test_presidio_us_ssn_entity_still_flagged_as_pii(monkeypatch):
    """The allowlist must not become so strict it drops real identifiers."""
    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: _fake_analyzer_returning("US_SSN"))
    result = check_pii("123-45-6789")
    assert result.found is True
    assert "us_ssn" in result.types


def test_redact_pii_actually_strips_presidio_only_detected_span(monkeypatch):
    """D-054: redact_pii previously reported redacted=True while leaving a
    Presidio-only match (no regex pattern for it) untouched in the text."""
    text = "Reach out to John Doe about the claim."
    start = text.index("John Doe")
    end = start + len("John Doe")
    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: _fake_analyzer_returning("PERSON", start, end))
    redacted, result = redact_pii(text)
    assert "John Doe" not in redacted
    assert "[REDACTED_PERSON]" in redacted
    assert result.redacted is True


def test_redact_pii_handles_both_regex_and_presidio_spans_together(monkeypatch):
    text = "Email jane.doe@example.com or call John Doe directly."
    start = text.index("John Doe")
    end = start + len("John Doe")
    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: _fake_analyzer_returning("PERSON", start, end))
    redacted, result = redact_pii(text)
    assert "jane.doe@example.com" not in redacted
    assert "John Doe" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PERSON]" in redacted
