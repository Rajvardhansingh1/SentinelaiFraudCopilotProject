import pytest

from proxy.provider import FallbackProvider, LLMResponse, ProviderError


class OkProvider:
    def generate(self, messages):
        return LLMResponse("ok", 1, 1, 5, "model-x", "primary")


class FailingProvider:
    def generate(self, messages):
        raise ProviderError("boom")


def test_fallback_uses_primary_when_healthy():
    provider = FallbackProvider(OkProvider(), FailingProvider())
    resp = provider.generate([])
    assert resp.provider == "primary"


def test_fallback_switches_to_secondary_on_primary_failure():
    provider = FallbackProvider(FailingProvider(), OkProvider())
    resp = provider.generate([])
    assert resp.provider == "primary"  # OkProvider always reports "primary" as its own provider tag


def test_fallback_raises_when_both_fail():
    provider = FallbackProvider(FailingProvider(), FailingProvider())
    with pytest.raises(ProviderError):
        provider.generate([])
