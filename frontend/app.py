# RETIRED (D-034/D-038, 2026-09-19): this Streamlit app is no longer the active
# frontend. Use web/ (Next.js) instead — see README.md for how to run it.
# Kept on disk, not deleted, in case of rollback need. Not maintained going forward.

import streamlit as st

from frontend.components import eval_dashboard, redteam_playground, review_screen
from frontend.db.session import init_db as init_frontend_db
from frontend.lib.health_check import ping_proxy

st.set_page_config(page_title="SentinelAI Playground (RETIRED — see web/)", page_icon="🛡️", layout="wide")
init_frontend_db()
st.warning("This Streamlit UI is retired. Use the Next.js app in `web/` instead — see README.md.")

st.sidebar.markdown("## 🛡️ SentinelAI")
st.sidebar.caption("Guardrail proxy + fraud-detection copilot")

if "proxy_awake" not in st.session_state:
    st.session_state["proxy_awake"] = ping_proxy()
if not st.session_state["proxy_awake"]:
    st.info("Waking up the server... this can take ~20-30s on the first request.")

page = st.sidebar.radio(
    "Page",
    ["Red-Team Playground", "Review Receipt", "Eval Dashboard"],
    captions=["Attack the proxy live", "Run the fraud pipeline", "See what's been caught"],
)
st.sidebar.divider()
st.sidebar.caption("Every LLM call is proxied, guardrailed, and logged. Nothing here auto-approves a claim.")

if page == "Red-Team Playground":
    redteam_playground.render()
elif page == "Review Receipt":
    review_screen.render()
else:
    eval_dashboard.render()
