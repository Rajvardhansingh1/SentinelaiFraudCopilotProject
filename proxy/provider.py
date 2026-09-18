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


class GroqProvider:
    """Groq client wrapper. Agents never import this directly (D-002)."""

    model = "openai/gpt-oss-20b"  # ponytail: llama-3.1-8b-instant was retired by Groq; update here if it changes again

    def generate(self, messages: list[Message]) -> LLMResponse:
        start = time.monotonic()
        try:
            from groq import Groq

            client = Groq(api_key=settings.groq_api_key)
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
    """Gemini client wrapper, backup/alternate provider (D-006)."""

    model = "gemini-1.5-flash"

    def generate(self, messages: list[Message]) -> LLMResponse:
        prompt = "\n\n".join(f"{m.role}: {m.content}" for m in messages)
        start = time.monotonic()
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
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


def get_provider() -> Provider:
    return FallbackProvider(GroqProvider(), GeminiProvider())
