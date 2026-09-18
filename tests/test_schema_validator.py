import pytest

from proxy.middleware.schema_validator import SchemaValidationFailed, validate_structured_output


def test_valid_on_first_try():
    validated, retried = validate_structured_output(
        "receipt_fields",
        lambda: '{"vendor": "Acme", "date": "2026-01-01", "line_items": ["pen"], "total": 5.0}',
    )
    assert validated.vendor == "Acme"
    assert retried is False


def test_retries_once_then_succeeds():
    attempts = {"n": 0}

    def getter():
        attempts["n"] += 1
        if attempts["n"] == 1:
            return "not json"
        return '{"vendor": "Acme", "date": null, "line_items": [], "total": null}'

    validated, retried = validate_structured_output("receipt_fields", getter)
    assert retried is True
    assert attempts["n"] == 2


def test_fails_after_one_retry():
    with pytest.raises(SchemaValidationFailed):
        validate_structured_output("receipt_fields", lambda: "still not json")
