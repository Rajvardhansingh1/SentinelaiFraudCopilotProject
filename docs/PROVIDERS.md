# SentinelAI Provider Abstraction + BYOK (D-041)

## Provider interface

`proxy/provider.py::Provider` is a `Protocol`:

```python
class Provider(Protocol):
    def generate(self, messages: list[Message]) -> LLMResponse: ...
```

`proxy/main.py` (the security engine) only ever calls `.generate()` on whatever
`Provider` it's handed. It never imports `groq`, `google.generativeai`, or any
other provider SDK directly — those imports live inside each provider class's
own `generate()` method, lazily, so a provider whose package isn't installed
doesn't break the others.

## Request/response abstraction

Every provider returns the same `LLMResponse` regardless of vendor:

```python
LLMResponse(text, tokens_in, tokens_out, latency_ms, model, provider)
```

`proxy/main.py` builds `Usage`/`Guardrails` from this shape only — no
provider-specific branching in the engine.

## Selecting a provider

`GenerateRequest.provider_config` (optional) is a `ProviderConfig`:

```json
{
  "provider": "groq" | "gemini" | null,
  "api_key": "caller-supplied-key" | null
}
```

- **Omitted / `provider: null`** — default behavior, unchanged since before
  D-041: `FallbackProvider(GroqProvider(), GeminiProvider())` using the
  server's own `GROQ_API_KEY`/`GEMINI_API_KEY`. No fallback logic changed.
- **`provider` set** — a single, non-fallback provider is built by name via
  `proxy/provider.py::build_provider(name, api_key)`. If `api_key` is given,
  it's used for that call only (BYOK); otherwise the server's own key for
  that provider is used.

## Credential handling

- A caller-supplied `api_key` is read once, passed straight into the SDK
  client constructor, and never stored, logged, or included in any response.
  `CallLog` (the persisted call record) has no `api_key` column — structurally
  impossible to leak it into the dashboard/logs.
- If no key is available (neither BYOK nor server config) for the requested
  provider, `MissingCredentialsError` is raised **before any SDK import or
  network call** — a missing key can never surface as a confusing upstream
  error.
- Keys are never sent to the browser: `provider_config.api_key` is something a
  server-side caller (an agent, a trusted backend) sends to SentinelAI over
  its own request; SentinelAI's *response* never contains it.

## Error handling

| Error code | Status | Meaning |
|---|---|---|
| `provider_credentials_missing` | 400 | No API key available for the requested provider (client-config error) |
| `provider_failed` | 502 | Key was present but the provider rejected the call (invalid credentials, timeout, any other SDK failure) |

`MissingCredentialsError` is a `ProviderError` subclass, so any code only
catching `ProviderError` still catches it — the more specific 400 branch in
`proxy/main.py::generate()` just runs first.

## Adding a new provider

1. Add a class in `proxy/provider.py` implementing `generate(self, messages) -> LLMResponse`, with an `api_key: str | None = None` constructor param following the `GroqProvider`/`GeminiProvider` pattern (lazy SDK import inside `generate()`, raise `MissingCredentialsError` if no key resolves).
2. Add it to `PROVIDER_REGISTRY`.
3. Add its name to `ProviderConfig.provider`'s `Literal` in `proxy/schemas.py`.

No change to `proxy/main.py` (the security engine) is needed.
