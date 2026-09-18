import streamlit as st

from frontend.data.sample_attacks import SAMPLE_ATTACKS, find_cached
from frontend.lib.proxy_client import call_generate
from frontend.lib.session import get_call_count, get_session_id, increment_call_count

MAX_FREE_TEXT_CHARS = 500
QUOTA_BANNER = "quota reached — here's a pre-run example"


def handle_response(status_code: int, body: dict, prompt_id: str | None) -> dict:
    """Pure logic, unit-testable without Streamlit. Returns {"banner", "display"}."""
    if status_code == 429:
        cached = find_cached(prompt_id)
        return {"banner": QUOTA_BANNER, "display": cached}
    return {"banner": None, "display": {"status_code": status_code, **body}}


def render() -> None:
    st.title("SentinelAI Red-Team Playground")
    st.caption("Try to jailbreak the proxy. Every attempt is scanned, scored, and logged in real time.")

    col_used, col_limit = st.columns(2)
    col_used.metric("Calls used this session", get_call_count())
    col_limit.metric("Free-text limit", f"{MAX_FREE_TEXT_CHARS} chars")

    with st.expander("What's the system prompt the attacker is up against?"):
        from frontend.lib.proxy_client import SYSTEM_PROMPT

        st.code(SYSTEM_PROMPT)

    st.divider()

    labels = [a["label"] for a in SAMPLE_ATTACKS]
    choice = st.selectbox("Pick a prewritten attack", ["(free text)"] + labels)

    if choice == "(free text)":
        prompt = st.text_area("Or type your own adversarial prompt", max_chars=MAX_FREE_TEXT_CHARS)
        prompt_id = None
    else:
        attack = next(a for a in SAMPLE_ATTACKS if a["label"] == choice)
        prompt = attack["prompt"]
        prompt_id = attack["id"]
        st.text(prompt)

    if st.button("Submit", type="primary") and prompt:
        session_id = get_session_id()
        with st.spinner("Running through the guardrail pipeline..."):
            status_code, body = call_generate(session_id, prompt)
        increment_call_count()
        result = handle_response(status_code, body, prompt_id)

        if result["banner"]:
            st.warning(result["banner"])

        display = result["display"]
        injection = display.get("guardrails", {}).get("injection", {})
        with st.container(border=True):
            if injection.get("flagged"):
                st.error(f"Blocked — caught by: {', '.join(injection.get('matched_patterns', []))}")
            elif display.get("status_code") == 200:
                st.success("Not caught")
                st.write(display.get("output"))
            else:
                st.info(display.get("error", {}).get("message", "Request failed."))
    elif not prompt:
        st.caption("Pick an attack or write your own, then submit it to see the proxy react.")
