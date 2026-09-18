# agents/ — module conventions

- No agent file imports a provider SDK (`groq`, `google.generativeai`) directly — every LLM call goes through `agents/proxy_client.py::call_proxy()`, which hits SentinelAI's `POST /v1/generate` (D-002). `tests/agents/test_no_direct_provider_calls.py` enforces this statically.
- Forensics (`forensics.py`) never calls the proxy — pure local OpenCV/exifread (D-003).
- State contract lives in `state.py` (`FraudCaseState`), shared by every node and by `graph.py`. Don't duplicate field definitions elsewhere.
- A node never lets an exception escape uncaught — record into `state["errors"]` and continue with `None` for the affected field (CLAUDE.md §11: no silent swallow, but also no crash).
