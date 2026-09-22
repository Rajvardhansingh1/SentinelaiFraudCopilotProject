import pytest

from proxy.provider import (
    PROVIDER_REGISTRY,
    FallbackProvider,
    GeminiProvider,
    GroqProvider,
    LLMResponse,
    MissingCredentialsError,
    ProviderError,
    build_provider,
)


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


# --- D-041: provider abstraction + BYOK ---


def test_build_provider_returns_named_registry_class():
    provider = build_provider("groq", api_key="byok-key")
    assert isinstance(provider, GroqProvider)
    assert provider.api_key == "byok-key"


def test_registry_covers_both_known_providers():
    assert set(PROVIDER_REGISTRY) == {"groq", "gemini"}


def test_groq_missing_credentials_raises_before_any_sdk_call(monkeypatch):
    monkeypatch.setattr("proxy.provider.settings.groq_api_key", "")
    provider = GroqProvider()  # no BYOK key, no server key
    with pytest.raises(MissingCredentialsError):
        provider.generate([])


def test_gemini_missing_credentials_raises_before_any_sdk_call(monkeypatch):
    monkeypatch.setattr("proxy.provider.settings.gemini_api_key", "")
    provider = GeminiProvider()
    with pytest.raises(MissingCredentialsError):
        provider.generate([])


def test_byok_key_overrides_empty_server_key(monkeypatch):
    """A caller-supplied key must be usable even when the server has none configured."""
    monkeypatch.setattr("proxy.provider.settings.groq_api_key", "")

    class FakeCompletions:
        def create(self, model, messages):
            class Resp:
                choices = [type("C", (), {"message": type("M", (), {"content": "hi"})()})]
                usage = None

            return Resp()

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("groq.Groq", FakeClient, raising=False)
    provider = GroqProvider(api_key="caller-supplied-key")
    resp = provider.generate([])
    assert resp.text == "hi"


def test_invalid_credentials_wrapped_as_provider_error(monkeypatch):
    """SDK-level rejection (bad key, auth failure) is a ProviderError, distinct
    from MissingCredentialsError (no key at all)."""

    class RejectingClient:
        def __init__(self, api_key):
            raise Exception("401 invalid api key")

    monkeypatch.setattr("groq.Groq", RejectingClient, raising=False)
    provider = GroqProvider(api_key="bad-key")
    with pytest.raises(ProviderError) as exc_info:
        provider.generate([])
    assert not isinstance(exc_info.value, MissingCredentialsError)


def test_provider_timeout_wrapped_as_provider_error(monkeypatch):
    class TimingOutClient:
        def __init__(self, api_key):
            raise TimeoutError("upstream timed out")

    monkeypatch.setattr("groq.Groq", TimingOutClient, raising=False)
    provider = GroqProvider(api_key="some-key")
    with pytest.raises(ProviderError):
        provider.generate([])


def test_credential_never_appears_in_error_message(monkeypatch):
    secret_key = "sk-super-secret-value-12345"

    class RejectingClient:
        def __init__(self, api_key):
            raise Exception("401 unauthorized")

    monkeypatch.setattr("groq.Groq", RejectingClient, raising=False)
    provider = GroqProvider(api_key=secret_key)
    with pytest.raises(ProviderError) as exc_info:
        provider.generate([])
    assert secret_key not in str(exc_info.value)
