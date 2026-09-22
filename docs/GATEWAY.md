# SentinelAI Runtime Gateway (D-049, phase_dev_upgrade.md Phase 10)

```
Application -> SentinelAI Gateway -> Model
```

A **separate service** (`gateway/`, default port 8002), independent of the
SentinelAI proxy app (`proxy/main.py`), its database, and the dashboard. It
reuses SentinelAI's inspectors and provider layer as a library only.

```bash
python -m uvicorn gateway.main:app --port 8002
```

## Pipeline (`gateway/pipeline.py::run_pipeline`)

1. **Request inspection** — injection detector + PII/secret scanner on
   non-system messages (system prompt is caller-trusted, same as D-033).
2. **Request policy** — injection → BLOCK (403) if `block_on_injection`;
   PII → `allow` / `redact` / `block`.
3. **Provider routing** — `route` names a provider from
   `proxy.provider.PROVIDER_REGISTRY`; omitted = default Groq→Gemini chain.
   Unknown route → 400. Provider failure → 502 (upstream message withheld).
4. **Response inspection** — PII/secret scanner on the model output.
5. **Response policy** — `allow` / `redact` / `block`.
6. **Final decision** — `ALLOW` / `BLOCK` / `ERROR`, with
   `request_modified` / `response_modified` flags.

## Configuration (server-side only, `.env`)

| Setting | Default |
|---|---|
| `GATEWAY_BLOCK_ON_INJECTION` | `true` |
| `GATEWAY_REQUEST_PII_ACTION` | `redact` |
| `GATEWAY_RESPONSE_PII_ACTION` | `redact` |
| `GATEWAY_STORE_RAW_CONTENT` | `false` |
| `GATEWAY_PORT` | `8002` |

## Stateless

No DB, no rate-limit counters, no session memory. Each decision comes from
the request, the policy, and the provider response alone. (Rate limiting
stays a proxy feature; add one at the load balancer if the gateway needs it.)

## Audit events and secret hygiene

Every stage emits one JSON line on logger `sentinelai.gateway.audit`, sharing
a `request_id`: `request_received`, `request_inspected`, `request_policy`,
`provider_called`, `response_inspected`, `final_decision`.

- Content is represented by `{length, sha256}` only — correlatable, not stored.
- `GATEWAY_STORE_RAW_CONTENT=true` adds raw text, **with secrets redacted first**.
- Provider error messages (which can echo keys) never reach the response or logs.
- The gateway never accepts, returns, or logs a provider credential.

## Endpoint

`POST /v1/gateway/chat` — `{messages, route?, application?}` →
`{request_id, decision, reason, output, provider, model, request_inspection,
response_inspection, request_modified, response_modified}`.

## Known limit

Redaction replaces regex-detected types (email, phone, card, api_key). If
Presidio is installed, extra NER types (e.g. person names) are *detected*
and reported but not redacted — `block` is the safe setting if that matters.
