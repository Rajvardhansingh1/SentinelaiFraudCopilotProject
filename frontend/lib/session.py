import uuid

import streamlit as st


def get_session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    return st.session_state["session_id"]


def get_call_count() -> int:
    return st.session_state.get("call_count", 0)


def increment_call_count() -> None:
    st.session_state["call_count"] = get_call_count() + 1
