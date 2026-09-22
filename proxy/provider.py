import time
from typing import Protocol

from proxy.config import settings
from proxy.schemas import Message


class LLMResponse:
    def __init__(self, text: str, tokens_in: int, tokens_out: int, latency_ms: int, model: str, provider: str):
        self.text = text
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.latency_ms = latency_ms
        self.model = model
        self.provider = provider


class Provider(Protocol):
    def generate(self, messages: list[Message]) -> LLMResponse: ...


class ProviderError(Exception):
    pass


class MissingCredentialsError(ProviderError):
    """Raised before any SDK call/import when no API key is available — never
    reaches a network call, so an invalid/missing key can't leak into a
    provider-side error message or log line."""


class GroqProvider:
    """Groq client wrapper. Agents never import this directly (D-002).

    `api_key`: BYOK override (D-041). None means "use the server's own key"
    (`settings.groq_api_key`) — this is the only place a caller-supplied key
    is read; it never gets logged or echoed in a response.
    """

    model = "openai/gpt-oss-20b"  # ponytail: llama-3.1-8b-instant was retired by Groq; update here if it changes again

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def generate(self, messages: list[Message]) -> LLMResponse:
        key = self.api_key or settings.groq_api_key
        if not key:
            raise MissingCredentialsError("No Groq API key configured (set GROQ_API_KEY or pass a BYOK key).")
        start = time.monotonic()
        try:
            from groq import Groq

            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
        except Exception as exc:
            raise ProviderError(f"groq call failed: {exc}") from exc
        latency_ms = int((time.monotonic() - start) * 1000)
        usage = resp.usage
        return LLMResponse(
            text=resp.choices[0].message.content,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
            model=self.model,
            provider="groq",
        )


class GeminiProvider:
    """Gemini client wrapper, backup/alternate provider (D-006). See GroqProvider
    for the `api_key` BYOK contract."""

    model = "gemini-1.5-flash"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def generate(self, messages: list[Message]) -> LLMResponse:
        key = self.api_key or settings.gemini_api_key
        if not key:
            raise MissingCredentialsError("No Gemini API key configured (set GEMINI_API_KEY or pass a BYOK key).")
        prompt = "\n\n".join(f"{m.role}: {m.content}" for m in messages)
        start = time.monotonic()
        try:
            import google.generativeai as genai

            genai.configure(api_key=key)
            client = genai.GenerativeModel(self.model)
            resp = client.generate_content(prompt)
        except Exception as exc:
            raise ProviderError(f"gemini call failed: {exc}") from exc
        latency_ms = int((time.monotonic() - start) * 1000)
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            text=resp.text,
            tokens_in=getattr(usage, "prompt_token_count", 0) if usage else 0,
            tokens_out=getattr(usage, "candidates_token_count", 0) if usage else 0,
            latency_ms=latency_ms,
            model=self.model,
            provider="gemini",
        )


class FallbackProvider:
    """Tries primary, falls back to secondary on ProviderError (D-006)."""

    def __init__(self, primary: Provider, secondary: Provider):
        self.primary = primary
        self.secondary = secondary

    def generate(self, messages: list[Message]) -> LLMResponse:
        try:
            return self.primary.generate(messages)
        except ProviderError:
            return self.secondary.generate(messages)


# Server-side registry of available providers (D-041). Adding a provider means
# adding a class above + one entry here — proxy/main.py never needs to change.
PROVIDER_REGISTRY: dict[str, type[Provider]] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
}


def get_provider() -> Provider:
    """Default provider: Groq-primary/Gemini-fallback using server-side keys.
    Unchanged from pre-BYOK behavior — existing callers/tests are unaffected."""
    return FallbackProvider(GroqProvider(), GeminiProvider())


def build_provider(provider_name: str, api_key: str | None = None) -> Provider:
    """Build a single, non-fallback provider by name (D-041 BYOK path). Raises
    MissingCredentialsError immediately if no key is available — no SDK import,
    no network call, so a missing key can never surface as a confusing upstream
    failure. `provider_name` is always one of PROVIDER_REGISTRY's keys because
    the request schema restricts it to a Literal at validation time."""
    provider_cls = PROVIDER_REGISTRY[provider_name]
    return provider_cls(api_key=api_key)
