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

    class FakeAnalyzer:
        def analyze(self, text, language):
            return [FakeEntity()]

    monkeypatch.setattr(pii_scanner, "_get_presidio_analyzer", lambda: FakeAnalyzer())
    result = check_pii("John Smith submitted this claim")
    assert "person" in result.types
